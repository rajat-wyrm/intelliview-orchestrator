"""
Unit tests for Voice Activity Detection (VAD) module.

Tests coverage:
- Silence-only audio recordings (skipped transcription)
- Speech-only audio recordings (detected speech chunks)
- Mixed audio (silence + speech + silence) with timestamp preservation
- Configurable VAD sensitivity & thresholds
- Preservation of short pauses between words (hangover & max pause merge)
- Integration with audio pipeline and backward compatibility
"""

import os
import tempfile
import wave

import numpy as np
import pytest

pytest.importorskip("numpy")

from workers.audio_pipeline import run_audio_analysis, transcribe_speech
from workers.vad import VADConfig, VoiceActivityDetector, detect_voice_activity, is_silence_only


def create_synthetic_wav(
    file_path: str,
    duration_sec: float = 3.0,
    sample_rate: int = 16000,
    tone_freq: float = 440.0,
    active_regions: list[tuple[float, float]] | None = None,
) -> None:
    """Helper to generate synthetic WAV files with specified speech (tone) and silence regions."""
    num_samples = int(duration_sec * sample_rate)
    samples = np.zeros(num_samples, dtype=np.float32)

    if active_regions:
        t = np.arange(num_samples) / sample_rate
        sine_wave = 0.5 * np.sin(2 * np.pi * tone_freq * t).astype(np.float32)

        for start_t, end_t in active_regions:
            start_idx = int(start_t * sample_rate)
            end_idx = min(num_samples, int(end_t * sample_rate))
            samples[start_idx:end_idx] = sine_wave[start_idx:end_idx]

    # Convert to 16-bit PCM bytes
    int16_samples = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_samples.tobytes())


def test_silence_only_audio():
    """Test that pure silence returns 0 speech segments."""
    sample_rate = 16000
    duration = 2.0
    silence = np.zeros(int(sample_rate * duration), dtype=np.float32)

    config = VADConfig(threshold_db=-40.0, sensitivity=0.5)
    detector = VoiceActivityDetector(config)
    segments = detector.process_audio(silence, sample_rate=sample_rate)

    assert len(segments) == 0
    assert is_silence_only(silence, config=config, sample_rate=sample_rate) is True


def test_speech_only_audio():
    """Test that continuous audio/tone is identified as speech segment."""
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    speech_tone = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

    config = VADConfig(threshold_db=-40.0, sensitivity=0.5, padding_ms=100)
    detector = VoiceActivityDetector(config)
    segments = detector.process_audio(speech_tone, sample_rate=sample_rate)

    assert len(segments) >= 1
    # Speech duration should cover most of the 2.0 seconds
    total_speech_dur = sum(s.duration for s in segments)
    assert total_speech_dur >= 1.5


def test_mixed_audio_timestamp_alignment():
    """Test mixed audio (silence -> speech -> silence -> speech) preserves exact timestamps relative to original timeline."""
    sample_rate = 16000
    total_duration = 5.0
    # Active speech regions: 1.0s to 2.0s and 3.5s to 4.5s
    active_regions = [(1.0, 2.0), (3.5, 4.5)]

    num_samples = int(total_duration * sample_rate)
    samples = np.zeros(num_samples, dtype=np.float32)
    t = np.arange(num_samples) / sample_rate
    sine = 0.6 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

    for s_t, e_t in active_regions:
        samples[int(s_t * sample_rate) : int(e_t * sample_rate)] = sine[
            int(s_t * sample_rate) : int(e_t * sample_rate)
        ]

    config = VADConfig(
        threshold_db=-35.0,
        sensitivity=0.5,
        padding_ms=100,  # 0.1s padding
        max_pause_merge_ms=200,  # 0.2s pause merge (should NOT merge 2.0s to 3.5s gap)
    )
    detector = VoiceActivityDetector(config)
    segments = detector.process_audio(samples, sample_rate=sample_rate)

    assert len(segments) == 2, f"Expected 2 separate speech segments, got {len(segments)}"

    # Check 1st segment start and end aligned to original timeline (~0.9s start, ~2.1s end with padding)
    seg1, seg2 = segments[0], segments[1]
    assert 0.8 <= seg1.start <= 1.1
    assert 1.9 <= seg1.end <= 2.2
    assert seg1.start < seg1.end

    # Check 2nd segment start and end aligned to original timeline (~3.4s start, ~4.6s end with padding)
    assert 3.3 <= seg2.start <= 3.6
    assert 4.4 <= seg2.end <= 4.7
    assert seg2.start < seg2.end


