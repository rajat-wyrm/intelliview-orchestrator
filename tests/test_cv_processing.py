from cv_service import processing
from cv_service.processing import detect_faces_in_frame


def test_garbled_frame_is_handled_and_logged(caplog, monkeypatch):
    monkeypatch.setattr(processing, "HAS_MEDIAPIPE", True)
    with caplog.at_level("WARNING"):
        result = detect_faces_in_frame(b"not-a-real-image")

    assert result is None
    assert "Unable to decode video frame" in caplog.text


def test_missing_frame_is_handled_and_logged(caplog, monkeypatch):
    monkeypatch.setattr(processing, "HAS_MEDIAPIPE", True)
    with caplog.at_level("WARNING"):
        result = detect_faces_in_frame()

    assert result is None
    assert "No frame bytes or frame path provided" in caplog.text


def test_invalid_file_path_is_handled_and_logged(caplog, monkeypatch):
    monkeypatch.setattr(processing, "HAS_MEDIAPIPE", True)
    with caplog.at_level("WARNING"):
        result = detect_faces_in_frame(frame_path="/tmp/this-file-does-not-exist.jpg")

    assert result is None
    assert "Unable to decode video frame" in caplog.text


def test_processing_exception_is_handled_and_logged(caplog, monkeypatch):
    import numpy as np

    image = np.zeros((480, 640, 3), dtype=np.uint8)

    monkeypatch.setattr(processing, "HAS_MEDIAPIPE", True)
    monkeypatch.setattr(
        processing.cv2,
        "imread",
        lambda _: image,
    )

    def raise_processing_error(*args, **kwargs):
        raise RuntimeError("simulated OpenCV processing failure")

    monkeypatch.setattr(
        processing.cv2,
        "cvtColor",
        raise_processing_error,
    )

    with caplog.at_level("WARNING"):
        result = detect_faces_in_frame(frame_path="/tmp/test-frame.jpg")

    assert result is None
    assert "MediaPipe face detection failed" in caplog.text
