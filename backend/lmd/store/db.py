"""Firestore client factory. Firestore is schemaless -- there is no DDL step
equivalent to the old sqlite _SCHEMA/ensure_schema; collections and documents
are created implicitly on first write.

The reason-to-believe hard gate (CLAUDE.md invariant 12) can no longer be
backed by a database CHECK constraint (Firestore has none). It is enforced
solely in lmd.store.repository.update_case_status, which raises
ReasonToBelieveRequired before any write reaches Firestore -- the second half
of the old "enforced twice" guarantee is now a documented gap, not a silent
one.

Fatal on misconfiguration, deliberately: a missing or invalid
FIRESTORE_CREDENTIALS_JSON must stop the server at startup, not fall back to
an unpersisted client (mirrors the loader's "no bare except" rule in
CLAUDE.md invariant 3, applied here to the store layer instead).
"""
from __future__ import annotations

import json
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

from lmd import config


def _load_credentials() -> credentials.Certificate:
    if not config.FIRESTORE_CREDENTIALS_JSON:
        raise RuntimeError(
            "FIRESTORE_CREDENTIALS_JSON is not set. Paste the full contents of a "
            "Firebase service account key JSON file into that env var (see "
            ".env.example) -- there is no other supported way to reach Firestore."
        )
    try:
        service_account_info = json.loads(config.FIRESTORE_CREDENTIALS_JSON)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "FIRESTORE_CREDENTIALS_JSON is not valid JSON. It must be the raw "
            "contents of the service account key file, not a file path."
        ) from exc
    return credentials.Certificate(service_account_info)


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Return a process-wide Firestore client, initializing the underlying
    firebase_admin App on first call. Cached because re-initializing the App
    on every request is both wasteful and raises ValueError on the second
    firebase_admin.initialize_app() call."""
    if not firebase_admin._apps:
        firebase_admin.initialize_app(_load_credentials())
    return firestore.client()
