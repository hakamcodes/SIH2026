"""Shared FastAPI dependencies: a per-request sqlite connection, the shared
rule engine instance, and inspector auth.

Auth is deliberately minimal: the research spec (database-api-data-model.md)
only ever says "Bearer token, Inspector role required" with no login
endpoint, no session table, and no RBAC model. Building a full auth system
was not asked for and would be scope creep beyond the vertical slice
(CLAUDE.md section 1). This checks a single shared bearer token
(LMD_INSPECTOR_API_TOKEN) and requires the caller to state which inspector
they are acting as -- real enough to gate write access in a single-inspector
demo, explicitly not a multi-user RBAC system.
"""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Header, HTTPException

from lmd import config
from lmd.engine.engine import RuleEngine
from lmd.engine.loader import load_rules


@lru_cache(maxsize=1)
def get_engine() -> RuleEngine:
    return RuleEngine(load_rules(config.RULES_PATH))


def get_db():
    from lmd.store.db import connect

    conn = connect(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def require_inspector(
    authorization: str = Header(default=""),
    x_inspector_id: str = Header(default=""),
) -> str:
    expected = os.environ.get("LMD_INSPECTOR_API_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="LMD_INSPECTOR_API_TOKEN is not configured on the server; inspector actions are disabled.",
        )
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid or missing inspector bearer token.")
    if not x_inspector_id:
        raise HTTPException(status_code=400, detail="X-Inspector-Id header is required for this action.")
    return x_inspector_id
