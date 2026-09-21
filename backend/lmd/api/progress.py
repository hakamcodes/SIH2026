"""NDJSON stage-progress streaming for the two long-running scan endpoints.

Both /api/v1/scans and /api/v1/scans/multi run entirely inside a single
request/response cycle -- there is no background job queue in this prototype
(CLAUDE.md scope boundary), and render.yaml runs uvicorn with
--limit-concurrency 1 because the 512MB Render free tier cannot hold two
concurrent scans' pipeline arrays. A job-id + poll or job-id + SSE design
needs a second concurrent connection, which would either deadlock behind the
in-flight scan or force raising that concurrency limit -- reintroducing the
exact memory overlap it exists to prevent. Streaming NDJSON lines over the
*same* connection is the only progress design compatible with that
constraint.

A caller opts in by sending `Accept: application/x-ndjson`; anything else
gets the plain JSON response, byte-identical to the pre-streaming behaviour,
so backend/tests/test_api_smoke.py and lmd.cli need no changes.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

NDJSON_MEDIA_TYPE = "application/x-ndjson"


def wants_ndjson(request: Request) -> bool:
    return NDJSON_MEDIA_TYPE in request.headers.get("accept", "")


class ProgressReporter:
    """Emits stage events from worker threads (inside asyncio.to_thread) to
    an asyncio.Queue drained on the event loop -- `stage()`/`panel_done()`
    are safe to call from a non-event-loop thread. `total` is fixed at
    construction (computed from the request's panel count before any
    pipeline work starts) so the browser gets a genuinely determinate
    index/total progress bar, not a guessed percentage.
    """

    def __init__(self, total: int) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._total = total
        self._index = 0

    def stage(self, panel: str | None, key: str, label: str, detail: str | None = None) -> None:
        self._index += 1
        payload: dict[str, Any] = {
            "event": "stage",
            "stage": key,
            "label": label,
            "index": min(self._index, self._total),
            "total": self._total,
        }
        if panel is not None:
            payload["panel"] = panel
        if detail is not None:
            payload["detail"] = detail
        self._emit(payload)

    def panel_done(self, panel: str, fields: int) -> None:
        self._emit({"event": "panel_done", "panel": panel, "fields": fields})

    def _emit(self, payload: dict[str, Any]) -> None:
        self._loop.call_soon_threadsafe(self._queue.put_nowait, payload)

    def _close(self) -> None:
        self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

    async def _drain(self):
        while True:
            item = await self._queue.get()
            if item is None:
                return
            yield item


async def ndjson_response(
    total: int,
    work: Callable[[ProgressReporter], Awaitable[dict[str, Any]]],
) -> StreamingResponse:
    """Run `work(reporter)` concurrently with streaming whatever it emits via
    `reporter`. The coroutine's return value is streamed as a final
    `{"event": "result", ...}` line -- exactly the dict the plain-JSON
    endpoint returns today. A raised HTTPException, or any other exception,
    becomes a terminal `{"event": "error", ...}` line instead: once the 200
    status and NDJSON body have started, there is no HTTP status code left
    to change, so failures must be signalled in-band."""
    reporter = ProgressReporter(total)

    async def _runner() -> None:
        try:
            result = await work(reporter)
            reporter._emit({"event": "result", **result})
        except HTTPException as exc:
            reporter._emit({"event": "error", "status": exc.status_code, "detail": exc.detail})
        except Exception:  # noqa: BLE001 -- must reach the client as an event, never as a hung connection
            logger.exception("scan pipeline failed mid-stream")
            reporter._emit(
                {"event": "error", "status": 500, "detail": "internal error during scan processing"}
            )
        finally:
            reporter._close()

    task = asyncio.ensure_future(_runner())

    async def _generate():
        async for event in reporter._drain():
            yield (json.dumps(event) + "\n").encode("utf-8")
        await task  # surface a task-level crash (e.g. in _runner itself) to the ASGI server

    return StreamingResponse(
        _generate(),
        media_type=NDJSON_MEDIA_TYPE,
        headers={
            # Disable proxy buffering (nginx-style reverse proxies respect
            # this header) so lines reach the client as they're produced
            # instead of arriving in one burst at the end.
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-store, no-transform",
        },
    )
