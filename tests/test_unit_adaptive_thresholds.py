"""
Unit tests for Adaptive Risk Scoring Thresholds.
"""

from unittest.mock import patch

from workers.adaptive_thresholds import (
    AdaptiveThresholdManager,
    FixedThresholdStrategy,
    HistoricalRiskStore,
    MovingAverageThresholdStrategy,
    PercentileThresholdStrategy,
    RiskThresholds,
    RollingWindowThresholdStrategy,
    calculate_quantile,
)
from workers.risk_engine import RiskScoringEngine, adaptive_threshold_manager


def test_risk_thresholds_clamping_and_validation():
    # Normal values
    t = RiskThresholds(low=0.2, medium=0.5, high=0.7)
    assert t.low == 0.2
    assert t.medium == 0.5
    assert t.high == 0.7
    assert t.as_dict() == {"low": 0.2, "medium": 0.5, "high": 0.7}

    # Out of range / inverted values should be clamped cleanly
    t_clamped = RiskThresholds(low=-0.1, medium=0.4, high=1.5)
    assert t_clamped.low == 0.0
    assert t_clamped.medium == 0.4
    assert t_clamped.high == 1.0


def test_calculate_quantile():
    data = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    assert calculate_quantile([], 0.5) == 0.0
    assert calculate_quantile([0.5], 0.5) == 0.5
    assert calculate_quantile(data, 0.0) == 0.1
    assert calculate_quantile(data, 1.0) == 1.0
    # 50th percentile (median) between index 4.5
    assert abs(calculate_quantile(data, 0.5) - 0.55) < 1e-6


def test_fixed_threshold_strategy():
    strategy = FixedThresholdStrategy(low=0.25, medium=0.55, high=0.75)
    fallback = RiskThresholds(0.3, 0.6, 0.8)
    t = strategy.calculate_thresholds([0.1, 0.9], fallback)
    assert t.low == 0.25
    assert t.medium == 0.55
    assert t.high == 0.75


def test_percentile_threshold_strategy():
    strategy = PercentileThresholdStrategy(low_percentile=0.60, medium_percentile=0.85, high_percentile=0.95)
    fallback = RiskThresholds(0.3, 0.6, 0.8)

    # Empty scores -> fallback
    assert strategy.calculate_thresholds([], fallback) == fallback

    # Distribution of 20 scores from 0.0 to 0.95
    scores = [i * 0.05 for i in range(20)]  # 0.0, 0.05, ..., 0.95
    t = strategy.calculate_thresholds(scores, fallback)

    assert 0.0 <= t.low < t.medium < t.high <= 1.0
    # 60th percentile of 20 values (idx 11.4) -> ~0.57
    assert t.low > 0.4
    assert t.medium > t.low
    assert t.high > t.medium


def test_moving_average_threshold_strategy():
    strategy = MovingAverageThresholdStrategy(low_std_mult=0.0, medium_std_mult=1.0, high_std_mult=2.0)
    fallback = RiskThresholds(0.3, 0.6, 0.8)

    assert strategy.calculate_thresholds([], fallback) == fallback

    scores = [0.2, 0.4, 0.6, 0.8]  # mean = 0.5, std ~ 0.2236
    t = strategy.calculate_thresholds(scores, fallback)

    assert abs(t.low - 0.5) < 1e-2
    assert t.medium > t.low
    assert t.high > t.medium


def test_rolling_window_threshold_strategy():
    inner = PercentileThresholdStrategy(0.50, 0.80, 0.90)
    strategy = RollingWindowThresholdStrategy(inner, window_size=5)
    fallback = RiskThresholds(0.3, 0.6, 0.8)

    # 10 scores: first 5 are low (0.1), last 5 are high (0.8)
    scores = [0.1, 0.1, 0.1, 0.1, 0.1, 0.8, 0.8, 0.8, 0.8, 0.8]
    t = strategy.calculate_thresholds(scores, fallback)

    # Window of last 5 scores are all 0.8
    assert t.low >= 0.79


