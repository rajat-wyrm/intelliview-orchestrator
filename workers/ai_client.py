"""
AI Client Module
Provides pluggable clients for OpenAI, Whisper, and MediaPipe/OpenCV
with automatic fallback to mocks when API keys or libraries are absent.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature detection — import optional dependencies at module level so the
# rest of the codebase can branch on `HAS_OPENAI`, `HAS_WHISPER`, etc.
# ---------------------------------------------------------------------------

try:
    from openai import OpenAI

    _openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if _openai_api_key:
        openai_client = OpenAI(api_key=_openai_api_key)
        HAS_OPENAI = True
        logger.info("OpenAI client initialised (API key detected)")
    else:
        openai_client = None
        HAS_OPENAI = False
        logger.info("No OPENAI_API_KEY — OpenAI client unavailable")
except ImportError:
    openai_client = None
    HAS_OPENAI = False
    logger.info("openai package not installed — OpenAI client unavailable")

try:
    import google.generativeai as genai

    _gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if _gemini_api_key:
        genai.configure(api_key=_gemini_api_key)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        HAS_GEMINI = True
        logger.info("Gemini client initialised (API key detected)")
    else:
        gemini_model = None
        HAS_GEMINI = False
        logger.info("No GEMINI_API_KEY — Gemini client unavailable")
except ImportError:
    gemini_model = None
    HAS_GEMINI = False
    logger.info("google-generativeai not installed — Gemini client unavailable")

try:
    from openai import OpenAI as GrokClient

    _grok_api_key = os.getenv("GROK_API_KEY", "")
    if _grok_api_key:
        grok_client = GrokClient(
            api_key=_grok_api_key,
            base_url="https://api.x.ai/v1",
        )
        HAS_GROK = True
        logger.info("Grok client initialised (API key detected)")
    else:
        grok_client = None
        HAS_GROK = False
        logger.info("No GROK_API_KEY — Grok client unavailable")
except ImportError:
    grok_client = None
    HAS_GROK = False
    logger.info("openai package not installed — Grok client unavailable")

try:
    import whisper  # type: ignore

    whisper_model_name = os.getenv("WHISPER_MODEL", "base")
    whisper_model = whisper.load_model(whisper_model_name)
    HAS_WHISPER = True
    logger.info("Whisper model loaded: %s", whisper_model_name)
except Exception:
    whisper_model = None
    HAS_WHISPER = False
    logger.info("Whisper not available — falling back to mock STT")

try:
    import cv2
    import mediapipe as mp  # type: ignore

    HAS_MEDIAPIPE = True
    logger.info("MediaPipe + OpenCV available")
except ImportError:
    HAS_MEDIAPIPE = False
    logger.info("MediaPipe/OpenCV not installed — falling back to mock face detection")


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str | None:
    """Send a chat completion request; returns the assistant text or None."""
    if not HAS_OPENAI:
        return None
    try:
        resp = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning("OpenAI chat completion failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------


def gemini_generate(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> str | None:
    """Generate text using Gemini; returns the text or None."""
    if not HAS_GEMINI:
        return None
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return response.text
    except Exception as exc:
        logger.warning("Gemini generation failed: %s", exc)
        return None


def gemini_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> str | None:
    """Multi-turn chat with Gemini; returns the response text or None."""
    if not HAS_GEMINI:
        return None
    try:
        chat = gemini_model.start_chat(history=[])
        for msg in messages:
            if msg["role"] == "user":
                chat.send_message(msg["content"])
            elif msg["role"] == "assistant":
                pass
        return chat.last.text if chat.last else None
    except Exception as exc:
        logger.warning("Gemini chat failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Grok helpers
# ---------------------------------------------------------------------------


def grok_completion(
    messages: list[dict[str, str]],
    *,
    model: str = "grok-2-1212",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str | None:
    """Send a chat completion request to Grok; returns the assistant text or None."""
    if not HAS_GROK:
        return None
    try:
        resp = grok_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning("Grok completion failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Whisper helpers
# ---------------------------------------------------------------------------


def transcribe_audio_file(
    audio_path: str,
    vad_config: Any | None = None,
    speech_segments: list[Any] | None = None,
    raw_audio: bool = False,
) -> dict[str, Any] | None:
    """Transcribe an audio file using VAD pre-filtering and local Whisper.

    Executes VAD pre-filtering and sends ONLY extracted speech segments to Whisper:
    - Silent or near-silent audio files skip Whisper execution completely to conserve compute.
    - Mid-file silence is trimmed out; only speech chunk arrays are passed to Whisper.
    - Preserves timestamps aligned with the original recording.
    """
    if not HAS_WHISPER:
        return None
    try:
        from workers.vad import VoiceActivityDetector

        # Run VAD ONCE if speech_segments not provided
        detector = VoiceActivityDetector(vad_config)

        if raw_audio:
            result = whisper_model.transcribe(audio_path)

            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", "en"),
                "segments": result.get("segments", []),
                "silence_only": False,
                "vad_segments": [],
                "total_speech_duration": 0.0,
            }

        if speech_segments is None:
            speech_segments = detector.process_audio(audio_path)

        # Skip transcription completely if audio is silent
        if len(speech_segments) == 0:
            logger.info("VAD detected silence only in %s — skipping Whisper transcription.", audio_path)
            return {
                "text": "",
                "language": "en",
                "segments": [],
                "silence_only": True,
                "vad_segments": [],
                "total_speech_duration": 0.0,
            }

        # Transcribe ONLY the extracted speech segments to trim out mid-file silence
        all_texts = []
        aligned_whisper_segments = []
        detected_language = "en"

        for seg in speech_segments:
            samples = getattr(seg, "audio_samples", None)
            if samples is None and os.path.exists(audio_path):
                raw_samples, sr = detector._load_samples(audio_path, detector.config.sample_rate)
                if len(raw_samples) > 0:
                    start_sec = getattr(seg, "start", seg.get("start", 0.0) if isinstance(seg, dict) else 0.0)
                    end_sec = getattr(seg, "end", seg.get("end", 0.0) if isinstance(seg, dict) else 0.0)
                    start_idx = int(start_sec * sr)
                    end_idx = min(len(raw_samples), int(end_sec * sr))
                    samples = raw_samples[start_idx:end_idx]

            if samples is None or len(samples) == 0:
                continue

            seg_result = whisper_model.transcribe(samples)
            if seg_result is None:
                continue

            seg_text = seg_result.get("text", "").strip()
            if seg_text:
                all_texts.append(seg_text)

            detected_language = seg_result.get("language", detected_language)
            seg_start = getattr(seg, "start", seg.get("start", 0.0) if isinstance(seg, dict) else 0.0)

            for w_seg in seg_result.get("segments", []):
                aligned_w_seg = dict(w_seg)
                aligned_w_seg["start"] = round(seg_start + w_seg.get("start", 0.0), 3)
                aligned_w_seg["end"] = round(seg_start + w_seg.get("end", 0.0), 3)
                aligned_whisper_segments.append(aligned_w_seg)

        combined_text = " ".join(all_texts).strip()
        vad_summary = [s.to_dict() if hasattr(s, "to_dict") else s for s in speech_segments]
        speech_duration = sum(
            getattr(s, "duration", s.get("duration", 0.0) if isinstance(s, dict) else 0.0)
            for s in speech_segments
        )

        return {
            "text": combined_text,
            "language": detected_language,
            "segments": aligned_whisper_segments,
            "silence_only": False,
            "vad_segments": vad_summary,
            "total_speech_duration": round(speech_duration, 3),
        }
    except Exception as exc:
        logger.warning("Whisper transcription failed: %s", exc)
        return None


def detect_speaker_segments(audio_path: str) -> list[dict[str, Any]] | None:
    """Return speaker-turn segments (start, end, speaker_id).

    Falls back to simple silence-based segmentation when pyannote is not
    available.
    """
    try:
        from pyannote.audio import Pipeline  # type: ignore

        diarization = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HF_TOKEN", ""),
        )
        diarization = diarization.to("cuda" if _cuda_available() else "cpu")
        hypothesis = diarization(audio_path)
        segments = []
        for turn, _, speaker in hypothesis.itertracks(yield_label=True):
            segments.append({"start": turn.start, "end": turn.end, "speaker_id": speaker})
        return segments
    except Exception:
        return None


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Face / vision helpers
# ---------------------------------------------------------------------------


def detect_faces_in_frame(frame_bytes: bytes | None = None, frame_path: str = "") -> dict[str, Any] | None:
    """Detect faces in a single frame using MediaPipe.

    Accepts raw bytes or a file path. Returns dict with face_count,
    bounding boxes, and confidence, or None if unavailable.
    """
    if not HAS_MEDIAPIPE:
        return None
    try:
        if frame_bytes:
            import numpy as np

            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif frame_path:
            image = cv2.imread(frame_path)
        else:
            return None
        if image is None:
            return None

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        with mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
            results = fd.process(rgb)
            detections = []
            if results.detections:
                for det in results.detections:
                    bbox = det.location_data.relative_bounding_box
                    detections.append(
                        {
                            "x": bbox.xmin,
                            "y": bbox.ymin,
                            "w": bbox.width,
                            "h": bbox.height,
                            "confidence": det.score[0],
                        }
                    )
            return {"face_count": len(detections), "faces": detections}
    except Exception as exc:
        logger.warning("MediaPipe face detection failed: %s", exc)
        return None


def detect_hand_gaze(frame_bytes: bytes | None = None, frame_path: str = "") -> dict[str, Any] | None:
    """Detect hand/palm positions that may indicate phone use, using MediaPipe Hands."""
    if not HAS_MEDIAPIPE:
        return None
    try:
        if frame_bytes:
            import numpy as np

            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif frame_path:
            image = cv2.imread(frame_path)
        else:
            return None
        if image is None:
            return None

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        with mp.solutions.hands.Hands(
            static_image_mode=True, max_num_hands=4, min_detection_confidence=0.5
        ) as hands:
            results = hands.process(rgb)
            hand_count = 0
            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
            return {"hands_detected": hand_count, "possibly_holding_phone": hand_count >= 2}
    except Exception as exc:
        logger.warning("MediaPipe hand detection failed: %s", exc)
        return None
