# CLAUDE.md — SIH PS 26034 Legal Metrology Compliance Scanner

Context file for all agent work in this repository. Read this before touching code.

---
important thing :- dont change any code until you are 95% sure abuot that

## 1. Project

**Smart India Hackathon problem statement 26034:** "Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels."

Currently building a prototype for the **college internal round**, on a one-week timeline, solo developer with Claude Code as the implementer. The prototype must genuinely work end to end. No mocked screens, no dead buttons, no fabricated numbers.

### Scope boundary

**In scope (the vertical slice):**

image upload or camera capture → CV extraction pipeline → deterministic rule engine → annotated overlay plus per-rule verdict with legal citations → inspector review with a mandatory "reason to believe" gate → signed PDF violation report with a SHA-256 evidence chain and a Section 63 BSA 2023 certificate.

**Out of scope — roadmap slide only, zero code:**

web crawler / marketplace scraping, eMaap registry integration, notice dispatch, multi-state case federation, supervisor and public dashboard tiers (a single counters page is the only dashboard).

Do not add out-of-scope surface without an explicit instruction. Breadth of working surface beats depth of hand-optimisation, but scope creep is the main way this prototype fails.

---

## 2. Environment gotchas

Verified on this machine — do not re-derive:

```
Windows 11 · Python 3.13.5 · Node v24.12.0 · npm 11.19.0 · git 2.53.0
No GPU (no nvidia-smi) · No Docker · No Tesseract binary
```

- **`rapidocr-onnxruntime` declares `requires_python <3.13` and will hard-fail on this interpreter.** Use `rapidocr==3.9.2`, which is a pure-Python wheel that bundles `PP-OCRv6_det_small.onnx`, `PP-OCRv6_rec_small.onnx` and a text-line classifier *inside the wheel*, so pipeline A runs fully offline with zero model downloads.
- **Do not use `paddleocr` / `paddlepaddle`.** A cp313 Windows wheel exists, but PaddleOCR 3.7 pulls roughly a gigabyte of dependencies and downloads models at first run.
- **Do not install `opencv-contrib-python`.** It double-installs `cv2` alongside the `opencv-python` that `rapidocr` depends on. Detect the ID-1 calibration card by contour aspect ratio (85.60 / 53.98 = 1.586) using base OpenCV. Pin `opencv-python==4.12.0.88`.
- **Set `PYTHONUTF8=1`.** The Windows console defaults to cp1252 and printing the rupee sign crashes with `UnicodeEncodeError: 'charmap' codec can't encode character '₹'`. Always pass `encoding="utf-8"` explicitly on file I/O.
- **OneDrive is syncing this working tree.** Letting it sync `node_modules` will stall the machine mid-build. Exclude the project folder from OneDrive sync, or at minimum `node_modules/` and `.venv/`. `.gitignore` must cover `.venv/`, `node_modules/`, `data/uploads/`, `data/lmd.db`, `**/__pycache__`.
- `pytesseract` installs but the `tesseract.exe` binary is absent. It is an optional third opinion only, gated behind `LMD_ENABLE_TESSERACT=0`.

---

## 3. Source of authority

`research/` holds two folders of prior deep research. They are **not duplicates** — the NotebookLM folder is *derived from* the mainResearch folder (same C/F/M/X/T/U rule taxonomy, same LM-U01/LM-U02 confidence gates, same three-state verdict). mainResearch is the reasoning and the measurements; NotebookLM is the artifacts.

`research/` is **read-only**. Never edit it. Port from it into `packages/` and `backend/`.

