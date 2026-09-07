# E-Commerce + Enforcement Workflow + Reporting — SIH PS 2634
### Turning the compliance-checker into a deployable enforcement product (v1.0, September 2026)

---

## 0. Grounding: what real Indian enforcement infrastructure already looks like

Before designing the workflow, here's what currently exists — your system needs to slot into this, not replace it:

- **The legal hook for automated scanning already exists.** The CCPA's *Guidelines for Prevention and Regulation of Illegal Listing and Sale of Radio Equipment, 2025* (issued under Section 18, Consumer Protection Act 2019) already mandates that e-commerce platforms run "automated keyword and frequency-based scanning systems" to detect non-compliant listings, plus a public reporting channel. This is the closest real precedent to PS 2634 — a government-mandated automated-scanning-plus-human-verification model — and it is recent enough (May 2025) to cite directly in your proposal.
- **The government has admitted it has no such tool for Legal Metrology yet.** In an April 2026 Rajya Sabha question, the Ministry of Consumer Affairs was asked directly whether it had built an AI system to detect counterfeit/non-compliant listings; its answer pivoted to the National Consumer Helpline's AI chatbot and speech recognition — which only handles *inbound complaints*, not *proactive detection*. This is the exact gap your prototype fills, and it's worth stating explicitly in your problem framing.
- **Registration/licensing is already digitised (eMaap).** The National Legal Metrology Portal (eMaap) unifies state-wise manufacturer/packer/importer registration, licensing, and verification records that were previously fragmented across states. Your system should treat eMaap as the authoritative registry to cross-check declared manufacturer/importer identities against (Rule 27 registration), not reinvent it.
- **A public transparency dashboard model already exists at state level.** Odisha's Directorate of Legal Metrology runs a public dashboard with filterable verification reports (by date range, instrument category, district, unit) and a grievance module ("e-Abhijoga"). Kerala runs a citizen complaint app ("Sutharyam") specifically for reporting Legal Metrology violations. Your dashboard design should mirror this filterable, public-facing structure, not invent a new paradigm.
- **Screenshots are not self-proving evidence.** Under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (which replaced Section 65B of the Evidence Act on 1 July 2024), an electronic record — including a scraped screenshot or saved HTML page — is admissible only with an accompanying certificate identifying the device, the process of production, and attesting to the record's integrity. Your evidence-capture module must generate this certificate (and a tamper-evident hash) automatically at capture time, or your evidence is worthless in a prosecution.
- **AI output cannot itself authorise seizure or coercive action.** The Supreme Court, in *ITC Ltd. v. State of Karnataka* (2025 INSC 1111), quashed a Legal Metrology seizure because the inspecting officer had not recorded "reasons to believe" or obtained a warrant before search/seizure under Section 15 of the Act, holding that CrPC/BNSS safeguards apply. This means your AI flag is legally a *trigger for an inspector's independent, documented "reason to believe"* — never a stand-alone basis for enforcement action. This single point should shape your entire workflow design (see Stage 2 below).

---

## 1. E-Commerce Compliance Checklist

Combines Legal Metrology (Packaged Commodities) Rules 2011 (Rule 6(10)) with the Consumer Protection (E-Commerce) Rules, 2020, since both apply simultaneously to a marketplace listing.

### A. Identity & Origin
- [ ] Manufacturer / packer / importer name + complete address displayed (Rule 6(1)(a), via Rule 6(10))
- [ ] Country of origin/manufacture/assembly displayed for every SKU, not just visibly imported ones (Rule 6(1)(a) proviso)
- [ ] Name and details of the importer additionally disclosed where goods are imported (CP(E-Commerce) Rules 2020, Rule 6(5))
- [ ] Legal name, principal place of business, and website details of the e-commerce entity itself displayed (CP(E-Commerce) Rules 2020, Rule 5)

### B. Product Identity & Quantity
- [ ] Common/generic name of the commodity present, distinct from marketing/brand name (Rule 6(1)(b))
- [ ] Net quantity declared in a standard SI unit, no vague qualifiers ("approx.", "about") (Rule 6(1)(c))
- [ ] Unit Sale Price declared where applicable, and **USP × net quantity ≈ MRP** (flag any arithmetic mismatch) — not required for Combination/Group/Multi-Piece Packages

