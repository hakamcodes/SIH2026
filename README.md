# SIH 26034 -- Legal Metrology Compliance Scanner

Prototype for Smart India Hackathon problem statement 26034: a software
system to check compliance of packaged commodities under the Legal
Metrology (Packaged Commodities) Rules, 2011 by scanning products, images
and labels.

See [CLAUDE.md](CLAUDE.md) for the full scope, invariants, and conflict
resolutions this build follows, and [LEGAL_DISCLAIMERS.md](LEGAL_DISCLAIMERS.md)
for what this system does and does not claim.

**Backend and frontend are both implemented.** See
[frontend/README.md](frontend/README.md) for the Next.js app and
[Deployment](#deployment) below for how the two are hosted separately.

## What's implemented

- `backend/lmd/engine/` + `backend/lmd/dsl/` -- a data-driven rule engine.
  Rules live in `packages/rules/lmd_rules.v1.json` and are evaluated by a
  safe, whitelisted AST interpreter (no `eval`/`exec`/`compile`).
- `backend/lmd/extraction/` -- the canonical `ExtractionEnvelope` contract
  every rule condition and every pipeline output speaks.
- `backend/lmd/cv/` -- pipeline A (RapidOCR, fully offline) with calibration
  card detection, glare masking, per-ROI enhancement, and font-height
  measurement; pipeline B (Claude vision cross-check, cached); a regex-based
  structuring stage; dual-pipeline reconciliation; an annotated overlay
  renderer.
- `backend/lmd/evidence/` -- SHA-256 hashing/chaining, a Section 63 BSA 2023
  certificate generator, and a 12-section violation report PDF.
- `backend/lmd/store/` -- Firestore persistence, a hash-chained audit log,
  and the reason-to-believe hard gate. Images (scan originals/overlays,
  evidence uploads, generated report PDFs) are stored as base64 fields on
  Firestore documents rather than files on disk, since the deploy target's
  disk does not survive a redeploy.
- `backend/lmd/api/` -- FastAPI endpoints: scan, case review, evidence
  attachment, report generation, ruleset introspection/hot-reload, and the
  single counters dashboard.
- `backend/lmd/cli.py` -- `evaluate` (fixtures), `scan` (a real image),
  `report` (a case already in the store).

## Setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip wheel
pip install -r backend\requirements.txt -r backend\requirements-dev.txt

copy .env.example .env
# then fill in ANTHROPIC_API_KEY, LMD_INSPECTOR_API_TOKEN, and
# FIRESTORE_CREDENTIALS_JSON (required -- see .env.example for how to get it;
# there is no local/offline database fallback).

$env:PYTHONUTF8 = "1"
python -c "from rapidocr import RapidOCR; print(RapidOCR()('research/mainResearch/02_flat_box_clean.jpg'))"

cd backend
python -m pytest -q -m "not slow"      # fast loop
python -m pytest -q                    # everything, including real-image CV tests (slow)

python -m lmd.cli scan ..\research\mainResearch\02_flat_box_clean.jpg --json --commodity-category personal_care --commodity-subtype toothpaste
uvicorn lmd.main:app --reload --port 8000
```

Frontend (separate terminal, requires the backend above running):

```powershell
cd frontend
npm install
copy .env.example .env.local   # then fill in LMD_BACKEND_URL / LMD_INSPECTOR_API_TOKEN
npm run dev
```

## Deployment

Backend and frontend deploy to different platforms and do not share a
process or a filesystem:

- **Backend -> Render.** `render.yaml` at the repo root is a Render Blueprint
  targeting `backend/` as the service root, running
  `uvicorn lmd.main:app --host 0.0.0.0 --port $PORT` on Render's free Python
  web service tier. No persistent disk is configured or needed -- all
  persistence is Firestore, reached via `FIRESTORE_CREDENTIALS_JSON`.
- **Frontend -> Vercel.** See [frontend/README.md](frontend/README.md). The
  frontend talks to the backend only through its own server-side proxy route,
  so the backend's CORS policy (`LMD_CORS_ORIGINS`) does not gate the
  browser -- it only matters if something calls the backend directly.
- **Database -> Firestore.** Create a Firebase project, generate a service
  account key, and paste its full JSON contents into `FIRESTORE_CREDENTIALS_JSON`
  on the backend (both locally in `.env` and on Render). There is no other
  supported persistence backend; a missing/invalid key fails loudly on first
  database access rather than falling back to anything.

Known operational tradeoffs of the free-tier path (not fixed by code): Render's
free web service sleeps after 15 minutes idle and takes 30-60s to cold-start,
and the CV dependencies (RapidOCR/onnxruntime/opencv) are memory- and
CPU-heavy relative to the free tier's 512MB RAM and throttled shared vCPU, so
a warm-instance scan is meaningfully slower there than the same scan run
locally.

## Known, honestly-documented limitations

- Manufacturer name/address and common/generic name are not yet parsed from
  raw OCR text (no reliable lexical marker the way "MRP"/"Net Wt." have).
  Every real photo in `research/mainResearch/` therefore currently evaluates
  `NON_COMPLIANT` via a genuinely-missing mandatory declaration -- see
  `backend/tests/test_golden_images.py`.
- Rule 7 Tables I/II (font-size thresholds) are unsourced; see
  `packages/rules/rule7_font_tables.json`.
- Six of seven Second Schedule commodity categories beyond biscuits remain
  untranscribed pending the actual gazette text; see
  `packages/rules/second_schedule_sizes.json`.
- `LM-C10` (multi-pack), `LM-F08` (GM-food), `LM-F09` (cosmetic dot) are
  reserved rule IDs (CLAUDE.md section 4.3) not yet authored -- their exact
  DSL conditions were not specified and inventing legal logic without a
  concrete source would violate this project's accuracy bar.