| Topic | Authoritative file |
|---|---|
| Legal rule numbers, penalties, exemptions | `research/NotebookLM/legal-claim-audit.md`, then `research/mainResearch/SIH_2634_Legal_Metrology_Compliance_Matrix.md` |
| The rules as data | `research/NotebookLM/machine-readable-compliance-rules.json` |
| Rule-engine math and verdict semantics | `research/mainResearch/SIH2634-Rule-Engine-Research.md` |
| CV/OCR pipeline and realistic accuracy expectations | `research/mainResearch/SIH2634-OCR-CV-Deep-Research.md` |
| Database schema, API surface, PDF report spec | `research/NotebookLM/database-api-data-model.md`, `violation-report-pdf-specification.md` |
| Product categories, Second Schedule sizes, exemptions | `research/mainResearch/Product Categories, Exceptions & Decision Logic.docx` |
| Starting code | `research/NotebookLM/rule_engine.py` — a reference to **port from, never to ship** |

`research/NotebookLM/legal-claim-audit.md` is the single most valuable file in the repository: it red-teams its sibling documents and catches real legal errors in them. When any two research files disagree, the audit wins.

---

## 4. Conflict resolutions — settled, do not re-litigate

### 4.1 Correct rule numbers

`research/mainResearch/SIH2634-Rule-Engine-Research.md` labels net quantity as `6(1)(b)`, MRP as `6(1)(f)` and consumer care as `6(1)(g)`. **All three are wrong.** The rules JSON already carries the correct numbers. Use these:

| Declaration | Rule |
|---|---|
| Manufacturer / packer / importer name and address | Rule 6(1)(a) |
| Country of origin (imports) | Rule 6(1)(a) proviso, 2017 amendment |
| Common or generic name | Rule 6(1)(b) |
| Net quantity | Rule 6(1)(c) |
| Month and year of manufacture / packing / import | Rule 6(1)(d) |
| Best before / use by | Rule 6(1)(da) |
| Maximum Retail Price, inclusive of all taxes | Rule 6(1)(e) |
| Dimensions, where size is price-relevant | Rule 6(1)(f) |
| Consumer care details | Rule 6(2) |
| Unit Sale Price | Rule 6(11), inserted 2021, effective 1 April 2022 |
| E-commerce display duty | Rule 6(10) |
| No sale above declared MRP | Section 18(2), LM Act 2009 |
| Standard pack sizes | Rule 5 and the Second Schedule |

### 4.2 Legal corrections that must be applied

- **`LM-M03` (mandatory 50-paise MRP rounding) is legally false.** Indian law permits any MRP — ₹12.55, ₹47.30 are legal. Enforcing this rule would fire on most compliant packaging. Ship it with `severity: "DIAGNOSTIC"`, a severity class that is *structurally incapable* of producing a non-compliant verdict, rendered in a separate "advisory observations" section.
- **`LM-M04` is legally wrong in the source engine.** The option to use non-standard sizes for Second Schedule commodities was withdrawn with effect from 1 July 2012. A non-standard size is a flat Rule 5 **BLOCKER regardless of whether USP is declared**. Split into `LM-M04a` (Rule 5 blocker, `effective_from: 2012-07-01`) and `LM-M04b` (USP presence, Rule 6(11), `effective_from: 2022-04-01`). Remove the "USP rescues a non-standard size" logic.
- **The Jan Vishwas dates are wrong throughout the research.** It is not "the Jan Vishwas Act 2026, effective 1 May 2026". It is the **Jan Vishwas (Amendment of Provisions) Act, 2023 (Act 19 of 2023)**, notified in stages from late 2023 to mid-2024. Fix every occurrence.
- **Two citations in the research are simulated and must never be cited.** `ITC Ltd. v. State of Karnataka (2025 INSC 1111)` and the "CCPA 2025 Radio Equipment Guidelines" do not exist as real precedent. The underlying legal requirement *is* real: cite **Section 15(4), Legal Metrology Act 2009, read with the BNSS 2023** — searches and seizures require reasons to believe recorded in writing beforehand.
- **A raw system-generated PDF is not court-admissible.** Under **Section 63 of the Bharatiya Sakshya Adhiniyam 2023** (which replaced Evidence Act s.65B on 1 July 2024) an electronic record needs a signed, timestamped certificate identifying the device, the production process and the integrity of the record. Generate that certificate alongside the report. Claim the record is *certifiable*, not automatically court-proven.
- **eMaap has no public API**, and enforcement is a **State subject**. Rule 27 registration lookup and cross-state repeat-offender tracking are proposed architecture. Present them as roadmap, clearly labelled. Never claim they are live.
- **Actual net weight cannot be verified from a photograph.** First Schedule maximum-permissible-error checking is out of scope by physics, not by choice. The system verifies *declaration consistency* only. State this plainly rather than letting a judge discover it.
- **Rule 7 Tables I and II** — the real minimum character-height thresholds in millimetres by pack size — appear in no research file. Do not invent them. See §7.