### C. Pricing
- [ ] MRP shown inclusive of all taxes, in the prescribed format (Rule 6(1)(e))
- [ ] Displayed/checkout price does not exceed MRP (Rule 18(2))
- [ ] Total price with a clear break-up of all other charges (delivery, packaging, etc.) shown before checkout (CP(E-Commerce) Rules 2020)
- [ ] No unjustified price manipulation or discrimination between consumers of the same class (CP(E-Commerce) Rules 2020)

### D. Dates
- [ ] Month & year of manufacture/packing/import present on the *package* (need not be shown on the *listing* — Rule 6(10) exempts this one field only)
- [ ] "Best before"/"Use by" date shown for perishable/consumable categories (Rule 6(1)(da))

### E. Consumer Care & Grievance
- [ ] Consumer-care name, address, phone, e-mail present on the listing (Rule 6(2))
- [ ] Grievance officer's name, designation, and contact details displayed on the platform (CP(E-Commerce) Rules 2020, Rule 4(4))
- [ ] Return/refund/exchange/warranty/guarantee/delivery-and-shipment terms disclosed pre-purchase

### F. Package-vs-Listing Cross-Verification (the core AI task)
- [ ] Net quantity on listing text matches net quantity OCR-read from the product/package image
- [ ] MRP on listing matches MRP visible on the package image
- [ ] Country of origin on listing matches package declaration
- [ ] Product image genuinely depicts the item being sold (not a generic/stock photo misrepresenting contents) — cross-reference seller's authenticity undertaking under CP(E-Commerce) Rules 2020
- [ ] Manufacturer/importer name on listing matches the declared entity in the eMaap registration database

### G. Category-Specific Overlays (switch rule-set by category)
- [ ] Food/beverage → defer labelling checks to FSSAI rules, keep only MRP/USP/consumer-care from LM Rules
- [ ] Medical devices → defer PDP font/placement checks to Medical Devices Rules, 2017 (2025 LM amendment carve-out)
- [ ] Radio equipment/wireless devices → check for Equipment Type Approval (ETA) disclosure and frequency band declaration (CCPA Guidelines, 2025)
- [ ] Cosmetics/drugs → defer to Drugs & Cosmetics Rules, 1945

