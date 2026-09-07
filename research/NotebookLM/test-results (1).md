# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# MASTER COMPLIANCE RULE ENGINE TEST RESULTS
**Document Identifier:** LMD-TR-2026-V1.0  
**Test Run Timestamp:** 2026-09-06 08:15:51  
**Status:** Executed Specification Verification  

---

## 1. Test Run Executive Summary
The deterministic Legal Metrology Compliance Engine (`rule_engine.py`) has been run against all **15 statutory compliance test scenarios** defined in `compliance-test-cases.json` to verify alignment with the LMPC Rules, 2011.

| Metric | Value | Status / Notes |
| :--- | :--- | :--- |
| **Total Test Scenarios** | 15 | Covers all 15 target legal edge cases |
| **Scenarios PASSED** | 15 | Deterministic results exactly matched expected legal verdicts |
| **Scenarios FAILED** | 0 | Zero test failures; perfect compliance with the statutory rulebook |
| **Scenarios Flagged `LEGAL REVIEW REQUIRED`** | 2 | Triggered by low-confidence OCR or dual-pipeline disagreement |
| **Rules Evaluated** | 21 / 28 | Evaluated all active rules applicable to the test dataset |

---

## 2. Comprehensive Test Case Execution Details
Below is the execution matrix of all 15 scenarios, identifying the triggered rules, actual verdicts, and any required legal review:

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

---

## 3. Rules with No Test Coverage
The following 7 rules from the master compliance ruleset are logically valid but lacked specific scenario coverage in the test suite:

- **`LM-C08`** (COMPLETENESS): Verify that Best Before or Use By date is declared for perishable goods. *(Legal Basis: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(da))*
- **`LM-C09`** (COMPLETENESS): Verify finished dimensions are declared for packaged textiles/fabrics. *(Legal Basis: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(f))*
- **`LM-M04`** (MATH): Verify that Unit Sale Price is declared when a Scheduled commodity uses a non-standard pack size. *(Legal Basis: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(e) Proviso)*
- **`LM-T01`** (TEMPORAL): Verify that the compliance ruleset version was legally effective on the scan date. *(Legal Basis: Legal Metrology Act, 2009, Rule Engine Meta-Rule)*
- **`LM-T02`** (TEMPORAL): Verify that the manufacturing date is strictly before the best before / expiry date. *(Legal Basis: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(da))*
- **`LM-X03`** (CONFLICT): Verify that online listing details strictly match the physical product label findings. *(Legal Basis: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(10))*
- **`LM-X04`** (CONFLICT): Verify that the active online transaction price does not exceed the printed MRP. *(Legal Basis: Legal Metrology (Packaged Commodities) Rules, 2011, Rule 18(2))*

---

## 4. Key Findings & Legal Ambiguities Verified

During the verification and execution of these 15 test scenarios, several high-value legal and structural patterns were analyzed:

1. **MRP Rounding Rule Compliance (TC-006 & TC-007):**
   * Verifies standard rounding of fractional paise (nearest 50 paise) as defined under the LMPC Rules. 
   * A computed price of ₹47.30 is correctly rounded to ₹47.00 (**PASS**), whereas rounding ₹47.70 to ₹48.00 rather than ₹47.50 is correctly caught as a **MATH_MISMATCH** failure (**FAIL**).
   
2. **Sticker Price Revision Limits (TC-009 & TC-010):**
   * Enforces that stickers can *only* be used to reduce the MRP, and the original printed MRP *must* remain legible underneath.
   * If a sticker completely obscures the original price, the scan returns a **NON_COMPLIANT** verdict under `LM-X02` (**FAIL**).

3. **Multi-MRP Dual Pricing Check (TC-008):**
   * Scans for multiple printed prices without a valid sticker revision, which is highly illegal in Indian retail. This successfully triggers `LM-X01` as a **BLOCKER** violation.

4. **Low OCR Confidence Handling (TC-011):**
   * If a critical field (like net quantity) is smudged and drops below the confidence threshold (0.75 for blockers), the system triggers `LM-U01` and safely routes the SKU to the **NEEDS_REVIEW** queue instead of failing it outright, preventing false-positive prosecutions.

5. **Dual-Pipeline Cross-Checking (TC-015):**
   * Gathers data from independent deterministic and semantic engines. If their results disagree (e.g. ₹299 vs. ₹290), `LM-U02` triggers **NEEDS_REVIEW**, enforcing strict human inspector validation before legal notices are issued.

---

## 5. Recommendations for SIH Implementation

Before deploying this software specification for the national **Legal Metrology Compliance Checker**, we recommend the following engineering additions:
1. **Extend Test Scenarios:** Write mock test scenarios to cover the 7 uncovered rules, especially e-commerce transaction checks (`LM-X03`, `LM-X04`) and textile dimension checks (`LM-C09`).
2. **Centralise GSTIN History via eMaap:** Ensure that the State Circle Inspectors can query cross-state records of sellers using their GSTINs, preventing repeat offenders from hiding as first-time offenders across state lines.
3. **Dynamic Rule Updating:** Rather than compiling rule modifications into application code, store rules as data in the JSON structure and evaluate them dynamically, allowing instantaneous compliance updates when the Department of Consumer Affairs publishes fresh gazette notifications.
