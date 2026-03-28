from app.services.risk_service import compute_risk


def test_high_on_two_class_c():
    rp = compute_risk([{"class": "C"}, {"class": "C"}], [])
    assert rp.caution_level == "High"
    assert rp.score == 8


def test_moderate_on_one_class_b():
    rp = compute_risk([{"class": "B"}], [])
    assert rp.caution_level == "Moderate"
    assert rp.score == 2


def test_low_on_empty():
    rp = compute_risk([], [])
    assert rp.caution_level == "Low"
    assert rp.score == 0


def test_litigation_adds_score():
    rp = compute_risk([], [{"case_id": "1"}])
    assert rp.score == 3
    assert "litigation" in rp.reasons[0].lower()


def test_combined_c_and_litigation_is_high():
    rp = compute_risk([{"class": "C"}], [{"case_id": "1"}])
    assert rp.caution_level == "High"
    assert rp.score == 7
