# MetriX — SIH 2026 Screening Round PPT Content Guide
### PS 26034 | Software System to Check Compliance of Packaged Commodities under Legal Metrology

> **IMPORTANT NOTE:**
> The Title Slide (with PS ID, Team Name, Theme) is a SEPARATE slide that you have already made.
> The 5 slides below are your CONTENT slides. These replace your current 5 content slides.
> Each slide heading is followed by what to REMOVE from your current slide and what the NEW content should be.

---

## ❌ CURRENT PPT PROBLEMS — Read First

| Slide | What to Remove | Why |
|-------|---------------|-----|
| Slide 1 (Problem) | The "Onion" architecture diagram | Confusing, wastes half the slide, explains nothing to a non-technical judge |
| Slide 2 (Technical) | The "Technology Stack" pyramid and circular flow diagram | Generic visuals anyone can copy; make it a straight linear pipeline instead |
| Slide 3 (Research) | The ENTIRE slide — all 4 reference links | A complete waste of a slide in a 5-slide screening pitch; judges know the law exists |
| Slide 4 (Feasibility) | The misspelled heading "VIABLLITY" | Basic quality issue that destroys credibility instantly |
| Slide 5 (Impact) | The duplicated text "Legal Metrology Inspectors:" appearing twice | Makes the slide look sloppy and unpolished |

---
---

## SLIDE 1 — Problem Statement & Solution Overview

> **Current Slide:** You show "Real-World Issue", "Legal Complexity", "Why it Matters", an Onion diagram, and a Risk vs Solution table.
> **Keep:** The "Risk vs Solution" table — it is excellent, keep it exactly as it is.
> **Remove:** The Onion diagram — replace it with a brief, punchy problem statement section.

---

### 🔴 THE REAL PROBLEM (Use 3 bullet points, large font)

- **~10 mandatory declarations** must be checked per package. Inspectors do this manually — it is slow, inconsistent, and impossible to scale across thousands of products in a market inspection.
- **The law changes frequently.** The Jan Vishwas Amendment Act 2023, Unit Sale Price rule (effective 1 April 2022), Second Schedule size restrictions (effective 1 July 2012) — manually applying the correct *version of the law* to a specific scan date is nearly impossible.
- **No defensible evidence.** A phone photo and a paper note are not court-admissible. There is no standardized way to create a tamper-proof, legally certifiable violation record in the field today.

---

### 🟢 THE SOLUTION — MetriX (One Powerful Sentence)

> **"MetriX is an AI-powered pre-screening assistant that photographs a packaged product, automatically checks all 10+ mandatory legal declarations, and generates a cryptographically signed, court-certifiable evidence report — in under 30 seconds."**

*(Note: MetriX is a decision-support tool for inspectors. Only a Legal Metrology Officer can issue a final notice.)*

---

### ✅ KEEP THIS SECTION EXACTLY AS IS — Risk vs Solution Table

| 🔴 RISK | 🟢 METRIX SOLUTION |
|---------|-------------------|
| Wrong legal version applied | Effective-date rule evaluation — each rule knows which date it was in force |
| Black-box AI result | Exact rule ID + legal citation + extracted values shown for every verdict |
| Uncertain OCR reading | `NEEDS_REVIEW` verdict — system flags uncertainty, never guesses |
| Evidence tampering risk | SHA-256 hash chain — any tampering breaks the chain and is instantly detectable |

---
---

## SLIDE 2 — Technical Architecture & How It Works

> **Current Slide:** You show a generic "Technology Stack" pyramid and a circular "Implementation Flow" with 7 steps.
> **Remove:** Both of these diagrams entirely.
> **Replace with:** A clean, LINEAR pipeline showing how data actually flows through MetriX, and a focused Tech Stack section. Add the font-size calibration feature prominently.

---

### ⚙️ THE METRIX PIPELINE (Linear, Left to Right — 6 stages)

```
[1. CAPTURE]  →  [2. DUAL-PIPELINE EXTRACTION]  →  [3. RECONCILIATION]
                                                           ↓
[6. SIGNED REPORT]  ←  [5. INSPECTOR GATE]  ←  [4. RULE ENGINE + VERDICT]
```

**Stage 1 — Capture:**
Inspector uploads a product label photo (or takes a live photo) via the MetriX web app. Works on any device — no special hardware needed.

**Stage 2 — Dual-Pipeline Extraction (The Most Unique Part):**
Two completely independent pipelines run IN PARALLEL on the same image:

- **Pipeline A — RapidOCR (Offline, Always Runs):**
  - First, detects an **ID-1 Calibration Card** (standard 85.60mm × 53.98mm card) in the image using OpenCV contour analysis. If found, this establishes a pixels-to-millimetres scale. This allows the system to **measure actual font height in millimetres** — a compliance requirement under Rule 7 of Legal Metrology Rules. Without the calibration card in frame, the system correctly states "not measurable" rather than guessing.
  - Applies **glare masking** only (the single global image edit) — replaces glare patches with local grey median. This was the only preprocessing step that actually *improved* OCR results on curved packaging (tested and measured).
  - Runs RapidOCR text detection + recognition on the full image. Any text box read with low confidence is re-read with local image enhancement; the better of the two results wins per box.
  - Measures **ink-height in pixels** using row-wise pixel projection profiles (NOT from OCR bounding box height, which is inflated by ascender/descender padding — this is a precise, engineering-level decision).
  - A custom regex structuring layer converts raw OCR lines into legal fields: MRP, net quantity, manufacturer/packer/importer name, manufacturing date, best-before date, country of origin, consumer care contact number, common/generic name of commodity.

- **Pipeline B — AI Vision Cross-Check (Optional, Cloud):**
  - Sends the same photo to a Vision AI model to extract the exact same fields independently.
  - Results are **cached by image SHA-256 hash** — demos run fully offline after the first run.

**Stage 3 — Reconciliation (Smart Merging):**
The two pipelines are merged using a trust hierarchy:
- OCR's own parsed value wins outright when present.
- AI-found value corroborated by an OCR text line → accepted at medium confidence.
- AI-only value (no OCR match) → recorded but **below the threshold required for any enforcement action** — cannot alone produce a COMPLIANT verdict.
- **For MRP and net quantity specifically:** Both pipelines must agree within tolerance. If they disagree, the case is automatically routed to `NEEDS_REVIEW`. A confidently wrong digit is treated as worse than "could not read."

**Stage 4 — Rule Engine + Verdict:**
*(Explained in detail in Slide 3)*

**Stage 5 — Inspector Review + Legal Gate:**
*(Explained in detail in Slide 4)*

**Stage 6 — Signed PDF Report:**
*(Explained in detail in Slide 4)*

---

### 🛠️ TECH STACK (Keep it clean — use logos + one-line descriptions)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js + Tailwind CSS | Fast, responsive web app — works on inspector's phone |
| Backend | Python + FastAPI | High-performance async API |
| OCR (Offline) | RapidOCR (PP-OCRv6) | Fully offline, no GPU, no cloud cost |
| AI Cross-check | Vision AI (Claude) | Independent second opinion, cached for offline demos |
| Database | SQLite (prototype) / PostgreSQL (production) | Evidence-grade storage with append-only audit log |
| Compliance Engine | Custom JSON DSL Interpreter | Safe, sandboxed, no `eval` — rules are data, not code |
| Evidence | SHA-256 + HMAC | Tamper-proof hash chain |
| Reports | ReportLab PDF + QR Code | Court-certifiable PDF with Section 63 BSA 2023 certificate |
| Image Processing | OpenCV 4.x | Contour detection, glare masking, annotated overlay rendering |

---
---

## SLIDE 3 — Key Innovations & Unique Value Proposition

> **Current Slide:** A "Research and References" slide with 4 links to government websites.
> **REMOVE THIS ENTIRE SLIDE.** Replace it entirely with the content below.
> **Why:** Linking to the Legal Metrology Act does NOT prove your solution is innovative. This slide is a complete missed opportunity. Replace it with your actual innovations — things NO other team has.

---

### 🏆 WHAT MAKES METRIX DIFFERENT FROM ALL OTHER SUBMISSIONS

#### Innovation 1 — A Real Legal Rule Engine (Not an AI Guesser)

MetriX does NOT use a generic AI model that says "compliant" or "not compliant" with a probability score. That is useless in a court of law.

Instead, MetriX uses a **custom-built, safe Domain-Specific Language (DSL) interpreter**:
- All 29 compliance rules are stored in a **JSON file** — not hardcoded in Python. Each rule has: its exact legal citation, severity level (BLOCKER / MAJOR / MINOR), the condition to evaluate, and an effective date range.
- The DSL interpreter evaluates each rule's condition safely using Python's `ast` module with a strict whitelist of only 16 allowed operations. **No `eval`, no `exec`, no code injection possible.** A rule file that violates this whitelist refuses to load at startup.
- This means rules can be **updated, hot-swapped at runtime without restarting the server** — when the government passes an amendment, a legal expert updates the JSON, and the new rule is live instantly. Zero code change, zero downtime.
- **Live demo opportunity:** Can demonstrate this in front of judges by reloading the ruleset live.