### H. Structural / Platform-Level (applies once per platform, not per SKU)
- [ ] Ranking-parameter disclosure present (why a product/seller appears where it does)
- [ ] No pre-checked/implied consent boxes for add-on purchases
- [ ] Seller identity disclosed to consumer on request (for dispute resolution)
- [ ] Cancellation-charge policy is symmetric (platform can't charge the consumer without bearing equivalent liability itself)

---

## 2. Complete Inspector Workflow

### Stage 0 — Automated Detection (machine layer, runs continuously)
1. Scheduled crawler/API client pulls listing pages (and, where available, official seller APIs) from target marketplaces.
2. OCR + NLP pipeline extracts each checklist field (Section 1 above) from listing text and product images.
3. Cross-check extracted fields against (a) each other for internal consistency (USP×qty≈MRP), (b) the eMaap registration database for manufacturer identity, and (c) prior scans of the same SKU for drift/changes.
4. Each field gets a **confidence score**; each SKU gets an overall **compliance status**: `Compliant / Non-Compliant / Needs Review`.
5. System auto-generates a **Case ID**, captures a timestamped, hashed (SHA-256) screenshot + full page snapshot, and drafts a BSA Section 63 certificate stub for the capture event. This bundle becomes the evidence packet from the very first moment — not something assembled later.

### Stage 1 — Triage & Queueing
6. Cases are bucketed into an inspector queue, prioritised by: severity (which rule, how central to consumer harm), confidence (low-confidence extractions surface for human review first), and repeat-seller/repeat-SKU clustering.
7. Duplicate detections (same seller, same defect, across multiple SKUs) are grouped into a single case to avoid flooding inspectors with near-identical items.

### Stage 2 — Inspector Verification (mandatory human-in-the-loop; this is the legally load-bearing step)
8. Inspector opens the case: sees the screenshot, an OCR overlay highlighting each extracted field, the specific rule citation for each flagged defect, and the confidence score.
9. Inspector marks each flag: **Confirm violation / False positive / Needs more evidence**.
10. If confirmed, the inspector must record a free-text **"reason to believe"** note tied to specific evidence and rule — this is not a formality; it is what *ITC v. State of Karnataka* (2025) requires before any coercive step follows. The system should refuse to progress a case to Stage 3 without this field populated.
11. Inspector may request supplementary evidence (re-crawl after 24h, request a physical sample via the state's local Legal Metrology office, or escalate to a physical inspection at the declared manufacturer address under Section 15).

### Stage 3 — Notice / Show-Cause
12. System auto-drafts a notice citing the exact rule violated, referencing the Case ID and evidence bundle, with a statutory response window (practice has used ~15 days).
13. Notice is dispatched to the seller and, separately, to the platform's grievance officer (whose contact is itself a mandatory disclosure under CP(E-Commerce) Rules 2020 — so the system should already have it on file from Stage 0 field extraction).
14. Dispatch timestamp and delivery/read receipts are logged.

### Stage 4 — Response & Compliance Check
15. Seller/platform may respond within the window with corrective evidence (e.g., an updated listing screenshot).
16. Inspector reviews the response against the original violation; either closes the case as **remediated** or escalates.

### Stage 5 — Escalation (Compounding or Prosecution)
17. Unresolved or repeat cases go to the Controller/Director for a compounding order (Section 48, LM Act) or a prosecution referral (Section 36).
18. If the case requires physical entry/seizure (e.g., verifying seller-held stock), the officer must independently record "reasons to believe" and follow CrPC/BNSS search-and-seizure safeguards — carry Identity card, Seizure Receipt Book, verified test weights, copy of Act & Rules, Notice Form, Seizure Memo, Panchnama, and sealing material, per the standard state Legal Metrology field checklist.
19. Physical sample testing, where triggered, follows the existing Rule 19 sampling procedure (Fifth Schedule sample sizes, Sixth Schedule test method, Seventh Schedule Form A/B data sheets) — your system should digitise these forms rather than replace the underlying procedure.

### Stage 6 — Penalty Determination
20. System computes the applicable penalty tier by cross-referencing the seller/manufacturer's **national** inspection history (by registration number/GSTIN, not just state records — directly addressing the long-standing problem that repeat offences are currently tracked only within each state, so a national offender can appear as a "first-time offender" in every new state).
21. Tier logic follows Section 36 (1st/2nd/subsequent offence fine bands) and Rule 32 (registration/other contraventions), pulling the current post-2026 Jan Vishwas amounts where applicable (see Matrix document, Part 2).

### Stage 7 — Order & Closure
22. Formal order (fine/compounding fee/prosecution referral) issued and logged.
23. Case added to the seller's permanent compliance history; dashboard and public aggregate stats update.

### Stage 8 — Post-Closure Monitoring
24. System auto-schedules a re-check of the same SKU/seller after a set interval (e.g., 30/60/90 days).
25. A repeat violation on the same field/seller automatically escalates the severity tier for the next cycle — this is what operationalises the "repeat violations" requirement rather than leaving it as a manual lookup.

---

## 3. Dashboard Feature List

### 3.1 Inspector Dashboard
- Personal case queue, sortable by priority/confidence/SLA deadline
- Case detail view: screenshot, OCR overlay, rule citations, confidence meter per field, package-vs-listing side-by-side comparison
- One-click actions: Confirm / False positive / Request more evidence / Escalate
- Mandatory "reason to believe" text field, rule-linked, before any escalation is allowed
- Evidence upload for physical inspection (photos, seizure memo, panchnama scan, Form A/B data sheet)
- Notice drafting, e-despatch, and delivery-tracking
- SLA countdown per case (response-window timer)

### 3.2 Supervisor / Controller Dashboard
- State/district violation heatmap
- Seller- and platform-wise repeat-violation tracker (national view)
- Category/rule-wise violation trend charts (which declaration is most frequently missing, by platform)
- Inspector workload and case-aging view
- Compounding/prosecution approval queue
- High-severity case alert digest

### 3.3 Public Transparency Dashboard (mirrors the Odisha DLM model)
- Aggregate counters: SKUs scanned, violations detected, notices issued, cases resolved
- Filters: state, district, platform, product category, date range
- Manufacturer/packer/importer registration-status lookup (linked to eMaap)
- Public complaint submission form (feeds directly into the Stage-0 detection queue, mirroring Kerala's Sutharyam app)

### 3.4 Platform-Facing Portal (optional, for the e-commerce entities)
- View notices issued against their listed SKUs
- Upload compliance-correction proof
- View own aggregate compliance score/history
- Bulk self-certification upload (e.g., linking SKUs to eMaap registration numbers) to pre-clear low-risk catalogues

### 3.5 System Admin / MLOps View
- Crawler health and coverage (platforms covered, SKUs scanned/day, error rate)
- Model accuracy monitoring — false-positive rate *per rule*, since some fields (e.g., MRP OCR) are far more reliable than others (e.g., "product image matches contents")
- Full audit-log viewer: every read/write on a case, by whom, when (see Section 6, Audit_Log table)

---

## 4. Sample Violation Report (illustrative mock case)

```
CASE ID: LMD-EC-2026-0091423
STATUS: Confirmed Violation — Notice Issued
DETECTED: 2026-09-02 03:14:17 IST (automated crawl cycle #4471)
VERIFIED BY: Inspector R. Deshmukh, Legal Metrology Office, Pune Circle
VERIFIED ON: 2026-09-03 11:20 IST

PLATFORM: [Marketplace Name]
SELLER: Suryoday Foods Pvt. Ltd. (Seller ID: SEL-88213; GSTIN on file)
SKU: "Suryoday Premium Masala Biscuits – Family Pack"
LISTING URL: https://[platform]/dp/B0XXXXXXX (archived snapshot: EVID-0091423-01)

VIOLATIONS FOUND:
1. Rule 6(1)(a) proviso [Country of Origin] — NOT DISPLAYED on listing.
   Confidence: 96% (field absent from full-page text scan; confirmed by inspector)
2. Rule 6(1)(e) [MRP mismatch] — Listing shows MRP ₹95.00; OCR of package
   image (seller-uploaded) shows printed MRP ₹85.00.
   Confidence: 89% (OCR); confirmed by inspector via zoomed image review
3. Rule 6(2) [Consumer care] — Email field present; phone number missing.
   Confidence: 99%

RULE REFERENCE: Legal Metrology (Packaged Commodities) Rules, 2011,
Rule 6(1)(a), 6(1)(e), 6(2), read with Rule 6(10) (e-commerce display duty),
inserted by GSR 629(E) dated 23.06.2017.

OFFENCE CLASSIFICATION: First offence (seller has no prior record in national
inspection history as of case date) — Section 36(1), Legal Metrology Act, 2009.

SEVERITY: Medium (pricing discrepancy — potential consumer overcharging —
elevates an otherwise Low-severity labelling gap)

INSPECTOR REMARKS:
"Price discrepancy confirmed by direct visual comparison of the seller's own
product image against the listed MRP; this is not an OCR artefact. Country-of-
origin field has never been populated for this SKU across 4 prior scan cycles
(2026-07-15 to 2026-09-02), indicating a persistent gap rather than a one-off
listing error. Recommend standard 15-day show-cause notice; physical inspection
not warranted at this stage as the discrepancy is verifiable from the public
listing and seller-submitted images alone."

ACTION TAKEN: Show-cause notice LMD-SCN-2026-004821 dispatched
2026-09-03 to seller and platform grievance officer; response due 2026-09-18.

EVIDENCE BUNDLE: EVID-0091423-01 (screenshot, SHA-256: 3f9a...c21e,
BSA s.63 certificate attached), EVID-0091423-02 (package image, seller-
uploaded, hash on file)
```

---

## 5. Sample PDF / Export Report Structure

A generated case report (for court filing, compounding order, or internal audit) should follow this section order:

1. **Cover block** — Case ID, QR code linking to the digital case record, department letterhead, date of generation, classification (Internal / For Prosecution / Public Summary)
2. **Executive summary** — one paragraph: what was found, on which platform/seller/SKU, current status
3. **Legal basis** — exact rule(s) and section(s) invoked, quoted by citation only (rule number + short paraphrase, not full text)
4. **Detection details** — crawl timestamp, detection method (automated/complaint-triggered), Case ID, link to live/archived listing
5. **Evidence exhibits** — each screenshot/photograph as a numbered exhibit, with: capture timestamp, SHA-256 hash, BSA Section 63 certificate reference, and a one-line caption of what it shows
6. **Field-by-field extraction table** — every checked field, extracted value, confidence score, pass/fail status (this is the machine-readable core of the report)
7. **Inspector verification & remarks** — inspector name/ID, verification timestamp, "reason to believe" statement, confirm/reject decision per flagged field
8. **Offence classification & penalty computation** — offence count (1st/2nd/subsequent) per the national inspection-history lookup, applicable fine band, statutory citation
9. **Enforcement action log** — notices issued, dispatch/delivery timestamps, seller/platform responses received, dates
10. **Officer determination & signature block** — digital signature or DSC, designation, office jurisdiction, date
11. **Annexures** — full raw HTML/DOM capture reference, prior-history summary for the same seller, any physical inspection Form A/B data sheets
12. **Audit trail footer on every page** — document hash, generation timestamp, "this document was system-generated from Case ID [X]; verify at [portal URL]"

---

## 6. Proposed Database Schema — Inspection History

### `sellers_manufacturers`
| Field | Type | Notes |
|---|---|---|
| entity_id (PK) | UUID | |
| legal_name | text | |
| registered_address | text | |
| gstin | varchar(15) | |
| lm_registration_no | varchar | cross-ref to eMaap (Rule 27) |
| registration_status | enum | Active/Lapsed/Not Found |
| entity_type | enum | Manufacturer/Packer/Importer/Seller |
| country_of_origin_declared | text | for imports |
| created_at / updated_at | timestamp | |

### `platforms`
| Field | Type | Notes |
|---|---|---|
| platform_id (PK) | UUID | |
| platform_name | text | |
| model_type | enum | Marketplace/Inventory |
| grievance_officer_name | text | CP(E-Commerce) Rules 2020, Rule 4(4) |
| grievance_officer_contact | text | |
| registered_office_india | text | |
| api_access_available | boolean | |

### `listings`
| Field | Type | Notes |
|---|---|---|
| listing_id (PK) | UUID | |
| platform_id (FK) | UUID | |
| seller_entity_id (FK) | UUID | |
| sku_name | text | |
| category | text | drives which rule-overlay applies (Section 1.G) |
| listing_url | text | |
| first_seen_at / last_scanned_at | timestamp | |
| current_status | enum | Compliant/Non-Compliant/Needs Review/Unscanned |

### `scan_extractions`
| Field | Type | Notes |
|---|---|---|
| extraction_id (PK) | UUID | |
| listing_id (FK) | UUID | |
| scan_timestamp | timestamp | |
| field_name | text | e.g. "country_of_origin", "mrp", "net_quantity" |
| extracted_value | text | |
| confidence_score | float | 0–1 |
| source | enum | listing_text/listing_image/package_image |
| rule_reference | text | e.g. "Rule 6(1)(a)" |

### `cases`
| Field | Type | Notes |
|---|---|---|
| case_id (PK) | varchar | e.g. LMD-EC-2026-0091423 |
| listing_id (FK) | UUID | |
| detected_at | timestamp | |
| severity | enum | Low/Medium/High/Critical |
| status | enum | Queued/Under Review/Notice Issued/Remediated/Escalated/Closed |
| assigned_inspector_id (FK) | UUID | |
| verified_at | timestamp | nullable until Stage 2 complete |
| reason_to_believe_note | text | mandatory before escalation (Section 15 safeguard) |
| offence_sequence_no | int | 1st/2nd/3rd+ for this entity, computed from history |
| closed_at | timestamp | nullable |

### `evidence`
| Field | Type | Notes |
|---|---|---|
| evidence_id (PK) | varchar | e.g. EVID-0091423-01 |
| case_id (FK) | varchar | |
| evidence_type | enum | Screenshot/Package Photo/Physical Sample Form/Test Report |
| file_path | text | |
| sha256_hash | varchar(64) | tamper-evidence |
| capture_timestamp | timestamp | |
| bsa_s63_certificate_id (FK) | UUID | links to `evidence_certificates` |
| captured_by | text | system/inspector ID |

### `evidence_certificates` (BSA Section 63 compliance)
| Field | Type | Notes |
|---|---|---|
| certificate_id (PK) | UUID | |
| evidence_id (FK) | varchar | |
| device_identification | text | crawler node ID / inspector device |
| production_process_description | text | auto-filled from capture pipeline |
| certifying_officer | text | for physical-inspection evidence only |
| generated_at | timestamp | |

### `violations`
| Field | Type | Notes |
|---|---|---|
| violation_id (PK) | UUID | |
| case_id (FK) | varchar | |
| rule_violated | text | e.g. "Rule 6(1)(e)" |
| act_section | text | e.g. "Section 36(1), LM Act 2009" |
| description | text | |
| confirmed_by_inspector | boolean | |

### `notices`
| Field | Type | Notes |
|---|---|---|
| notice_id (PK) | varchar | e.g. LMD-SCN-2026-004821 |
| case_id (FK) | varchar | |
| issued_at | timestamp | |
| response_due_by | date | |
| dispatch_channel | enum | Email/Post/eMaap portal |
| delivery_status | enum | Sent/Delivered/Read/Bounced |
| seller_response_received_at | timestamp | nullable |
| seller_response_text | text | nullable |

### `orders_penalties`
| Field | Type | Notes |
|---|---|---|
| order_id (PK) | UUID | |
| case_id (FK) | varchar | |
| order_type | enum | Compounding/Prosecution Referral/Warning-Improvement Notice |
| fine_amount | decimal | |
| statutory_basis | text | e.g. "Section 36(1), 1st offence" |
| issuing_officer_id (FK) | UUID | |
| issued_at | timestamp | |

### `audit_log`
| Field | Type | Notes |
|---|---|---|
| log_id (PK) | UUID | |
| case_id (FK, nullable) | varchar | |
| actor_id | UUID | user or "SYSTEM" |
| action | text | e.g. "viewed case", "confirmed violation", "generated report" |
| timestamp | timestamp | |
| ip_address / device_id | text | |

### `inspectors`
| Field | Type | Notes |
|---|---|---|
| inspector_id (PK) | UUID | |
| name | text | |
| designation | text | e.g. "Inspector", "Assistant Controller" |
| jurisdiction | text | state/district/circle |
| active | boolean | |

---

## 7. Open Items to Verify Before Build

1. Confirm with your mentor/department contact whether the system is meant to feed **into** existing DoCA infrastructure (eMaap, INGRAM) via API, or operate as a **standalone recommendation** — this materially changes whether `sellers_manufacturers.lm_registration_no` is a live lookup or a static import.
2. Clarify jurisdiction: Legal Metrology enforcement is largely a **state subject** (state Controllers, state Inspectors) even though the Rules are central — your national repeat-offender view (Stage 6) is valuable precisely because no such cross-state view exists today, but you should be explicit in your pitch that this is a *proposed* capability, not one that currently exists.
3. Get legal sign-off (or at least a documented assumption) on whether AI-confirmed evidence bundles, once BSA-certified, would actually be accepted by a given state's Legal Metrology Controller in practice — this is a policy question your prototype can flag but not resolve on its own.
