# Rule Engine + Mathematical Validation + MRP
### Research Deliverable — SIH PS 2634 (Automated Legal Metrology Compliance Checker)

---

## 0. Grounding & a scoping call you need to make explicitly

This problem sits under the **Legal Metrology Act, 2009** and the **Legal Metrology (Packaged Commodities) Rules, 2011 ("LMPC Rules")**, as amended (notable amendments: 2017, 2022, Feb/Apr 2026 e-commerce amendments adding stricter Country-of-Origin disclosure). The core mandatory declarations come from **Rule 6**: manufacturer/packer/importer name & address, common/generic name, net quantity, month & year of manufacture/packing/import, MRP inclusive of all taxes, consumer care details, and country of origin (for imports).

**Important honest caveat:** the exact numeric bands for things like Maximum Permissible Error (First Schedule) and the permitted "standard quantities" list (commodity-specific schedules) are long, commodity-specific tables in the Act — I am not going to fabricate precise numbers for those tables here. Since your PS is about **e-commerce listing/label compliance** (checking declarations from photos/OCR/scraped text), not physical weighment enforcement, **MPE-by-physical-measurement is out of scope** — you cannot verify true net weight from a photo, only declaration *consistency*. Say this explicitly in your submission; claiming your AI verifies "actual quantity accuracy" from an image is a claim you cannot back up and a judge who knows the domain will catch it immediately.

---

## 1. How extraction becomes a "legally meaningful decision"

Extraction (OCR/LLM) gives you **unstructured, probabilistic text**. Law requires **binary/graded compliance verdicts with citable justification**. The bridge is a 5-stage deterministic pipeline — the LLM never makes the compliance decision, it only proposes structured data:

```
[Raw Image/Listing]
      │
      ▼
Stage 1 — EXTRACTION (LLM/OCR)          → raw fields + per-field confidence
      │
      ▼
Stage 2 — NORMALIZATION                 → canonical types (Decimal, Unit enum, ISO date, ISO country)
      │
      ▼
Stage 3 — DETERMINISTIC RULE ENGINE     → pure functions, NO LLM, NO randomness, versioned rule set
      │
      ▼
Stage 4 — VERDICT AGGREGATION           → COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW + evidence trail
      │
      ▼
Stage 5 — HUMAN REVIEW QUEUE (for NEEDS_REVIEW only)
```

The thing that makes a verdict "legally meaningful" rather than "an AI vibe":
1. Every rule cites an exact **Rule/sub-rule number + effective-date range** (rules amend — a verdict must say which version of law it applied).
2. Every FAIL carries **the specific field values and the arithmetic** that produced it (reproducible by a human).
3. The engine is **deterministic and stateless** — same input always produces same output. This is non-negotiable for anything that could feed an actual notice/show-cause process.
4. Uncertainty is a **first-class output state**, not silently rounded to PASS or FAIL.

---

## 2. Rule Engine Design

### 2.1 Core design decision: rules as data, not code

Don't hardcode `if net_qty is None: fail()` scattered through your codebase. Encode rules as a declarative JSON/YAML rule set evaluated by a generic condition-tree interpreter (same idea as JSON Logic / Drools, simplified). This gets you:
- Legal team / non-engineers can review and amend rules without touching code.
- You can version rule sets by effective date (`effective_from`, `effective_to`) — required because LMPC Rules amend periodically.
- Auditable: you can literally print "rule LM-C02 v2, in force since 2011-03-07" as evidence.

### 2.2 Rule categories

| Category | Purpose | Example |
|---|---|---|
| **Completeness (C)** | Is a mandatory field present at all? | Net quantity missing |
| **Format/Validity (F)** | Is the present value well-formed? | Unit is "approx" instead of "g" |
| **Mathematical (M)** | Do numeric relationships hold? | USP ≠ MRP/quantity |
| **Multi-value/Conflict (X)** | Do multiple sources agree? | Two different MRPs found |
| **Temporal (T)** | Are dates internally consistent & rule-version-correct? | Mfg date after expiry date |
| **Uncertainty/Meta (U)** | Should this even be trusted enough to judge? | OCR confidence too low |

### 2.3 Severity tiers
- **BLOCKER** — a mandatory declaration is absent or contradictory. Verdict cannot be PASS.
- **MAJOR** — present but non-compliant (bad rounding, wrong format).
- **MINOR** — cosmetic (e.g., "Rs." used correctly but inconsistent symbol across panels — legal, but worth flagging).

