# Workers

This folder holds the Celery worker code that actually runs an interview
session: video analysis, audio analysis, answer evaluation, and risk
scoring. If you're trying to understand how a session moves from "just
submitted" to "here's the risk report," this is the place to look.

## What's in here

- `celery_app.py` – Celery app + broker/backend setup, plus the
  `task_failure` signal that marks a session `FAILED` only once retries run
  out.
- `tasks.py` – the actual task graph: `process_interview_session`,
  `_run_video`, `_run_audio`, `_after_parallel`, and the beat job
  `scan_and_dispatch_retries`.
- `video_pipeline.py`, `audio_pipeline.py`, `evaluation_pipeline.py` – the
  three analysis stages.
- `risk_engine.py` – combines all three stage outputs into a final risk
  score/report.
- `ai_client.py` – shared client the pipelines use to talk to the AI
  provider.
- `worker_agent.py` / `worker_entrypoint.py` – how a worker process boots.
- `_stubs.py` – fakes used for local/test runs.

Session state itself isn't owned here — it lives in
[`SessionManager`](../orchestrator/session_manager.py), synced across
Postgres and Redis by [`StateSynchronizer`](../orchestrator/state_sync.py).
This code just calls into that.

## How this folder fits into the rest of the system

```mermaid
flowchart TB
    subgraph API["Orchestrator (orchestrator/)"]
        SCH[Scheduler]
        SM[SessionManager]
        SS[StateSynchronizer]
        RM[RetryManager]
        HM[HealthMonitor]
    end

    subgraph WORK["Workers (workers/)"]
        CA[celery_app.py]
        TK[tasks.py]
        VP[video_pipeline.py]
        AP[audio_pipeline.py]
        EP[evaluation_pipeline.py]
        RE[risk_engine.py]
        AI[ai_client.py]
    end

    subgraph STORE["Storage"]
        PG[(Postgres)]
        RD[(Redis)]
    end

    SCH -->|dispatch session_id| TK
    TK --> VP
    TK --> AP
    TK --> EP
    EP --> AI
    VP --> AI
    AP --> AI
    TK --> RE
    TK -->|status updates| SM
    SM --> PG
    SM --> RD
    SS --> PG
    SS --> RD
    RM --> RD
    HM -->|scans for stuck sessions| PG
    CA -->|task_failure signal| SM
    TK -->|scan_and_dispatch_retries| RM
    RM -->|retry_scheduled keys| SCH
```

Nothing in `workers/` talks to Postgres or Redis directly except through
`SessionManager` — the pipelines themselves (`video_pipeline.py`,
`audio_pipeline.py`, `evaluation_pipeline.py`) are mostly stateless, they
just get a `session_id`, do their analysis, and hand a dict back up to
`tasks.py`.

## How a session actually flows through this

`process_interview_session` is the one entry point the
[`Scheduler`](../orchestrator/scheduler.py) calls. Roughly:

1. If the session was previously `FAILED`, it gets reset to `QUEUED` for
   another go.
2. Session flips to `PROCESSING`, worker hostname gets recorded.
3. Session flips to `VIDEO_PROCESSING`, and video + audio analysis run at
   the same time as a Celery `group` (they don't depend on each other, so
   no reason to run them sequentially).
4. Once both come back, `_after_parallel` takes over: marks the session
   `EVALUATING`, runs answer evaluation, then risk scoring, then writes
   everything to Postgres and marks it `COMPLETED`.
5. If `process_interview_session` throws anywhere, it calls `self.retry(...)`
   with a backoff of `2 ** attempt` seconds, up to 3 attempts. Note that the
   session is **not** immediately marked `FAILED` on an exception — that only
   happens once Celery gives up, via the `task_failure` signal in
   `celery_app.py`.
6. Separately, `scan_and_dispatch_retries` runs every 60s (Celery Beat),
   checks Redis for anything whose scheduled retry time has passed, and
   re-dispatches it through the Scheduler.

