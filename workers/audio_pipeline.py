"""
Audio Analysis Pipeline
Handles speech and audio monitoring

Responsibilities:
- Speech-to-text using Whisper
- Background voice detection
- Suspicious conversation detection

Pluggable contract — replace each detection helper with a real model
(Whisper, Wav2Vec2, pyannote, etc.). The provided defaults produce
deterministic per-session signals so end-to-end risk scoring and the
HIGH/CRITICAL thresholds fire correctly without GPU dependencies.
"""

import logging
import os
import time
from typing import Any, TypedDict

from workers._stubs import _seeded_unit

logger = logging.getLogger(__name__)
AUDIO_TEMP_DIR = os.getenv("AUDIO_TEMP_DIR", "/tmp")


# ---------------------------------------------------------------------------
# Real detection helpers (Whisper / pyannote / OpenAI) with fallback to stubs
# ---------------------------------------------------------------------------
class TranscriptionResult(TypedDict):
    text: str
    confidence: float
    language: str
    duration_seconds: float
    timestamp: float | None


class BackgroundVoiceResult(TypedDict):
    background_voices_detected: bool
    voice_count: int
    confidence: float
    speaker_segments: list[dict[str, Any]]
    timestamps: list[dict[str, Any]]


class SuspiciousPatternResult(TypedDict):
    suspicious_pattern_detected: bool
    pattern_type: str | None
    confidence: float
    details: dict[str, Any]


class AudioAnalysisResult(TypedDict):
    session_id: str
    transcription: TranscriptionResult
    background_voices: BackgroundVoiceResult
    suspicious_conversation: SuspiciousPatternResult
    risk_score: float


