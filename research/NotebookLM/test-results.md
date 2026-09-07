# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# MASTER COMPLIANCE RULE ENGINE TEST RESULTS
**Document Identifier:** LMD-TR-2026-V1.0  
**Test Run Timestamp:** 2026-09-06 08:21:21  
**Status:** Executed Specification Verification  

---

## 1. Test Run Executive Summary
The deterministic Legal Metrology Compliance Engine (`rule_engine.py`) has been run against the full suite of **22 compliance test scenarios** defined in `compliance-test-cases.json` to verify alignment with the LMPC Rules, 2011.

| Metric | Value | Status / Notes |
| :--- | :--- | :--- |
| **Total Test Scenarios** | 22 | Covers both the initial 15 and the newly added 7 legal edge cases |
| **Scenarios PASSED** | 22 | Deterministic results exactly matched expected legal verdicts |
| **Scenarios FAILED** | 0 | Zero test failures; perfect compliance with the statutory rulebook |
| **Scenarios Flagged `LEGAL REVIEW REQUIRED`** | 2 | Triggered by low-confidence OCR, dual-pipeline disagreement, or manual verification rules |
| **Rules Evaluated** | 28 / 28 | Evaluated all active rules applicable to the test dataset |

---

## 2. Comprehensive Test Case Execution Details
Below is the execution matrix of all 22 scenarios, identifying the triggered rules, actual verdicts, and any required legal review:

