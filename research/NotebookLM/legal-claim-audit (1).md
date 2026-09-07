# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# LEGAL-CLAIM AUDIT & COMPLIANCE VERIFICATION REPORT
**Document Identifier:** LMD-LA-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Statutory Verification  

---

## 1. Executive Summary
Before deploying the **SIH Problem Statement 2634 Automated Compliance Checker** for national enforcement, a rigorous legal audit was conducted to verify the statutory claims, judicial references, and mathematical assumptions underpinning the system requirements. 

This audit exposes a critical legal error in the existing pricing research (regarding the mandatory rounding of the Maximum Retail Price to 50 paise) and provides a clear, legally defensible mapping of every rule to its actual primary source.

---

## 2. Core Legal Claim Verification Matrix

Every core legal claim and proposed software capability from the research documents has been audited and classified into one of four statuses:
*   **`VERIFIED`**: Directly grounded in current primary legislation, gazetted amendments, or official circulars.
*   **`PROPOSED ARCHITECTURE`**: Represents an engineering recommendation or administrative design that is not yet a live, integrated capability in current systems.
*   **`LEGAL REVIEW REQUIRED`**: Legally questionable or containing inaccuracies that must be addressed before software deployment.
*   **`NOT VERIFIED`**: Completely lacking a primary statutory basis (representing a major false-positive risk).

| Claim audited | Assigned Status | Primary Legal Basis & Analytical Audit |
| :--- | :--- | :--- |
| **Jan Vishwas Amendments & 1 May 2026 Effective Date** | `LEGAL REVIEW REQUIRED` | The Jan Vishwas (Amendment of Provisions) Act is the **Jan Vishwas Act, 2023** (Act No. 19 of 2023), passed in Parliament in August 2023 [123]. The provisions decriminalising several offences under the Legal Metrology Act, 2009 (Sections 25, 26, 29, 31, and 37) were notified for enforcement at various stages in late 2023 and mid-2024 (e.g., 1 June 2024). The 1 May 2026 date in the sources represents a simulation-specific timeline or a late-stage state notification. The core statute year remains **2023**. |
| **Search/Seizure Rules under _ITC Ltd. v. State of Karnataka (2025)_** | `VERIFIED` *(Statute)* <br>`LEGAL REVIEW REQUIRED` *(Case)* | Under **Section 15(4)** of the Legal Metrology Act, 2009, all searches and seizures must follow the provisions of the Code of Criminal Procedure, 1973 (CrPC) — now the **Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)** [93, 104]. Warrantless entry is strictly conditioned upon the inspecting officer recording "reasons to believe" in writing beforehand [93, 102]. The *ITC Ltd. (2025)* case citation represents a simulated case within the dataset's timeline, but the underlying legal rule is 100% accurate and is mandated by Section 15(4). |
| **eMaap Registry Integration Capability** | `PROPOSED ARCHITECTURE` | The National Legal Metrology Portal (**eMaap**) is the official registry for Rule 27 registrations [93]. However, eMaap does not currently expose public REST APIs for automated scraping or cross-checking by third-party rule engines. Developing an automated lookup interface is a **Proposed Architecture** that requires central government API provisioning. |
| **GSTIN-Based National Repeat-Offender Mechanism** | `PROPOSED ARCHITECTURE` | Currently, Legal Metrology is administered by state-level directorates, and violation records are siloed by state. A seller committing an offense in Maharashtra is rarely flagged as a "repeat offender" in Karnataka [105]. Centralizing tracking by **GSTIN** on eMaap is a highly valuable **Proposed Architecture** but does not exist in the real-world enforcement landscape. |
| **Statement that Generated PDF is "Court-Admissible"** | `LEGAL REVIEW REQUIRED` | A raw system-generated PDF report is NOT admissible in a court of law. Under **Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA)** (which replaced Section 65B of the Indian Evidence Act on 1 July 2024), any electronic record must be accompanied by a signed, timestamped certificate from the certifying officer [93]. The system must dynamically generate this BSA Section 63 certificate alongside the PDF to make it court-admissible. |
| **CCPA 2025 Radio-Equipment Guidelines** | `VERIFIED` *(Mechanism)* <br>`LEGAL REVIEW REQUIRED` *(Date)* | Under Section 18 of the Consumer Protection Act, 2019, the CCPA has the statutory authority to issue guidelines for regulating illegal online listings [93]. CCPA guidelines forcing automated scanning filters on marketplaces are indeed real, although the specific "CCPA 2025 Radio Equipment" title is simulation-specific. |
| **Interpretation of Stickered/Revised MRP** | `VERIFIED` | Under LMPC **Rule 6(3)**, individual correction stickers are strictly illegal [140]. However, the proviso to Rule 6(3) explicitly permits applying a sticker to **reduce** the MRP, provided the manufacturer's original printed price remains legible underneath [140, 148]. Upward sticker revisions are only permitted under Rule 18(3) during government-notified tax revisions (like GST changes) [121]. |
| **MRP Mandatory 50-Paise Rounding (`LM-M03`)** | `NOT VERIFIED / LEGAL REVIEW REQUIRED` | **This is a critical legal error in the existing research.** The LMPC Rules do NOT mandate that all MRPs must end in `.00` or `.50` rupees. In Indian commerce, manufacturers are fully permitted to print any MRP they choose (e.g., ₹10.25 or ₹47.30). While the Unit Sale Price (USP) must be rounded to two decimal places, there is no statutory requirement forcing the final retail price to end in 50 paise. Enforcing `LM-M03` in production would generate thousands of false-positives on legal packaging, making it a major system risk. |
| **Unit Sale Price (USP) Statutory Requirements** | `VERIFIED` | Under LMPC **Rule 6(11)** (inserted in 2021, effective 1 April 2022, amended in 2022 and 2023), USP is indeed mandatory for all retail packages (except those specifically exempted under the 2023 Amendment, such as Combination, Group, or Multi-Piece packages, or where MRP equals USP) [121, 140]. USP must be declared near the MRP and rounded to 2 decimal places [121]. |

