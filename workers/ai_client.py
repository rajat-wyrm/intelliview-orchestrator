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


def transcribe_audio_file(audio_path: str) -> dict[str, Any] | None:
    """Transcribe an audio file using local Whisper; returns dict or None."""
    if not HAS_WHISPER:
        return None
    try:
        result = whisper_model.transcribe(audio_path)
        return {
            "text": result.get("text", ""),
            "language": result.get("language", "en"),
            "segments": result.get("segments", []),
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
