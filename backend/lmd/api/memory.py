"""Resident-set measurement and an explicit return-memory-to-the-OS call.

`gc.collect()` frees Python objects but glibc keeps the freed arenas mapped, so
RSS stays at its high-water mark. On the 512MB Render free tier that means each
panel of a multi-panel scan ratchets RSS upward instead of reusing the previous
panel's space. `malloc_trim(0)` is what actually hands the arenas back.

Both functions are no-ops off Linux so the Windows dev loop is unaffected.
"""
from __future__ import annotations

import ctypes
import gc
import logging
import os
import sys

logger = logging.getLogger(__name__)

_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def rss_mb() -> float:
    """Current resident set size in MiB, or 0.0 where /proc is unavailable."""
    try:
        with open("/proc/self/statm", encoding="utf-8") as handle:
            resident_pages = int(handle.read().split()[1])
    except (OSError, IndexError, ValueError):
        return 0.0
    return resident_pages * _PAGE_SIZE / (1024 * 1024)


def _load_malloc_trim():
    if not sys.platform.startswith("linux"):
        return None
    try:
        libc = ctypes.CDLL("libc.so.6")
        return libc.malloc_trim
    except (OSError, AttributeError):
        # musl-based images have no malloc_trim; reclaiming is best-effort and
        # must never break a scan.
        logger.info("malloc_trim unavailable; falling back to gc.collect() only")
        return None


_MALLOC_TRIM = _load_malloc_trim()


def release_to_os(label: str = "") -> float:
    """Collect garbage, then hand freed arenas back to the OS. Returns the RSS
    in MiB after reclaiming, and logs the before/after pair so the ratchet is
    visible in the Render logs."""
    before = rss_mb()
    gc.collect()
    if _MALLOC_TRIM is not None:
        _MALLOC_TRIM(0)
    after = rss_mb()
    logger.info("rss %s: %.1fMB -> %.1fMB (freed %.1fMB)", label or "release", before, after, before - after)
    return after
