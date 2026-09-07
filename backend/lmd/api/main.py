"""FastAPI app: scan -> case -> evidence -> report, plus rules introspection
and the single counters dashboard. Run with:
    uvicorn lmd.main:app --reload --port 8000
(lmd/main.py just re-exports `app` from here, per the repo map).
"""
from __future__ import annotations

from fastapi import FastAPI

from . import cases, limitations, metrics, reports, rules, scan
from .errors import register_error_handlers

app = FastAPI(
    title="Legal Metrology Compliance Scanner (SIH 26034)",
    description=(
        "Advisory pre-screening signal only. Only a Legal Metrology Officer may "
        "determine a violation and issue a notice. See /api/v1/rules for the "
        "current data-driven ruleset and /api/v1/limitations for known gaps."
    ),
)

register_error_handlers(app)
app.include_router(scan.router)
app.include_router(cases.router)
app.include_router(rules.router)
app.include_router(reports.router)
app.include_router(metrics.router)
app.include_router(limitations.router)


@app.get("/health")
def health():
    return {"status": "ok"}
