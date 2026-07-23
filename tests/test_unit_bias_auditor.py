from workers.bias_auditor import ALERT_THRESHOLD, REVIEW_THRESHOLD, BiasAuditor


def test_threshold_constants_are_defined_for_fairness_audits():
    assert REVIEW_THRESHOLD == 0.1
    assert ALERT_THRESHOLD == 0.2
    assert BiasAuditor.REVIEW_THRESHOLD == REVIEW_THRESHOLD
    assert BiasAuditor.ALERT_THRESHOLD == ALERT_THRESHOLD


def test_analyze_scoring_consistency_detects_group_gap():
    auditor = BiasAuditor(db_session=None)
    evaluations = [
        {"candidate_id": "c1", "score": 0.9, "gender": "female"},
        {"candidate_id": "c2", "score": 0.8, "gender": "female"},
        {"candidate_id": "c3", "score": 0.5, "gender": "male"},
        {"candidate_id": "c4", "score": 0.4, "gender": "male"},
    ]

    result = auditor.analyze_scoring_consistency(evaluations, "gender")

    assert result["demographic_attribute"] == "gender"
    assert result["fairness_gap"] > 0.2
    assert result["status"] in {"REVIEW", "ALERT"}
    assert result["groups"]["female"]["average_score"] > result["groups"]["male"]["average_score"]


def test_analyze_scoring_consistency_reports_pass_when_scores_are_balanced():
    auditor = BiasAuditor(db_session=None)
    evaluations = [
        {"candidate_id": "c1", "score": 0.8, "gender": "female"},
        {"candidate_id": "c2", "score": 0.75, "gender": "female"},
        {"candidate_id": "c3", "score": 0.78, "gender": "male"},
        {"candidate_id": "c4", "score": 0.74, "gender": "male"},
    ]

    result = auditor.analyze_scoring_consistency(evaluations, "gender")

    assert result["status"] == "PASS"
    assert result["fairness_gap"] <= 0.1
    assert result["recommendations"] == []
