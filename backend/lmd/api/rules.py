"""GET /api/v1/rules -- introspect the currently loaded ruleset (proves the
rule engine really is data-driven: rules, severities, citations and
effective dates live in JSON, not in a hardcoded if/elif ladder).

POST /api/v1/rules/reload demonstrates the ruleset is hot-swappable at
runtime: it re-reads packages/rules/lmd_rules.v1.json (or LMD_RULES_PATH)
from disk without restarting the process.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .deps import get_engine, require_inspector

router = APIRouter(prefix="/api/v1", tags=["rules"])


@router.get("/rules")
def list_rules(engine=Depends(get_engine)):
    return {
        "rule_count": len(engine.rules),
        "rules": [
            {
                "rule_id": r.rule_id,
                "category": r.category,
                "description": r.description,
                "legal_basis": r.legal_basis,
                "severity": r.severity,
                "effective_from": r.effective_from,
                "effective_to": r.effective_to,
                "citation_verified": r.citation_verified,
            }
            for r in engine.rules
        ],
    }


@router.post("/rules/reload")
def reload_rules(_inspector_id: str = Depends(require_inspector)):
    get_engine.cache_clear()
    engine = get_engine()
    return {"reloaded": True, "rule_count": len(engine.rules)}