Here's the same thing as a sequence diagram, since the parallel step trips
people up the most:

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant T as process_interview_session
    participant V as _run_video
    participant A as _run_audio
    participant P as _after_parallel
    participant R as RiskScoringEngine
    participant DB as Postgres / Redis

    S->>T: dispatch(session_id)
    T->>DB: status = PROCESSING
    T->>DB: status = VIDEO_PROCESSING
    par video + audio run together
        T->>V: _run_video.s(session_id)
        T->>A: _run_audio.s(session_id)
    end
    V-->>T: video_result
    A-->>T: audio_result
    T->>P: _after_parallel(video_result, audio_result)
    P->>DB: status = EVALUATING
    P->>P: evaluate_answers(session_id)
    P->>R: generate_risk_report(...)
    R-->>P: risk_report
    P->>DB: persist results, status = COMPLETED
```

## State machine

First, the path a session actually takes in normal operation — this is
what `process_interview_session` and `_after_parallel` walk every time,
with no exceptions and no retries:

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> QUEUED
    QUEUED --> PROCESSING
    PROCESSING --> VIDEO_PROCESSING
    VIDEO_PROCESSING --> AUDIO_PROCESSING
    AUDIO_PROCESSING --> EVALUATING
    EVALUATING --> COMPLETED
    COMPLETED --> [*]
```

Now here's the full picture — every transition the
*validator* allows, per `SessionManager.VALID_TRANSITIONS`. It's a lot
busier than the happy path above because the validator is more permissive
than the code that actually runs: it allows things like resuming from
`EVALUATING` back to `PROCESSING`, or `QUEUED` jumping straight to
`VIDEO_PROCESSING`, that `tasks.py` never actually exercises today. Treat
this one as "what's technically legal," not "what commonly happens":

```mermaid
stateDiagram-v2
    [*] --> CREATED

    CREATED --> QUEUED
    CREATED --> FAILED
    CREATED --> CANCELLED

    QUEUED --> PROCESSING
    QUEUED --> FAILED
    QUEUED --> CANCELLED

    PROCESSING --> VIDEO_PROCESSING
    PROCESSING --> AUDIO_PROCESSING
    PROCESSING --> EVALUATING
    PROCESSING --> COMPLETED
    PROCESSING --> FAILED
    PROCESSING --> TIMEOUT

    VIDEO_PROCESSING --> AUDIO_PROCESSING
    VIDEO_PROCESSING --> PROCESSING
    VIDEO_PROCESSING --> FAILED
    VIDEO_PROCESSING --> TIMEOUT

    AUDIO_PROCESSING --> EVALUATING
    AUDIO_PROCESSING --> PROCESSING
    AUDIO_PROCESSING --> FAILED
    AUDIO_PROCESSING --> TIMEOUT

    EVALUATING --> COMPLETED
    EVALUATING --> PROCESSING
    EVALUATING --> FAILED
    EVALUATING --> TIMEOUT

    TIMEOUT --> FAILED

    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

A quick word on each state, and who's responsible for setting it:

- **CREATED** – session row exists, nothing has happened yet
  (`SessionManager.create_session`).
- **QUEUED** – sitting in line for a worker (`Scheduler`).
- **PROCESSING** – a worker has picked it up and is about to start the
  actual stages (`process_interview_session`).
- **VIDEO_PROCESSING** – video + audio are running in parallel; this is the
  status shown while both are in flight (`process_interview_session`).
- **AUDIO_PROCESSING** – part of the same valid-transition set for the
  audio side; in practice video and audio run together under one
  `VIDEO_PROCESSING` status update (`session_manager.py`).
- **EVALUATING** – both analysis stages are done, now scoring the answers
  and building the risk report (`_after_parallel`).
- **COMPLETED** – terminal, risk report is saved (`_after_parallel`).
- **FAILED** – terminal, either retries got exhausted or something broke
  post-parallel (`celery_app.py`'s `task_failure` handler, or
  `_after_parallel`'s except block).
- **TIMEOUT** – a stage took too long and `HealthMonitor` flagged it; always
  rolls into `FAILED` next.
- **CANCELLED** – terminal, session was cancelled before it ever got picked
  up (`SessionManager`).

## Retries, failures, timeouts

There are actually two layers of retry logic and it's easy to conflate
them:

- **Task-level retries** — plain Celery retry with exponential backoff,
  handled inside `process_interview_session`, `_run_video`, `_run_audio`
  (`max_retries=3`, delay = `2 ** attempt` seconds).
- **Session-level retry bookkeeping** — `RetryManager` tracks attempt counts
  and schedules a retry time in Redis; `scan_and_dispatch_retries` is what
  actually notices that time has passed and kicks the session back into the
  scheduler.

```mermaid
flowchart TD
    A[Task raises exception] --> B{Retries left? max_retries=3}
    B -- yes --> C["self.retry(countdown=2**attempt)"]
    C --> A
    B -- no --> D[task_failure signal fires]
    D --> E[Session marked FAILED]
    E --> F[RetryManager.schedule_retry]
    F --> G[retry_scheduled:* key in Redis]
    G --> H[Beat job: scan_and_dispatch_retries every 60s]
    H --> I{retry_after has passed?}
    I -- no --> H
    I -- yes --> J[Scheduler.schedule_task]
    J --> A
