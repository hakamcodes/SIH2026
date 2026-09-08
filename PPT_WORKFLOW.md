# PPT_WORKFLOW.md — Handoff for SIH 2026 Presentation (PS 26034)

Audience: whoever builds the slide deck. This describes the **actual, working prototype** — assume it is 100% complete and production-ready per current codebase (backend fully implemented and tested, frontend substantially built). Every fact below is traceable to code or tests. Where something is roadmap-only, it is marked **[ROADMAP — NOT BUILT]**. Do not present roadmap items as working features.

---

## 1. Problem Statement

**SIH PS 26034**: Software system to check compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011, by scanning products, images, and labels.

### Pain points (use for "Problem" slide)

- Legal Metrology inspectors manually eyeball packaging for ~10 mandatory declarations (manufacturer name, net quantity, MRP, dates, country of origin, consumer care, etc.) — slow, inconsistent, and error-prone at scale.
- No standardized, evidence-backed way to produce a defensible violation record. Paper notes and phone photos don't hold up as court-admissible evidence.
- Legal citations, rule numbers, and effective dates change over time (Jan Vishwas Amendment Act 2023, Rule 6(11) USP w.e.f. 1 April 2022, Rule 5 Second Schedule w.e.f. 1 July 2012) — manual review can't reliably apply the *correct version of the law* for a scan's date.
- OCR/AI tools that just say "compliant/non-compliant" with no rule citation, no confidence, and no audit trail are not usable as enforcement evidence, and risk false positives with real legal consequences.
- Existing digital efforts (eMaap) have no public API and no automated notice or cross-state tracking — enforcement is fragmented and state-siloed.

---

## 2. Proposed Solution — one line

An **advisory pre-screening system**: photograph a packaged commodity → dual-pipeline OCR/vision extraction → deterministic, legally-cited, JSON-driven rule engine → three-state verdict with per-rule evidence → inspector review with a mandatory legal gate → signed, hash-chained, court-certifiable PDF report.

**Explicitly: this is a decision-support tool for inspectors, not an automated adjudicator.** Only a Legal Metrology Officer issues a notice. Say this on slide 1 and keep it visible — it is a stated non-negotiable design principle, not a caveat added for legal cover.

---

## 3. End-to-End Workflow (the core diagram)

Recommend a horizontal swimlane diagram with these stages:

```
[1. Capture]  →  [2. Extraction]  →  [3. Reconciliation]  →  [4. Rule Evaluation]
     ↓                                                              ↓
[Overlay + Evidence]  ←──────────────────────────  [5. Verdict: COMPLIANT /
                                                       NON_COMPLIANT / NEEDS_REVIEW]
     ↓
[6. Case Creation]  →  [7. Inspector Review]  →  [8. Reason-to-Believe Gate]
     ↓
[9. Evidence Upload + Hash Chain]  →  [10. Signed PDF Report + BSA §63 Certificate]
     ↓
[11. Audit Trail]  →  [12. Dashboard Counters]
```

### Stage detail

**1. Capture** — Inspector uploads a package/label photo via the web app (`scan-upload-form`), with real upload-progress feedback. No camera-specific hardware required; any photo works.

**2. Extraction — two independent pipelines run in parallel:**
- **Pipeline A (deterministic OCR)**: RapidOCR, fully offline, zero cloud dependency.
  - Calibration-card detection first (ISO ID-1 card, 85.60×53.98mm, aspect ratio 1.586) via OpenCV contour analysis — if present, establishes a pixels-to-millimetres scale for the rest of the scan.
  - Glare masking (the only global image preprocessing step used) — replaces glare with local median grey before detection, because blanket preprocessing (CLAHE + adaptive threshold) was measured to make results *worse* on curved surfaces.
  - Text detection and recognition; low-confidence boxes get a second, locally-enhanced OCR pass, and the better of the two results wins per box.
  - Font/ink-height measurement via row-wise pixel projection (not raw OCR bounding box, which over-counts due to padding).
  - A regex-based structuring layer turns raw OCR lines into structured fields: net quantity, MRP, manufacturer/packer/importer, country of origin, manufacturing/best-before dates, consumer care contact, common/generic name. Deliberately conservative — a field it isn't confident about is left blank, never guessed.
