def assess_risk(data: dict) -> dict:
    """
    Expert housing risk scoring engine.
    Calculates caution scores from violations, bedbugs, and complaints.
    Generates specific follow-up questions for the renter to ask the landlord.
    """
    score = 0
    reasons = []
    landlord_questions = []

    violations  = data.get("violations", [])
    bedbugs     = data.get("bedbug_reports", [])
    complaints  = data.get("complaints", [])

    # --- Violations scoring (HPD Classes A / B / C) ---
    num_haz      = 0  # Class B
    num_imm_haz  = 0  # Class C

    for v in violations:
        v_class = str(v.get("class", "")).upper()
        if v_class == 'B':
            num_haz += 1
            score += 2
        elif v_class == 'C':
            num_imm_haz += 1
            score += 4

    if num_imm_haz > 0:
        reasons.append(f"{num_imm_haz} immediately hazardous (Class C) violation(s) on record.")
        landlord_questions.append(
            "Can you provide HPD documentation proving the recent Class C (immediately hazardous) "
            "violations have been fully corrected and closed?"
        )

    if num_haz > 0:
        reasons.append(f"{num_haz} hazardous (Class B) violation(s) reported.")
        if not landlord_questions:
            landlord_questions.append(
                "When were the open Class B violations last addressed, and do you have the HPD "
                "inspection sign-off to confirm they're resolved?"
            )

    # --- Bedbug scoring ---
    if len(bedbugs) > 0:
        score += 3
        total_infested = sum(
            int(b.get("infested_dwelling_unit_count", 0) or 0) for b in bedbugs
        )
        reasons.append(
            f"Bedbug history found — {total_infested} infested unit(s) reported across "
            f"{len(bedbugs)} filing period(s)."
        )
        landlord_questions.append(
            "Given the bedbug history on file, can you share documentation of the last certified "
            "pest-eradication treatment and confirm no active infestation exists?"
        )

    # --- Complaints scoring (open/active complaints) ---
    open_complaints = [
        c for c in complaints
        if str(c.get("complaint_status", "")).upper() in ("OPEN", "PENDING")
    ]
    if len(open_complaints) > 0:
        score += min(len(open_complaints), 5)  # cap contribution at 5 pts
        # find the top category
        cats = [c.get("major_category", "Unknown") for c in open_complaints]
        top_cat = max(set(cats), key=cats.count)
        reasons.append(
            f"{len(open_complaints)} open complaint(s) filed with 311, most commonly about: {top_cat}."
        )
        landlord_questions.append(
            f"There are {len(open_complaints)} open 311 complaints — especially around {top_cat}. "
            "What steps are being taken to resolve them before the lease is signed?"
        )
    elif len(complaints) > 0:
        # resolved complaints — mild note
        reasons.append(f"{len(complaints)} past complaint(s) found (all resolved).")

    # --- Final caution level ---
    if not reasons:
        reasons.append("No major red flags found in recent HPD records.")
        landlord_questions.append(
            "Are there any upcoming major repairs or capital projects planned for the building "
            "or specifically for my unit?"
        )

    caution_level = "Low"
    if score >= 8:
        caution_level = "High"
    elif score >= 3:
        caution_level = "Moderate"

    return {
        "score":           score,
        "caution_level":   caution_level,
        "reasons":         reasons,
        "questions_to_ask": landlord_questions[:3],  # top 3 max
        "violation_count": len(violations),
        "bedbug_count":    len(bedbugs),
        "complaint_count": len(complaints),
    }