#### Innovation 2 — Point-in-Time Legal Evaluation

Every rule in the JSON carries an `effective_from` and `effective_to` date. When a product is scanned:
- The engine evaluates each rule only if it was **in force on the date of that scan**.
- Example: Unit Sale Price (Rule 6(11)) only applies from 1 April 2022. A scan of a product manufactured in 2021 correctly skips this rule.
- This means MetriX can correctly evaluate the SAME product against DIFFERENT versions of the law — something a human inspector frequently gets wrong.

#### Innovation 3 — Font Size Measurement via Calibration Card

Rule 7 of the Legal Metrology Rules specifies **minimum character heights in millimetres** based on pack size. This cannot be verified from a photograph without knowing the physical scale.

MetriX solves this: If the inspector places a standard **ID-1 calibration card** (the same size as a bank ATM card — 85.60mm × 53.98mm) next to the product in the photo, the system:
- Detects the card automatically using OpenCV contour detection (aspect ratio 1.586).
- Establishes a pixels-to-millimetres scale for the entire image.
- Measures font ink-height in millimetres using **row-wise pixel projection profiles** (a precise measurement that ignores font padding/leading, unlike OCR bounding box height).

Without the calibration card, the system correctly reports: `height_mm: null, measurable: false, reason: "no_calibration_reference_in_frame"` — it **never guesses a physical measurement.**

#### Innovation 4 — Explainable AI, Not a Black Box

Every single rule verdict shows its work:
- **Which rule failed** (e.g., `LM-C03`)
- **Exact legal citation** (e.g., "Rule 6(1)(c), Legal Metrology (PC) Rules 2011")
- **What value was extracted** (e.g., "Found: 400g")
- **What value was expected / what the rule checks** (e.g., "Net quantity must match declared value on all panels")
- **The confidence level of the extraction**

This is what makes the verdict usable as **inspector evidence in a court proceeding** — not just a score.

#### Innovation 5 — Structural Absence Beats Confidence

One of the most common hackathon AI failures: a system says "compliant" because the AI is confident it did NOT find any problems (when it simply missed a field). MetriX is built the opposite way:

- **A mandatory field that is simply not detected = automatic FAIL (BLOCKER)**. It is not treated as "maybe present, low confidence." The nine Completeness rules use `"confidence_policy": "structural"` — they bypass confidence scoring entirely.
- **Verdict precedence is fixed and cannot be overridden:** `NON_COMPLIANT` always outranks `NEEDS_REVIEW`, which always outranks `COMPLIANT`. Failures can never be hidden by review flags.
- **MISSING sentinel, not null/false:** An absent field resolves to a `MISSING` sentinel value. Any comparison involving a MISSING value raises an `UnknownValue` error, which maps to REVIEW with the offending field logged — it can never silently pass.

#### Innovation 6 — Dual-Pipeline Agreement for Legal Numbers

MRP and net quantity are the two most legally consequential numbers on a package. MetriX treats them differently from all other fields:
- **Both Pipeline A (OCR) and Pipeline B (Vision AI) must agree within tolerance** before a numeric legal field is accepted.
- If only one pipeline found the number, or they disagree → automatic `NEEDS_REVIEW`.
- The AI vision model alone is **never sufficient** to assert a legal numeric fact. A confidently wrong digit is treated as worse than an honest "could not read."

---
---

## SLIDE 4 — Feasibility, Risks, Mitigations & Case Workflow

> **Current Slide:** Feasibility + "VIABLLITY" (typo) + Mitigation Strategies.
> **Fix:** Correct the typo. Rename "Viability" to "Technical Challenges". Add the Inspector Case Workflow and the Reason-to-Believe Gate — these are critical legal features your current PPT completely misses.

---

### ✅ FEASIBILITY (Why We Can Actually Build This)

- **Uses proven, production-grade technology.** RapidOCR (PP-OCRv6 model), OpenCV, FastAPI, Next.js — none of this is experimental or unproven.
- **Fully offline deterministic pipeline.** No cloud dependency for the core OCR and rule engine — works in warehouses, markets, and areas with poor connectivity.
- **Modular, data-driven architecture.** Adding a new legal rule = editing a JSON file. Adding a new product category = adding rows to a JSON file. No code changes needed for most legal updates.
- **Database-enforced legal gates.** Critical legal requirements (like the reason-to-believe note) are enforced as database constraints AND API validations — impossible to bypass even by a developer.

