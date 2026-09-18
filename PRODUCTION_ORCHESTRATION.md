# Production orchestration (Google Cloud)

M4 uses a Google Compute Engine VM as the production host and Docker Compose as the application orchestrator. Managed Postgres and Redis are provided externally by the M2 task.

## Services

- `fastapi`: API service, published only on `127.0.0.1:8000` for the reverse proxy.
- `worker`: Celery worker service. It has no host port and no fixed `container_name`, so multiple replicas can run simultaneously.
- `celery-beat`: single periodic scheduler; do not scale this service.
- `cv-service`: internal CV service used by the API/worker.

## Independent worker scaling

Start the production stack:

```bash
docker compose -f docker-compose.production.yml up -d --build
```

Scale only workers:

```bash
docker compose -f docker-compose.production.yml up -d --scale worker=3 worker
```

Scale workers back down:

```bash
docker compose -f docker-compose.production.yml up -d --scale worker=1 worker
```

The API remains a separate `fastapi` service and is not recreated by these worker-only scaling commands.

## Verification

1. Confirm the API is healthy:

```bash
curl -fsS http://127.0.0.1:8000/health
```

2. Confirm the requested worker replicas exist:

```bash
docker compose -f docker-compose.production.yml ps worker
```

3. While the API health check is passing, scale workers up and down and call `/health` again. The API must remain available throughout.

4. Confirm worker registration/heartbeat through the existing worker endpoints or dashboard.

## Required production environment

Set the managed Postgres/Redis connection values and secrets through the VM's environment/secrets mechanism. Do not commit a production `.env` file or real credentials.

Required values include `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `API_TOKEN`, `JWT_SECRET_KEY`, and `CORS_ALLOW_ORIGINS`.

`DATABASE_SSLMODE` defaults to `require` in the production Compose file.

## Why this design

The development `docker-compose.yml` remains unchanged. The production file is separate so production-only orchestration changes cannot break local development. Docker Compose services are independently scalable; the worker service intentionally has no fixed container name or host port, because fixed container names prevent scaling beyond one replica.
