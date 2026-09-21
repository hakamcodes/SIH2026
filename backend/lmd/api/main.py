"""FastAPI app: scan -> case -> evidence -> report, plus rules introspection
and the single counters dashboard. Run with:
    uvicorn lmd.main:app --reload --port 8000
(lmd/main.py just re-exports `app` from here, per the repo map).
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import cases, images, limitations, metrics, reports, rules, scan, scan_multi
from .deps import get_engine
from .errors import register_error_handlers


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001 -- FastAPI lifespan signature
    # RapidOCR's ONNX det/cls/rec sessions are the single largest contributor
    # to idle RSS (~200-350 MB) on Render's 512 MB free tier -- loading them
    # here at boot pushed the process near the OOM ceiling before a single
    # scan ever ran. lmd.cv.pipeline_a._get_engine is @lru_cache(maxsize=1),
    # so leaving it unloaded costs only a ~10s one-time init on the first real
    # scan, not every scan. Only the rule-engine JSON load happens at startup;
    # a bad ruleset must still fail fast (CLAUDE.md invariant 3).
    await asyncio.to_thread(get_engine)
    yield


app = FastAPI(
    title="Legal Metrology Compliance Scanner (SIH 26034)",
    description=(
        "Advisory pre-screening signal only. Only a Legal Metrology Officer may "
        "determine a violation and issue a notice. See /api/v1/rules for the "
        "current data-driven ruleset and /api/v1/limitations for known gaps."
    ),
    lifespan=_lifespan,
)

# Frontend Phase 0: the API had no CORS policy at all, which blocks every
# browser-based frontend outright. LMD_CORS_ORIGINS is a comma-separated
# allowlist; default covers the Next.js dev server only.
_cors_origins = [
    origin.strip()
    for origin in os.environ.get("LMD_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(scan_multi.router)  # must come before scan.router so /scans/multi is matched before /scans/{id}
app.include_router(scan.router)
app.include_router(cases.router)
app.include_router(rules.router)
app.include_router(reports.router)
app.include_router(metrics.router)
app.include_router(limitations.router)
app.include_router(images.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/health")
def health_v1():
    # The frontend's Next.js proxy rewrites /api/lmd/<path> to
    # /api/v1/<path> (see route.ts), so the wake-up/keep-alive poll needs a
    # health route under the versioned prefix -- Render's own health check
    # keeps using unprefixed /health above.
    return {"status": "ok"}
