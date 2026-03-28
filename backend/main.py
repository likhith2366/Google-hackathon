from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Gather
from pydantic import BaseModel
import os
import json
from dotenv import load_dotenv

load_dotenv()

from services.data_lookup import lookup_address
from agents.risk_agent import assess_risk
from agents.address_agent import extract_address
from agents.explainer_agent import generate_summary
from agents.property_agent import find_nearby_properties
from twilio.rest import Client as TwilioClient


def send_findings_sms(to_number: str, result: dict):
    """Send a full findings report via SMS to the caller."""
    try:
        account_sid  = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token   = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number  = os.environ.get("TWILIO_PHONE_NUMBER")

        if not all([account_sid, auth_token, from_number]):
            print("Twilio SMS credentials missing — skipping SMS")
            return

        risk     = result["risk_profile"]
        address  = result["address"]
        caution  = risk["caution_level"]
        score    = risk["score"]
        v        = risk["violation_count"]
        b        = risk["bedbug_count"]
        c        = risk["complaint_count"]
        reasons  = "\n".join([f"- {r}" for r in risk.get("reasons", [])])
        questions = "\n".join([f"- {q}" for q in risk.get("questions_to_ask", [])])

        message = (
            f"Before You Sign - Report\n"
            f"========================\n"
            f"Address: {address}\n"
            f"Caution: {caution} (Score: {score})\n\n"
            f"Violations: {v}\n"
            f"Bedbug Reports: {b}\n"
            f"Complaints: {c}\n\n"
            f"Findings:\n{reasons}\n\n"
            f"Ask your landlord:\n{questions}"
        )

        client = TwilioClient(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{to_number}"
        )
        print(f"SMS sent to {to_number}")

    except Exception as e:
        print(f"SMS error: {e}")

