from workers.risk_engine import RiskDecisionTree


def test_multiple_persons_returns_critical():
    video = {
        "multiple_persons": {"multiple_persons_detected": True},
        "face_detected": {"faces_found": True},
        "phone_detected": {"phone_detected": False},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {
        "background_voices": {"background_voices_detected": False},
        "suspicious_conversation": {"suspicious_pattern_detected": False},
    }

    evaluation = {}

    assert RiskDecisionTree.classify(video, audio, evaluation) == "CRITICAL"


def test_no_face_returns_high():
    video = {
        "multiple_persons": {"multiple_persons_detected": False},
        "face_detected": {"faces_found": False},
        "phone_detected": {"phone_detected": False},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {}
    evaluation = {}

    assert RiskDecisionTree.classify(video, audio, evaluation) == "HIGH"


def test_phone_detected_returns_high():
    video = {
        "multiple_persons": {"multiple_persons_detected": False},
        "face_detected": {"faces_found": True},
        "phone_detected": {"phone_detected": True},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {}
    evaluation = {}

    assert RiskDecisionTree.classify(video, audio, evaluation) == "HIGH"


def test_background_voice_and_conversation_returns_high():
    video = {
        "multiple_persons": {"multiple_persons_detected": False},
        "face_detected": {"faces_found": True},
        "phone_detected": {"phone_detected": False},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {
        "background_voices": {"background_voices_detected": True},
        "suspicious_conversation": {"suspicious_pattern_detected": True},
    }

    evaluation = {}

    assert RiskDecisionTree.classify(video, audio, evaluation) == "HIGH"


def test_background_voice_only_returns_medium():
    video = {
        "multiple_persons": {"multiple_persons_detected": False},
        "face_detected": {"faces_found": True},
        "phone_detected": {"phone_detected": False},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {
        "background_voices": {"background_voices_detected": True},
        "suspicious_conversation": {"suspicious_pattern_detected": False},
    }

    evaluation = {}

    assert RiskDecisionTree.classify(video, audio, evaluation) == "MEDIUM"


def test_low_quality_returns_medium():
    video = {
        "multiple_persons": {"multiple_persons_detected": False},
        "face_detected": {"faces_found": True},
        "phone_detected": {"phone_detected": False},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {}

    evaluation = {
        "answer_quality_score": {"overall_quality_score": 30},
        "technical_accuracy": {"accuracy_score": 80},
        "communication_clarity": {"clarity_score": 80},
    }

    assert RiskDecisionTree.classify(video, audio, evaluation) == "MEDIUM"


def test_clean_interview_returns_low():
    video = {
        "multiple_persons": {"multiple_persons_detected": False},
        "face_detected": {"faces_found": True},
        "phone_detected": {"phone_detected": False},
        "head_movement_suspicious": {"suspicious_movement_detected": False},
    }

    audio = {
        "background_voices": {"background_voices_detected": False},
        "suspicious_conversation": {"suspicious_pattern_detected": False},
    }

    evaluation = {
        "answer_quality_score": {"overall_quality_score": 80},
        "technical_accuracy": {"accuracy_score": 90},
        "communication_clarity": {"clarity_score": 95},
    }

    assert RiskDecisionTree.classify(video, audio, evaluation) == "LOW"
