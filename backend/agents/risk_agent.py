def assess_risk(data: dict) -> dict:
    """
    Rule-based risk scoring agent. 
    Takes dataset rows and calculates a Caution Score.
    """
    score = 0
    reasons = []
    
    violations = data.get("violations", [])
    bedbugs = data.get("bedbug_reports", [])
    
    num_haz = 0
    num_imm_haz = 0
    for v in violations:
        v_class = str(v.get("class", "")).upper()
        if v_class == 'B':
            num_haz += 1
            score += 2
        elif v_class == 'C':
            num_imm_haz += 1
            score += 4
            
    if num_imm_haz > 0:
        reasons.append(f"{num_imm_haz} immediately hazardous (Class C) violations")
    if num_haz > 0:
        reasons.append(f"{num_haz} hazardous (Class B) violations")
        
    if len(bedbugs) > 0:
        score += 3
        reasons.append(f"Recent bedbug reporting found on record")
        
    caution_level = "Low"
    if score >= 5:
        caution_level = "High"
    elif score >= 2:
        caution_level = "Moderate"
        
    return {
        "score": score,
        "caution_level": caution_level,
        "reasons": reasons
    }
