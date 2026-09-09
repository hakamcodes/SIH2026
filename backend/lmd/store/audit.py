"""Append-only, hash-chained audit log. Every case-affecting action (viewing
a case, recording a reason-to-believe note, changing status) is written here
so the chain itself proves nothing was retroactively edited -- required for
the evidence record's Section 63 certifiability claim (lmd.evidence.bsa63).

Firestore has no autoincrement rowid to order inserts by, so chain order is
the `timestamp` field (ISO 8601, sorts lexicographically) instead. This
prototype has a single inspector acting serially, so two entries never share
a microsecond-resolution timestamp in practice.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from google.cloud.firestore import Client, Query

from lmd.evidence.hashing import GENESIS_HASH, chain_next, verify_chain

_COLLECTION = "audit_log"


def _last_hash(client: Client) -> str:
    docs = list(
        client.collection(_COLLECTION).order_by("timestamp", direction=Query.DESCENDING).limit(1).stream()
    )
    return docs[0].to_dict()["entry_hash"] if docs else GENESIS_HASH


def append(
    client: Client,
    actor_id: str,
    action: str,
    case_id: str | None = None,
) -> str:
    """Append one audit entry and return its log_id."""
    log_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    prev_hash = _last_hash(client)
    payload = f"{log_id}|{case_id or ''}|{actor_id}|{action}|{timestamp}"
    entry_hash = chain_next(prev_hash, payload)

    client.collection(_COLLECTION).document(log_id).set(
        {
            "log_id": log_id,
            "case_id": case_id,
            "actor_id": actor_id,
            "action": action,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
            "entry_hash": entry_hash,
        }
    )
    return log_id


def list_entries(client: Client, case_id: str | None = None) -> list[dict]:
    """Firestore requires a composite index for a query that combines a
    where() filter with an order_by() on a different field, and that index
    does not exist by default on a freshly created project -- it would have
    to be created once per Firestore project via the console or the Firebase
    CLI, which is exactly the kind of manual step a fresh deploy target
    should not depend on. Filtering by case_id in Python instead avoids
    needing that index at all; fine at hackathon audit-log volumes."""
    query = client.collection(_COLLECTION).order_by("timestamp", direction=Query.ASCENDING)
    entries = [doc.to_dict() for doc in query.stream()]
    if case_id is not None:
        entries = [e for e in entries if e.get("case_id") == case_id]
    return entries


def verify(client: Client, case_id: str | None = None) -> bool:
    """Recompute the chain from stored rows and confirm it is unbroken.

    If case_id is given, verifies only that case's entries in isolation --
    note this checks internal consistency of the filtered subsequence, not
    that it was contiguous within the *global* chain (a full-log audit
    should call this with case_id=None).
    """
    entries_raw = list_entries(client, case_id=case_id)
    entries = [
        (
            row["prev_hash"],
            f"{row['log_id']}|{row.get('case_id') or ''}|{row['actor_id']}|{row['action']}|{row['timestamp']}",
            row["entry_hash"],
        )
        for row in entries_raw
    ]

    if case_id is not None:
        # A per-case slice legitimately starts mid-chain; only check that each
        # entry's hash is correctly derived from its own recorded prev_hash.
        return all(chain_next(prev_hash, payload) == claimed_hash for prev_hash, payload, claimed_hash in entries)

    return verify_chain(entries)
