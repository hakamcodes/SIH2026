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


def _warm_ocr_engine() -> None:
    # Constructing RapidOCR() only loads the ONNX model files; the first
    # real inference call still pays extra one-time session/graph
    # initialization cost on top of that (measured: ~10s slower than every
    # call after it). Run one throwaway detect+cls+rec pass now so that
    # cost lands at server startup, not on a demo's first upload.
    import numpy as np

    from lmd.cv.pipeline_a import _get_engine as get_ocr_engine

    engine = get_ocr_engine()
    engine(np.zeros((64, 64, 3), dtype=np.uint8), use_det=True, use_cls=True, use_rec=True)


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001 -- FastAPI lifespan signature
    # RapidOCR's ONNX model load/first-inference and the rule-engine JSON
    # load all cost real wall time; paying it once at startup instead of on
    # the first request means a demo's first upload isn't the slowest one.
    await asyncio.to_thread(_warm_ocr_engine)
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
