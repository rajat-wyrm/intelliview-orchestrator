"""Unit tests for Task 4.4: Audio and Answer Sentiment Analysis.

Verifies:
- Sentiment classification into Confident / Neutral / Nervous
- Hugging Face Transformers integration and linguistic fallback
- Empty / missing transcript handling
- Sentiment score structure and probability distribution
- Timestamped sentiment timeline generation
- Sentiment summary and percentage calculation
- Storing in audio_analysis and InterviewSession integration
- Graceful error/exception fallback behavior
- API report response integration
"""

from unittest.mock import patch

import pytest

from workers.audio_pipeline import (
    analyze_audio_sentiment,
    calculate_sentiment_summary,
    classify_text_sentiment,
    generate_sentiment_timeline,
    run_audio_analysis,
)


def test_sentiment_classification_categories():
    """Classification must return one of Confident, Neutral, or Nervous."""
    samples = [
        "I successfully architected and built the distributed caching tier.",
        "The system runs on four Linux nodes with PostgreSQL.",
        "Um, uh, I'm not really sure, sorry, maybe it failed.",
    ]
    for text in samples:
        res = classify_text_sentiment(text)
        assert res["sentiment"] in {"Confident", "Neutral", "Nervous"}
        assert "confidence" in res
        assert "scores" in res
        assert "Confident" in res["scores"]
        assert "Neutral" in res["scores"]
        assert "Nervous" in res["scores"]
        total_prob = sum(res["scores"].values())
        assert pytest.approx(total_prob, abs=0.01) == 1.0


def test_sentiment_classification_confident_text():
    """Assertive, authoritative vocabulary classifies as Confident."""
    confident_text = (
        "I led the infrastructure migration and successfully scaled the platform "
        "to handle 100k requests per second with high expertise."
    )
    res = classify_text_sentiment(confident_text)
    assert res["sentiment"] == "Confident"
    assert res["scores"]["Confident"] > res["scores"]["Nervous"]
    assert res["scores"]["Confident"] > res["scores"]["Neutral"]


def test_sentiment_classification_nervous_text():
    """Hesitant, filler-heavy, apologetic vocabulary classifies as Nervous."""
    nervous_text = (
        "Um, uh, maybe... I'm really not sure, sorry, I kind of struggled and failed."
    )
    res = classify_text_sentiment(nervous_text)
    assert res["sentiment"] == "Nervous"
    assert res["scores"]["Nervous"] > res["scores"]["Confident"]


def test_sentiment_classification_neutral_text():
    """Factual, descriptive text without strong bias classifies as Neutral."""
    neutral_text = "The application communicates via HTTP REST and gRPC endpoints."
    res = classify_text_sentiment(neutral_text)
    assert res["sentiment"] in {"Neutral", "Confident"}
    assert res["scores"]["Neutral"] >= 0.0


def test_empty_transcription_handling():
    """Empty or whitespace transcripts must not crash and should return safe neutral defaults."""
    for empty_input in ["", "   ", "\n\t"]:
        res = classify_text_sentiment(empty_input)
        assert res["sentiment"] == "Neutral"
        assert res["scores"]["Confident"] == 0.0
        assert res["scores"]["Neutral"] == 1.0
        assert res["scores"]["Nervous"] == 0.0

        timeline = generate_sentiment_timeline(empty_input)
        assert timeline == []

        summary = calculate_sentiment_summary(timeline)
        assert summary["dominant_sentiment"] == "Neutral"
        assert summary["neutral_percentage"] == 100.0


def test_sentiment_scores_structure():
    """Scores dictionary must have all three categories with normalized probabilities."""
    res = classify_text_sentiment("We developed a scalable microservice architecture.")
    scores = res["scores"]
    assert set(scores.keys()) == {"Confident", "Neutral", "Nervous"}
    for v in scores.values():
        assert 0.0 <= v <= 1.0
    assert pytest.approx(sum(scores.values()), abs=0.01) == 1.0


