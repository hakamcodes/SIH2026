"""GET /api/v1/limitations -- surfaces every known gap explicitly, built
from the sentinel files in packages/rules/ rather than a hand-maintained
list, per CLAUDE.md section 4.2: "state this plainly rather than letting a
judge discover it."
"""
from __future__ import annotations

from fastapi import APIRouter

from lmd.limitations import get_known_limitations

router = APIRouter(prefix="/api/v1", tags=["limitations"])


@router.get("/limitations")
def list_limitations():
    return get_known_limitations()
