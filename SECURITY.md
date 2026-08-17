# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security bugs.**

Email **rajatkumar7861813@gmail.com** with:
- A short description of the issue
- Steps to reproduce, including any session IDs / sample payloads
- The impact you believe it has (auth bypass, info leak, RCE, …)

You should receive an acknowledgement within 72 hours and a status update
every 7 days until the fix ships.

## Production hardening checklist

Before exposing this service to the public internet:

- [ ] Set a strong, unique `API_TOKEN` (>= 32 random bytes, base64).
      Default `"dev-token-change-me"` is rejected by the lifetime
      warning logged at startup.
- [ ] Set `CORS_ALLOW_ORIGINS` to an explicit, comma-separated list of
      trusted origins. Do **not** use `*` with credentials.
- [ ] Front the API with a TLS-terminating reverse proxy (nginx, Caddy,
      Traefik). Never expose `uvicorn` directly to the internet.
- [ ] Run Postgres and Redis on private subnets; restrict by network
      policy, not just password.
- [ ] Rotate `API_TOKEN` and any DB credentials regularly.
- [ ] Enable structured JSON logs (`JSON_LOGGING=1`) and ship them to
      your log aggregator.
- [ ] Mount the Docker image as non-root (already the default in the
      provided `Dockerfile`).
- [ ] Restrict `/switch-strategy`, `/retry-session/{id}`, and
      `/detect-failures` to admin-only callers via your reverse proxy
      if your `API_TOKEN` is shared with broader automation.

## Threat model (current)

- **Trusted operators** hold the `API_TOKEN`. They can start interviews,
  register workers, switch strategies, and trigger retries.
- **Workers** hold the same `API_TOKEN` in this release; a future
  release will split worker and operator scopes.
- **Public candidates** do not authenticate directly; their interview
  media is expected to flow through an ingest service you operate.
- **Database and Redis** are assumed to be on a private network.

## Dependencies

We run Dependabot (see `.github/dependabot.yml`) and review alerts
weekly. Security-relevant advisories are patched within 7 days of
release.