---

### 🔴 TECHNICAL CHALLENGES & RISKS

| Challenge | Honest Impact |
|-----------|--------------|
| OCR errors on blurred, curved, or rotated text | Near-zero recovery on curved cylindrical packaging and dot-matrix printed date stamps — measured and documented |
| Multilingual packages (Hindi + English) | Devanagari numerals like ₹ symbols have known OCR failure modes (e.g., `₹100` read as `₹]00`) |
| Frequent legal amendments | Any new gazette notification can invalidate or add rules |
| Font-size compliance needs calibration | Without an ID-1 card in frame, Rule 7 font-size checks are physically impossible |
| AI hallucination risk | Vision AI model can confidently extract wrong numbers |

---

### 🟡 MITIGATION STRATEGIES

| Challenge | Our Concrete Fix |
|-----------|-----------------|
| OCR errors | Low-confidence boxes get a second local-enhancement OCR pass. If still uncertain → `NEEDS_REVIEW` for human inspector |
| Curved/dot-matrix packaging | Explicitly documented as known limitations in the app's own Limitations page and in every PDF report |
| Legal amendments | Hot-reloadable JSON rule files — update rules without redeploying the app |
| Font-size without calibration | System reports `NOT_EVALUABLE` with an explanation — never invents a measurement |
| AI hallucination | Dual-pipeline agreement required for MRP/net quantity. AI alone cannot produce a verdict |
| Devanagari numeric OCR | Numeric sub-fields from Devanagari lines are gated separately; falls back to Pipeline B for those specific fields |

---

### ⚖️ INSPECTOR CASE WORKFLOW + THE LEGAL GATE (Often Missed — Include This!)

This is a crucial feature that most teams miss. MetriX is NOT just an OCR scanner. It is a complete enforcement workflow system:

```
SCAN → VERDICT → CASE CREATED → QUEUED → UNDER_REVIEW → [LEGAL GATE] → CONFIRMED_VIOLATION
```

**The Reason-to-Believe Gate (Section 15(4), Legal Metrology Act 2009):**

Before a case can be advanced to `CONFIRMED_VIOLATION` or `ESCALATED`, the inspector **must** type a written "reason to believe" note. This is not just a UI form — it is enforced:
1. At the **API layer** — the `/cases/{id}/status` endpoint returns HTTP 422 with a citation to Section 15(4) if no note is present.
2. At the **database layer** — a `CHECK` constraint in the SQL schema prevents any status advance without a recorded note, even if someone bypasses the API.

Under the Indian legal system (BNSS 2023), search and seizure actions require reasons to believe recorded in writing beforehand. MetriX builds this directly into the software so inspectors are legally compliant by default.

---
---

## SLIDE 5 — Impact, Scalability & Future Roadmap

> **Current Slide:** Impact on Target Audience + Key Benefits — good structure but has duplicated text and some missing content.
> **Fix:** Remove the duplicated "Legal Metrology Inspectors:" heading. Add quantified impact where possible. Add a proper Future Roadmap section. Mention the honest limitations clearly (this shows maturity to judges).

---

### 👥 WHO BENEFITS & HOW (3 Clean Columns — No Duplicated Text)

**1. Legal Metrology Field Inspectors:**
- Scan a product in under 30 seconds vs. 15-20 minutes of manual checking
- Get a standardized, consistent verdict — no more inspector-to-inspector variability
- Generate a court-certifiable evidence report with one click
- Never have to memorize which legal amendments are currently in force
- The system guides them through the legally correct process step-by-step

**2. Manufacturers & Businesses (Self-Compliance Tool):**
- Use MetriX to scan their own packaging BEFORE sending to print — catch violations before millions of units are produced
- Avoid massive recall penalties and reputation damage
- Get specific, actionable feedback ("MRP font height is below minimum — Rule 7 violation")
- Monitor rule changes via the hot-reloadable rules browser in the app

**3. Consumers (Indirect Beneficiary):**
- Ensures MRP, net quantity, manufacturer contact, and best-before dates are accurate and present
- Protects against overcharging (no sale above declared MRP — Section 18(2) LM Act 2009)
- Promotes accountability and transparency in packaged goods

---

