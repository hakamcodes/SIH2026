# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# NATIONAL LEGAL METROLOGY INTEGRATED ENFORCEMENT WORKFLOW & DASHBOARD SPECIFICATION
**Document Identifier:** LMD-EW-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Implementation-Ready Specification  

---

## 1. Executive Summary
This document specifies the operational design, real-world integration hooks, and multi-tier dashboard specifications for **SIH Problem Statement 2634** [93]. The objective is to transition the automated compliance-checking engine into a fully deployable, legally resilient national enforcement system [93].

To ensure legal defensibility in Indian courts, this specification integrates the **Bharatiya Sakshya Adhiniyam, 2023 (BSA)** [93], the landmark Supreme Court decision in **_ITC Ltd. v. State of Karnataka_ (2025 INSC 1111)** [93], and existing government digital platforms like **eMaap** [93].

---

## 2. Integrated Enforcement Workflow (9-Stage Lifecycle)
The software must enforce a rigid, non-linear lifecycle for every scanned SKU, ensuring human accountability at every step [93, 101, 102]:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0: Automated Detection (Continuous Crawl, OCR/LLM Extraction, reserved Case ID)  │ [100]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Triage & Intelligent Queueing (Group duplicates, prioritize by severity)      │ [101]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: LMO Verification (Inspector reviews AI flags, records mandatory "Reason")     │ [102]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Show-Cause Notice (Auto-drafts notice with Case ID, SCN PDF sent via eMaap)   │ [103]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Response Assessment (Seller responds within 15 days; LMO accepts/escalates)   │ [104]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: Escalation & Seizure (If un-remediated, escalate; physical checks trigger S15)│ [104]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: National History Lookup & Penalty Determination (GSTIN check on eMaap)        │ [105]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 7: Formal Order & Logging (Fine/Compounding fee issued, dashboard updates)       │ [106]
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 8: Post-Closure Active Auditing (System auto-schedules follow-up scans)          │ [106]
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Real-World Legal & System Integration Hooks

### 3.1 eMaap Integration (National Registry Verification)
* **The Legal Context:** The **National Legal Metrology Portal (eMaap)** unifies state-wise manufacturer, packer, and importer registrations [93]. Under Rule 27, registration is mandatory [121].
* **System Action:** During Stage 0, when the system extracts a manufacturer name or registration number, it must execute a real-time API call to the eMaap registry database to check:
  $$\text{Is Registered} = \text{eMaapLookup}(\text{registration\_no} \lor \text{gstin})$$
  If the seller is not found, or if their status is lapsed, the rule engine triggers an immediate **Rule 27 / Section 32(1)** BLOCKER flag [121, 122].

### 3.2 CCPA 2025 Radio Equipment Scanning Precedent
* **The Legal Context:** The Central Consumer Protection Authority (CCPA) issued the *Guidelines for Prevention and Regulation of Illegal Listing and Sale of Radio Equipment, 2025* [93]. This guideline explicitly mandates e-commerce marketplaces to deploy "automated keyword and frequency-based scanning systems" to filter non-compliant radio listings [93].
* **System Action:** This system utilizes this exact regulatory precedent to justify automated, proactive scanning [93]. By mapping Legal Metrology checks onto the same continuous-scanning framework, the system provides DoCA with a ready-to-deploy automated scanning model [93].

### 3.3 BSA 2023 Section 63 Evidence Certificates
* **The Legal Context:** Effective July 1, 2024, **Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA)** replaced Section 65B of the Evidence Act [93]. Digital records (screenshots, scraped HTML, or JSON payloads) are inadmissible in court without an accompanying electronic certificate attesting to the integrity of the device and production process [93].
* **System Action:** At the exact millisecond of e-commerce listing capture, Stage 0 must:
  1. Capture a full-page PNG screenshot and convert the raw HTML DOM into a flat text document.
  2. Calculate the SHA-256 hash of both files.
  3. Generate a system-signed **BSA Section 63 Digital Certificate** containing: Device/Server Node ID, System OS, Timestamp (network-synchronized), Python Script Version, and the SHA-256 payload hashes [100].
  Any evidence lacking this certificate cannot be used in formal compounding or prosecution proceedings [93].