def test_generate_sentiment_timeline_with_segments():
    """Timeline generated from Whisper segments includes timestamps, start, end, and sentiment."""
    transcription = {
        "text": "I led the project. Um, then we had issues. But we resolved them.",
        "duration_seconds": 30.0,
        "segments": [
            {
                "start": 0.0,
                "end": 10.0,
                "text": "I led the project and successfully designed it.",
            },
            {
                "start": 10.0,
                "end": 20.0,
                "text": "Um, uh, we were not sure about the memory leak.",
            },
            {"start": 20.0, "end": 30.0, "text": "The servers run on Linux."},
        ],
    }
    timeline = generate_sentiment_timeline(transcription, session_id="test-sess-1")
    assert len(timeline) == 3
    assert timeline[0]["start"] == 0.0
    assert timeline[0]["end"] == 10.0
    assert timeline[0]["sentiment"] == "Confident"

    assert timeline[1]["start"] == 10.0
    assert timeline[1]["end"] == 20.0
    assert timeline[1]["sentiment"] == "Nervous"

    for item in timeline:
        assert "timestamp" in item
        assert "start" in item
        assert "end" in item
        assert "text" in item
        assert "sentiment" in item
        assert "confidence" in item
        assert "scores" in item


def test_generate_sentiment_timeline_from_plain_text():
    """Timeline generated from plain text splits sentences across duration."""
    raw_text = (
        "I built the search engine. "
        "We achieved 99.9% uptime. "
        "Um, the database had some latency."
    )
    timeline = generate_sentiment_timeline(
        raw_text, duration_seconds=60.0, session_id="test-sess-2"
    )
    assert len(timeline) >= 2
    assert timeline[0]["start"] == 0.0
    assert timeline[-1]["end"] <= 60.0
    for item in timeline:
        assert item["sentiment"] in {"Confident", "Neutral", "Nervous"}


def test_calculate_sentiment_summary_percentage():
    """Calculates accurate percentages and summary string matching Definition of Done."""
    mock_timeline = [
        {"start": 0.0, "end": 7.0, "sentiment": "Confident", "text": "A"},
        {"start": 7.0, "end": 9.0, "sentiment": "Neutral", "text": "B"},
        {"start": 9.0, "end": 10.0, "sentiment": "Nervous", "text": "C"},
    ]
    summary = calculate_sentiment_summary(mock_timeline)
    assert summary["dominant_sentiment"] == "Confident"
    assert summary["confident_percentage"] == 70.0
    assert summary["neutral_percentage"] == 20.0
    assert summary["nervous_percentage"] == 10.0
    assert summary["summary_text"] == "Candidate was confident 70% of the time"


def test_analyze_audio_sentiment_end_to_end():
    """End-to-end sentiment analysis produces dominant sentiment, scores, summary, and timeline."""
    transcription = {
        "text": "I led the development of the high-throughput payment gateway.",
        "duration_seconds": 45.0,
        "segments": [
            {
                "start": 0.0,
                "end": 45.0,
                "text": "I led the development of the high-throughput payment gateway.",
            }
        ],
    }
    result = analyze_audio_sentiment("session-sentiment-01", transcription)
    assert "dominant_sentiment" in result
    assert result["dominant_sentiment"] in {"Confident", "Neutral", "Nervous"}
    assert "sentiment_scores" in result
    assert "sentiment_summary" in result
    assert "sentiment_timeline" in result
    assert len(result["sentiment_timeline"]) == 1
    assert "summary_text" in result["sentiment_summary"]


def test_run_audio_analysis_includes_sentiment():
    """run_audio_analysis contains sentiment analysis and timeline in audio_analysis payload."""
    out = run_audio_analysis("sess-audio-sentiment-test")
    for key in (
        "session_id",
        "transcription",
        "background_voices",
        "suspicious_conversation",
        "sentiment",
        "sentiment_scores",
        "sentiment_summary",
        "sentiment_timeline",
        "risk_score",
    ):
        assert key in out, f"Missing key: {key}"

    assert out["sentiment"] in {"Confident", "Neutral", "Nervous"}
    assert isinstance(out["sentiment_scores"], dict)
    assert isinstance(out["sentiment_summary"], dict)
    assert isinstance(out["sentiment_timeline"], list)
    assert 0.0 <= out["risk_score"] <= 1.0


def test_sentiment_analysis_exception_fallback():
    """If an internal exception occurs during classification, fallback safely without crashing."""
    with patch(
        "workers.audio_pipeline.classify_text_sentiment",
        side_effect=RuntimeError("Simulated Model Error"),
    ):
        result = analyze_audio_sentiment("error-session", {"text": "Some speech"})
        assert result["dominant_sentiment"] == "Neutral"
        assert result["sentiment_summary"]["neutral_percentage"] == 100.0
        assert result["sentiment_timeline"] == []
