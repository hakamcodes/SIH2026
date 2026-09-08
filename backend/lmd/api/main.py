"""FastAPI app: scan -> case -> evidence -> report, plus rules introspection
and the single counters dashboard. Run with:
    uvicorn lmd.main:app --reload --port 8000
(lmd/main.py just re-exports `app` from here, per the repo map).
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import cases, images, limitations, metrics, reports, rules, scan
from .errors import register_error_handlers

app = FastAPI(
    title="Legal Metrology Compliance Scanner (SIH 26034)",
    description=(
        "Advisory pre-screening signal only. Only a Legal Metrology Officer may "
        "determine a violation and issue a notice. See /api/v1/rules for the "
        "current data-driven ruleset and /api/v1/limitations for known gaps."
    ),
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
