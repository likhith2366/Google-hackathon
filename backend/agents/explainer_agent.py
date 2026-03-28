from google import genai

def generate_summary(risk_data: dict, address: str, api_key: str) -> str:
    """Uses Gemini to generate a plain-English spoken summary of the risk."""
    client = genai.Client(api_key=api_key)
    
    score = risk_data['score']
    caution = risk_data['caution_level']
    reasons = "\n".join([f"- {r}" for r in risk_data['reasons']])
    
    system_instruction = (
        "You are an AI assistant helping a renter understand building risks in NYC. "
        "Keep the summary brief, conversational, punchy, and under 3 sentences for text-to-speech playback."
    )
    
    prompt = f"""
    Address: {address}
    Caution Level: {caution} (Caution Score: {score})
    Top Reasons for caution level: 
    {reasons if reasons else "No major red flags found."}
    
    Generate a strictly short spoken-audio script to summarize this to the renter.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'system_instruction': system_instruction,
            'temperature': 0.3
        }
    )
    return response.text