### 2.4 Verdict states (three, not two)
`COMPLIANT` · `NON_COMPLIANT` · `NEEDS_REVIEW` — see Section 5. A binary PASS/FAIL system is a design flaw for this domain; don't build one.

### 2.5 Generic rule schema

```json
{
  "rule_id": "string, unique",
  "category": "COMPLETENESS | FORMAT | MATH | CONFLICT | TEMPORAL | UNCERTAINTY",
  "description": "human-readable",
  "legal_basis": "e.g. LMPC Rules 2011, Rule 6(1)(b)",
  "effective_from": "YYYY-MM-DD",
  "effective_to": "YYYY-MM-DD or null",
  "applicable_when": "condition expression, e.g. commodity.is_imported == true",
  "condition": "condition expression that must hold for PASS",
  "severity": "BLOCKER | MAJOR | MINOR",
  "on_fail_code": "MISSING_DECLARATION | INVALID_FORMAT | MATH_MISMATCH | CONFLICTING_DECLARATION | ...",
  "min_field_confidence": 0.0
}
```

---

## 3. Machine-Readable Rule Set (25 rules — exceeds the 20 minimum)

### A. Completeness / Missing-Declaration Rules

```json
[
 {"rule_id":"LM-C01","category":"COMPLETENESS","legal_basis":"Rule 6(1)(b)","severity":"BLOCKER",
  "condition":"exists(net_quantity.value) AND exists(net_quantity.unit)","on_fail_code":"MISSING_DECLARATION"},
 {"rule_id":"LM-C02","category":"COMPLETENESS","legal_basis":"Rule 6(1)(f)","severity":"BLOCKER",
  "condition":"exists(mrp.value)","on_fail_code":"MISSING_DECLARATION"},
 {"rule_id":"LM-C03","category":"COMPLETENESS","legal_basis":"Rule 6(1)(a)","severity":"BLOCKER",
  "condition":"exists(manufacturer_or_packer_or_importer.name) AND exists(...address)","on_fail_code":"MISSING_DECLARATION"},
 {"rule_id":"LM-C04","category":"COMPLETENESS","legal_basis":"Rule 6 (import proviso), amended 2026","severity":"BLOCKER",
  "applicable_when":"commodity.is_imported == true",
  "condition":"exists(country_of_origin) AND country_of_origin != ''","on_fail_code":"MISSING_DECLARATION"},
 {"rule_id":"LM-C05","category":"COMPLETENESS","legal_basis":"Rule 6(1)(c)","severity":"BLOCKER",
  "condition":"exists(mfg_or_pack_or_import_month_year)","on_fail_code":"MISSING_DECLARATION"},
 {"rule_id":"LM-C06","category":"COMPLETENESS","legal_basis":"Rule 6(1)(g)","severity":"MAJOR",
  "condition":"exists(consumer_care.phone) OR exists(consumer_care.email)","on_fail_code":"MISSING_DECLARATION"},
 {"rule_id":"LM-C07","category":"COMPLETENESS","legal_basis":"Rule 6(1)(a)","severity":"MAJOR",
  "condition":"exists(common_or_generic_name)","on_fail_code":"MISSING_DECLARATION"}
]
```

### B. Format / Validity Rules

```json
[
 {"rule_id":"LM-F01","category":"FORMAT","severity":"BLOCKER",
  "condition":"net_quantity.unit IN {g,kg,mg,ml,l,cm,m,mm,N}","on_fail_code":"INVALID_FORMAT",
  "note":"reject vague text like 'approx', 'net wt varies', 'family pack'"},
 {"rule_id":"LM-F02","category":"FORMAT","severity":"BLOCKER",
  "condition":"is_numeric(net_quantity.value) AND net_quantity.value > 0","on_fail_code":"INVALID_FORMAT"},
 {"rule_id":"LM-F03","category":"FORMAT","severity":"BLOCKER",
  "condition":"is_numeric(mrp.value) AND mrp.value > 0 AND mrp.currency_marker IN {'₹','Rs.','Rs'}",
  "on_fail_code":"INVALID_FORMAT"},
 {"rule_id":"LM-F04","category":"FORMAT","legal_basis":"Rule 6(1)(f) proviso","severity":"MAJOR",
  "condition":"mrp.text CONTAINS_PHRASE('inclusive of all taxes') OR mrp.text MATCHES 'MRP.*incl'",
  "on_fail_code":"INVALID_FORMAT"},
 {"rule_id":"LM-F05","category":"FORMAT","severity":"MAJOR",
  "condition":"is_valid_calendar_date(mfg_date) AND mfg_date <= today()","on_fail_code":"INVALID_FORMAT"},
 {"rule_id":"LM-F06","category":"FORMAT","severity":"MAJOR",
  "applicable_when":"commodity.is_imported == true",
  "condition":"country_of_origin IN valid_country_list AND country_of_origin NOT IN {'N/A','-',''}",
  "on_fail_code":"INVALID_FORMAT"}
]
```