### 4.3 Naming and vocabulary

- `LM-X03` and `LM-X04` mean different things in the two research folders. Use the NotebookLM meanings, which match the rules JSON and the e-commerce framing: `LM-X03` = online listing versus physical package mismatch; `LM-X04` = checkout price exceeds printed MRP.
- Canonical severity vocabulary: **`BLOCKER` / `MAJOR` / `MINOR`**, plus **`DIAGNOSTIC`** for advisory-only rules. Ignore the Low/Medium/High/Critical and minor/major/critical variants found elsewhere in the research.
- Canonical verdicts: **`COMPLIANT` / `NON_COMPLIANT` / `NEEDS_REVIEW`**.
- Rule-level statuses: `PASS` / `FAIL` / `REVIEW` / `NOT_APPLICABLE` / `NOT_IN_FORCE` / `NOT_EVALUABLE`.
- New rules taken from the docx get **fresh IDs**. Do not reuse `LM-C05`, which is already the manufacturing-date rule. Use `LM-C10` for Rule 6(5) multi-pack, `LM-F08` for Rule 6(7) GM-food declaration, `LM-F09` for the cosmetic green/brown dot.

---

## 5. Known defects in `research/NotebookLM/rule_engine.py`

Port it, never copy it. All eight are confirmed by reading the file.

1. **The "rules as data" claim is false.** The `applicable_when` and `condition` strings in the rules JSON are never parsed. All 28 rules are a hardcoded `if/elif` ladder, written twice — applicability at lines 84–151 and evaluation at lines 161–465. Adding a rule to the JSON does nothing.
2. **Silent-pass bug.** With `rules_path=None` the constructor falls back to `/workspace/artifacts/...` inside a bare `except: pass`, leaving `self.rules == []`, so `run_compliance` returns `COMPLIANT` having evaluated zero rules. `test_rule_engine.py:11` constructs it exactly this way.
3. `to_base_unit` calls `unit.lower()` and then tests `unit in ['l','L']`, making the `'L'` branch unreachable. Unknown units `return value` unchanged, silently corrupting every mathematical rule.
4. **Dimension collision** (not caught by the research): `g`, `ml` and `cm` all map to magnitude 1, so `500 g` compares equal to `500 ml`, and the cross-panel rule would pass a weight-versus-volume mismatch. Return a `(dimension, magnitude)` tuple and refuse cross-dimension comparison.
5. `is_close` computes its tolerance from the *computed* value; the JSON condition specifies `0.005 * usp_declared`.
6. `LM-F04` matches the substring `'incl'`, so "including" passes the "inclusive of all taxes" check.
7. `LM-M04` has a `standard_sizes` table for biscuits only; the other Second Schedule categories are unencoded.
8. **Verdict precedence is inverted.** `REVIEW` outranks blocker failures, so a single low-confidence field masks a definite missing-declaration violation.

Also entirely absent: `effective_from` / `effective_to` filtering, so point-in-time law evaluation does not exist; and `min_field_confidence` is present on all 28 rules but read by nothing.

---

## 6. Canonical extraction contract

The research contains **three incompatible field-name sets**. The canonical shape is the **nested rules-JSON shape**, because the 28 rule conditions already reference `net_quantity.value`, `mrp.value` and `commodity.is_exempt`. Choosing anything else means rewriting all 28 conditions.

