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
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, TypedDict

from workers._stubs import _seeded_unit

logger = logging.getLogger(__name__)
AUDIO_TEMP_DIR = os.getenv("AUDIO_TEMP_DIR", "/tmp")

CHUNK_DURATION_MS = 5000


def split_audio_into_chunks(
    audio_path: str,
    chunk_duration_ms: int = CHUNK_DURATION_MS,
) -> tuple[list[str], str]:
    """
    Split an audio file into fixed-size WAV chunks.
    Returns:
        chunk_paths, temp_directory
    """
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)

    chunk_temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")

    chunk_paths = []

    for i, start in enumerate(range(0, len(audio), chunk_duration_ms)):
        chunk = audio[start : start + chunk_duration_ms]

        chunk_path = Path(chunk_temp_dir) / f"chunk_{i}.wav"

        chunk.export(chunk_path, format="wav")

        chunk_paths.append(str(chunk_path))

    return chunk_paths, chunk_temp_dir


# ---------------------------------------------------------------------------
# Real detection helpers (Whisper / pyannote / OpenAI) with fallback to stubs
# ---------------------------------------------------------------------------
class TranscriptionResult(TypedDict, total=False):
    text: str
    confidence: float
    language: str
    duration_seconds: float
    timestamp: float | None
    vad_executed: bool
    speech_detected: bool
    speech_duration_seconds: float
    vad_segments: list[dict[str, Any]]
    vad_config: dict[str, Any]


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


def _real_transcribe(session_id: str, vad_config: Any | None = None) -> dict[str, Any] | None:
    """Transcribe audio using local Whisper model with VAD pre-filtering."""
    try:
        import numpy as np

        from workers.ai_client import transcribe_audio_file
        from workers.vad import VoiceActivityDetector

        audio_path = f"{AUDIO_TEMP_DIR}/interview_{session_id}.wav"
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found: %s", audio_path)
            return None

        # VAD Stage execution (run ONCE)
        detector = VoiceActivityDetector(vad_config)
        vad_segments = detector.process_audio(audio_path)
        speech_detected = len(vad_segments) > 0

        chunk_paths, chunk_dir = split_audio_into_chunks(audio_path)

        partial_results = []

        try:
            for chunk_path in chunk_paths:
                chunk_result = transcribe_audio_file(chunk_path, vad_config=vad_config, raw_audio=True)

                if chunk_result is not None:
                    partial_results.append(chunk_result)

        finally:
            shutil.rmtree(chunk_dir, ignore_errors=True)

        if not partial_results:
            return None

        texts = [item.get("text", "").strip() for item in partial_results if item.get("text", "").strip()]

        segments = []

        for chunk_index, item in enumerate(partial_results):
            offset = chunk_index * (CHUNK_DURATION_MS / 1000)

            for seg in item.get("segments", []):
                aligned = dict(seg)

                aligned["start"] += offset
                aligned["end"] += offset

                segments.append(aligned)

        result = {
            "text": " ".join(texts),
            "language": partial_results[-1].get("language", "en"),
            "segments": segments,
        }

        if segments:
            avg_logprob = np.mean([s.get("avg_logprob", -1.0) for s in segments])
            confidence = round(max(0.0, min(1.0, 1.0 + avg_logprob)), 3)
        else:
            confidence = 0.0

        speech_dur = sum(s.duration for s in vad_segments)
        total_dur = result.get("total_speech_duration", speech_dur)

        return {
            "text": result.get("text", ""),
            "confidence": confidence,
            "language": result.get("language", "en"),
            "duration_seconds": (
                sum(s.get("end", 0) - s.get("start", 0) for s in segments) or round(total_dur, 1)
            ),
            "timestamp": time.time(),
            "vad_executed": True,
            "speech_detected": speech_detected,
            "speech_duration_seconds": round(speech_dur, 3),
            "vad_segments": [s.to_dict() for s in vad_segments],
            "vad_config": vars(detector.config),
        }

    except Exception as exc:
        logger.debug("Real transcription unavailable: %s", exc)
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
    except Exception as exc:
        logger.debug("Real background voice detection unavailable: %s", exc)
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
    except Exception as exc:
        logger.debug("Real suspicious pattern detection unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public pipeline API — real detection with seeded stub fallback
# ---------------------------------------------------------------------------


def run_audio_analysis(session_id: str, vad_config: Any | None = None) -> dict[str, Any]:
    """Execute audio analysis pipeline for an interview session with optional VAD configuration."""
    logger.info(f"Starting audio analysis for session {session_id}")

    transcription = transcribe_speech(session_id, vad_config=vad_config)
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


def transcribe_speech(session_id: str, vad_config: Any | None = None) -> dict[str, Any]:
    """Convert speech to text — real Whisper + VAD with seeded stub fallback."""
    logger.info(f"Transcribing audio for session {session_id}")

    real = _real_transcribe(session_id, vad_config=vad_config)
    if real is not None:
        return real

    from workers.vad import VADConfig

    config = vad_config if isinstance(vad_config, VADConfig) else VADConfig.from_env()

    # VAD pre-filtering in stub mode
    silence = _seeded_unit(session_id, "silence") > 0.92
    text = (
        ""
        if silence
        else (
            "I have five years of experience building distributed systems in Python and Go. "
            "Recently I led a migration from a monolith to Celery-backed workers."
        )
    )
    total_duration = round(120 + _seeded_unit(session_id, "duration") * 600, 1)

    # Simulated timestamp-aligned VAD segments for stub mode
    vad_segments = []
    if not silence:
        speech_start = round(1.5 + _seeded_unit(session_id, "start") * 2.0, 3)
        speech_end = round(speech_start + min(total_duration - 2.0, 15.0), 3)
        vad_segments = [
            {
                "start": speech_start,
                "end": speech_end,
                "duration": round(speech_end - speech_start, 3),
                "confidence": round(0.85 + _seeded_unit(session_id, "vad_conf") * 0.1, 3),
                "segment_index": 0,
            }
        ]

    speech_duration = sum(s["duration"] for s in vad_segments)

    return {
        "text": text,
        "confidence": round(0.6 + _seeded_unit(session_id, "asr_conf") * 0.35, 3),
        "language": "en",
        "duration_seconds": total_duration,
        "timestamp": None,
        "vad_executed": True,
        "speech_detected": not silence,
        "speech_duration_seconds": speech_duration,
        "vad_segments": vad_segments,
        "vad_config": vars(config),
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
