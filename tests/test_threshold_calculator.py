from workers.threshold_calculator import AdaptiveThresholdCalculator


def test_default_thresholds():

    thresholds = AdaptiveThresholdCalculator.get_thresholds()

    assert "low" in thresholds
    assert "medium" in thresholds
    assert "high" in thresholds

    assert thresholds["low"] < thresholds["medium"]
    assert thresholds["medium"] < thresholds["high"]