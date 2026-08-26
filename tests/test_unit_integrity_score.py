import pytest
from workers.integrity_score import IntegrityScorer


def test_integrity_score_perfect():
    # No penalties
    score = IntegrityScorer.calculate_integrity_score(
        tab_switches=0, cv_flags=0, risk_score=0.0
    )
    assert score == 100


def test_integrity_score_missing_data():
    # Missing data should not penalize
    score = IntegrityScorer.calculate_integrity_score()
    assert score == 100

    score_partial = IntegrityScorer.calculate_integrity_score(tab_switches=2)
    assert score_partial == 90  # 100 - (2*5)


def test_integrity_score_tab_switches():
    # 3 tab switches = 15 penalty
    assert IntegrityScorer.calculate_integrity_score(tab_switches=3) == 85
    # Max tab switch penalty is 20
    assert IntegrityScorer.calculate_integrity_score(tab_switches=10) == 80


def test_integrity_score_cv_flags():
    # 2 cv flags = 20 penalty
    assert IntegrityScorer.calculate_integrity_score(cv_flags=2) == 80
    # Max cv flag penalty is 30
    assert IntegrityScorer.calculate_integrity_score(cv_flags=5) == 70


def test_integrity_score_risk_engine():
    # risk_score 0.5 = 25 penalty
    assert IntegrityScorer.calculate_integrity_score(risk_score=0.5) == 75
    # Max risk score penalty is 50
    assert IntegrityScorer.calculate_integrity_score(risk_score=1.0) == 50
    # Out of bounds risk score should be clamped
    assert IntegrityScorer.calculate_integrity_score(risk_score=1.5) == 50


def test_integrity_score_combined():
    # tab_switches(2)=10, cv_flags(1)=10, risk_score(0.2)=10 => total penalty 30 => score 70
    score = IntegrityScorer.calculate_integrity_score(
        tab_switches=2, cv_flags=1, risk_score=0.2
    )
    assert score == 70


def test_integrity_score_zero_bound():
    # Ensure score doesn't drop below 0
    # max penalty: tab(20) + cv(30) + risk(50) = 100 -> score 0
    score = IntegrityScorer.calculate_integrity_score(
        tab_switches=10, cv_flags=10, risk_score=1.0
    )
    assert score == 0