- `ExtractionEnvelope` is Pydantic-typed and versioned (`schema_version: "1.0"`), defined in `backend/lmd/extraction/contract.py`.
- The OCR document's flat `fields[]` array is **kept but derived**, generated by `flatten(product)`. Never author it by hand.
- The classification document's names (`declared_value`, `mrp_price`, `packing_date`) become a one-way input adapter in `adapters/legacy_names.py`, so the original research artifacts remain loadable in tests.
- `fields[]`, the DSL's `min_confidence()`, the confidence gate and the frontend overlay all address fields through **the same dotted-path keyspace**. This is the whole reason for picking one shape.
- `FontMetrics.ink_h_px` comes from a row-wise projection profile inside the box, **not** the OCR bounding-box height, which includes leading and ascender/descender padding. `height_mm` is `None` whenever `px_per_mm` is `None`.

---

## 7. Non-negotiable invariants

These are the things that make the prototype defensible. Do not weaken any of them to make a demo smoother or a test greener.

1. **Rules are always evaluated through the JSON DSL interpreter.** Never add a hardcoded `if rule_id == ...` branch. If a rule cannot be expressed in the DSL, extend the function registry, not the engine.
2. **The DSL never uses `eval`, `exec` or `compile`.** Validation happens at load time via `ast.parse(..., mode="eval")` plus a node whitelist. No attribute calls, no subscripts, no comprehensions, no lambdas, no dunder access. The only reachable callables are the twelve in `dsl/registry.py`'s hand-registered `FUNCTIONS` table, plus four evaluator-level special forms (`exists`, `is_null`, `coalesce`, `get_fields_for_blockers`) that need lazy or context-bound semantics a plain table entry can't express -- sixteen names total, pinned by a test. A rule file that violates this must **refuse to load** rather than degrade silently.
3. **The loader has no default rules path and no bare `except`.** A missing or invalid rules file is a fatal startup error. It must be impossible to run against an empty ruleset.
4. **Three-state verdict, never collapsed.** `NEEDS_REVIEW` is a first-class outcome, not a soft option to be folded into pass or fail for a cleaner demo. Fail toward review, never toward pass.
5. **Structural absence beats confidence.** A mandatory declaration that is simply not present is a `FAIL`, not a confidence question. The nine COMPLETENESS rules bypass the confidence threshold entirely (`"confidence_policy": "structural"`). `NON_COMPLIANT` outranks `NEEDS_REVIEW` in aggregation.
6. **Missing values are tri-state, never silently false.** An absent dotted path resolves to a `MISSING` sentinel; any comparison involving it raises `UnknownValue`, which maps to `REVIEW` with the offending path recorded. A missing field must never look like a passing rule.
7. **Numeric legal fields require dual-pipeline agreement.** Accept an MRP or net quantity only when pipeline A (RapidOCR) and pipeline B (vision model) agree within tolerance. Disagreement, or an empty pipeline A, routes to `NEEDS_REVIEW`. The vision model is never the sole source of a numeric legal field — a confidently wrong digit is worse than "could not read".
8. **Devanagari numerals are gated separately from their surrounding line.** The measured finding is that the script recognises well while embedded numerals fail (`₹100` became `₹]00`, a phone number scrambled). Gate the numeric sub-field on its own confidence.
9. **Never guess a physical scale.** Without a calibration reference in frame, emit `height_mm: null`, `measurable: false`, `reason: "no_calibration_reference_in_frame"`. Relative height ratios remain valid; absolute millimetre compliance does not.
10. **Never fabricate a legal citation or a numeric legal threshold.** Unsourced thresholds are represented as `NOT_EVALUABLE` with the reason surfaced in the UI — currently Rule 7 Tables I and II. `citations.json` carries `verified: true|false`, and unverified citations render greyed and tagged "illustrative".
11. **No global image preprocessing.** This is a measured negative result: CLAHE plus adaptive threshold made the curved pouch *worse* by surfacing background noise. Run OCR on the raw image first, enhance per-ROI only inside low-confidence boxes, and keep `max(raw, enhanced)` per box. Glare masking is the single pre-recognition exception, because glare produces confident false-positive text rather than blanks.
12. **The reason-to-believe gate is a hard gate.** Enforced in the database CHECK constraint *and* the API. Advancing a case without a recorded note returns 422 citing Section 15(4).
13. **The system is an advisory pre-screening signal, not a legal adjudication.** Only a Legal Metrology Officer can issue a notice. This disclaimer is visible sitewide, not buried in a README.