### C. Mathematical / Numeric Validation Rules

```json
[
 {"rule_id":"LM-M01","category":"MATH","severity":"BLOCKER",
  "condition":"abs(usp_declared - (mrp.value / to_base_unit(net_quantity))) <= max(0.01, 0.005*usp_computed)",
  "on_fail_code":"MATH_MISMATCH"},
 {"rule_id":"LM-M02","category":"MATH","severity":"BLOCKER",
  "condition":"IF both_units_declared THEN abs(to_base_unit(qty_a) - to_base_unit(qty_b)) <= 0.01*to_base_unit(qty_a)",
  "on_fail_code":"MATH_MISMATCH", "note":"e.g. '500 g' vs '0.5 kg' must agree after conversion"},
 {"rule_id":"LM-M03","category":"MATH","legal_basis":"LMPC Rules, MRP paise-rounding provision (verify current wording)",
  "severity":"MAJOR",
  "condition":"mrp.value == round_mrp_paise(mrp.computed_pre_round_value)","on_fail_code":"MATH_MISMATCH"},
 {"rule_id":"LM-M04","category":"MATH","severity":"MAJOR",
  "condition":"IF net_quantity NOT IN standard_quantity_table(commodity_category) THEN exists(usp_declared)",
  "on_fail_code":"MISSING_DECLARATION","note":"USP mandatory when package size isn't a scheduled standard quantity"}
]
```

### D. Multi-Value / Conflict Rules

```json
[
 {"rule_id":"LM-X01","category":"CONFLICT","severity":"BLOCKER",
  "condition":"count(distinct(normalize(mrp_candidates))) == 1","on_fail_code":"CONFLICTING_DECLARATION"},
 {"rule_id":"LM-X02","category":"CONFLICT","severity":"MAJOR",
  "applicable_when":"count(distinct(normalize(mrp_candidates))) == 2 AND sticker_pattern_detected == true",
  "condition":"original_mrp.legible == true AND exists(revision_reason) AND exists(revision_date) AND revised_mrp == round_mrp_paise(computed_revised_value)",
  "on_fail_code":"INVALID_REVISION"},
 {"rule_id":"LM-X03","category":"CONFLICT","severity":"BLOCKER",
  "condition":"panel_a.net_quantity == panel_b.net_quantity (after normalization) AND panel_a.mrp == panel_b.mrp",
  "on_fail_code":"CONFLICTING_DECLARATION"},
 {"rule_id":"LM-X04","category":"CONFLICT","severity":"MAJOR",
  "condition":"across_listings_same_sku: count(distinct(mrp)) == 1 OR revision_trail_exists",
  "on_fail_code":"CONFLICTING_DECLARATION"}
]
```

### E. Temporal / Versioning Rules

```json
[
 {"rule_id":"LM-T01","category":"TEMPORAL","severity":"BLOCKER",
  "condition":"rule_set_version.effective_from <= listing_scan_date <= (rule_set_version.effective_to OR today())",
  "on_fail_code":"STALE_RULESET", "note":"meta-rule: engine must refuse to evaluate with an expired rule version"},
 {"rule_id":"LM-T02","category":"TEMPORAL","severity":"MAJOR",
  "condition":"mfg_date <= best_before_date","on_fail_code":"INVALID_FORMAT"}
]
```

### F. Confidence / Meta Rules (the "trust gate")

```json
[
 {"rule_id":"LM-U01","category":"UNCERTAINTY","severity":"BLOCKER",
  "condition":"min(confidence(fields_used_by(any_BLOCKER_rule))) >= tau_blocker",
  "on_fail_code":"NEEDS_REVIEW","tau_blocker":0.75},
 {"rule_id":"LM-U02","category":"UNCERTAINTY","severity":"MAJOR",
  "condition":"abs(pipeline_A.value - pipeline_B.value) <= tolerance FOR same field",
  "on_fail_code":"NEEDS_REVIEW","note":"two independent extractors (OCR vs text-parse) disagreeing forces review, never auto-averaged"}
]
```

