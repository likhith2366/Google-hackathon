from google import genai
from pydantic import BaseModel, Field
import json

class AddressSchema(BaseModel):
    house_number: str = Field(description="The numeric house or building number (e.g., '125', '22', '3333C'). ALWAYS KEEP any trailing letters if spoken or typed (e.g. '3333C' remains '3333C'). Do NOT remove letters.")
    street_name: str = Field(description="The name of the street. MUST expand abbreviations (e.g., 'St' to 'STREET', 'Ave' to 'AVENUE', 'Rd' to 'ROAD'). Do not include the house number here.")
    borough: str = Field(description="The NYC borough in UPPERCASE: MANHATTAN, BROOKLYN, QUEENS, BRONX, or STATEN ISLAND.")

def extract_address(query: str, api_key: str) -> AddressSchema:
    """Uses Gemini with few-shot prompting to accurately extract and normalize NYC addresses."""
    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "You are an elite address parsing pipeline for NYC Open Data. "
        "You must extract the house number, street name, and borough from rough or messy spoken text. "
        "CRITICAL RULES: \n"
        "1. Expand all street suffixes (St -> STREET, Ave -> AVENUE, Pl -> PLACE). \n"
        "2. If no borough is mentioned, but the query mentions an NYC neighborhood (like Astoria), infer the borough (QUEENS). \n"
        "3. Only return valid JSON matching the schema."
    )
    
    prompt = f"""
    Example 1:
    Input: "Check 1 25 Example St, Brooklyn. Any red flags before I sign?"
    Output: {{"house_number": "125", "street_name": "EXAMPLE STREET", "borough": "BROOKLYN"}}
    
    Example 2:
    Input: "Hey I'm looking at twenty two front avenue in Manhattan"
    Output: {{"house_number": "22", "street_name": "FRONT AVENUE", "borough": "MANHATTAN"}}
    
    Now process this voice query:
    Input: "{query}"
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'system_instruction': system_instruction,
            'response_mime_type': 'application/json',
            'response_schema': AddressSchema,
            'temperature': 0.1
        },
    )
    return response.parsed
