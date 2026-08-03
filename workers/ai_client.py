"""
AI Client Module
Provides pluggable clients for OpenAI, Whisper, and MediaPipe/OpenCV
with automatic fallback to mocks when API keys or libraries are absent.
Includes token usage tracking for OpenAI, Gemini, and Grok calls.
"""

import logging
import os
from typing import Any, Tuple

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
# Helper function to construct standard usage dictionary
# ---------------------------------------------------------------------------


def _build_usage_dict(
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> dict[str, Any]:
    """Helper to structure token usage and estimated cost metadata."""
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Tuple[str | None, dict[str, Any]]:
    """
    Send a chat completion request to OpenAI.
    Returns a tuple: (content_text or None, usage_dict).
    """
    if not HAS_OPENAI:
        return None, _build_usage_dict("openai", model)
    try:
        resp = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content

        usage = _build_usage_dict("openai", model)
        if getattr(resp, "usage", None):
            usage = _build_usage_dict(
                provider="openai",
                model=model,
                prompt_tokens=getattr(resp.usage, "prompt_tokens", 0),
                completion_tokens=getattr(resp.usage, "completion_tokens", 0),
                total_tokens=getattr(resp.usage, "total_tokens", 0),
            )

        logger.info(
            "OpenAI call finished [%s] — Tokens: Prompt=%d, Completion=%d, Total=%d",
            model,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("OpenAI chat completion failed: %s", exc)
        return None, _build_usage_dict("openai", model)


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------


def gemini_generate(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> Tuple[str | None, dict[str, Any]]:
    """
    Generate text using Gemini.
    Returns a tuple: (content_text or None, usage_dict).
    """
    model_name = "gemini-2.0-flash"
    if not HAS_GEMINI:
        return None, _build_usage_dict("google", model_name)
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        content = response.text

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0)

        usage = _build_usage_dict(
            provider="google",
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        logger.info(
            "Gemini generation finished [%s] — Tokens: Prompt=%d, Completion=%d, Total=%d",
            model_name,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("Gemini generation failed: %s", exc)
        return None, _build_usage_dict("google", model_name)


def gemini_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> Tuple[str | None, dict[str, Any]]:
    """
    Multi-turn chat with Gemini.
    Returns a tuple: (response_text or None, usage_dict).
    """
    model_name = "gemini-2.0-flash"
    if not HAS_GEMINI:
        return None, _build_usage_dict("google", model_name)
    try:
        chat = gemini_model.start_chat(history=[])
        response = None
        for msg in messages:
            if msg["role"] == "user":
                response = chat.send_message(msg["content"])
            elif msg["role"] == "assistant":
                pass

        content = chat.last.text if chat.last else None

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if response and hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0)

        usage = _build_usage_dict(
            provider="google",
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        logger.info(
            "Gemini chat finished [%s] — Tokens: Prompt=%d, Completion=%d, Total=%d",
            model_name,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("Gemini chat failed: %s", exc)
        return None, _build_usage_dict("google", model_name)


# ---------------------------------------------------------------------------
# Grok helpers
# ---------------------------------------------------------------------------


def grok_completion(
    messages: list[dict[str, str]],
    *,
    model: str = "grok-2-1212",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Tuple[str | None, dict[str, Any]]:
    """
    Send a chat completion request to Grok.
    Returns a tuple: (content_text or None, usage_dict).
    """
    if not HAS_GROK:
        return None, _build_usage_dict("grok", model)
    try:
        resp = grok_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content

        usage = _build_usage_dict("grok", model)
        if getattr(resp, "usage", None):
            usage = _build_usage_dict(
                provider="grok",
                model=model,
                prompt_tokens=getattr(resp.usage, "prompt_tokens", 0),
                completion_tokens=getattr(resp.usage, "completion_tokens", 0),
                total_tokens=getattr(resp.usage, "total_tokens", 0),
            )

        logger.info(
            "Grok completion finished [%s] — Tokens: Prompt=%d, Completion=%d, Total=%d",
            model,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        )
        return content, usage
    except Exception as exc:
        logger.warning("Grok completion failed: %s", exc)
        return None, _build_usage_dict("grok", model)


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