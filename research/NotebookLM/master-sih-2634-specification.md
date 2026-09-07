# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# MASTER SPECIFICATION FOR SIH PROBLEM STATEMENT 2634: AUTOMATED GOVERNMENT COMPLIANCE AND ENFORCEMENT ENGINE
**Document Identifier:** LMD-MS-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Single Source of Truth / Master Architecture  

---

## 1. Executive Summary & Objective
This Master Specification serves as the single source of truth and architectural blue-print for **Smart India Hackathon (SIH) Problem Statement 2634**. 

Naïve hackathon submissions treat this problem statement as a basic "image scanner." This specification establishes a comprehensive, legally resilient, and implementation-ready **National Legal Metrology Digital Enforcement Platform** [93]. It bridges the gap between raw machine-vision text extraction and formal, court-admissible government prosecution [74, 93, 111].

---

## 2. Document Map & Interconnection
The 8 deliverables created for this specification operate as an integrated technical ecosystem, rather than isolated files. The diagram below illustrates how data and control flow through these documents:

```
                                  +---------------------------------------+
                                  |   1. Legal & Compliance Rulebook      | <--- Statutory foundation [118]
                                  +---------------------------------------+
                                                      │
                                                      ▼
+---------------------------------------+  +---------------------------------------+
| 2. Product Classification & Logic     |  | 4. System Requirements & CV Pipeline  |
| • Classifies product categories [28]  |  | • Extracts raw text & metrics [51]    |
| • Identifies exemptions (Rule 26) [33]|  | • Measures character heights [66, 67] |
+---------------------------------------+  +---------------------------------------+
                    │                                          │
                    │ (Category & Exemption Flags)             │ (Extracted Box Values)
                    └─────────────────────┬────────────────────┘
                                          │
                                          ▼
                               +---------------------------------------+
                               | 3. Machine-Readable Compliance Rules  | <--- Evaluates conditions [76]
                               |    (compliance-rules.json)            |
                               +---------------------------------------+
                                                   │
                                                   ▼ (Verdict & Evidentiary Signatures)
                               +---------------------------------------+
                               | 5. Database Schema & REST APIs        | <--- Writes records & logs [112, 117]
                               +---------------------------------------+
                                                   │
                                                   ▼ (Assigned Queues & Escalations)
                               +---------------------------------------+
                               | 6. Enforcement Workflow & Dashboard   | <--- Human-in-the-loop review [102]
                               +---------------------------------------+
                                                   │
                        ┌──────────────────────────┴──────────────────────────┐
                        ▼                                                     ▼
+---------------------------------------+                  +---------------------------------------+
| 7. Violation Report & PDF Spec        |                  | 8. Compliance Test Cases              |
| • Auto-generates certified PDFs [111] |                  | • Mocks compliance scenarios [89]    |
| • Embeds digital signatures [111]     |                  | • Validates ruleset logic [89]        |
+---------------------------------------+                  +---------------------------------------+
```

### Document Relationship Index:
1. **Rulebook $\rightarrow$ Classification & Logic:** The Rulebook defines the legal boundaries (e.g., LMPC Rule 6 and 26) [118, 121], which are operationalized into specific decision trees and standard pack sizes in the Product Classification document [28, 33].
2. **Classification & Requirements $\rightarrow$ Machine-Readable Rules:** The inputs extracted by the CV Pipeline (Document 4) [51] and the classifications determined by the Decision Logic (Document 2) [44] are merged into a flat JSON payload. This payload is passed to the Rule Engine (Document 3) for deterministic evaluation [74, 78].
3. **Machine-Readable Rules $\rightarrow$ Database & APIs:** The Rule Engine output, containing per-rule PASS/FAIL/NEEDS_REVIEW states [75, 78], is ingested by the REST APIs (Document 5) and written to the `scan_extractions` and `violations` tables [113, 115].
4. **Database & APIs $\rightarrow$ Workflow & Dashboards:** The relational database (Document 5) [112] drives the multi-tiered dashboards (Document 6) [107], feeding the Inspector triage queue and the public transparency module [101, 108].
5. **Workflow & Dashboards $\rightarrow$ PDF Violation Reports:** When a human LMO confirms a violation on the Dashboard (Document 6) [102], the backend queries the database tables and runs the FPDF2 generator (Document 7) to output a legally certified, court-admissible PDF [111].
6. **Test Cases $\rightarrow$ Rule Engine:** The 15 compliance test cases (Document 8) [89] are executed in the CI/CD pipeline to verify that the Machine-Readable Rules (Document 3) do not produce regressions [75, 89].