That's **25 machine-readable conditions** across 6 categories.

---

## 4. Mathematical Formulas

**4.1 Unit normalization (base units: gram, millilitre, centimetre, count)**

```
to_base_unit(value, unit):
  g  → value            kg → value * 1000        mg → value / 1000
  ml → value             l → value * 1000
  cm → value             m → value * 100          mm → value / 10
  N  → value   (count/number of items — no conversion)
```

**4.2 Unit Sale Price (USP)**

```
USP = MRP / to_base_unit(net_quantity.value, net_quantity.unit)

Worked example (the one you gave):
  Net Quantity = 500 g, MRP = ₹100
  USP_computed = 100 / 500 = ₹0.20 / g
  Declared = ₹0.20/g  →  |0.20 - 0.20| = 0 ≤ tolerance → PASS
```

**4.3 Tolerance for numeric comparisons**

```
is_close(declared, computed) := |declared - computed| <= max(ε_abs, ε_rel * computed)
  ε_abs = 0.01      (₹0.01 / smallest unit — absolute floor tolerance)
  ε_rel = 0.005     (0.5% — absorbs legitimate MRP-rounding effects)
```
Never use a bare `==` on floats/currency — you will generate false FAILs from rounding alone.

**4.4 MRP paise-rounding function** *(verify exact current wording/applicability against the gazetted Rule text before demo — treat this as the shape of the rule, not a guaranteed-current legal citation)*

```
round_mrp_paise(x):
  rupees = floor(x)
  paise  = round((x - rupees) * 100)
  if paise < 50:            return rupees
  elif 50 <= paise <= 95:   return rupees + 0.50
  else (96..99):            return rupees + 1
```

**4.5 Confidence propagation**

```
rule_confidence(rule, fields) = min( confidence(f) for f in fields )

verdict(rule):
  if any mandatory field structurally absent  → NON_COMPLIANT (MISSING_DECLARATION)   # not a confidence question
  elif rule_confidence(rule, fields) < tau     → NEEDS_REVIEW
  elif condition(rule) evaluates true          → COMPLIANT
  else                                          → NON_COMPLIANT
```

**4.6 Multi-MRP conflict resolution**

```
distinct = set( normalize(v) for v in mrp_candidates )   # normalize strips symbol/whitespace differences
if len(distinct) == 1:                     → single value, PASS-eligible
elif len(distinct) == 2 and sticker_pattern_detected: → evaluate LM-X02 (revised MRP path)
else:                                       → NON_COMPLIANT / NEEDS_REVIEW (CONFLICTING_DECLARATION)
```

**4.7 Aggregate verdict formula**

```
overall_verdict =
  NON_COMPLIANT   if any BLOCKER rule fails with confidence ≥ tau
  NEEDS_REVIEW    if any BLOCKER rule is under-confidence, OR any CONFLICT unresolved, OR extractor disagreement
  else if any MAJOR rule fails → NON_COMPLIANT (flag severity=MAJOR, distinct from BLOCKER fails in reporting)
  else → COMPLIANT
```

---

## 5. Test Cases (15 — exceeds the 10+ requirement)

| # | Scenario (input, abbreviated) | Rule(s) hit | Verdict | Why |
|---|---|---|---|---|
| 1 | Qty=500g, MRP=₹100, declared USP=₹0.20/g | LM-M01 | **PASS** | 100/500=0.20, matches exactly |
| 2 | MRP field not detected at all | LM-C02 | **FAIL** | Mandatory declaration missing |
| 3 | Net quantity not detected, MRP present | LM-C01 | **FAIL** | Mandatory declaration missing |
| 4 | Qty extracted as "1 pack" (no weight unit) for a weight-sold good | LM-F01 | **FAIL** | Unit not in allowed set / vague qualifier |
| 5 | Qty=250g, MRP=₹50, declared USP=₹0.25/g | LM-M01 | **FAIL** | Computed = 50/250 = ₹0.20/g ≠ 0.25 declared |
| 6 | Computed pre-round price ₹47.30, declared MRP ₹47.00 | LM-M03 | **PASS** | 30 paise < 50 → rounds down to ₹47.00, matches |
| 7 | Computed pre-round price ₹47.70, declared MRP ₹48.00 | LM-M03 | **FAIL** | 70 paise is in 50–95 band → should round to ₹47.50, not ₹48.00 |
| 8 | Two MRPs found on package images: ₹120 and ₹150, no sticker pattern | LM-X01 | **FAIL** | Genuine conflicting declaration, no revision trail |
| 9 | Original ₹100 struck-through but legible; sticker: revised ₹105, reason "GST rate revision", dated | LM-X02 | **PASS** | Original visible + reason + date + rounding checks out |
| 10 | Sticker present, but original MRP fully covered/illegible | LM-X02 | **FAIL** | Original must remain visible for a valid revision |
| 11 | Net quantity text partially smudged; OCR confidence = 0.41 (τ=0.75) | LM-U01 | **NEEDS_REVIEW** | Below confidence gate on a field feeding a BLOCKER rule |
| 12 | Front panel: "500 g"; back/meta panel: "0.6 kg" (=600g) | LM-M02 | **FAIL** | Converted values disagree beyond tolerance |
| 13 | Imported product, "Country of Origin: Vietnam" present | LM-C04 | **PASS** | Mandatory import declaration present and valid |
| 14 | Imported product (foreign manufacturer address, no Indian packer), no COO field | LM-C04 | **FAIL** | Conditional mandatory declaration missing |
| 15 | OCR reads MRP=₹299; independent listing-text parse reads ₹290; both confident individually | LM-U02 | **NEEDS_REVIEW** | Two independent pipelines disagree — never silently averaged or auto-resolved |