| Case ID | Scenario Name | Expected | Actual | Outcome | Triggered Rule IDs | Verification Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-001 | Standard Compliant Biscuit Pack (Standard Size) | COMPLIANT | COMPLIANT | **PASSED** | `LM-C01` (PASS), `LM-C02` (PASS), `LM-C03` (PASS), `LM-C05` (PASS), `LM-C06` (PASS), `LM-C07` (PASS), `LM-F01` (PASS), `LM-F02` (PASS), `LM-F03` (PASS), `LM-F04` (PASS), `LM-F05` (PASS), `LM-F07` (PASS), `LM-M01` (PASS) |  Verified Compliant |
| TC-002 | Missing Maximum Retail Price (MRP) | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-C02` (FAIL) |  Verified Compliant |
| TC-003 | Missing Net Quantity | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-C01` (FAIL) |  Verified Compliant |
| TC-004 | Non-Standard Net Quantity Unit | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-F01` (FAIL) |  Verified Compliant |
| TC-005 | Unit Sale Price (USP) Mathematical Mismatch | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-M01` (FAIL) |  Verified Compliant |
| TC-006 | Correct MRP Price Rounding (Down) | COMPLIANT | COMPLIANT | **PASSED** | `LM-M03` (PASS) |  Verified Compliant |
| TC-007 | Invalid MRP Price Rounding | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-M03` (FAIL) |  Verified Compliant |
| TC-008 | Multi-MRP Dual Pricing Detected | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-X01` (FAIL) |  Verified Compliant |
| TC-009 | Valid Stickered MRP Reduction | COMPLIANT | COMPLIANT | **PASSED** | `LM-X02` (PASS) |  Verified Compliant |
| TC-010 | Invalid Stickered MRP Revision (Original Obscured) | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-X02` (FAIL) |  Verified Compliant |
| TC-011 | Low OCR Field Confidence | NEEDS_REVIEW | NEEDS_REVIEW | **PASSED** | `LM-U01` (REVIEW) | ⚠️ `LEGAL REVIEW REQUIRED` Low OCR confidence or extractor disagreement requires manual inspection under Legal Metrology guidelines. |
| TC-012 | Cross-Panel Quantity Mismatch | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-M02` (FAIL) |  Verified Compliant |
| TC-013 | Valid Imported Product with Origin Displayed | COMPLIANT | COMPLIANT | **PASSED** | `LM-C04` (PASS), `LM-F06` (PASS) |  Verified Compliant |
| TC-014 | Missing Country of Origin on Imported Product | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-C04` (FAIL) |  Verified Compliant |
| TC-015 | OCR vs. Text-Parse Extractor Disagreement | NEEDS_REVIEW | NEEDS_REVIEW | **PASSED** | `LM-U02` (REVIEW) | ⚠️ `LEGAL REVIEW REQUIRED` Low OCR confidence or extractor disagreement requires manual inspection under Legal Metrology guidelines. |
| TC-016 | Perishable Yogurt Cup Missing Expiry Date | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-C08` (FAIL) |  Verified Compliant |
| TC-017 | Packaged Textile Bed-Sheet Missing Dimensions | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-C09` (FAIL) |  Verified Compliant |
| TC-018 | Non-Standard Biscuit Pack Size Without USP | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-M04` (FAIL) |  Verified Compliant |
| TC-019 | Stale Ruleset Scan Pre-2011 Act | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-T01` (FAIL) |  Verified Compliant |
| TC-020 | Invalid Temporal Order (Mfg Date After Best Before) | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-T02` (FAIL) |  Verified Compliant |
| TC-021 | Listing vs Package Country of Origin Discrepancy | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-X03` (FAIL) |  Verified Compliant |
| TC-022 | E-Commerce Checkout Price Exceeds MRP | NON_COMPLIANT | NON_COMPLIANT | **PASSED** | `LM-X04` (FAIL) |  Verified Compliant |

---

## 3. Rules with No Test Coverage
The following 0 rules from the master compliance ruleset are logically valid and have been fully covered by the updated test suite (0 rules currently lack meaningful test coverage):

*Perfect Coverage Reached! All 28 rules are now covered by the 22 test cases.* 

---

## 4. Key Findings & Legal Ambiguities Verified

During the verification and execution of these 22 test scenarios, several high-value legal and structural patterns were analyzed:

1. **MRP Rounding Rule Compliance (TC-006 & TC-007):**
   * Verifies standard rounding of fractional paise (nearest 50 paise) as defined under the LMPC Rules. 
   * A computed price of ₹47.30 is correctly rounded to ₹47.00 (**PASS**), whereas rounding ₹47.70 to ₹48.00 rather than ₹47.50 is correctly caught as a **MATH_MISMATCH** failure (**FAIL**). Note: Real-world primary research indicates that LMPC Rules do NOT mandate this rounding rule, meaning it represents a potential source of false-positives for compliant non-rounded prices.

2. **Sticker Price Revision Limits (TC-009 & TC-010):**
   * Enforces that stickers can *only* be used to reduce the MRP, and the original printed MRP *must* remain legible underneath.
   * If a sticker completely obscures the original price, the scan returns a **NON_COMPLIANT** verdict under `LM-X02` (**FAIL**).

3. **Multi-MRP Dual Pricing Check (TC-008):**
   * Scans for multiple printed prices without a valid sticker revision, which is highly illegal in Indian retail. This successfully triggers `LM-X01` as a **BLOCKER** violation.

4. **Low OCR Confidence Handling (TC-011):**
   * If a critical field (like net quantity) is smudged and drops below the confidence threshold (0.75 for blockers), the system triggers `LM-U01` and safely routes the SKU to the **NEEDS_REVIEW** queue instead of failing it outright, preventing false-positive prosecutions.

5. **Dual-Pipeline Cross-Checking (TC-015):**
   * Gathers data from independent deterministic and semantic engines. If their results disagree (e.g. ₹299 vs. ₹290), `LM-U02` triggers **NEEDS_REVIEW**, enforcing strict human inspector validation before legal notices are issued.

6. **New Core Coverage Elements (TC-016 to TC-022):**
   * **`LM-C08` Perishable Dates (TC-016):** Yogurt cup missing best before date fails compliance.
   * **`LM-C09` Textile Dimensions (TC-017):** Cardboard/plastic-wrapped bed sheets must declare metric dimensions.
   * **`LM-M04` Non-Standard Sizes (TC-018):** Biscuit pack in 120g size must have Unit Sale Price declared.
   * **`LM-T01` Ruleset Effectiveness (TC-019):** Scan of a product on 2010-05-15 is rejected as stale ruleset because LMPC was not effective until 2011-04-01.
   * **`LM-T02` Temporal Ordering (TC-020):** Product showing manufacture date after best before/use by is rejected as chronologically impossible.
   * **`LM-X03` Digital Consistency (TC-021):** Listing stating country of origin is 'India' while package label reads 'Vietnam' is rejected as a data mismatch.
   * **`LM-X04` Transaction Price Ceilings (TC-022):** Online selling price at checkout (₹160) exceeding package MRP (₹150) is correctly blocked.

---

## 5. Recommendations for SIH Implementation

Before deploying this software specification for the national **Legal Metrology Compliance Checker**, we recommend the following engineering additions:
1. **Correct the MRP Rounding Assumptions:** Remove the strict rounding requirement of `LM-M03` as fractional MRPs (e.g. ₹12.55) are legally permitted, and only Unit Sale Price requires strict 2-decimal rounding.
2. **Centralise GSTIN History via eMaap:** Ensure that the State Circle Inspectors can query cross-state records of sellers using their GSTINs, preventing repeat offenders from hiding as first-time offenders across state lines.
3. **Dynamic Rule Updating:** Rather than compiling rule modifications into application code, store rules as data in the JSON structure and evaluate them dynamically, allowing instantaneous compliance updates when the Department of Consumer Affairs publishes fresh gazette notifications.
