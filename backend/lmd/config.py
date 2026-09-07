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
DB_PATH = Path(os.environ.get("LMD_DB_PATH", _REPO_ROOT / "data" / "lmd.db"))
UPLOAD_DIR = Path(os.environ.get("LMD_UPLOAD_DIR", _REPO_ROOT / "data" / "uploads"))
RULESET_VERSION = os.environ.get("LMD_RULESET_VERSION", "v1")

RULESET_META = {"effective_from": "2011-04-01", "effective_to": None}