---

## 6. Handling `"UNKNOWN / NEEDS REVIEW"`

**Design stance:** this is not a soft third option bolted on for demo purposes — it is the safety valve that makes the whole system defensible. A consumer-protection tool that silently defaults uncertain fields to PASS is worse than no tool at all, because it launders unverified data into an apparent compliance certificate.

**Triggers for NEEDS_REVIEW:**
- Field confidence below its type-specific threshold (`τ`), when that field feeds a BLOCKER rule.
- Two independent extraction pipelines disagree beyond tolerance on the same field (LM-U02).
- A conflict rule (LM-X0x) can't be cleanly resolved into PASS or FAIL by pattern-matching (e.g., sticker detected but reason text unreadable).
- Anything requiring subjective/visual judgment the rule-set can't encode deterministically (e.g., "is this font legible enough" — flag for human, don't guess).

**Strategy:**
1. **Three-state verdict**, always: `COMPLIANT` / `NON_COMPLIANT` / `NEEDS_REVIEW`. Never collapse the third state into either of the first two for a cleaner demo — that's the exact failure mode judges will probe.
2. **Fail toward review, not toward pass.** If in doubt about a mandatory field, the safe default is NEEDS_REVIEW, never COMPLIANT.
3. **Evidence bundle attached to every NEEDS_REVIEW item**: cropped source image region, raw extracted text, per-pipeline confidence scores, exact rule IDs blocked, and the specific numeric/textual disagreement. A human reviewer should never have to re-derive what the system already knows.
4. **Confidence thresholds are field-type-specific**, not global — numeric fields (MRP, quantity) need tighter thresholds than free-text fields (manufacturer name), because numeric errors compound into wrong verdicts silently.
5. **Priority queue by severity**: NEEDS_REVIEW items tied to a BLOCKER rule outrank those tied to MAJOR/MINOR rules.
6. **Feedback loop**: human corrections get logged and used to recalibrate extractor confidence and/or retrain the extraction model — this is what should differentiate your submission from a static rule dump.
7. **Explainability output**: every NEEDS_REVIEW (and every FAIL) carries a plain-language justification generated from rule metadata (`legal_basis`, values compared, confidence) — needed both for the human reviewer and for any downstream appeal process.
8. **Scope your claim honestly**: this system produces an *advisory pre-screening signal*, not a legal adjudication. Only a Legal Metrology Officer can issue an actual notice. Say this explicitly in your pitch — it preempts the "so your AI decides legal violations?" question, which is the kind of question that sinks otherwise-good SIH pitches.

---

## Blind spots to fix before you present this

- **You have no MPE/physical-weight verification, and you shouldn't claim one.** From a photo you can check *declaration consistency*, not truth. Say so.
- **The exact MRP rounding rule and standard-quantity tables are commodity-specific and amend over time** — don't hardcode numbers you pulled from a summary; source them from the gazette text and version them (see LM-T01).
- **A rule engine that can't say "which version of the law did I apply"** is not defensible in a compliance context — this is why every rule above carries `effective_from`/`effective_to`.
- **Don't build binary PASS/FAIL.** It's the single most common mistake in this exact problem statement's submissions — teams that skip the NEEDS_REVIEW tier get marked down hard on judgment questions about false positives.