---

## 8. Test discipline

The research ships `test-results.md` claiming **22/22 passing, 28/28 rules covered, "Perfect Coverage Reached!"**. That claim does not hold up, and we must not reproduce it:

- The harness asserts only on each fixture's own `expected_triggered_rules` subset and **never compares the engine's real `overall_verdict`**.
- Measured reality: comparing the actual verdict to the expected verdict gives **18/22**. TC-001, TC-006, TC-009 and TC-013 return `NON_COMPLIANT`.
- The report's narrative sections are hardcoded f-strings, not derived from the run.
- Only TC-001 has ten input fields; the rest have three to seven. They are single-rule micro-fixtures missing most mandatory declarations.
- The sixteen `NON_COMPLIANT` micro-fixtures are right *for the wrong reason* — their absent mandatory fields would fail anyway.

**Rules for this repository:**

- **Complete the four broken fixtures; do not weaken their expected verdicts.** `expected_verdict: COMPLIANT` encodes the fixture's legal intent, and structural absence must yield `NON_COMPLIANT`. A "compliant" fixture that omits mandatory fields is self-contradictory: the fixture is wrong, the engine is right. Weakening it would train the system to under-report, the one failure mode an inspector cannot tolerate. TC-001 needs `best_before_date`, legally mandatory for food under Rule 6(1)(da). Record additions under a `_fixture_notes` key so the change is auditable.
- Keep the stripped originals as a **`TC-M0xx` minimal-field class** with `expected_verdict: NON_COMPLIANT`, so both directions are covered.
- Assert the **full** `rule_results` mapping, not just the expected subset.
- **Golden-image expectations encode measured reality, including known failures.** The dot-matrix and curved-jar photos must assert `NEEDS_REVIEW` and must assert they never return `COMPLIANT`. Encoding a known failure as an expected outcome is what makes the suite trustworthy.
- Replace `research/NotebookLM/test_rule_engine.py` entirely. It is not pytest, has no exit code, and hardcodes `/workspace/scratch/sih2634/` Linux paths.
- Measure coverage with `pytest --cov --cov-branch`, not by checking whether a rule ID appears in some fixture's list.

---

## 9. Commands

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip wheel
pip install -r backend\requirements.txt -r backend\requirements-dev.txt
pip download -r backend\requirements.txt -d backend\vendor\wheels   # offline reinstall mirror

# hard gate before writing any other code
python -c "from rapidocr import RapidOCR; print(RapidOCR()('research/mainResearch/02_flat_box_clean.jpg'))"

pytest -q                                  # everything
pytest -q -m "not slow"                    # fast loop
pytest tests/test_dsl_security.py -v       # the safety proof
pytest tests/test_effective_dates.py -v    # point-in-time law
pytest tests/test_golden_images.py --update-golden
pytest --cov=lmd --cov-branch --cov-report=term-missing
ruff check backend

python -m lmd.cli evaluate --case TC-002 --as-of 2022-03-31
python -m lmd.cli scan research\mainResearch\01_curved_pouch_dense_text.jpg --json
python -m lmd.cli report --case <id>
uvicorn lmd.main:app --reload --port 8000

