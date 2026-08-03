"""Voice Activity Detection (VAD)

This module checks audio files for speech and silence before sending them
to the speech-to-text model.

It helps us:
- Skip silent audio chunks so we don't waste CPU/GPU time.
- Keep exact start and end timestamps so transcripts match the original recording.
- Tune energy thresholds and padding so quick pauses between words aren't cut off.
"""

import logging
import math
import os
import wave
from dataclasses import dataclass, field
from typing import TypedDict

import numpy as np

logger = logging.getLogger(__name__)


class SpeechSegmentDict(TypedDict):
    start: float
    end: float
    duration: float
    confidence: float
    segment_index: int


@dataclass
class VADConfig:
    """Configuration settings for Voice Activity Detection."""

    sensitivity: float = 0.5
    """Sensitivity factor between 0.0 (least aggressive / keep more audio) and 1.0 (most aggressive / drop low energy)."""

    threshold_db: float = -40.0
    """RMS energy threshold in decibels (dB relative to max amplitude 1.0). Audio above this is speech."""

    frame_duration_ms: int = 30
    """Frame size in milliseconds for analysis (typically 10, 20, or 30 ms)."""

    min_speech_duration_ms: int = 150
    """Minimum duration of a speech segment in ms. Shorter bursts are ignored as noise."""

    padding_ms: int = 200
    """Hangover / padding in ms added before and after speech segments to avoid clipping speech boundaries."""

    max_pause_merge_ms: int = 300
    """Maximum pause duration in ms between speech segments to merge into a single segment (preserves inter-word pauses)."""

    sample_rate: int = 16000
    """Target audio sample rate in Hz."""

    @classmethod
    def from_env(cls) -> "VADConfig":
        """Load configuration options from environment variables with sensible defaults."""
        return cls(
            sensitivity=float(os.getenv("VAD_SENSITIVITY", "0.5")),
            threshold_db=float(os.getenv("VAD_THRESHOLD_DB", "-40.0")),
            frame_duration_ms=int(os.getenv("VAD_FRAME_DURATION_MS", "30")),
            min_speech_duration_ms=int(os.getenv("VAD_MIN_SPEECH_MS", "150")),
            padding_ms=int(os.getenv("VAD_PADDING_MS", "200")),
            max_pause_merge_ms=int(os.getenv("VAD_MAX_PAUSE_MERGE_MS", "300")),
            sample_rate=int(os.getenv("VAD_SAMPLE_RATE", "16000")),
        )


@dataclass
class SpeechSegment:
    """Represents a detected speech segment with timing and optional audio data."""

    start: float
    """Start time in seconds from original recording start."""

    end: float
    """End time in seconds from original recording start."""

    duration: float
    """Duration of segment in seconds."""

    confidence: float = 0.95
    """VAD confidence score for speech in this segment."""

    segment_index: int = 0
    """0-indexed position of speech segment in audio timeline."""

    audio_samples: np.ndarray | None = field(default=None, repr=False)
    """Raw floating-point audio samples for this segment (-1.0 to 1.0)."""

    def to_dict(self) -> SpeechSegmentDict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "confidence": round(self.confidence, 3),
            "segment_index": self.segment_index,
        }


