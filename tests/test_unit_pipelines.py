"""Unit tests for the AI pipeline stubs.

These verify the pluggable contracts still hold: each pipeline returns the
shape the RiskScoringEngine consumes, and the seeded deterministic outputs
let end-to-end risk classification thresholds fire.
"""

from workers.audio_pipeline import (
    calculate_audio_risk_score,
    detect_background_voices,
    detect_suspicious_conversation,
    run_audio_analysis,
    transcribe_speech,
)
from workers.evaluation_pipeline import (
    evaluate_answer_quality,
    evaluate_answers,
    evaluate_communication,
    evaluate_technical_accuracy,
    generate_feedback,
)
from workers.video_pipeline import (
    calculate_video_risk_score,
    detect_face,
    detect_mobile_phone,
    detect_multiple_persons,
    detect_suspicious_head_movement,
    run_video_analysis,
)


def test_video_pipeline_runs_end_to_end():
    out = run_video_analysis("abc123")
    for key in (
        "session_id",
        "face_detected",
        "head_movement_suspicious",
        "phone_detected",
        "multiple_persons",
        "risk_score",
    ):
        assert key in out
    assert 0.0 <= out["risk_score"] <= 1.0


def test_video_pipeline_is_deterministic_per_session():
    a = run_video_analysis("session-X")
    b = run_video_analysis("session-X")
    assert a == b


def test_audio_pipeline_returns_expected_shape():
    out = run_audio_analysis("s-audio")
    for key in (
        "session_id",
        "transcription",
        "background_voices",
        "suspicious_conversation",
        "risk_score",
    ):
        assert key in out
    assert 0.0 <= out["risk_score"] <= 1.0


def test_audio_pipeline_variation_across_sessions():
    samples = {run_audio_analysis(f"sess-{i}")["risk_score"] for i in range(20)}
    assert len(samples) > 1, "Expected deterministic-but-varied outputs"


def test_evaluation_pipeline_returns_inverse_risk():
    out = evaluate_answers("s-eval")
    assert 0.0 <= out["risk_score"] <= 1.0
    assert "answer_quality_score" in out
    assert "feedback" in out


def test_video_risk_accumulates_signals():
    high_risk_input = {
        "face_detected": {"faces_found": False},
        "head_movement_suspicious": {"suspicious_movement_detected": True},
        "phone_detected": {"phone_detected": True},
        "multiple_persons": {"multiple_persons_detected": True},
    }
    score = calculate_video_risk_score(high_risk_input)
    assert score >= 0.9  # multiple + phone + movement + no_face -> clamped at 1.0


def test_audio_risk_handles_empty_transcription():
    out = {
        "transcription": {"text": ""},
        "background_voices": {"background_voices_detected": False},
        "suspicious_conversation": {"suspicious_pattern_detected": False},
    }
    assert calculate_audio_risk_score(out) >= 0.3


def test_helper_functions_return_dicts():
    for fn, sid in [
        (detect_face, "x"),
        (detect_suspicious_head_movement, "x"),
        (detect_mobile_phone, "x"),
        (detect_multiple_persons, "x"),
        (transcribe_speech, "x"),
        (detect_background_voices, "x"),
        (detect_suspicious_conversation, "x"),
        (evaluate_answer_quality, "x"),
        (evaluate_technical_accuracy, "x"),
        (evaluate_communication, "x"),
        (generate_feedback, "x"),
    ]:
        assert isinstance(fn(sid), dict)


def test_audio_pipeline_temp_file_cleanup():
    import os
    import sys
    from unittest.mock import MagicMock, patch
    from workers.audio_pipeline import AUDIO_TEMP_DIR, run_audio_analysis

    # Setup a mock/dummy audio file at the legacy path
    session_id = "test-session-cleanup-123"
    legacy_file_path = os.path.join(AUDIO_TEMP_DIR, f"interview_{session_id}.wav")

    # Ensure the directory exists
    os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
    with open(legacy_file_path, "wb") as f:
        f.write(b"mock audio bytes")

    assert os.path.exists(legacy_file_path)

    # Mock dependencies to bypass real AI model invocation.
    mock_numpy = MagicMock()
    mock_transcribe = MagicMock(return_value={"text": "Hello world", "language": "en", "segments": []})
    mock_diarization = MagicMock(return_value=[])

    original_numpy = sys.modules.get("numpy")
    sys.modules["numpy"] = mock_numpy

    try:
        with patch("workers.ai_client.transcribe_audio_file", mock_transcribe), \
             patch("workers.ai_client.detect_speaker_segments", mock_diarization), \
             patch("workers.ai_client.HAS_WHISPER", True):

            result = run_audio_analysis(session_id)

            # Check that transcribe_audio_file was indeed called on the temporary copy
            assert mock_transcribe.call_count == 2
            called_path = mock_transcribe.call_args_list[0][0][0]

            # The path should NOT be the legacy path
            assert called_path != legacy_file_path
            assert "interview_test-session-cleanup-123_" in called_path
            assert called_path.endswith(f"interview_{session_id}.wav")

            # The temporary directory and file should no longer exist after the run
            temp_dir = os.path.dirname(called_path)
            assert not os.path.exists(temp_dir)
            assert not os.path.exists(called_path)

            # The legacy path should also be cleaned up automatically upon successful completion
            assert not os.path.exists(legacy_file_path)

            # The return shape and contents should still be correct
            assert result["session_id"] == session_id
            assert result["transcription"]["text"] == "Hello world"

    finally:
        # Restore sys.modules['numpy']
        if original_numpy is not None:
            sys.modules["numpy"] = original_numpy
        else:
            sys.modules.pop("numpy", None)

        # Clean up legacy file if it still exists
        if os.path.exists(legacy_file_path):
            try:
                os.remove(legacy_file_path)
            except Exception:
                pass

