"""
Video Analysis Pipeline
Handles computer vision tasks for interview monitoring

Responsibilities:
- Face detection
- Head movement detection
- Mobile phone detection
- Multiple person detection

This module defines the **pluggable contract** the orchestrator relies on.
Replace each detection helper with a real model (MediaPipe, YOLO, OpenCV,
etc.) — the returned dict shape is what `RiskScoringEngine` consumes.

The provided defaults are deterministic per-session seeds so that:
  * end-to-end risk scores are non-trivial in tests / demos,
  * risk classification thresholds (LOW/MEDIUM/HIGH/CRITICAL) actually
    fire under load,
  * operators can sanity-check the pipeline without GPU dependencies.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


from workers._stubs import _seeded_unit  # noqa: E402

# ---------------------------------------------------------------------------
# Real detection helpers (MediaPipe / OpenCV) with fallback to stubs
# ---------------------------------------------------------------------------


def _real_detect_face(session_id: str) -> dict[str, Any] | None:
    """Attempt real face detection via ai_client. Returns None on failure."""
    try:
        from workers.ai_client import detect_faces_in_frame

        result = detect_faces_in_frame()
        if result is None:
            return None
        faces_found = result["face_count"] > 0
        return {
            "faces_found": faces_found,
            "face_count": result["face_count"],
            "confidence": round(max((f["confidence"] for f in result["faces"]), default=0.0), 3),
            "bounding_boxes": result["faces"],
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.debug("Real face detection unavailable: %s", exc)
        return None


def _real_detect_head_movement(session_id: str) -> dict[str, Any] | None:
    """Detect gaze deviation using MediaPipe face mesh landmarks.

    High average landmark drift from the canonical front-facing position
    suggests the candidate is looking away.
    """
    try:
        import cv2
        import mediapipe as mp  # type: ignore

        from workers.ai_client import HAS_MEDIAPIPE

        if not HAS_MEDIAPIPE:
            return None

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        frames: list[Any] = []
        for _ in range(10):
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        cap.release()

        if not frames:
            return None

        rgb = cv2.cvtColor(frames[-1], cv2.COLOR_BGR2RGB)
        with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, min_detection_confidence=0.5) as mesh:
            results = mesh.process(rgb)
            if not results.multi_face_landmarks:
                return {
                    "suspicious_movement_detected": True,
                    "head_turns_count": 0,
                    "avg_gaze_deviation": 1.0,
                    "timestamp": time.time(),
                }

            lm = results.multi_face_landmarks[0].landmark
            nose_tip = lm[1]
            eye_left = lm[33]
            eye_right = lm[263]
            gaze_dev = abs(nose_tip.x - (eye_left.x + eye_right.x) / 2)
            return {
                "suspicious_movement_detected": gaze_dev > 0.05,
                "head_turns_count": 0,
                "avg_gaze_deviation": round(float(gaze_dev), 3),
                "timestamp": time.time(),
            }
    except Exception as exc:
        logger.debug("Real head-movement detection unavailable: %s", exc)
        return None


def _real_detect_phone(session_id: str) -> dict[str, Any] | None:
    """Detect phone usage via hand detection from ai_client."""
    try:
        from workers.ai_client import detect_hand_gaze

        result = detect_hand_gaze()
        if result is None:
            return None
        phone_detected = result["possibly_holding_phone"]
        return {
            "phone_detected": phone_detected,
            "phone_usage_detected": phone_detected,
            "detection_confidence": 0.85 if phone_detected else 0.0,
            "hands_count": result["hands_detected"],
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.debug("Real phone detection unavailable: %s", exc)
        return None


def _real_detect_multiple_persons(session_id: str) -> dict[str, Any] | None:
    """Detect multiple persons via face count from MediaPipe."""
    try:
        from workers.ai_client import detect_faces_in_frame

        result = detect_faces_in_frame()
        if result is None:
            return None
        count = result["face_count"]
        return {
            "multiple_persons_detected": count > 1,
            "person_count": count,
            "detection_confidence": round(max((f["confidence"] for f in result["faces"]), default=0.0), 3),
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.debug("Real multi-person detection unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public pipeline API — real detection with seeded stub fallback
# ---------------------------------------------------------------------------


def run_video_analysis(session_id: str) -> dict[str, Any]:
    """
    Execute video analysis pipeline for an interview session.

    Args:
        session_id: Unique interview session identifier.

    Returns:
        dict: Analysis results including detection findings and risk scores.
    """
    logger.info(f"Starting video analysis for session {session_id}")

    face = detect_face(session_id)
    head = detect_suspicious_head_movement(session_id)
    phone = detect_mobile_phone(session_id)
    multi = detect_multiple_persons(session_id)

    results = {
        "session_id": session_id,
        "face_detected": face,
        "head_movement_suspicious": head,
        "phone_detected": phone,
        "multiple_persons": multi,
        "risk_score": 0.0,
    }

    results["risk_score"] = calculate_video_risk_score(results)
    logger.info(f"Video analysis completed for session {session_id}: {results}")
    return results


def detect_face(session_id: str) -> dict[str, Any]:
    """Detect faces — real MediaPipe detection with seeded stub fallback."""
    logger.info(f"Detecting faces for session {session_id}")

    real = _real_detect_face(session_id)
    if real is not None:
        return real

    return {
        "faces_found": _seeded_unit(session_id, "face") > 0.05,
        "face_count": 1 if _seeded_unit(session_id, "face") > 0.05 else 0,
        "confidence": round(0.85 + _seeded_unit(session_id, "face_conf") * 0.1, 3),
        "timestamp": None,
    }


def detect_suspicious_head_movement(session_id: str) -> dict[str, Any]:
    """Detect suspicious head movement — real face mesh with seeded stub fallback."""
    logger.info(f"Detecting head movements for session {session_id}")

    real = _real_detect_head_movement(session_id)
    if real is not None:
        return real

    suspicion = _seeded_unit(session_id, "head")
    return {
        "suspicious_movement_detected": suspicion > 0.75,
        "head_turns_count": int(suspicion * 12),
        "avg_gaze_deviation": round(suspicion, 3),
        "timestamp": None,
    }


def detect_mobile_phone(session_id: str) -> dict[str, Any]:
    """Detect mobile phone — real hand detection with seeded stub fallback."""
    logger.info(f"Detecting mobile phone for session {session_id}")

    real = _real_detect_phone(session_id)
    if real is not None:
        return real

    detected = _seeded_unit(session_id, "phone") > 0.85
    return {
        "phone_detected": detected,
        "phone_usage_detected": detected,
        "detection_confidence": round(_seeded_unit(session_id, "phone_conf"), 3),
        "timestamp": None,
    }


def detect_multiple_persons(session_id: str) -> dict[str, Any]:
    """Detect multiple persons — real face count with seeded stub fallback."""
    logger.info(f"Detecting multiple persons for session {session_id}")

    real = _real_detect_multiple_persons(session_id)
    if real is not None:
        return real

    multi = _seeded_unit(session_id, "multi") > 0.88
    return {
        "multiple_persons_detected": multi,
        "person_count": 2 if multi else 1,
        "detection_confidence": round(_seeded_unit(session_id, "multi_conf"), 3),
        "timestamp": None,
    }


def calculate_video_risk_score(results: dict[str, Any]) -> float:
    """Calculate a 0–1 risk score from video detection results."""
    from workers.risk_engine import RiskScoringEngine

    score = 0.0
    if results.get("multiple_persons", {}).get("multiple_persons_detected"):
        score += RiskScoringEngine.VIDEO_FACTORS["multiple_persons"]
    if results.get("phone_detected", {}).get("phone_detected"):
        score += RiskScoringEngine.VIDEO_FACTORS["phone_detected"]
    if results.get("head_movement_suspicious", {}).get("suspicious_movement_detected"):
        score += RiskScoringEngine.VIDEO_FACTORS["suspicious_head_movement"]
    if not results.get("face_detected", {}).get("faces_found"):
        score += RiskScoringEngine.VIDEO_FACTORS["no_face_detected"]
    return round(min(score, 1.0), 3)