```

Stuck sessions (stuck, not failed — e.g. a worker died mid-task) are caught
separately by `HealthMonitor.detect_stuck_sessions`, using the
`PROCESSING_TIMEOUT` / `QUEUED_TIMEOUT` thresholds defined on
`SessionManager`. That path looks like this:

```mermaid
flowchart TD
    A[HealthMonitor runs periodically] --> B[Scan sessions in PROCESSING / QUEUED / VIDEO_PROCESSING / AUDIO_PROCESSING / EVALUATING]
    B --> C{Time in current state > threshold?}
    C -- "PROCESSING > PROCESSING_TIMEOUT" --> D[Mark session TIMEOUT]
    C -- "QUEUED > QUEUED_TIMEOUT" --> D
    C -- no --> A
    D --> E[TIMEOUT --> FAILED]
    E --> F[RetryManager.schedule_retry]
    F --> G[Picked up by scan_and_dispatch_retries later]
```

This is a separate mechanism from the Celery-level retry in
`process_interview_session` — that one fires from inside the task when an
exception is raised. `HealthMonitor` instead catches the case where nothing
raised an exception at all; the worker process just died, got OOM-killed,
or lost its connection, and the session is left sitting in a
non-terminal state with nobody actively working on it.

## Gotcha: FAILED isn't actually terminal

The state diagram above shows `FAILED` with no way out, because that's what
`SessionManager.VALID_TRANSITIONS` says. In practice there's a bypass, right
at the top of `process_interview_session`:

```python
if interview.status == "FAILED":
    interview.status = "QUEUED"
    db_session.commit()
```

`scan_and_dispatch_retries` doesn't check a session's current status before
re-dispatching it — it just reads `retry_scheduled:*` keys from Redis and
fires the session_id back into the `Scheduler` once the retry time has
passed. So when the task runs again, Postgres may still say `FAILED`, and
this line quietly flips it back to `QUEUED` and carries on — bypassing
`session_manager.update_session_status()` entirely (no validation, no
Redis sync through the normal path, just a direct write).

```mermaid
flowchart LR
    A[Session status: FAILED] --> B[scan_and_dispatch_retries fires]
    B --> C[Scheduler.schedule_task re-dispatches]
    C --> D[process_interview_session starts]
    D --> E{status == FAILED?}
    E -- yes --> F["interview.status = QUEUED\n(direct write, bypasses SessionManager)"]
    F --> G[continues into PROCESSING as normal]
    E -- no --> G
```

Two things worth knowing if you're touching this code:

- This reset doesn't check `RetryManager`'s attempt count or the Celery-level
  `self.request.retries` counter — they're separate tallies from this check.
  Anything that re-dispatches a `FAILED` session_id (a bug, a manual retry,
  a duplicate beat tick) gets it un-failed with no extra gate.
- If you're debugging "why did this failed session start processing again
  with no obvious retry log," this is the line to check first.

## Where to look next

- [`orchestrator/session_manager.py`](../orchestrator/session_manager.py) — source of truth for state transitions.
- [`orchestrator/state_sync.py`](../orchestrator/state_sync.py) — Postgres/Redis sync.
- [`orchestrator/scheduler.py`](../orchestrator/scheduler.py) — how sessions get dispatched to workers.
- [`orchestrator/retry_manager.py`](../orchestrator/retry_manager.py) — retry attempt tracking + backoff scheduling.
- [`orchestrator/health_monitor.py`](../orchestrator/health_monitor.py) — timeout/stuck-session detection.
- [`monitoring/dashboard.html`](../monitoring/dashboard.html), [`monitoring/metrics_collector.py`](../monitoring/metrics_collector.py) — live view of what's happening.
- [Celery docs](https://docs.celeryq.dev/en/stable/) — for the retry/group/beat mechanics referenced above.
