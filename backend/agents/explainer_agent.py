from google import genai
import re

def clean_for_tts(text: str) -> str:
    """Strip all markdown so text sounds natural when spoken aloud."""
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'[-•]\s+', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def generate_summary(risk_data: dict, address: str, api_key: str) -> str:
    """
    For the WEB CHATBOT — rich, formatted text with markdown is fine.
    """
    client = genai.Client(api_key=api_key)

    score      = risk_data['score']
    caution    = risk_data['caution_level']
    violations = risk_data.get('violation_count', 0)
    bedbugs    = risk_data.get('bedbug_count', 0)
    complaints = risk_data.get('complaint_count', 0)
    reasons    = risk_data.get('reasons', [])
    questions  = risk_data.get('questions_to_ask', [])

    reasons_text  = "\n".join([f"- {r}" for r in reasons]) if reasons else "No major red flags found."
    question_text = "\n".join([f"- {q}" for q in questions]) if questions else ""

    system_instruction = (
        "You are an NYC housing assistant for renters. "
        "You are writing a response for a web chatbot — markdown formatting is welcome. "
        "Be clear, structured, and empathetic. "
        "Use bold for key terms and bullet points for lists."
    )

    prompt = f"""
    Address: {address}
    Caution Level: {caution} (score: {score})
    Violations: {violations} | Bedbug Reports: {bedbugs} | Complaints: {complaints}
    Key Findings:
    {reasons_text}
    Questions to ask the landlord:
    {question_text}

    Write a helpful 4-6 sentence summary for this renter.
    Start with the caution level. List key findings. End with landlord questions.
    Use markdown formatting freely.
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={'system_instruction': system_instruction, 'temperature': 0.3}
    )
    return response.text


def generate_voice_summary(risk_data: dict, address: str, api_key: str) -> str:
    """
    For PHONE CALLS and VOICE AGENTS — plain spoken English only, no markdown.
    """
    client = genai.Client(api_key=api_key)

    score      = risk_data['score']
    caution    = risk_data['caution_level']
    violations = risk_data.get('violation_count', 0)
    bedbugs    = risk_data.get('bedbug_count', 0)
    complaints = risk_data.get('complaint_count', 0)
    reasons    = risk_data.get('reasons', [])
    questions  = risk_data.get('questions_to_ask', [])

    reasons_text  = ". ".join(reasons) if reasons else "No major red flags found."
    question_text = questions[0] if questions else "Ask the landlord about any upcoming repairs."

    system_instruction = (
        "You are Alex, a friendly NYC housing assistant speaking on the phone. "
        "STRICT RULES: No asterisks. No bullet points. No dashes. No markdown of any kind. "
        "Write only plain spoken English sentences. Sound warm and natural like a knowledgeable friend. "
        "Mention the exact violation count, bedbug count, and complaint count clearly in your response."
    )

    prompt = f"""
    Address: {address}
    Caution Level: {caution} (score: {score})
    Violations: {violations} | Bedbug Reports: {bedbugs} | Complaints: {complaints}
    Key findings: {reasons_text}
    Top question to ask: {question_text}

    Write a 4 to 5 sentence spoken response.
    Start with the caution level. Mention all counts. Explain the biggest concern simply.
    End with the one question they should ask their landlord.
    Plain spoken sentences only. No markdown at all.
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={'system_instruction': system_instruction, 'temperature': 0.3}
    )
    return clean_for_tts(response.text)