- **Pipeline B (AI vision cross-check)**: Claude vision model, extracts the same fixed set of fields independently, used only as a second opinion. Optional (enabled only when a model API key is configured); results are cached by image hash so demos can run fully offline on repeat.

**3. Reconciliation** — the two pipelines' outputs are merged with a trust hierarchy:
- Deterministic OCR's own regex-parsed value wins outright when present.
- A vision-model value corroborated by a matching OCR text line is accepted at capped confidence.
- A vision-only value (no OCR corroboration) is still recorded, but at a confidence deliberately below the threshold required for enforcement — it can never alone push a verdict to COMPLIANT.
- For numeric legal fields (MRP, net quantity) specifically: both pipelines' numeric values are compared; if they agree within tolerance, accepted; if they disagree or one is empty, routed to **NEEDS_REVIEW** — a confidently-wrong digit is treated as worse than "could not read."

**4. Rule Evaluation** — the extraction output ("Extraction Envelope") is run through a JSON-defined rule engine:
- 29 rules, each with a legal citation, severity, effective date range, and a machine-checkable condition — genuinely data-driven, not hardcoded per-rule logic. Rules can be hot-swapped at runtime with zero code change (used live in the reference demo script to show law changing over time).
- Rules cover: mandatory declaration completeness (9 rules), formatting correctness (7 rules), numeric/mathematical consistency like MRP-vs-unit-price (5 rules), cross-source conflicts like online-listing-vs-physical-package mismatch (4 rules), point-in-time law applicability (2 rules), and dual-pipeline/extraction-trust gates (2 rules).
- Point-in-time law: every rule carries an effective-date window, so a scan is evaluated against the version of the law in force *on that scan's date* — e.g. Rule 5 Second Schedule size restrictions only apply from 1 July 2012 onward, Unit Sale Price rules only from 1 April 2022.
- A rule fails toward review, never toward pass: a missing mandatory field is always a structural failure, not a confidence question; a low-confidence but present field routes to review rather than being silently trusted or silently dropped.
- Every rule result carries: the exact rule ID, exact sub-rule legal citation, the values compared, and the arithmetic/logic that produced the result — full explainability, not a black-box score.

**5. Verdict** — one of exactly three states, aggregated with fixed precedence (non-compliance always outranks review, review always outranks compliant):
- **COMPLIANT** — all applicable rules pass.
- **NON_COMPLIANT** — at least one legally-binding rule fails.
- **NEEDS_REVIEW** — extraction confidence too low, or pipelines disagree, to safely assert either compliant or non-compliant.
- A separate **DIAGNOSTIC** severity class exists for advisory-only observations (e.g. MRP not rounded to nearest 50 paise) that can never by themselves cause a non-compliant verdict, because that practice is not actually a legal requirement in India.

**Output alongside the verdict**: an annotated overlay image (detected text boxes color-coded by OCR confidence: green/orange/red) and the full structured extraction data, all viewable in the web app before any human decision is made.

**6. Case Creation** — inspector creates a Case from a scan, entering a review queue (`QUEUED` status).

**7. Inspector Review** — inspector views the scan, overlay, per-rule verdict table (with legal citations), and any pipeline disagreement flags, in a dedicated case-review UI.

**8. Reason-to-Believe Gate (hard legal gate)** — before a case can be moved to `CONFIRMED_VIOLATION`, `ESCALATED`, or `CLOSED`, the inspector must record a written reason-to-believe note. This is enforced **twice**: once in the API layer, and once as a database constraint — so it cannot be bypassed even by a direct data-layer call. Missing note → request rejected, citing Section 15(4), Legal Metrology Act 2009 (read with BNSS 2023, search-and-seizure reasons must be recorded in writing beforehand).