### 📊 KEY BENEFITS (Keep your current layout — it is well-structured)

- **Social:** Promotes consumer rights, transparency, and fair trade practices
- **Economic:** Reduces manual inspection time significantly; reduces compliance-related costs for businesses
- **Regulatory:** Improves consistency, traceability, and accountability across all inspectors and regions
- **Technological:** Explainable AI results backed by exact legal citations, audit trails, and signed certificates — not a black box
- **Scalable:** Can be extended to FSSAI (food safety) packaging, CDSCO (drugs/cosmetics) labeling, and other regulatory domains by updating the JSON rules file

---

### 🚀 FUTURE ROADMAP (Label These Clearly as "Not Yet Built")

> These are genuine next steps, NOT current features. Being honest about this is what earns credibility with SIH judges.

| Roadmap Item | Why It Matters |
|-------------|----------------|
| Multi-image scan (front + back + side of package) | Real packages need multiple panel analysis; MRP is usually on front, address on back, date on bottom |
| Live camera capture mode in browser | Field inspectors need to point-and-scan without downloading an app |
| Barcode / QR scan for product identity lookup | Pre-fill product category from barcode; detect if barcode matches declared product |
| Complete Second Schedule (all 7 commodity categories) | Currently only biscuits are fully encoded; bread, milk powder, soaps, edible oil etc. are remaining |
| eMaap Registry Integration | Cross-check the product with the official Ministry registry (no public API today — future) |
| Cross-state repeat offender tracking | Identify manufacturers with multiple violations across states |
| Hindi / Bilingual OCR on real packaging photos | Tested only on synthetic renders so far; real bilingual photo testing is next |
| Automated penalty computation per violation | Section-wise penalty lookup under the Legal Metrology Act |
| Multi-tier supervisor & public dashboard | Aggregate data across inspectors and regions |

---

### ⚠️ HONEST LIMITATIONS (Include 2-3 Lines — This Is What Wins Judge Respect)

> Judges at SIH are experienced evaluators. Overclaiming is the single most common reason teams fail at screening. Stating your limitations honestly shows engineering maturity.

- **MetriX verifies declaration consistency — it does NOT verify actual physical net weight.** That requires a weighing scale, not a camera. The system clearly states this in every generated report.
- **Font-size compliance under Rule 7 requires a calibration card in the photo.** Without it, those checks report `NOT_EVALUABLE` — MetriX never guesses a physical measurement.
- **The generated PDF report is certifiable under Section 63, Bharatiya Sakshya Adhiniyam 2023 — it is not automatically court-admissible.** A human Legal Metrology Officer's process and signature still matter.
- **MetriX is an advisory pre-screening tool.** The final legal decision is always made by a qualified Legal Metrology Inspector, not by the software.

---
---

## 📋 SLIDE SEQUENCE SUMMARY

| Slide | Title | Core Message |
|-------|-------|-------------|
| [SEPARATE] | Title Slide | PS ID, Team Name, Problem Statement |
| Slide 1 | Problem & Solution Overview | The real pain + MetriX one-liner + Risk vs Solution table |
| Slide 2 | Technical Architecture | Linear pipeline + Calibration card + Dual-pipeline reconciliation |
| Slide 3 | Key Innovations & USP | DSL rule engine + Explainable AI + Font size measurement + Structural absence |
| Slide 4 | Feasibility, Risks & Case Workflow | Honest challenges + Mitigations + Inspector legal gate |
| Slide 5 | Impact, Scale & Roadmap | Who benefits + Future features + Honest limitations |

---

## 🎯 TERMINOLOGY TO USE CORRECTLY (Judges May Ask)

| Use This | Not This |
|----------|---------|
| `COMPLIANT` / `NON_COMPLIANT` / `NEEDS_REVIEW` | "Pass/Fail" or "High/Medium/Low risk" |
| `BLOCKER` / `MAJOR` / `MINOR` / `DIAGNOSTIC` | "Critical / Warning / Info" |
| "Certifiable under Section 63 BSA 2023" | "Court-admissible" |
| "Advisory pre-screening tool" | "Automated compliance system" |
| "Declaration consistency" | "Actual net weight verification" |
| "Reason-to-Believe Gate (Section 15(4) LM Act 2009)" | "Inspector approval step" |
| "Rule 6(11), effective 1 April 2022" | "The unit price rule" |
| "Jan Vishwas (Amendment of Provisions) Act, 2023" | "Jan Vishwas Act 2026" ← Wrong year, never say this |