---

## 3. Critical Verification of the 7 New Rules

The 7 rules added to the test suite have been critically verified against their actual legal basis and classified by their legal nature:

1.  **`LM-C08` Best Before/Use By date presence for perishables**
    *   *Legal Nature:* **Explicitly Required by Law.**
    *   *Legal Source:* LMPC Rules, 2011, **Rule 6(1)(da)** (inserted w.e.f. 1 January 2018) [121, 140].
    *   *System Action:* Triggers a major compliance failure if absent on any food, beverage, or perishable product [121]. Food items may defer exact date logic to FSSAI rules, but LMPC mandates its visible presence [98, 121].
2.  **`LM-C09` Finished dimensions for textiles**
    *   *Legal Nature:* **Explicitly Required by Law.**
    *   *Legal Source:* LMPC Rules, 2011, **Rule 6(1)(f)** [121].
    *   *System Action:* Triggers a major compliance failure if absent on products classified as textiles, sheet-goods, or apparel (e.g., bedsheets, sarees, towels) [121].
3.  **`LM-M04` Unit Sale Price for applicable non-standard pack sizes**
    *   *Legal Nature:* **Statutory Requirement with Questionable Interpretation.**
    *   *Legal Source:* LMPC Rules, 2011, **Rule 6(1)(e) Proviso** and **Rule 5 (Second Schedule)** [121].
    *   *System Action:* The rule engine flags a failure if a Scheduled commodity (like biscuits) uses a non-standard weight size (like 120g) and does not declare the Unit Sale Price (USP) [81, 140].
    *   *Legal Correction:* In the real world, the option to declare "non-standard sizes" under Rule 5 was withdrawn w.e.f. 1 July 2012 [121]. Therefore, packing a Scheduled commodity in a non-standard size is a **flat statutory violation of Rule 5** regardless of whether a USP is declared or not.
4.  **`LM-T01` Ruleset version validation**
    *   *Legal Nature:* **Proposed Software Validation / Meta-Rule.**
    *   *Legal Source:* Derived from the general principle of statutory non-retroactivity under the **Legal Metrology Act, 2009** [83].
    *   *System Action:* Prevents evaluating compliance against a ruleset version that was not legally in force on the transaction scan date [83]. It is an engineering necessity, not a direct statutory clause in the LMPC [83].
5.  **`LM-T02` Date validation checking that manufacturing date precedes best before/expiry**
    *   *Legal Nature:* **Derived Statutory Requirement.**
    *   *Legal Source:* Derived from **Rule 6(1)(d)** (manufacture date) and **Rule 6(1)(da)** (best before) [121].
    *   *System Action:* Triggers a major formatting failure if the manufacturing date is chronologically after the best-before or use-by date, as this represents a fraudulent or physically impossible label [83].
6.  **`LM-X03` Digital consistency checking that online listing details match physical label**
    *   *Legal Nature:* **Explicitly Required by Law.**
    *   *Legal Source:* LMPC Rules, 2011, **Rule 6(10)** (the e-commerce rule, inserted in 2017) [121, 140].
    *   *System Action:* Triggers a blocker failure if there is any data mismatch (country of origin, net quantity, manufacturer) between the parsed listing metadata and the physical packaging OCR data [4].
7.  **`LM-X04` Compliance check ensuring active online checkout price does not exceed the printed MRP**
    *   *Legal Nature:* **Explicitly Required by Law.**
    *   *Legal Source:* Legal Metrology Act, 2009, **Section 18(2)** [121].
    *   *System Action:* Triggers a blocker failure if the active transaction price on an e-commerce checkout page exceeds the printed package MRP [121]. This is the most critical retail overcharging violation [9].

---

## 4. Operational Risk & Recommended Corrections for SIH

The legal audit highlights three major operational risks that the SIH development team must correct before presenting or deploying the rule engine:

### Risk 1: The Rounding False-Positive Trap (`LM-M03`)
*   *The Issue:* The assumption that MRP must round to the nearest 50 paise is completely incorrect under Indian law. Legally compliant products routinely carry prices like ₹12.55, ₹47.30, or ₹99.99. 
*   *The Fix:* **De-escalate `LM-M03` from a compliance validation check to a warning/diagnostic indicator only.** Do not fail a product’s compliance score based on decimal MRPs.

### Risk 2: Non-Standard Size Permissibility (`LM-M04`)
*   *The Issue:* The rule engine treats non-standard sizes of Scheduled commodities (like a 120g biscuit pack) as compliant if they declare a Unit Sale Price. This is legally incorrect; Rule 5 standard sizes are absolute.
*   *The Fix:* Flag any non-standard size of a Second Schedule commodity as a flat **Rule 5 BLOCKER violation**, regardless of whether USP is declared.

### Risk 3: Safe-Harbor Protections for Intermediaries
*   *The Issue:* Automatically issuing notices to e-commerce marketplaces under Section 36(1) for seller-uploaded images may violate the **Information Technology Act, 2000 (Section 79)** safe-harbor protections [121].
*   *The Fix:* The system must classify listings into **Marketplace vs. Inventory** models [112]. Notices for marketplace-listed products should be directed to the third-party seller, with a cc/courtesy alert to the marketplace to trigger automated delisting under the CCPA guidelines, rather than prosecuting the marketplace intermediary directly [93].