def test_vad_sensitivity_configuration():
    """Test that higher sensitivity drops low-energy noise while lower sensitivity retains it."""
    sample_rate = 16000
    duration = 2.0
    num_samples = int(duration * sample_rate)

    # Low energy signal (ambient noise level)
    low_energy_signal = 0.005 * np.sin(2 * np.pi * 300 * np.linspace(0, duration, num_samples)).astype(
        np.float32
    )

    # Low sensitivity (lenient -> detect speech)
    lenient_config = VADConfig(threshold_db=-40.0, sensitivity=0.0)
    lenient_segments = VoiceActivityDetector(lenient_config).process_audio(
        low_energy_signal, sample_rate=sample_rate
    )

    # High sensitivity (strict -> drop low energy signal)
    strict_config = VADConfig(threshold_db=-40.0, sensitivity=1.0)
    strict_segments = VoiceActivityDetector(strict_config).process_audio(
        low_energy_signal, sample_rate=sample_rate
    )

    assert len(lenient_segments) >= len(strict_segments)


def test_short_pause_preservation():
    """Test that very short pauses between words (e.g. 150ms gap) are preserved and merged, not incorrectly removed."""
    sample_rate = 16000
    total_duration = 3.0

    # Two words separated by a 150ms pause (Word 1: 0.5-1.0s, Pause: 1.0-1.15s, Word 2: 1.15-1.65s)
    active_regions = [(0.5, 1.0), (1.15, 1.65)]

    num_samples = int(total_duration * sample_rate)
    samples = np.zeros(num_samples, dtype=np.float32)
    t = np.arange(num_samples) / sample_rate
    sine = 0.5 * np.sin(2 * np.pi * 500 * t).astype(np.float32)

    for s_t, e_t in active_regions:
        samples[int(s_t * sample_rate) : int(e_t * sample_rate)] = sine[
            int(s_t * sample_rate) : int(e_t * sample_rate)
        ]

    # Max pause merge set to 300ms (should merge the 150ms gap into a continuous speech segment)
    config = VADConfig(
        threshold_db=-40.0,
        sensitivity=0.5,
        max_pause_merge_ms=300,
        padding_ms=100,
    )
    detector = VoiceActivityDetector(config)
    segments = detector.process_audio(samples, sample_rate=sample_rate)

    assert len(segments) == 1, (
        "Short inter-word pause (150ms) should be preserved inside single merged segment"
    )
    assert segments[0].start <= 0.5
    assert segments[0].end >= 1.65


