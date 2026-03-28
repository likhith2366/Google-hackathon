from google import genai
from pydantic import BaseModel, Field
import json

class AddressSchema(BaseModel):
    house_number: str = Field(description="The house number of the building")
    street_name: str = Field(description="The street name of the building without the house number")
    borough: str = Field(description="The NYC borough (MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN ISLAND)")

def extract_address(query: str, api_key: str) -> AddressSchema:
    """Uses Gemini to extract structured address data from user request."""
    client = genai.Client(api_key=api_key)
    prompt = f"Extract the NYC address from this spoken query: '{query}'"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': AddressSchema,
            'temperature': 0.1
        },
    )
    return response.parsed