### 3.4 _ITC Ltd. v. State of Karnataka (2025)_ Seizure Safeguards
* **The Legal Context:** In **_ITC Ltd. v. State of Karnataka_ (2025 INSC 1111)**, the Supreme Court quashed a Legal Metrology seizure because the inspecting officer did not record independent "reasons to believe" before entering and seizing goods under Section 15 [93]. The Court held that BNSS/CrPC safeguards apply strictly to Metrology enforcement [93].
* **System Action:** The system's rule engine and user interface must enforce this rule:
  * **AI results are advisory pre-screening signals only.** [91]
  * **Mandatory UI Constraint:** The system must prevent any case from progressing to Stage 3 (Notice) or Stage 5 (Seizure Escalation) until the assigned Legal Metrology Officer has typed a manual, detailed **"Reason to Believe"** statement in the UI [93, 102]. The SCN and Seizure Memo must display this note [103, 111].

---

## 4. Multi-Tiered Dashboard Specifications

### 4.1 Tier 1: Inspector Dashboard (Operational Interface)
Designed for the Legal Metrology Officer (LMO) executing day-to-day verifications [107]:
* **Personalized Triage Queue:** Filterable by priority (Severity + SLA deadline) and confidence score [107].
* **Unified Visual Verification View:**
  * Displays the captured e-commerce screenshot on the left and the zoomable PDP packaging image on the right [107].
  * Displays color-coded bounding-box overlays over extracted fields: Green for high confidence ($>75\%$), Orange for review ($<75\%$) [61, 62, 107].
* **One-Click Determinations:** "Confirm Violation", "Flag False Positive", "Request Field Sample" [107].
* **Reasoning Input Block:** A rich-text editor for recording the mandatory "Reason to Believe" (the system will block save if empty) [107].
* **SCN Despatch Center:** Quick-send button to auto-generate and dispatch the show-cause notice PDF [103, 107].

### 4.2 Tier 2: Supervisor & Controller Dashboard (Tactical Interface)
Designed for Regional Controllers approving compound orders or prosecution referrals [108]:
* **District Violation Heatmap:** Color-coded geospatial mapping of registered manufacturers and sellers flagged with outstanding violations [108].
* **National Seller-Wise Repeat Offender Tracker:** Aggregates violation records across state borders [105, 108]. If a seller based in Maharashtra commits a violation in Karnataka, the system automatically tags them with an "Offense Sequence No. 2", triggering double-fine calculations under Section 36(1) [10, 105, 114].
* **Prosecution Approval Queue:** Single-view summary of LMO-verified cases requesting compounding or court prosecution referrals, with immediate access to BSA certificates and evidence hashes [104, 108].
* **Inspector Workload & SLA Tracker:** Visualizes active queues, average case resolution times, and notice response rates [108].

### 4.3 Tier 3: Public Transparency Dashboard (Citizen Interface)
Mirroring Odisha's Directorate of Legal Metrology model to build citizen trust [93, 108]:
* **Active Enforcement Counters:** Real-time counters showing total listings scanned, SCNs issued, fines compounded, and consumer savings [108].
* **Filterable Verification Reports:** Citizens can search by Date Range, Product Category, E-Commerce Platform, and District [108].
* **eMaap Registration Status Lookup:** Public portal allowing consumers to type a GSTIN or LMPC registration number to verify if a manufacturer is registered [108].
* **"e-Abhijoga" Citizen Complaint Portal:** Feeds citizen-reported e-commerce URLs or photo uploads directly into the Stage-0 automated scanning queue (mirroring Kerala's Sutharyam app) [93, 108].

### 4.4 Tier 4: Platform-Facing Portal (Intermediary Interface)
Designed for e-commerce platforms (e.g., Amazon, Flipkart) to manage catalog compliance [109]:
* **Active Compliance Scorecard:** Platform-wide compliance percentage, updated weekly [109].
* **Notice Inbox:** Direct access to SCNs issued against sellers on their platform [109].
* **Proof-of-Remediation Portal:** Interface to upload screenshots of delisted or corrected SKU pages to resolve active cases [109].
* **Bulk eMaap Linker:** API channel for platforms to upload seller catalogs and automatically link them to eMaap registration numbers to bypass low-risk scanning queues [109].

### 4.5 Tier 5: System Admin / MLOps View (Engine Diagnostics)
Designed for technical administrators [109]:
* **Crawler Health Monitor:** Active crawler nodes, scrape success rate, and page block/captcha occurrences [109].
* **Model Accuracy Diagnostics:** False-positive and false-negative tracking per rule [109]. Enables fine-tuning of the $\tau$ confidence thresholds for numeric fields [64, 109].
* **Immutable Audit Trail Viewer:** Logs every user action, timestamp, IP address, and database modification to prevent internal tampering [26, 109, 117].