def test_wav_file_processing():
    """Test VAD file processing on actual WAV files on disk."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create synthetic WAV with 1.0s silence, 1.5s speech, 0.5s silence
        create_synthetic_wav(tmp_path, duration_sec=3.0, active_regions=[(1.0, 2.5)])

        config = VADConfig(threshold_db=-35.0, padding_ms=100)
        segments = detect_voice_activity(tmp_path, config=config)

        assert len(segments) == 1
        assert 0.8 <= segments[0].start <= 1.1
        assert 2.4 <= segments[0].end <= 2.7
        assert segments[0].duration > 1.2
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_audio_pipeline_vad_integration():
    """Test that transcribe_speech and run_audio_analysis include VAD metadata and execute VAD stage."""
    custom_vad = VADConfig(sensitivity=0.8, threshold_db=-35.0, padding_ms=150)

    result = transcribe_speech("session-vad-test", vad_config=custom_vad)
    assert "vad_executed" in result
    assert result["vad_executed"] is True
    assert "speech_detected" in result
    assert "vad_segments" in result
    assert "vad_config" in result
    assert result["vad_config"]["sensitivity"] == 0.8

    analysis = run_audio_analysis("session-vad-analysis", vad_config=custom_vad)
    assert "transcription" in analysis
    assert analysis["transcription"]["vad_executed"] is True
    assert 0.0 <= analysis["risk_score"] <= 1.0


def test_mid_file_silence_trimmed_and_only_speech_sent_to_whisper(monkeypatch):
    """Test that mid-file silence is trimmed out and only speech segment audio arrays are passed to Whisper."""
    from unittest.mock import MagicMock

    import workers.ai_client as ai_client
    from workers.vad import SpeechSegment

    mock_whisper = MagicMock()
    mock_whisper.transcribe.side_effect = lambda samples, **kwargs: {
        "text": "Hello world",
        "language": "en",
        "segments": [{"start": 0.1, "end": 0.8, "text": "Hello world"}],
    }

    monkeypatch.setattr(ai_client, "HAS_WHISPER", True)
    monkeypatch.setattr(ai_client, "whisper_model", mock_whisper)

    sr = 16000
    dummy_samples1 = np.ones(int(1.0 * sr), dtype=np.float32)
    dummy_samples2 = np.ones(int(1.5 * sr), dtype=np.float32)

    # 2 speech segments at timestamps 2.0s-3.0s and 5.0s-6.5s
    speech_segments = [
        SpeechSegment(
            start=2.0, end=3.0, duration=1.0, confidence=0.9, segment_index=0, audio_samples=dummy_samples1
        ),
        SpeechSegment(
            start=5.0, end=6.5, duration=1.5, confidence=0.95, segment_index=1, audio_samples=dummy_samples2
        ),
    ]

    res = ai_client.transcribe_audio_file("dummy.wav", speech_segments=speech_segments)

    assert res is not None
    assert mock_whisper.transcribe.call_count == 2
    # Verify whole file was NOT passed, only chunk samples
    for call in mock_whisper.transcribe.call_args_list:
        passed_audio = call[0][0]
        assert isinstance(passed_audio, np.ndarray)
        assert passed_audio.shape[0] in (len(dummy_samples1), len(dummy_samples2))

    # Verify timestamps were offset relative to segment start
    assert res["segments"][0]["start"] == 2.1  # 2.0 + 0.1
    assert res["segments"][0]["end"] == 2.8  # 2.0 + 0.8
    assert res["segments"][1]["start"] == 5.1  # 5.0 + 0.1
    assert res["segments"][1]["end"] == 5.8  # 5.0 + 0.8
    assert res["text"] == "Hello world Hello world"


def test_vad_runs_only_once(monkeypatch):
    """Test that VAD process_audio is executed exactly once during real transcription."""
    from unittest.mock import MagicMock

    import workers.audio_pipeline as ap
    from workers.vad import SpeechSegment

    tmp_dir = tempfile.mkdtemp()
    session_id = "test_once_123"
    wav_path = os.path.join(tmp_dir, f"interview_{session_id}.wav")

    try:
        create_synthetic_wav(wav_path, duration_sec=2.0, active_regions=[(0.5, 1.5)])
        monkeypatch.setattr(ap, "AUDIO_TEMP_DIR", tmp_dir)

        mock_detector_instance = MagicMock()
        mock_detector_instance.config.sample_rate = 16000
        mock_detector_instance.process_audio.return_value = [
            SpeechSegment(
                start=0.5,
                end=1.5,
                duration=1.0,
                confidence=0.9,
                segment_index=0,
                audio_samples=np.zeros(16000, dtype=np.float32),
            )
        ]

        monkeypatch.setattr("workers.vad.VoiceActivityDetector", lambda cfg=None: mock_detector_instance)
        monkeypatch.setattr("workers.ai_client.HAS_WHISPER", True)
        monkeypatch.setattr(
            "workers.ai_client.whisper_model",
            MagicMock(transcribe=lambda s, **kw: {"text": "test", "language": "en", "segments": []}),
        )

        ap._real_transcribe(session_id)

        # Assert process_audio was called exactly 1 time
        assert mock_detector_instance.process_audio.call_count == 1
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)


def test_min_speech_duration_unpadded_filtering():
    """Test that a tiny 20ms noise spike is filtered out before padding is applied."""
    sr = 16000
    total_duration = 2.0
    num_samples = int(total_duration * sr)
    samples = np.zeros(num_samples, dtype=np.float32)

    # 20ms noise spike (0.50s to 0.52s)
    spike_start = int(0.50 * sr)
    spike_end = int(0.52 * sr)
    samples[spike_start:spike_end] = 0.8

    config = VADConfig(
        threshold_db=-40.0,
        min_speech_duration_ms=150,  # 150ms required
        padding_ms=200,  # 200ms padding
    )
    detector = VoiceActivityDetector(config)
    segments = detector.process_audio(samples, sample_rate=sr)

    # Should be 0 segments because raw unpadded duration (20ms) < min_speech_duration_ms (150ms)
    assert len(segments) == 0


def test_partial_last_frame_included():
    """Test that loud speech in the partial last frame is not dropped by floor division."""
    sr = 16000
    frame_ms = 30
    frame_samples = int(sr * (frame_ms / 1000.0))  # 480 samples

    # 10 full quiet frames + 1 partial frame with loud speech (200 samples)
    total_samples = 10 * frame_samples + 200
    samples = np.zeros(total_samples, dtype=np.float32)

    # Place loud speech in the last 200 samples
    samples[10 * frame_samples :] = 0.8

    config = VADConfig(threshold_db=-40.0, frame_duration_ms=30, padding_ms=0, min_speech_duration_ms=10)
    detector = VoiceActivityDetector(config)
    segments = detector.process_audio(samples, sample_rate=sr)

    assert len(segments) >= 1
    assert segments[-1].end >= (total_samples / sr) - 0.001