cd frontend; npm run dev
cd frontend; npm run build
```

---

## 10. Repository map

```
SIH2634/
  CLAUDE.md  README.md  DEMO_SCRIPT.md  LEGAL_DISCLAIMERS.md  .gitignore
  research/                       # READ-ONLY source of truth
  packages/rules/
    lmd_rules.v1.json             # ported, legally corrected, 29 rules
                                   # (LM-C10/LM-F08/LM-F09 reserved, unwritten pending source)
    lmd_rules.v2.draft.json       # hot-swap demo payload
    second_schedule_sizes.json  exemptions.json  citations.json
    rule7_font_tables.json        # {"status":"UNVERIFIED_SOURCE","tables":{}}
    schema/{rules.schema.json, extraction.v1.schema.json}
  backend/lmd/
    config.py  main.py  cli.py  limitations.py
    api/          scan cases rules reports metrics errors limitations deps
    dsl/          normalize compiler evaluator registry errors
                   # (registry.py holds the whitelisted function table --
                   # there is no separate builtins.py)
    engine/       loader engine verdict units models
                   # (units.py is a thin re-export of dsl.registry)
    extraction/   contract adapters/legacy_names
                   # (flatten() lives in contract.py, not a separate flatten.py;
                   # cv/reconcile.py performs the two-pipeline merge the map used
                   # to assign to adapters/from_a.py + from_b.py -- there is no
                   # from_a.py/from_b.py)
    cv/           pipeline_a pipeline_b reconcile overlay stages/
    evidence/     hashing bsa63 report_pdf
    store/        db models repository ddl_postgres.sql audit
  backend/tests/  dsl_security, units, verdict, effective_dates, fixtures,
                  contract_roundtrip, golden_images, api_smoke, report_pdf,
                  cli, evidence, overlay, pipeline_a, pipeline_b, reconcile,
                  schema_validation, structuring
  frontend/src/                   # NOT YET BUILT
    app/{page, scan/[id], case/[id], rules, dashboard}
    components/{AnnotatedCanvas, FieldConfidenceChip, RuleVerdictCard,
                DisagreementBanner, ReasonToBelieveDialog, AdvisoryBanner, ui/}
```

`data/cache/vision/<sha256>.json` holds cached vision-model responses and **is committed** — it is what makes an offline demo possible. `data/lmd.db` and `data/uploads/` are gitignored.

---

## 11. Honest claims register

What we may say to judges:

- The rule engine is genuinely data-driven: rules, severities, legal citations and effective dates live in JSON, are hot-swappable at runtime, and are evaluated by a safe interpreter with no code path per rule.
- The system performs point-in-time legal evaluation — it can state which version of the law it applied to a given scan date.
- Every verdict carries the rule ID, the exact sub-rule citation, the values compared and the arithmetic that produced it.
- Two independent extraction pipelines must agree before a numeric legal field is accepted.
- Evidence carries a SHA-256 chain and a Section 63 BSA 2023 certificate, making the record certifiable.
- Optical character recognition works well on flat, high-contrast printed panels — this is measured, not claimed.

What we must **not** say:

- That the system verifies actual net weight, or performs any physical weighment or maximum-permissible-error check.
- That output is a legal adjudication, or that the system can issue a notice.
- That the PDF is automatically court-admissible.
- That eMaap registration lookup or cross-state repeat-offender tracking is live.
- That font-size compliance is verified from an arbitrary photograph with no calibration reference in frame.
- That dot-matrix batch and expiry stamps, or curved cylindrical surfaces, are reliably read — both measured at zero recovery with classical OCR.
- That Hindi accuracy is proven, until a photograph of a real bilingual package replaces the synthetic render.
- Any accuracy percentage that is not backed by a run over a labelled set in this repository.

---

## 12. Outstanding data tasks

Small, bounded, not research:

- Transcribe the seven Second Schedule commodity categories from `research/mainResearch/Product Categories, Exceptions & Decision Logic.docx` into `second_schedule_sizes.json`. The source engine covers biscuits only.
- Photograph one real bilingual (Hindi and English) package back panel. The only Devanagari asset today is a synthetic font render.
- Re-shoot two package photographs with a standard ID-1 card (85.60 mm) in frame, so the pixels-to-millimetres path is demonstrable. None of the seven existing photos contains a calibration object.
- Optional: source the real Rule 7 Tables I and II thresholds from the gazette. Until then the rule stays `NOT_EVALUABLE`.
- Note as a known limitation: the content of GSR 128(E), dated 13 February 2026, was not read during the research and may affect the encoded rules.