---

## 3. The Implementation Source of Truth
During software development, conflicts may arise between the machine-vision extraction confidence and legal definitions. **The statutory Legal & Compliance Rulebook (Document 1) is the ultimate, non-negotiable source of truth.** 

If a computer vision model achieves $99\%$ confidence that a product net quantity is "300 g approx", the **Rulebook (Rule 6/Rule 11)** strictly bans the word "approx" [121]. Therefore, the system must override the high AI confidence and issue a **BLOCKER** non-compliance verdict [78, 80].

---

## 4. Multi-Phase Deployment and Integration Roadmap

```
  PHASE 1 (Weeks 1-4)       PHASE 2 (Weeks 5-8)       PHASE 3 (Weeks 9-12)      PHASE 4 (Weeks 13-16)
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│ Core Engine & CV      │ │ DB, API, & Triage     │ │ Enforcement Workflow  │ │ National Pilot        │
│                       │ │                       │ │                       │ │                       │
│ • Build 8-stage image │ │ • Deploy PostgreSQL   │ │ • Integrate eMaap     │ │ • Deploy Platform-    │
│   processing pipeline │ │   relational schema.  │ │   national registry.  │ │   facing portals for  │
│ • Implement CRAFT     │ │ • Expose REST APIs for│ │ • Build LMO UI with   │ │   self-certification. │
│   polygon detection.  │ │   SKU ingestion.      │ │   mandatory 'Reason'  │ │ • Launch filterable   │
│ • Run Tesseract +     │ │ • Integrate rule     │ │   block input.        │ │   public dashboard    │
│   PaddleOCR hybrid.   │ │   engine interpreter. │ │ • Deploy SCN generator│ │   with Grievance app. │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘ └───────────────────────┘
```

---

## 5. Architectural Enhancements for SIH 2634 (Missing Topics Added)
To differentiate this implementation and provide maximum national utility, we have researched and incorporated three critical enhancements that address long-standing government metrology pain points [122, 126]:

### 5.1 Cross-State Jurisdictional Data Sharing (National Repeat-Offender Logic)
* **The Problem:** Currently, Legal Metrology is heavily state-administered [105, 126]. If a manufacturer registered in Gujarat commits labeling violations in Karnataka, they are often penalized as a "first-time offender" in Karnataka because state databases do not share compliance histories [105]. This allows national entities to bypass the severe "subsequent offense" penalties under Section 36(1) (fines up to ₹1,00,000 or 1-year imprisonment) [105, 122].
* **The Solution:** The `cases` and `orders_penalties` tables utilize a centralized, national PostgreSQL schema linked by **GSTIN** and **eMaap Registration Number** [112, 114]. When an inspector verifies a case, the system auto-calculates `offence_sequence_no` across all states [114]:
  $$\text{offence\_sequence\_no} = \text{Count}(\text{past\_cases\_verified} \text{ where } \text{seller\_gstin} = \text{current\_gstin}) + 1$$
  This enforces the statutory "second/subsequent offense" severity tiers nationwide [10, 105].

### 5.2 Multi-Platform Delisting API Automation
* **The Problem:** Once a violation is confirmed, there is a lag of weeks before the platform delists the non-compliant SKU, exposing consumers to ongoing overcharging or misleading labels [3, 121].
* **The Solution:** The system implements a **G2B Webhook Broker**. When the Controller signs a compounding order or issues an approved Show-Cause Notice [103, 104], the system triggers an encrypted, real-time webhook sent to the e-commerce platform's private API (Platform-Facing Portal) [109, 112]. The platform's catalog engine immediately flags the ASIN/SKU as "Suspended" or "Delisted" pending remediation [3, 109].

### 5.3 Dynamic Web-Based Rule Engine Updates (Zero-Downtime Hot Swaps)
* **The Problem:** Legal Metrology rules amend frequently (e.g., 2021, 2022, 2023, 2025, 2026 amendments) [118]. Hardcoding these checks into code requires redeploying the entire software stack, leading to compliance evaluation lag and system downtime [76].
* **The Solution:** Following the "Rules as Data" paradigm, rules are encoded in a structured, declarative JSON ruleset [76]. The rule engine interprets these conditions dynamically [76]. When a new gazette amendment is published, the Admin Portal uploads a new JSON file with versioning tags (`effective_from`, `effective_to`) [76, 78]. The engine hot-swaps the ruleset in memory with zero downtime, ensuring that listings scanned on a specific date are evaluated using the exact version of the law in force on that date [75, 76, 83].
