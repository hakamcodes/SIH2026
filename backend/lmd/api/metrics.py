"""GET /api/v1/metrics -- the single counters page (CLAUDE.md section 1:
"a single counters page is the only dashboard"). No state/district/platform
breakdown; that tiering is out of scope."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from lmd.store import repository

from .deps import get_db

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics")
def dashboard_metrics(conn=Depends(get_db)):
    return repository.dashboard_counters(conn)
