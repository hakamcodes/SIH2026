"""Shared FastAPI exception handlers. The reason-to-believe 422 is the one
that matters most (CLAUDE.md invariant 12: "Advancing a case without a
recorded note returns 422 citing Section 15(4)")."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lmd.store.repository import ReasonToBelieveRequired


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReasonToBelieveRequired)
    async def _reason_to_believe_handler(request: Request, exc: ReasonToBelieveRequired):  # noqa: ARG001
        return JSONResponse(
            status_code=422,
            content={
                "error": "reason_to_believe_required",
                "detail": str(exc),
                "legal_basis": "Section 15(4), Legal Metrology Act 2009",
            },
        )

    @app.exception_handler(KeyError)
    async def _not_found_handler(request: Request, exc: KeyError):  # noqa: ARG001
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": str(exc)})
