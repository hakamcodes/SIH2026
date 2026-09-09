# LMD frontend (Next.js)

Talks to the FastAPI backend only through the server-side proxy at
`src/app/api/lmd/[...path]/route.ts` -- the browser never calls the backend
directly, so `LMD_INSPECTOR_API_TOKEN` never reaches client-side code.

## Local development

```bash
npm install
npm run dev
```

Requires the backend running locally (`uvicorn lmd.main:app --reload --port 8000`
from `backend/`) plus a local `.env.local` with at least:

```
LMD_BACKEND_URL=http://localhost:8000
LMD_INSPECTOR_API_TOKEN=<same value as the backend's LMD_INSPECTOR_API_TOKEN>
```

## Deploying on Vercel

1. Import this repo into Vercel, set the project root to `frontend/`.
2. Set these environment variables in the Vercel project settings (server-side
   only -- do not prefix with `NEXT_PUBLIC_`, or they'd ship to the browser):
   - `LMD_BACKEND_URL` -- the deployed backend's URL (e.g. the Render service
     from `render.yaml` at the repo root).
   - `LMD_INSPECTOR_API_TOKEN` -- must match the backend's `LMD_INSPECTOR_API_TOKEN`
     exactly.
3. Deploy. No build-time env vars are required -- every backend call happens
   at request time through the proxy route, not during `next build`.