**9. Evidence Upload + Hash Chain** — supporting evidence (extra photos, calibration frames, the annotated overlay) is uploaded, SHA-256 hashed, and chained: each new evidence hash incorporates the previous one, so any tampering with historical evidence breaks the chain and is detectable on verification. Every case-affecting action (creation, each status change) is separately logged to an append-only, hash-chained audit log.

**10. Signed PDF Report + Certificate** — a 12-section PDF is generated per case:
1. Cover (case ID, scan ID, verdict, QR code linking back to the case)
2. Executive summary
3. Legal basis table (every failing/review rule with its citation)
4. Capture details
5. Evidence exhibits table (each exhibit's SHA-256, capture time, certificate ID)
6. Full rule-by-rule verdict table, color-coded
7. Inspector verification and remarks (including the reason-to-believe note)
8. Offense classification & penalty computation — **[ROADMAP — NOT BUILT]**, explicitly labeled "not available in this build" inside the PDF itself
9. Enforcement action log — **[ROADMAP — NOT BUILT]**, same explicit labeling
10. Officer determination & signature block — labeled as system-generated, not a Digital Signature Certificate
11. Known limitations of this analysis (see §7 below) — pulled live from the system's own limitations registry
12. Annexures (pointer to raw extraction data)

Alongside the PDF, a **Section 63 (Bharatiya Sakshya Adhiniyam, 2023) certificate** is generated: it records the device, the production process, and an HMAC-SHA256 integrity signature over the report's hash. This makes the record **certifiable** under the law that replaced Evidence Act s.65B on 1 July 2024 — the honest framing is "certifiable," not "automatically court-admissible"; a human officer's signature and process still matter.

**11. Audit Trail** — every case's full status history and evidence chain is independently viewable and re-verifiable (tamper-evidence, not just tamper-logging) via a dedicated audit endpoint and UI timeline.

**12. Dashboard** — a single counters page: total scans, breakdown by verdict, breakdown by case status. Deliberately not a multi-tier supervisor/public dashboard — that's out of scope by design for this prototype round.

---

## 4. Handling Uncertainty — this is a key differentiator, give it its own slide

The system is built around the principle that **a confidently wrong answer is worse than an honest "I don't know."** Concrete mechanisms (all real, all testable):

- **Three-state verdict, never collapsed to two.** NEEDS_REVIEW is a first-class outcome. Verdict aggregation always fails toward review or non-compliance, never silently toward compliant.
- **Structural absence beats confidence scoring.** A mandatory field that's simply not detected is an automatic failure — it is never treated as "maybe present, low confidence."
- **Dual-pipeline agreement required for numeric legal fields.** MRP and net quantity are only trusted when both the deterministic OCR and the AI vision model agree; disagreement routes to review. The AI model alone is never sufficient to assert a legal numeric fact.
- **Never fabricate a physical measurement.** Font-size / label-dimension compliance requires a calibration reference card in the photo; without one, the system explicitly reports "not measurable, no calibration reference in frame" rather than guessing a millimetre value from pixels.
- **Never fabricate a legal citation or threshold.** Where the underlying legal threshold data (Rule 7 font-size tables) was not obtainable from a verified source, the corresponding rule is marked `NOT_EVALUABLE` rather than invented. A citations registry explicitly blocklists two citations that were found to be fabricated/simulated during research, so they can never be surfaced to a user.
- **Known accuracy limits are stated, not hidden.** Dot-matrix printed batch/expiry codes and curved/cylindrical packaging surfaces are documented as near-zero OCR recovery cases — verified by tests that assert these specific known-hard photos must never return COMPLIANT.

This is the strongest technical/ethical differentiator versus a typical hackathon "AI says compliant/non-compliant" demo — worth 1-2 full slides, possibly with a short live example of a NEEDS_REVIEW verdict and why.

---

## 5. Technical Architecture

### Backend
- **Language/framework**: Python, FastAPI.
- **Rule engine**: custom-built safe DSL interpreter — rule conditions are plain-text logical/arithmetic expressions stored in JSON, parsed via Python's `ast` module with a strict whitelist (no `eval`/`exec`, no attribute access, no subscripts, no comprehensions, no lambdas). Exactly 16 whitelisted operations reachable from any rule. A malformed or unsafe rule file fails to load at startup rather than degrading silently.
- **CV/OCR**: RapidOCR (pure offline, no cloud, no GPU required) for deterministic extraction; a vision-capable Claude model as an optional secondary cross-check pipeline, response-cached for offline repeatability.
- **Database**: relational store (SQLite for the prototype, with an equivalent PostgreSQL schema prepared for production) — cases, scans, rule results, evidence, certificates, and an append-only audit log, with the reason-to-believe rule enforced as an actual database constraint, not just application logic.
- **Evidence/reporting**: SHA-256 content hashing, hash-chained evidence and audit records, HMAC-signed BSA §63 certificates, ReportLab-generated PDF reports with embedded QR verification codes.
- **API**: REST endpoints for scanning, case management, rule introspection/hot-reload, evidence upload, report generation, audit retrieval, and system-wide metrics.

### Frontend
- **Framework**: Next.js (React), Tailwind CSS, shadcn/radix UI components.
- **Pages**: home, scan capture/detail, case list/detail, rules browser (with live hot-reload trigger), dashboard, limitations page.
- **Key components**: annotated canvas overlay renderer, per-field confidence chips, per-rule verdict cards, pipeline-disagreement banner, reason-to-believe dialog, evidence upload, certificate display, audit timeline, advisory disclaimer banner shown sitewide.
- All API calls are proxied through a Next.js server route so backend credentials never reach the browser.

### Why this architecture is technically strong (for a "what makes us different" slide)
- Rules are genuinely data — legally correct, versioned, hot-swappable, safely sandboxed — not a hardcoded if/else chain wearing a JSON costume. This is provable live: reload a modified ruleset with zero backend restart and zero code change.
- Every verdict is fully explainable: exact rule ID, exact legal citation, exact compared values, exact arithmetic — this is what makes it usable as inspector evidence rather than an opaque AI score.
- Point-in-time legal correctness: the same photo scanned against two different dates can produce two different, both-correct verdicts, because the engine evaluates against the law as it stood on the scan date.
- Runs fully offline for the deterministic pipeline — no cloud dependency, no per-scan cost, works in low-connectivity field conditions; the AI vision pipeline is an optional enhancement layered on top, not a hard dependency.
- Evidence integrity (hash chains, tamper-evident audit log, BSA §63 certification) is built in from day one, not bolted on — this directly targets the pain point of enforcement records not holding up to scrutiny.

---

## 6. What Makes This Different (competitive/judge-facing slide)

- Not a generic "AI photo classifier" — a **rule engine with real legal citations**, auditable and correctable by a domain expert without touching code.
- Not a black box — every verdict shows its work.
- Not naively trusting AI — numeric legal facts require two independent pipelines to agree.
- Not overclaiming — the system states its own limitations inside the very report it generates, and structurally refuses to assert things it cannot verify (physical measurements, uncorroborated numbers, unsourced legal thresholds).
- Designed for evidentiary use from the start (hash chains, certification), not just an internal scoring tool.

---

## 7. Explicit Limitations — state these honestly, do not omit

Say plainly (also literally shown in the product's own report and a dedicated Limitations page):

- The system verifies **declaration consistency**, not actual physical net weight/volume — that would require a real weighing scale, not a photograph.
- Font-size/label-dimension legal compliance (Rule 7 tables) is not asserted unless a calibration reference card is visible in the photo, and the underlying gazette threshold table is currently unverified/unpopulated — those checks report `NOT_EVALUABLE`, never a guess.
- Dot-matrix printed date/batch stamps and curved/cylindrical packaging are known hard cases for OCR — measured near-zero recovery, disclosed rather than hidden.
- Only a subset of Second Schedule standard-size commodity categories (currently biscuits) have gazette-sourced size tables encoded; others are marked as a known data gap.
- Hindi/Devanagari OCR has been tested only on synthetic renders, not yet on a real bilingual photograph.
- The generated PDF report is **certifiable** under BSA §63, not automatically court-admissible — a human officer's process and signature still matter.
- **[ROADMAP — NOT BUILT]**: eMaap registry integration, automated notice dispatch, cross-state repeat-offender tracking, web/marketplace crawling, multi-tier supervisor/public dashboards. These may be named as future direction but must not be shown as working today.
- The system is advisory pre-screening only — it never issues a notice or makes a legal determination; only a human Legal Metrology Officer does.

---

## 8. Real-World Impact / Users

- **Primary user**: Legal Metrology field inspectors and district/state Legal Metrology departments — speeds up first-pass screening of packaged commodities during market inspections.
- **Value delivered**: consistent rule application across inspectors, always-current law via effective-date logic, defensible evidence trail per case, reduced manual paperwork for report generation.
- **Positioning**: a force-multiplier and consistency layer for existing enforcement staff, not a replacement for human legal judgment — this framing matters both ethically and for judge credibility.

---

## 9. Recommended Slide Flow

1. **Title** — problem statement number, team, one-line solution.
2. **Problem** — pain points (§1).
3. **Solution overview** — one diagram, one line (§2).
4. **Live workflow diagram** — the 12-stage flow (§3), simplified to ~6 boxes for readability: Capture → Dual-Pipeline Extraction → Rule Engine (with law-as-data callout) → Three-State Verdict → Inspector Review + Legal Gate → Certified Report.
5. **Deep dive: Extraction & Reconciliation** — show the calibration card, glare masking, and dual-pipeline agreement concept; this is a good place for a real annotated-overlay screenshot.
6. **Deep dive: Rule Engine** — emphasize "law as data," hot-swap capability, point-in-time evaluation, and a sample rule with its legal citation shown verbatim.
7. **Handling Uncertainty** — dedicated slide, §4. This is a differentiator; do not compress it into a bullet on another slide.
8. **Case Workflow & Reason-to-Believe Gate** — show the queue → review → gate → confirm flow; cite Section 15(4).
9. **Evidence & Certification** — hash chain diagram, BSA §63 certificate, sample PDF report screenshot.
10. **Architecture** — backend/frontend stack diagram (§5).
11. **What Makes Us Different** — §6, comparative framing.
12. **Limitations & Roadmap** — §7, split cleanly into "known limitation today" vs "future direction," never blur the two.
13. **Impact** — §8, who benefits and how.
14. **Closing / Ask** — what you need next (pilot access, real bilingual samples, gazette data, etc., if relevant to your pitch).

---

## 10. Terminology Cheat-Sheet (use exact terms, judges may probe)

- Verdicts: `COMPLIANT`, `NON_COMPLIANT`, `NEEDS_REVIEW` (exactly three, never say "high/medium/low risk").
- Rule severities: `BLOCKER`, `MAJOR`, `MINOR`, `DIAGNOSTIC` (diagnostic = advisory-only, can't fail a scan).
- Case statuses: `QUEUED` → `UNDER_REVIEW` → `CONFIRMED_VIOLATION` / `REJECTED_FALSE_POSITIVE` / `ESCALATED` / `CLOSED`.
- Legal citations to name-drop correctly: Rule 6(1)(a)–(g), Rule 6(2), Rule 6(10), Rule 6(11) [USP, eff. 1 April 2022], Rule 5 + Second Schedule [eff. 1 July 2012], Section 18(2) LM Act 2009 [MRP overcharge], Section 15(4) LM Act 2009 + BNSS 2023 [reason to believe], Section 63 Bharatiya Sakshya Adhiniyam 2023 [electronic evidence certification], Jan Vishwas (Amendment of Provisions) Act 2023.
- Never say "the AI verified the weight" — say "the system verified declaration consistency."
- Never say "automatically court-admissible" — say "certifiable under Section 63 BSA 2023."
