"""Append-only, hash-chained audit log. Every case-affecting action (viewing
a case, recording a reason-to-believe note, changing status) is written here
so the chain itself proves nothing was retroactively edited -- required for
the evidence record's Section 63 certifiability claim (lmd.evidence.bsa63).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from lmd.evidence.hashing import GENESIS_HASH, chain_next, verify_chain


def _last_hash(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT entry_hash FROM audit_log ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    return row["entry_hash"] if row else GENESIS_HASH


def append(
    conn: sqlite3.Connection,
    actor_id: str,
    action: str,
    case_id: str | None = None,
) -> str:
    """Append one audit entry and return its log_id. Commits the connection."""
    log_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    prev_hash = _last_hash(conn)
    payload = f"{log_id}|{case_id or ''}|{actor_id}|{action}|{timestamp}"
    entry_hash = chain_next(prev_hash, payload)

    conn.execute(
        """INSERT INTO audit_log (log_id, case_id, actor_id, action, timestamp, prev_hash, entry_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (log_id, case_id, actor_id, action, timestamp, prev_hash, entry_hash),
    )
    conn.commit()
    return log_id


def verify(conn: sqlite3.Connection, case_id: str | None = None) -> bool:
    """Recompute the chain from stored rows and confirm it is unbroken.

    If case_id is given, verifies only that case's entries in isolation --
    note this checks internal consistency of the filtered subsequence, not
    that it was contiguous within the *global* chain (a full-database audit
    should call this with case_id=None).
    """
    query = "SELECT log_id, case_id, actor_id, action, timestamp, prev_hash, entry_hash FROM audit_log"
    params: tuple = ()
    if case_id is not None:
        query += " WHERE case_id = ?"
        params = (case_id,)
    query += " ORDER BY rowid ASC"

    rows = conn.execute(query, params).fetchall()
    entries = []
    for row in rows:
        payload = f"{row['log_id']}|{row['case_id'] or ''}|{row['actor_id']}|{row['action']}|{row['timestamp']}"
        entries.append((row["prev_hash"], payload, row["entry_hash"]))

    if case_id is not None:
        # A per-case slice legitimately starts mid-chain; only check that each
        # entry's hash is correctly derived from its own recorded prev_hash.
        for prev_hash, payload, claimed_hash in entries:
            if chain_next(prev_hash, payload) != claimed_hash:
                return False
        return True

    return verify_chain(entries)
