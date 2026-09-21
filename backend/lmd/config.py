"""Central, env-overridable paths and settings. Reads .env once via
python-dotenv so ANTHROPIC_API_KEY / LMD_EVIDENCE_SIGNING_KEY etc. are
available without every module reaching into os.environ + dotenv itself.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPO_ROOT / "backend"

load_dotenv(_REPO_ROOT / ".env")

RULES_PATH = Path(os.environ.get("LMD_RULES_PATH", _REPO_ROOT / "packages" / "rules" / "lmd_rules.v1.json"))
RULESET_VERSION = os.environ.get("LMD_RULESET_VERSION", "v1")

# Cap on panels per /scans/multi request. Each panel's OCR pass peaks RSS on
# its own, so this bounds worst-case memory on Render's 512MB free tier --
# not just an API sanity check.
LMD_MAX_PANELS = int(os.environ.get("LMD_MAX_PANELS", "4"))

# Firestore is the only persistence backend now (CLAUDE.md deploy decision:
# Render's disk is ephemeral, so cases/scans/evidence must live off-box).
# FIRESTORE_CREDENTIALS_JSON holds the *contents* of a Firebase service
# account key file, not a path -- this is the one env var that has to be set
# identically whether running locally via .env or as a Render env var, and a
# path wouldn't survive either deploy target the same way. Project ID is
# read from inside that same JSON, so there is nothing else required.
FIRESTORE_CREDENTIALS_JSON = os.environ.get("FIRESTORE_CREDENTIALS_JSON", "")

RULESET_META = {"effective_from": "2011-04-01", "effective_to": None}