class VoiceActivityDetector:
    """Engine for performing Voice Activity Detection on audio data."""

    def __init__(self, config: VADConfig | None = None):
        self.config = config or VADConfig.from_env()

    def process_audio(
        self,
        audio_input: np.ndarray | bytes | str,
        sample_rate: int | None = None,
    ) -> list[SpeechSegment]:
        """Detect speech segments in audio input.

        Args:
            audio_input: Audio as numpy float array (-1 to 1), raw 16-bit PCM bytes,
                         or file path to a WAV audio file.
            sample_rate: Audio sampling rate in Hz (defaults to config.sample_rate).

        Returns:
            List of SpeechSegment objects containing exact timestamps aligned to the original recording.
        """
        sr = sample_rate or self.config.sample_rate
        samples, sr = self._load_samples(audio_input, sr)

        if len(samples) == 0:
            return []

        total_duration = len(samples) / sr
        frame_size = int(sr * (self.config.frame_duration_ms / 1000.0))
        if frame_size <= 0:
            frame_size = 480  # Default 30ms at 16kHz

        # Try optional external ML VAD engines first (e.g. WebRTC VAD) if available
        webrtc_segments = self._try_webrtc_vad(samples, sr)
        if webrtc_segments is not None:
            return webrtc_segments

        # Standard signal-based VAD using RMS energy & hysteresis
        effective_db_threshold = self._compute_effective_threshold(samples)
        num_frames = math.ceil(len(samples) / frame_size)

        is_speech_frame = []
        for i in range(num_frames):
            frame = samples[i * frame_size : min(len(samples), (i + 1) * frame_size)]
            if len(frame) == 0:
                continue
            rms = math.sqrt(np.mean(frame**2) + 1e-12)
            db = 20.0 * math.log10(rms + 1e-12)
            is_speech_frame.append(db >= effective_db_threshold)

        if not is_speech_frame:
            return []

        # Convert frame boolean decisions to raw time intervals
        frame_sec = self.config.frame_duration_ms / 1000.0
        raw_intervals: list[tuple[float, float]] = []
        in_speech = False
        start_time = 0.0

        for i, speech in enumerate(is_speech_frame):
            t_start = i * frame_sec
            if speech and not in_speech:
                in_speech = True
                start_time = t_start
            elif not speech and in_speech:
                in_speech = False
                raw_intervals.append((start_time, t_start))

        if in_speech:
            raw_intervals.append((start_time, total_duration))

        if not raw_intervals:
            return []

        # Step 1: Merge short pauses (inter-word gaps <= max_pause_merge_ms)
        max_pause_sec = self.config.max_pause_merge_ms / 1000.0
        merged_intervals: list[tuple[float, float]] = []

        curr_start, curr_end = raw_intervals[0]
        for next_start, next_end in raw_intervals[1:]:
            if (next_start - curr_end) <= max_pause_sec:
                curr_end = next_end
            else:
                merged_intervals.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_intervals.append((curr_start, curr_end))

        # Step 2: Filter unpadded duration first, then apply hangover padding
        padding_sec = self.config.padding_ms / 1000.0
        min_speech_sec = self.config.min_speech_duration_ms / 1000.0

        final_segments: list[SpeechSegment] = []
        for idx, (s_start, s_end) in enumerate(merged_intervals):
            raw_dur = s_end - s_start
            # Skip noise bursts shorter than min_speech_duration BEFORE padding
            if raw_dur < min_speech_sec:
                continue

            padded_start = max(0.0, s_start - padding_sec)
            padded_end = min(total_duration, s_end + padding_sec)
            duration = padded_end - padded_start

            # Extract segment audio slice
            start_sample = int(padded_start * sr)
            end_sample = min(len(samples), int(padded_end * sr))
            segment_samples = samples[start_sample:end_sample]

            # Calculate confidence based on energy ratio
            segment_rms = math.sqrt(np.mean(segment_samples**2) + 1e-12) if len(segment_samples) > 0 else 0.0
            seg_db = 20.0 * math.log10(segment_rms + 1e-12)
            conf = min(1.0, max(0.5, 0.5 + (seg_db - effective_db_threshold) / 40.0))

            final_segments.append(
                SpeechSegment(
                    start=padded_start,
                    end=padded_end,
                    duration=duration,
                    confidence=conf,
                    segment_index=idx,
                    audio_samples=segment_samples,
                )
            )

        # Handle potential overlap caused by padding between adjacent segments
        return self._resolve_overlapping_segments(final_segments, total_duration)

    def _compute_effective_threshold(self, samples: np.ndarray) -> float:
        """Calculate dynamic energy threshold based on audio energy distribution and sensitivity setting."""
        if len(samples) == 0:
            return self.config.threshold_db

        # Dynamic adaptation: sensitivity shifts threshold up (more aggressive) or down (less aggressive)
        # sensitivity 0.5 -> use config.threshold_db
        # sensitivity 1.0 -> raise threshold by 12dB (stricter)
        # sensitivity 0.0 -> lower threshold by 12dB (lenient)
        shift = (self.config.sensitivity - 0.5) * 24.0
        target = self.config.threshold_db + shift

        # Ensure threshold is reasonable relative to maximum signal amplitude
        return max(-60.0, min(-10.0, target))

    def _load_samples(self, audio_input: np.ndarray | bytes | str, target_sr: int) -> tuple[np.ndarray, int]:
        """Convert various audio inputs into float32 numpy array (-1.0 to 1.0)."""
        if isinstance(audio_input, np.ndarray):
            samples = audio_input.astype(np.float32)
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            # Normalize int16 range to [-1.0, 1.0] if needed
            if np.max(np.abs(samples)) > 1.0:
                samples = samples / 32768.0
            return samples, target_sr

        if isinstance(audio_input, bytes):
            # Assume 16-bit PCM bytes
            int16_samples = np.frombuffer(audio_input, dtype=np.int16)
            float_samples = int16_samples.astype(np.float32) / 32768.0
            return float_samples, target_sr

        if isinstance(audio_input, str) and os.path.exists(audio_input):
            try:
                with wave.open(audio_input, "rb") as wf:
                    n_channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    sr = wf.getframerate()
                    n_frames = wf.getnframes()
                    frames = wf.readframes(n_frames)

                    if sampwidth == 2:
                        int16_samples = np.frombuffer(frames, dtype=np.int16)
                        if n_channels > 1:
                            int16_samples = int16_samples.reshape(-1, n_channels).mean(axis=1)
                        float_samples = int16_samples.astype(np.float32) / 32768.0
                        return float_samples, sr
                    if sampwidth == 4:
                        float32_samples = np.frombuffer(frames, dtype=np.float32)
                        if n_channels > 1:
                            float32_samples = float32_samples.reshape(-1, n_channels).mean(axis=1)
                        return float32_samples, sr
            except Exception as exc:
                logger.warning("Failed to parse WAV file %s: %s", audio_input, exc)

        # Fallback: empty array
        return np.array([], dtype=np.float32), target_sr

    def _try_webrtc_vad(self, samples: np.ndarray, sr: int) -> list[SpeechSegment] | None:
        """Attempt WebRTC VAD detection if webrtcvad package is installed."""
        try:
            import webrtcvad  # type: ignore

            # Map sensitivity (0..1) to WebRTC VAD mode (0..3)
            mode = min(3, max(0, int(self.config.sensitivity * 3)))
            vad = webrtcvad.Vad(mode)

            # WebRTC VAD requires 16kHz/8kHz/32kHz/48kHz PCM 16-bit
            pcm16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
            frame_duration_ms = self.config.frame_duration_ms
            if frame_duration_ms not in (10, 20, 30):
                frame_duration_ms = 30
            frame_bytes = int(sr * (frame_duration_ms / 1000.0) * 2)

            num_frames = math.ceil(len(pcm16) / frame_bytes)
            is_speech_frame = []
            for i in range(num_frames):
                chunk = pcm16[i * frame_bytes : (i + 1) * frame_bytes]
                if len(chunk) < frame_bytes:
                    chunk = chunk + b"\x00" * (frame_bytes - len(chunk))
                is_speech_frame.append(vad.is_speech(chunk, sr))

            # Build segments using standard window logic
            frame_sec = frame_duration_ms / 1000.0
            total_duration = len(samples) / sr
            raw_intervals = []
            in_speech = False
            start_time = 0.0

            for i, speech in enumerate(is_speech_frame):
                t_start = i * frame_sec
                if speech and not in_speech:
                    in_speech = True
                    start_time = t_start
                elif not speech and in_speech:
                    in_speech = False
                    raw_intervals.append((start_time, t_start))
            if in_speech:
                raw_intervals.append((start_time, total_duration))

            if not raw_intervals:
                return []

            # Merge short pauses
            max_pause_sec = self.config.max_pause_merge_ms / 1000.0
            merged = []
            cs, ce = raw_intervals[0]
            for ns, ne in raw_intervals[1:]:
                if (ns - ce) <= max_pause_sec:
                    ce = ne
                else:
                    merged.append((cs, ce))
                    cs, ce = ns, ne
            merged.append((cs, ce))

            padding_sec = self.config.padding_ms / 1000.0
            min_speech_sec = self.config.min_speech_duration_ms / 1000.0
            results = []

            for idx, (s_start, s_end) in enumerate(merged):
                raw_dur = s_end - s_start
                if raw_dur < min_speech_sec:
                    continue

                p_start = max(0.0, s_start - padding_sec)
                p_end = min(total_duration, s_end + padding_sec)
                dur = p_end - p_start
                s_samples = samples[int(p_start * sr) : int(p_end * sr)]
                results.append(
                    SpeechSegment(
                        start=p_start,
                        end=p_end,
                        duration=dur,
                        confidence=0.9,
                        segment_index=idx,
                        audio_samples=s_samples,
                    )
                )
            return self._resolve_overlapping_segments(results, total_duration)

        except ImportError:
            return None
        except Exception as exc:
            logger.warning("WebRTC VAD execution failed: %s", exc)
            return None

    def _resolve_overlapping_segments(
        self, segments: list[SpeechSegment], total_duration: float
    ) -> list[SpeechSegment]:
        """Merge any overlapping segments produced by start/end padding."""
        if not segments:
            return []

        resolved: list[SpeechSegment] = []
        curr = segments[0]

        for nxt in segments[1:]:
            if nxt.start <= curr.end:
                # Merge overlapping segments
                new_end = max(curr.end, nxt.end)
                merged_samples = None
                if curr.audio_samples is not None and nxt.audio_samples is not None:
                    # Combined array duration
                    merged_samples = np.concatenate([curr.audio_samples, nxt.audio_samples])
                curr = SpeechSegment(
                    start=curr.start,
                    end=new_end,
                    duration=new_end - curr.start,
                    confidence=max(curr.confidence, nxt.confidence),
                    segment_index=curr.segment_index,
                    audio_samples=merged_samples,
                )
            else:
                resolved.append(curr)
                curr = nxt
        resolved.append(curr)

        # Re-index
        for i, s in enumerate(resolved):
            s.segment_index = i

        return resolved


def detect_voice_activity(
    audio_input: np.ndarray | bytes | str,
    config: VADConfig | None = None,
    sample_rate: int | None = None,
) -> list[SpeechSegment]:
    """Helper function to run Voice Activity Detection on audio input."""
    detector = VoiceActivityDetector(config)
    return detector.process_audio(audio_input, sample_rate)


def is_silence_only(
    audio_input: np.ndarray | bytes | str,
    config: VADConfig | None = None,
    sample_rate: int | None = None,
) -> bool:
    """Returns True if the audio contains only silent or near-silent non-speech segments."""
    segments = detect_voice_activity(audio_input, config, sample_rate)
    return len(segments) == 0
