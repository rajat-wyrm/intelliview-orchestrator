from workers.risk_engine import RiskScoringEngine


def test_dynamic_classification_low():
    thresholds = {
        "low": 0.30,
        "medium": 0.60,
        "high": 0.80,
    }

    assert (
        RiskScoringEngine.classify_risk_dynamic(
            0.20,
            thresholds,
        )
        == "LOW"
    )


def test_dynamic_classification_medium():
    thresholds = {
        "low": 0.30,
        "medium": 0.60,
        "high": 0.80,
    }

    assert (
        RiskScoringEngine.classify_risk_dynamic(
            0.50,
            thresholds,
        )
        == "MEDIUM"
    )


def test_dynamic_classification_high():
    thresholds = {
        "low": 0.30,
        "medium": 0.60,
        "high": 0.80,
    }

    assert (
        RiskScoringEngine.classify_risk_dynamic(
            0.70,
            thresholds,
        )
        == "HIGH"
    )


def test_dynamic_classification_critical():
    thresholds = {
        "low": 0.30,
        "medium": 0.60,
        "high": 0.80,
    }

    assert (
        RiskScoringEngine.classify_risk_dynamic(
            0.95,
            thresholds,
        )
        == "CRITICAL"
    )