def test_historical_risk_store():
    store = HistoricalRiskStore()
    store.clear()

    store.record_score("session-1", 0.25)
    store.record_score("session-2", 0.75)

    scores = store.get_scores()
    assert scores == [0.25, 0.75]

    limited = store.get_scores(limit=1)
    assert limited == [0.75]


def test_adaptive_threshold_manager_min_samples_fallback():
    store = HistoricalRiskStore()
    store.clear()

    manager = AdaptiveThresholdManager(
        store=store,
        strategy_name="percentile",
        min_samples=5,
        fixed_low=0.3,
        fixed_medium=0.6,
        fixed_high=0.8,
    )

    # Record 3 scores (< min_samples 5) -> returns fallback
    for i in range(3):
        manager.record_and_update(f"s-{i}", 0.2)

    current = manager.get_current_thresholds()
    assert current == RiskThresholds(0.3, 0.6, 0.8)


def test_adaptive_threshold_manager_dynamic_update():
    store = HistoricalRiskStore()
    store.clear()

    manager = AdaptiveThresholdManager(
        store=store,
        strategy_name="percentile",
        min_samples=5,
        fixed_low=0.3,
        fixed_medium=0.6,
        fixed_high=0.8,
        low_percentile=0.60,
        medium_percentile=0.85,
        high_percentile=0.95,
    )

    # Record 10 scores
    scores_to_add = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.8, 0.9]
    for idx, s in enumerate(scores_to_add):
        manager.record_and_update(f"s-{idx}", s)

    thresholds = manager.get_current_thresholds()
    assert thresholds.low != 0.3 or thresholds.medium != 0.6
    assert 0.0 <= thresholds.low < thresholds.medium < thresholds.high <= 1.0


def test_risk_scoring_engine_classify_risk_adaptive_and_backward_compatible():
    # 1. Custom thresholds object
    custom_t = RiskThresholds(low=0.2, medium=0.4, high=0.7)
    assert RiskScoringEngine.classify_risk(0.1, thresholds=custom_t) == "LOW"
    assert RiskScoringEngine.classify_risk(0.3, thresholds=custom_t) == "MEDIUM"
    assert RiskScoringEngine.classify_risk(0.5, thresholds=custom_t) == "HIGH"
    assert RiskScoringEngine.classify_risk(0.8, thresholds=custom_t) == "CRITICAL"

    # 2. Custom dict thresholds
    dict_t = {"low": 0.2, "medium": 0.4, "high": 0.7}
    assert RiskScoringEngine.classify_risk(0.1, thresholds=dict_t) == "LOW"

    # 3. Static fallback (when adaptive disabled)
    with patch.dict("workers.risk_engine.RISK_CONFIG", {"adaptive_thresholds_enabled": False}):
        assert RiskScoringEngine.classify_risk(0.0) == "LOW"
        assert RiskScoringEngine.classify_risk(0.29) == "LOW"
        assert RiskScoringEngine.classify_risk(0.3) == "MEDIUM"
        assert RiskScoringEngine.classify_risk(0.59) == "MEDIUM"
        assert RiskScoringEngine.classify_risk(0.6) == "HIGH"
        assert RiskScoringEngine.classify_risk(0.79) == "HIGH"
        assert RiskScoringEngine.classify_risk(0.8) == "CRITICAL"


def test_generate_risk_report_includes_thresholds():
    adaptive_threshold_manager.store.clear()

    report = RiskScoringEngine.generate_risk_report(
        "s100",
        {"face_detected": {"faces_found": True}},
        {"transcription": {"text": "hello"}},
        {
            "answer_quality_score": {"overall_quality_score": 80},
            "technical_accuracy": {"accuracy_score": 80},
            "communication_clarity": {"clarity_score": 80},
        },
    )

    assert report["session_id"] == "s100"
    assert "thresholds_used" in report
    assert "low" in report["thresholds_used"]
    assert "medium" in report["thresholds_used"]
    assert "high" in report["thresholds_used"]
