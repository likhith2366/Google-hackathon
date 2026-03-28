from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Import agents and services
from services.data_lookup import lookup_address
from agents.risk_agent import assess_risk
from agents.address_agent import extract_address
from agents.explainer_agent import generate_summary

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

@app.post("/analyze")
async def analyze_building(request: QueryRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable not set")
        
    try:
        # 1. Address Extraction Agent
        address_parsed = extract_address(request.query, api_key)
        full_address = f"{address_parsed.house_number} {address_parsed.street_name}, {address_parsed.borough}"
        
        # 2. Data Retrieval (Pandas Lookup)
        building_data = lookup_address(
            housenumber=address_parsed.house_number,
            streetname=address_parsed.street_name,
            borough=address_parsed.borough
        )
        
        # 3. Risk Assessment Agent
        risk_profile = assess_risk(building_data)
        
        # 4. Explainer Agent
        summary = generate_summary(risk_profile, full_address, api_key)
        
        return {
            "address": full_address,
            "parsed": address_parsed.model_dump(),
            "risk_profile": risk_profile,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
