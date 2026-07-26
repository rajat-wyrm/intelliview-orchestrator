# Celery Workers — `intelliview-orchestrator`

This module implements the **asynchronous processing pipeline** for interview sessions. It picks up a session from the queue, runs video and audio analysis in parallel, evaluates the candidate's answers, computes a risk score, and persists the final result — all coordinated through Celery with Redis as the broker and result backend.

---

## 📁 Module Contents

| File | Responsibility |
|---|---|
| `celery_app.py` | Celery application instance, reliability config, Beat schedule, and the `task_failure` signal handler |
| `tasks.py` | The actual task definitions and the pipeline orchestration logic |
| `video_pipeline.py` | Video analysis stage (invoked by `_run_video`) |
| `audio_pipeline.py` | Audio analysis stage (invoked by `_run_audio`) |
| `evaluation_pipeline.py` | Answer evaluation stage |
| `risk_engine.py` | Final risk scoring, run after evaluation |

---

## ⚙️ Celery Configuration (`celery_app.py`)

The Celery app (`interview_tasks`) is initialised with Redis as **both broker and result backend**, and tuned for reliability over raw throughput:

- **Serialization**: JSON only (`task_serializer`, `result_serializer`, `accept_content`)
- **Time limits**: 30 min hard limit, 25 min soft limit per task
- **`task_acks_late=True`**: a task is only acknowledged after it completes — if a worker dies mid-task, the job is redelivered instead of lost
- **`task_reject_on_worker_lost=True`**: guarantees a lost worker's task isn't silently dropped
- **`worker_prefetch_multiplier=1`**: ensures fair task distribution across workers instead of one worker hoarding a batch
- **`broker_connection_retry_on_startup=True`**: workers keep retrying the Redis connection on boot instead of crashing
- **Autodiscovery**: `celery_app.autodiscover_tasks(["workers"])` automatically registers all tasks defined under `workers/`

### Failure handling
A `task_failure` signal handler is registered so that a session is only marked `FAILED` **after Celery has exhausted its retries** — not on every transient error. This avoids flapping a session's status on temporary issues (e.g. a brief Redis blip) and only surfaces a real failure once retries are genuinely exhausted.

### Scheduled task (Celery Beat)
A periodic task, `scan_and_dispatch_retries`, runs every **60 seconds** to catch and re-dispatch any sessions whose retry window has elapsed (see below).

---

## 🔄 Celery Workflow (`tasks.py`)

Each interview session moves through a defined pipeline of states:

```
QUEUED → PROCESSING → VIDEO_PROCESSING (+ AUDIO in parallel) → EVALUATING → COMPLETED
```

### 1. Entry point — `process_interview_session`
- Fetches the session from Postgres; resets `FAILED` sessions back to `QUEUED` for a clean retry
- Updates status to `PROCESSING`, records the assigned worker hostname and start time
- Dispatches a **Celery `group`** running `_run_video` and `_run_audio` **in parallel**
- Blocks (with a 600s timeout) until both finish, then hands off to `_after_parallel`
- On any exception, retries with **exponential backoff** (`2^attempt` seconds, up to 3 attempts) via `self.retry(...)`

### 2. Parallel stage tasks
- `_run_video` → calls `video_pipeline.run_video_analysis`
- `_run_audio` → calls `audio_pipeline.run_audio_analysis`
- Each has its own retry budget (`max_retries=3`) independent of the parent task

### 3. Post-parallel callback — `_after_parallel`
Once both video and audio results are available:
1. Status updated to `EVALUATING`
2. `evaluate_answers()` scores the candidate's responses
3. `RiskScoringEngine.generate_risk_report()` combines video, audio, and evaluation results into a final risk score + classification
4. Results are written to Postgres (`InterviewSession` row), the session is marked `COMPLETED`, and its Redis state is cleared

### 4. Retry scanning — `scan_and_dispatch_retries` (Beat, every 60s)
Scans Redis for `retry_scheduled:*` keys whose `retry_after` timestamp has passed, and re-dispatches those sessions through the normal `Scheduler` with `TaskPriority.MEDIUM`, then deletes the processed key.

---

## 📊 Metrics & Observability

Worker activity is exported in Prometheus format via `monitoring/prometheus_metrics.py`, and visualized in Grafana. The metrics directly relevant to this module:

**Worker health**
| Metric | Type | Description |
|---|---|---|
| `intelliview_workers_registered` | Gauge | Number of registered workers |
| `intelliview_workers_healthy` / `intelliview_workers_unhealthy` | Gauge | Healthy vs. unhealthy worker counts |
| `intelliview_worker_active_tasks{worker_id}` | Gauge | Active tasks per worker |
| `intelliview_worker_capacity{worker_id}` | Gauge | Capacity per worker |
| `intelliview_worker_heartbeat_age_seconds{worker_id}` | Gauge | Seconds since a worker's last heartbeat — flags stalled/dead workers |

**Session & pipeline processing**
| Metric | Type | Description |
|---|---|---|
| `intelliview_sessions_created_total` / `_completed_total` / `_failed_total` | Counter | Session lifecycle counts |
| `intelliview_sessions_active` | Gauge | Currently active sessions |
| `intelliview_session_processing_duration_seconds` | Histogram | End-to-end session processing time (buckets 1s–600s) |
| `intelliview_pipeline_latency_seconds{stage}` | Histogram | Per-stage latency (video / audio / evaluation) |
| `intelliview_pipeline_errors_total{stage, error_type}` | Counter | Errors per pipeline stage |
| `intelliview_risk_score` | Histogram | Distribution of generated risk scores |

**Retry / fault tolerance**
| Metric | Type | Description |
|---|---|---|
| `intelliview_retries_total` | Counter | Total retry attempts across tasks |
| `intelliview_failures_total{failure_type}` | Counter | Failures by type, post-retry |
| `intelliview_dead_letter_queue_size` | Gauge | Sessions that exhausted retries |
| `intelliview_queue_depth` | Gauge | Current Celery queue depth |
| `intelliview_circuit_breaker_state` | Gauge | 0=closed, 1=open, 2=half_open |

These map directly onto the worker code's behavior: `task_track_started`, the retry/backoff logic in `process_interview_session`, and the `task_failure` signal handler in `celery_app.py` are the natural emission points for the retry, failure, and latency metrics above. Metrics are scraped from `/metrics` and rendered on Grafana dashboards (see `monitoring/grafana/provisioning`).

---

## 🧵 Concurrency Model

- **Video + audio run in parallel** per session via `celery.group`, minimizing per-session latency
- **Evaluation + risk scoring run sequentially**, since they depend on both prior results
- **Horizontal scaling**: additional worker processes/nodes can be added freely since `worker_prefetch_multiplier=1` ensures even task distribution, and `task_acks_late` + `task_reject_on_worker_lost` make it safe to kill/restart workers without losing in-flight jobs

---

## 🚀 Running a Worker

```bash
celery -A workers.celery_app worker --loglevel=info
```

To run the periodic retry-scanning beat schedule:

```bash
celery -A workers.celery_app beat --loglevel=info
```
