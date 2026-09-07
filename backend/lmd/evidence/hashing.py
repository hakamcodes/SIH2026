"""SHA-256 evidence chain primitives (CLAUDE.md: "Evidence carries a SHA-256
chain and a Section 63 BSA 2023 certificate, making the record certifiable").

Two distinct hashing needs are kept separate:
- `sha256_file` / `sha256_bytes`: content-integrity hash of a single evidence
  artifact (an image, a generated PDF).
- `chain_next`: a blockchain-style link hash for an append-only sequence
  (the audit log) -- each entry's hash commits to the previous entry's hash,
  so any retroactive edit to an earlier row changes every hash after it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

GENESIS_HASH = "0" * 64


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def chain_next(prev_hash: str, entry_payload: str) -> str:
    """Compute the link hash for the next entry in a hash chain.

    `prev_hash` must be `GENESIS_HASH` for the first entry. `entry_payload`
    should be a stable serialization of everything about this entry except
    its own hash (e.g. f"{actor_id}|{action}|{timestamp}|{case_id}").
    """
    return sha256_bytes(f"{prev_hash}|{entry_payload}".encode("utf-8"))


def verify_chain(entries: list[tuple[str, str, str]]) -> bool:
    """entries: ordered list of (prev_hash, entry_payload, claimed_entry_hash).

    Returns True iff every claimed_entry_hash matches chain_next(prev_hash,
    entry_payload) AND each entry's prev_hash equals the prior entry's
    claimed_entry_hash (or GENESIS_HASH for the first entry).
    """
    expected_prev = GENESIS_HASH
    for prev_hash, payload, claimed_hash in entries:
        if prev_hash != expected_prev:
            return False
        if chain_next(prev_hash, payload) != claimed_hash:
            return False
        expected_prev = claimed_hash
    return True