app = FastAPI(title="BeforeYouSign NYC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str


# ─── Core analysis logic (shared by all routes) ─────────────────────────────

def run_analysis(query: str, api_key: str) -> dict:
    address_parsed = extract_address(query, api_key)
    full_address   = f"{address_parsed.house_number} {address_parsed.street_name}, {address_parsed.borough}"
    building_data  = lookup_address(
        housenumber=address_parsed.house_number,
        streetname=address_parsed.street_name,
        borough=address_parsed.borough
    )
    risk_profile   = assess_risk(building_data)
    summary        = generate_summary(risk_profile, full_address, api_key)
    return {
        "address":      full_address,
        "parsed":       address_parsed.model_dump(),
        "risk_profile": risk_profile,
        "summary":      summary
    }


# ─── REST endpoint (used by web frontend) ────────────────────────────────────

@app.post("/analyze")
async def analyze_building(request: QueryRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_goes_here":
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    try:
        return run_analysis(request.query, api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Twilio voice routes ──────────────────────────────────────────────────────

@app.post("/twilio/incoming")
async def twilio_incoming():
    response = VoiceResponse()
    gather   = Gather(input='speech', action='/twilio/process', timeout=5, speechTimeout='auto')
    gather.say(
        "Hi! I'm Alex, your Before You Sign assistant. "
        "Tell me any NYC address and I'll check it for violations, bedbugs, and complaints. "
        "Go ahead.",
        voice='Polly.Joanna'   # US English female — sounds more natural than default
    )
    response.append(gather)
    # If no speech detected, loop back
    response.redirect('/twilio/incoming')
    return Response(content=str(response), media_type="application/xml")


@app.post("/twilio/process")
async def twilio_process(request: Request):
    api_key   = os.environ.get("GEMINI_API_KEY")
    form_data = await request.form()
    spoken    = form_data.get("SpeechResult", "").strip()

    response  = VoiceResponse()

    if not api_key or api_key == "your_api_key_goes_here":
        response.say("Sorry, the API key is missing. Please check the backend setup.", voice='Polly.Joanna')
        return Response(content=str(response), media_type="application/xml")

    if not spoken:
        gather = Gather(input='speech', action='/twilio/process', timeout=5, speechTimeout='auto')
        gather.say("I didn't catch that. Which NYC address would you like me to check?", voice='Polly.Joanna')
        response.append(gather)
        response.redirect('/twilio/incoming')
        return Response(content=str(response), media_type="application/xml")

    try:
        result  = run_analysis(spoken, api_key)
        summary = result["summary"]

        # Speak the full summary
        response.say(summary, voice='Polly.Joanna')

        # Keep the conversation going
        gather = Gather(input='speech', action='/twilio/process', timeout=5, speechTimeout='auto')
        gather.say("Is there another address you'd like me to check? Just say it now.", voice='Polly.Joanna')
        response.append(gather)
        response.redirect('/twilio/incoming')

    except Exception as e:
        print(f"Error processing '{spoken}': {e}")
        response.say(
            "I'm sorry, I had trouble looking up that address. "
            "Please try again with the house number, street name, and borough.",
            voice='Polly.Joanna'
        )
        gather = Gather(input='speech', action='/twilio/process', timeout=5, speechTimeout='auto')
        gather.say("Which address should I check?", voice='Polly.Joanna')
        response.append(gather)

    return Response(content=str(response), media_type="application/xml")


# ─── Vapi end-of-call webhook — sends WhatsApp summary after call ends ────────

@app.post("/vapi/end-call")
async def vapi_end_call(request: Request):
    body         = await request.json()
    message      = body.get("message", {})
    msg_type     = message.get("type", "")

    if msg_type != "end-of-call-report":
        return JSONResponse({"status": "ignored"})

    caller_number = message.get("call", {}).get("customer", {}).get("number", "")
    transcript    = message.get("transcript", "")

    print(f"Call ended. Caller: {caller_number}")
    print(f"Transcript snippet: {transcript[:200]}")

    # Extract last address from transcript and send summary
    if caller_number and transcript:
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            result  = run_analysis(transcript, api_key)
            send_findings_sms(caller_number or "+19297911358", result)
        except Exception as e:
            print(f"End-of-call SMS error: {e}")

    return JSONResponse({"status": "ok"})


# ─── Vapi tool-call webhook (for human-quality voice with interruptions) ─────

@app.post("/")
async def vapi_tool_root(request: Request):
    return await vapi_tool(request)

@app.post("/vapi/tool")
async def vapi_tool(request: Request):
    api_key = os.environ.get("GEMINI_API_KEY")
    body    = await request.json()

    try:
        tool_calls = body.get("message", {}).get("toolCalls", [])
        if not tool_calls:
            return JSONResponse({"results": [{"result": "No tool call received."}]})

        call    = tool_calls[0]
        call_id = call.get("id", "")
        raw_args = call.get("function", {}).get("arguments", {})
        args     = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)
        query   = args.get("query", "")

        if not query:
            return JSONResponse({
                "results": [{"toolCallId": call_id, "result": "Please provide an address to look up."}]
            })

        result  = run_analysis(query, api_key)
        summary = result["summary"]

        # Send SMS with full findings to the caller
        caller_number = body.get("message", {}).get("call", {}).get("customer", {}).get("number", "") or "+19297911358"
        print(f"Sending SMS to: {caller_number}")
        send_findings_sms(caller_number, result)

        return JSONResponse({
            "results": [{"toolCallId": call_id, "result": summary}]
        })

    except Exception as e:
        print(f"Vapi tool error: {e}")
        return JSONResponse({
            "results": [{"result": f"Error looking up address: {str(e)}"}]
        })


# ─── Vapi tool: find nearby properties (rent or buy) ─────────────────────────

@app.post("/vapi/properties")
async def vapi_properties(request: Request):
    body = await request.json()
    try:
        tool_calls = body.get("message", {}).get("toolCalls", [])
        if not tool_calls:
            return JSONResponse({"results": [{"result": "No tool call received."}]})

        call     = tool_calls[0]
        call_id  = call.get("id", "")
        raw_args = call.get("function", {}).get("arguments", {})
        args     = raw_args if isinstance(raw_args, dict) else json.loads(raw_args)

        address       = args.get("address", "")
        preference    = args.get("preference", "rent")
        caller_number = body.get("message", {}).get("call", {}).get("customer", {}).get("number", "")

        if not address:
            return JSONResponse({
                "results": [{"toolCallId": call_id, "result": "Please provide an address to search near."}]
            })

        result = find_nearby_properties(address, preference, caller_number)
        return JSONResponse({
            "results": [{"toolCallId": call_id, "result": result}]
        })

    except Exception as e:
        print(f"Vapi properties error: {e}")
        return JSONResponse({
            "results": [{"result": f"Sorry, I had trouble finding nearby properties: {str(e)}"}]
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
