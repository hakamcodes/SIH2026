# SIH 26034 -- Legal Metrology Compliance Scanner

Prototype for Smart India Hackathon problem statement 26034: a software
system to check compliance of packaged commodities under the Legal
Metrology (Packaged Commodities) Rules, 2011 by scanning products, images
and labels.

See [CLAUDE.md](CLAUDE.md) for the full scope, invariants, and conflict
resolutions this build follows, and [LEGAL_DISCLAIMERS.md](LEGAL_DISCLAIMERS.md)
for what this system does and does not claim.

**Backend is implemented; frontend is not (out of scope for this pass).**

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
- `backend/lmd/store/` -- sqlite persistence (`ddl_postgres.sql` documents
  the production target schema), a hash-chained audit log, and the
  reason-to-believe hard gate.
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
# then fill in ANTHROPIC_API_KEY, LMD_INSPECTOR_API_TOKEN, etc.

$env:PYTHONUTF8 = "1"
python -c "from rapidocr import RapidOCR; print(RapidOCR()('research/mainResearch/02_flat_box_clean.jpg'))"

cd backend
python -m pytest -q -m "not slow"      # fast loop
python -m pytest -q                    # everything, including real-image CV tests (slow)

python -m lmd.cli scan ..\research\mainResearch\02_flat_box_clean.jpg --json --commodity-category personal_care --commodity-subtype toothpaste
uvicorn lmd.main:app --reload --port 8000
```

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
