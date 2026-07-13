"""
Tests for the #43 fix: duration_seconds must reflect the real audio file
length, not the sum of transcript segment spans.

Place this file at: tests/test_audio_pipeline_duration.py
"""

import wave

import pytest

from workers.audio_pipeline import _get_audio_duration


def _make_wav_file(path: str, seconds: float, framerate: int = 16000) -> None:
    """Create a minimal silent mono 16-bit .wav file of an exact duration."""
    n_frames = int(seconds * framerate)
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(framerate)
        wav_file.writeframes(b"\x00\x00" * n_frames)


def test_duration_matches_real_file_length(tmp_path):
    """Duration should come from the actual .wav file, not segment math."""
    audio_path = str(tmp_path / "sample.wav")
    _make_wav_file(audio_path, seconds=17.5)

    # Segments deliberately understate the true duration (simulating pauses
    # / silence that Whisper doesn't include in any segment). The old buggy
    # implementation would have summed these to ~9.0s instead of 17.5s.
    segments = [
        {"start": 0.0, "end": 4.0},
        {"start": 6.0, "end": 9.0},
    ]

    duration = _get_audio_duration(audio_path, segments)

    assert duration == pytest.approx(17.5, abs=0.05)


def test_duration_ignores_gaps_between_segments(tmp_path):
    """Silence between segments must not shrink the reported duration."""
    audio_path = str(tmp_path / "with_pauses.wav")
    _make_wav_file(audio_path, seconds=60.0)

    # Old buggy code: sum(end - start) = 5 + 5 = 10s (very wrong).
    # Fixed code: reads the file -> 60.0s.
    segments = [
        {"start": 0.0, "end": 5.0},
        {"start": 50.0, "end": 55.0},
    ]

    duration = _get_audio_duration(audio_path, segments)

    assert duration == pytest.approx(60.0, abs=0.05)
    assert duration != pytest.approx(10.0, abs=0.05)


def test_duration_falls_back_to_segments_when_file_missing():
    """If the file can't be read, fall back to max(segment end), not sum()."""
    segments = [
        {"start": 0.0, "end": 4.0},
        {"start": 6.0, "end": 9.0},
    ]

    duration = _get_audio_duration("/tmp/does_not_exist_12345.wav", segments)

    # max(end) = 9.0, not sum(end - start) = 7.0
    assert duration == pytest.approx(9.0, abs=0.01)


def test_duration_is_zero_when_nothing_available():
    """No file and no segments -> 0.0, not a hardcoded fake value like 120.0."""
    duration = _get_audio_duration("/tmp/does_not_exist_12345.wav", [])

    assert duration == 0.0


def test_duration_handles_silent_recording_with_no_segments(tmp_path):
    """A real silent recording with zero transcript segments should still
    report its true length, not the old hardcoded 120.0 fallback."""
    audio_path = str(tmp_path / "silent.wav")
    _make_wav_file(audio_path, seconds=45.0)

    duration = _get_audio_duration(audio_path, [])

    assert duration == pytest.approx(45.0, abs=0.05)
    assert duration != 120.0
