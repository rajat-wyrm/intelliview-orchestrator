# Frontend (Next.js)

Dashboard UI for the AI Interview Orchestrator.

## Quick start (local dev)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The dashboard will be available at <http://localhost:3000>.

## Docker

The frontend is wired into the root `docker-compose.yml` as the `frontend`
service. The Next.js app talks to the FastAPI backend via `NEXT_PUBLIC_API_URL`.

## Architecture

```
frontend/
├── src/
│   ├── app/          # Next.js App Router pages
│   │   ├── page.tsx           # Overview dashboard
│   │   ├── sessions/          # Session management
│   │   ├── workers/           # Worker registry
│   │   ├── analytics/         # Risk + retry analytics
│   │   └── settings/          # API token + strategy controls
│   ├── components/   # Reusable UI components
│   ├── lib/          # API client, types, utils
│   └── hooks/        # Data-fetching hooks
├── Dockerfile
└── package.json
```

## Adding a new page

1. Create `src/app/<route>/page.tsx`.
2. Use the `useApi` hook for data fetching.
3. Use components from `src/components/` for consistency.
