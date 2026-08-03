# Voice Activity Detection (VAD) Guide

This guide explains how Voice Activity Detection (VAD) is implemented in our audio processing pipeline.

## How VAD Works

Before transcribing audio with Whisper, the audio passes through VAD first:

1. **Single-Pass VAD Execution**: VAD runs once on the audio recording to detect speech vs. non-speech regions. The resulting speech segments (`vad_segments`) are reused across the pipeline to prevent redundant compute.
2. **Mid-File Silence Trimming**: Silent audio sections (both leading/trailing silence and mid-file gaps between speech) are completely trimmed out. Only the extracted speech segment audio arrays are passed to Whisper.
3. **Exact Timestamp Alignment**: Each extracted speech chunk retains its absolute `start` and `end` timestamps relative to the original audio recording timeline ($t = 0\text{s}$). Whisper segment timestamps are offset by `segment.start` so the final transcript matches the original recording.
4. **Raw Duration Filtering**: Audio energy bursts are checked against `min_speech_duration_ms` before adding hangover padding, ensuring noise spikes are filtered out.
5. **Partial Frame Support**: Frame calculations use ceiling division (`math.ceil`) to ensure the final partial audio frame is evaluated rather than dropped.

---

## Benefits

- **Reduces Compute Usage**: Whisper never processes silent gaps.
- **Lowers Latency**: Non-speech sections are skipped instantly.
- **Prevents Hallucinations**: Background room noise and static cannot generate false transcriptions.
- **Preserves Timestamps**: Transcribed text remains perfectly aligned with the original recording.

---

## Configuration (`VADConfig`)

You can tune VAD settings via environment variables or by passing a custom `VADConfig` object.

| Option | Env Variable | Default | What it does |
|---|---|---|---|
| `sensitivity` | `VAD_SENSITIVITY` | `0.5` | Sensitivity from `0.0` (keep more audio) to `1.0` (stricter cut-off). |
| `threshold_db` | `VAD_THRESHOLD_DB` | `-40.0` | RMS energy threshold in dB. Audio louder than this is classified as speech. |
| `frame_duration_ms` | `VAD_FRAME_DURATION_MS` | `30` | Frame size in milliseconds (10, 20, or 30 ms). |
| `min_speech_duration_ms` | `VAD_MIN_SPEECH_MS` | `150` | Minimum speech duration in ms (checked before padding to drop noise spikes). |
| `padding_ms` | `VAD_PADDING_MS` | `200` | Extra hangover padding in ms added to start and end of speech segments. |
| `max_pause_merge_ms` | `VAD_MAX_PAUSE_MERGE_MS` | `300` | Maximum pause duration in ms between speech frames to merge together. |
| `sample_rate` | `VAD_SAMPLE_RATE` | `16000` | Target audio sample rate in Hz. |

---

## Code Examples

### Running VAD on an Audio File
```python
from workers.vad import VADConfig, VoiceActivityDetector

config = VADConfig(threshold_db=-38.0, padding_ms=200)
detector = VoiceActivityDetector(config)

segments = detector.process_audio("interview_session.wav")

for seg in segments:
    print(f"Speech segment: [{seg.start:.2f}s - {seg.end:.2f}s] (duration: {seg.duration:.2f}s)")
```

### Running Pipeline Transcription with VAD
```python
from workers.audio_pipeline import run_audio_analysis, transcribe_speech
from workers.vad import VADConfig

config = VADConfig(sensitivity=0.6)

# Transcribe with VAD pre-filtering & mid-file silence trimming
result = transcribe_speech("session-123", vad_config=config)
print("Transcript:", result["text"])
print("Speech detected:", result["speech_detected"])

# Full audio pipeline run
analysis = run_audio_analysis("session-123", vad_config=config)
print("Risk score:", analysis["risk_score"])
```