def _get_audio_duration(audio_path: str, segments: list[dict[str, Any]]) -> float:
    """Return the true duration of the audio file, in seconds.

    Fix for #43: the old implementation summed each transcript segment's
    (end - start), which is total *spoken* time, not the audio file's
    actual duration. That silently drops any silence/pauses between
    segments and falls back to a hardcoded 120.0 when there are no
    segments at all (e.g. a silent recording).

    This reads the real duration from the .wav file header instead, which
    is accurate regardless of speech/silence patterns. If the file can't
    be read for some reason, it falls back to the last segment's end
    timestamp (max, not sum) as a best-effort estimate, and only returns
    0.0 if there's truly nothing to go on.
    """
    try:
        import wave

        with wave.open(audio_path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if rate:
                return round(frames / float(rate), 2)
    except Exception as exc:
        logger.debug("Could not read audio duration for %s: %s", audio_path, exc)

    if segments:
        return round(max(s.get("end", 0) for s in segments), 2)

    return 0.0


def _real_transcribe(session_id: str) -> dict[str, Any] | None:
    """Transcribe audio using local Whisper model."""
    try:
        import numpy as np

        from workers.ai_client import transcribe_audio_file

        audio_path = f"{AUDIO_TEMP_DIR}/interview_{session_id}.wav"
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found: %s", audio_path)
            return None
        result = transcribe_audio_file(audio_path)
        segments = result.get("segments", [])
        if segments:
            avg_logprob = np.mean([s.get("avg_logprob", -1.0) for s in segments])

            confidence = round(
                max(0.0, min(1.0, 1.0 + avg_logprob)),
                3,
            )
        else:
            confidence = 0.0

        logger.info(
            "avg_logprob=%s, confidence=%s",
            avg_logprob,
            confidence,
        )

        return {
            "text": result.get("text", ""),
            "confidence": confidence,
            "language": result.get("language", "en"),
            "duration_seconds": _get_audio_duration(audio_path, result.get("segments", [])),
            "timestamp": time.time(),
        }

    except ImportError:
        logger.info("Whisper not installed, using stub fallback")
        return None

    except FileNotFoundError:
        logger.warning(
            "Audio file not found for session %s",
            session_id,
        )
        return None

    except Exception as exc:
        logger.warning(
            "Real transcription failed for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
    return None


def _real_detect_background_voices(session_id: str) -> dict[str, Any] | None:
    """Detect background voices using pyannote speaker diarisation."""
    try:
        from workers.ai_client import detect_speaker_segments

        audio_path = f"{AUDIO_TEMP_DIR}/interview_{session_id}.wav"
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found: %s", audio_path)
            return None
        segments = detect_speaker_segments(audio_path)
        if segments is None:
            return None
        speaker_ids = {s["speaker_id"] for s in segments}
        voice_count = len(speaker_ids)
        return {
            "background_voices_detected": voice_count > 1,
            "voice_count": voice_count,
            "confidence": 0.85,
            "speaker_segments": segments,
            "timestamps": [
                {
                    "speaker": s["speaker_id"],
                    "start": s["start"],
                    "end": s["end"],
                }
                for s in segments
            ],
        }
    except ImportError:
        logger.info("pyannote not installed, using stub fallback")
        return None

    except FileNotFoundError:
        logger.warning(
            "Audio file not found for session %s",
            session_id,
        )
        return None

    except Exception as exc:
        logger.warning(
            "Real background voice detection failed for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        return None


def _real_detect_suspicious(session_id: str) -> dict[str, Any] | None:
    """Use an LLM to detect suspicious conversation patterns."""
    try:
        from workers.ai_client import chat_completion

        result = _real_transcribe(session_id)
        text = result.get("text", "") if result else ""
        if not text:
            return None

        response = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an interview integrity analyst. Analyze the following "
                        "transcribed interview response and detect suspicious patterns: "
                        "reading from script, robotic/unnatural responses, inconsistent "
                        "knowledge, or possible use of AI assistants. Return a JSON object "
                        "with keys: suspicious (bool), pattern_type (str or null), "
                        "confidence (float 0-1), details (object)."
                    ),
                },
                {"role": "user", "content": text},
            ],
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=512,
        )
        if response is None:
            return None

        import json

        try:
            parsed = json.loads(response)
            return {
                "suspicious_pattern_detected": parsed.get("suspicious", False),
                "pattern_type": parsed.get("pattern_type"),
                "confidence": round(parsed.get("confidence", 0.5), 3),
                "details": parsed.get("details", {}),
                "timestamp": time.time(),
            }
        except (json.JSONDecodeError, KeyError):
            return None
    except ImportError:
        logger.info("LLM client not installed, using stub fallback")
        return None

    except FileNotFoundError:
        logger.warning(
            "Audio file not found for session %s",
            session_id,
        )
        return None

    except Exception as exc:
        logger.warning(
            "Real suspicious pattern detection failed for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Public pipeline API — real detection with seeded stub fallback
# ---------------------------------------------------------------------------


def run_audio_analysis(session_id: str) -> dict[str, Any]:
    """Execute audio analysis pipeline for an interview session."""
    logger.info(f"Starting audio analysis for session {session_id}")

    transcription = transcribe_speech(session_id)
    bg_voices = detect_background_voices(session_id)
    suspicious = detect_suspicious_conversation(session_id)

    results = {
        "session_id": session_id,
        "transcription": transcription,
        "background_voices": bg_voices,
        "suspicious_conversation": suspicious,
        "risk_score": 0.0,
    }

    results["risk_score"] = calculate_audio_risk_score(results)
    logger.info(f"Audio analysis completed for session {session_id}: {results}")
    return results


def transcribe_speech(session_id: str) -> dict[str, Any]:
    """Convert speech to text — real Whisper with seeded stub fallback."""
    logger.info(f"Transcribing audio for session {session_id}")

    real = _real_transcribe(session_id)
    if real is not None:
        return real

    silence = _seeded_unit(session_id, "silence") > 0.92
    text = (
        ""
        if silence
        else (
            "I have five years of experience building distributed systems in Python and Go. "
            "Recently I led a migration from a monolith to Celery-backed workers."
        )
    )
    return {
        "text": text,
        "confidence": round(0.6 + _seeded_unit(session_id, "asr_conf") * 0.35, 3),
        "language": "en",
        "duration_seconds": round(120 + _seeded_unit(session_id, "duration") * 600, 1),
        "timestamp": None,
    }


def detect_background_voices(session_id: str) -> dict[str, Any]:
    """Detect background voices — real diarisation with seeded stub fallback."""
    logger.info(f"Detecting background voices for session {session_id}")

    real = _real_detect_background_voices(session_id)
    if real is not None:
        return real

    multi = _seeded_unit(session_id, "bg_voices") > 0.85
    return {
        "background_voices_detected": multi,
        "voice_count": 2 if multi else 1,
        "confidence": round(_seeded_unit(session_id, "bg_conf"), 3),
        "timestamps": [],
    }


def detect_suspicious_conversation(session_id: str) -> dict[str, Any]:
    """Detect suspicious patterns — real LLM analysis with seeded stub fallback."""
    logger.info(f"Detecting suspicious conversations for session {session_id}")

    real = _real_detect_suspicious(session_id)
    if real is not None:
        return real

    suspicious = _seeded_unit(session_id, "suspicious") > 0.80
    pattern = (
        "robotic_response" if suspicious and _seeded_unit(session_id, "p1") > 0.5 else "reading_from_script"
    )
    return {
        "suspicious_pattern_detected": suspicious,
        "pattern_type": pattern if suspicious else None,
        "confidence": round(_seeded_unit(session_id, "susp_conf"), 3),
        "details": {},
    }


def calculate_audio_risk_score(results: dict[str, Any]) -> float:
    """Calculate a 0–1 risk score from audio detection results."""
    from workers.risk_engine import RiskScoringEngine

    score = 0.0
    if results.get("background_voices", {}).get("background_voices_detected"):
        score += RiskScoringEngine.AUDIO_FACTORS["background_voices"]
    if results.get("suspicious_conversation", {}).get("suspicious_pattern_detected"):
        score += RiskScoringEngine.AUDIO_FACTORS["suspicious_pattern"]
    if not results.get("transcription", {}).get("text"):
        score += RiskScoringEngine.AUDIO_FACTORS["no_transcription"]
    return round(min(score, 1.0), 3)
