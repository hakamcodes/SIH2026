# Government of India
## Department of Consumer Affairs
### Legal Metrology Enforcement Division

# DATABASE SCHEMA & REST API SPECIFICATION
**Document Identifier:** LMD-DB-2026-V1.0  
**Effective Date:** September 6, 2026  
**Status:** Implementation-Ready Specification  

---

## 1. Relational Database Schema (PostgreSQL DDL)
To ensure absolute data integrity, compliance history tracking, and compatibility with Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (electronic record certification) [93], the database must be structured relationally with strict foreign key constraints, check constraints, and an immutable audit logging trigger [26, 115]:

```sql
-- Enable UUID extension for secure, non-sequential identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Define Custom Enum Types
CREATE TYPE registration_status_enum AS ENUM ('Active', 'Lapsed', 'Not Found');
CREATE TYPE entity_type_enum AS ENUM ('Manufacturer', 'Packer', 'Importer', 'Seller');
CREATE TYPE platform_model_enum AS ENUM ('Marketplace', 'Inventory');
CREATE TYPE severity_enum AS ENUM ('Low', 'Medium', 'High', 'Critical');
CREATE TYPE case_status_enum AS ENUM ('Queued', 'Under Review', 'Notice Issued', 'Remediated', 'Escalated', 'Closed');
CREATE TYPE evidence_type_enum AS ENUM ('Screenshot', 'Package Photo', 'Physical Sample Form', 'Test Report');
CREATE TYPE dispatch_channel_enum AS ENUM ('Email', 'Post', 'eMaap Portal');
CREATE TYPE delivery_status_enum AS ENUM ('Sent', 'Delivered', 'Read', 'Bounced');
CREATE TYPE order_type_enum AS ENUM ('Compounding', 'Prosecution Referral', 'Warning-Improvement Notice');

-- 1. Sellers & Manufacturers Table
CREATE TABLE sellers_manufacturers (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    legal_name TEXT NOT NULL,
    registered_address TEXT NOT NULL,
    gstin VARCHAR(15) UNIQUE CHECK (gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    lm_registration_no VARCHAR(50) UNIQUE, -- Cross-ref to eMaap national registry [112]
    registration_status registration_status_enum NOT NULL DEFAULT 'Not Found',
    entity_type entity_type_enum NOT NULL,
    country_of_origin_declared VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. E-Commerce Platforms Table
CREATE TABLE platforms (
    platform_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_name TEXT NOT NULL UNIQUE,
    model_type platform_model_enum NOT NULL,
    grievance_officer_name TEXT NOT NULL,
    grievance_officer_contact TEXT NOT NULL,
    registered_office_india TEXT NOT NULL,
    api_access_available BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Listings Table
CREATE TABLE listings (
    listing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_id UUID NOT NULL REFERENCES platforms(platform_id) ON DELETE RESTRICT,
    seller_entity_id UUID REFERENCES sellers_manufacturers(entity_id) ON DELETE SET NULL,
    sku_name TEXT NOT NULL,
    category TEXT NOT NULL, -- Category maps which ruleset overlay is applied [113]
    listing_url TEXT NOT NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_scanned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    current_status VARCHAR(50) DEFAULT 'Unscanned'
);

-- 4. Inspectors Table
CREATE TABLE inspectors (
    inspector_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    designation TEXT NOT NULL,
    jurisdiction TEXT NOT NULL, -- state/district/circle boundary [117]
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Cases Table
CREATE TABLE cases (
    case_id VARCHAR(50) PRIMARY KEY, -- Standardized string format, e.g., 'LMD-EC-2026-0001' [114]
    listing_id UUID NOT NULL REFERENCES listings(listing_id) ON DELETE RESTRICT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    severity severity_enum NOT NULL DEFAULT 'Low',
    status case_status_enum NOT NULL DEFAULT 'Queued',
    assigned_inspector_id UUID REFERENCES inspectors(inspector_id) ON DELETE SET NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    reason_to_believe_note TEXT, -- Mandatory before SCN or Seizure escalation [93, 102]
    offence_sequence_no INT DEFAULT 1 CHECK (offence_sequence_no >= 1), -- Track repeat offense count [105, 114]
    closed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_verified_reason CHECK (
        (status IN ('Notice Issued', 'Escalated', 'Closed') AND reason_to_believe_note IS NOT NULL AND reason_to_believe_note != '') OR
        (status IN ('Queued', 'Under Review'))
    )
);

-- 6. BSA Section 63 Evidence Certificates Table (Electronic record integrity)
CREATE TABLE evidence_certificates (
    certificate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_identification TEXT NOT NULL, -- Crawler node or inspector mobile IMEI [115]
    production_process_description TEXT NOT NULL, -- System logging of extraction routine [115]
    certifying_officer TEXT DEFAULT 'SYSTEM-GENERATED',
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Evidence Table
CREATE TABLE evidence (
    evidence_id VARCHAR(50) PRIMARY KEY, -- Standardized format, e.g., 'EVID-0001' [114]
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    evidence_type evidence_type_enum NOT NULL,
    file_path TEXT NOT NULL, -- Storage bucket reference
    sha256_hash VARCHAR(64) NOT NULL CHECK (length(sha256_hash) = 64), -- Tamper evidence validation [93]
    capture_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    bsa_s63_certificate_id UUID REFERENCES evidence_certificates(certificate_id) ON DELETE SET NULL,
    captured_by TEXT NOT NULL
);

-- 8. Scan Extractions Table (Raw OCR/LLM findings per field)
CREATE TABLE scan_extractions (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    listing_id UUID NOT NULL REFERENCES listings(listing_id) ON DELETE CASCADE,
    scan_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    field_name VARCHAR(100) NOT NULL, -- e.g., 'mrp', 'net_quantity', 'country_of_origin'
    extracted_value TEXT,
    confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    source VARCHAR(50) NOT NULL, -- 'listing_text', 'package_image', 'listing_image'
    rule_reference VARCHAR(50) NOT NULL -- Mapped to rulebook rule_id, e.g., 'LM-C01'
);

-- 9. Violations Table
CREATE TABLE violations (
    violation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    rule_violated VARCHAR(50) NOT NULL, -- e.g., 'LM-M01'
    act_section VARCHAR(100) NOT NULL, -- e.g., 'Section 36(1), LM Act 2009'
    description TEXT NOT NULL,
    confirmed_by_inspector BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Notices Table (Show-Cause notice tracking)
CREATE TABLE notices (
    notice_id VARCHAR(50) PRIMARY KEY, -- e.g., 'LMD-SCN-2026-0001'
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_due_by DATE NOT NULL,
    dispatch_channel dispatch_channel_enum NOT NULL,
    delivery_status delivery_status_enum NOT NULL DEFAULT 'Sent',
    seller_response_received_at TIMESTAMP WITH TIME ZONE,
    seller_response_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. Orders & Penalties Table
CREATE TABLE orders_penalties (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(50) NOT NULL REFERENCES cases(case_id) ON DELETE RESTRICT,
    order_type order_type_enum NOT NULL,
    fine_amount DECIMAL(12, 2) NOT NULL CHECK (fine_amount >= 0.0),
    statutory_basis TEXT NOT NULL, -- Cites Section 36(1) or Section 29, etc.
    issuing_officer_id UUID NOT NULL REFERENCES inspectors(inspector_id) ON DELETE RESTRICT,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. Immutable System Audit Log Table
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE SET NULL,
    actor_id UUID NOT NULL, -- Matches inspector_id or 'SYSTEM_UUID'
    action TEXT NOT NULL, -- Logged as: 'viewed case', 'issued notice', etc. [117]
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) NOT NULL,
    device_id TEXT NOT NULL
);
```

---

## 2. REST API Endpoint Specification

### 2.1 SKU Ingestion / Submission for Compliance Scanning
* **Endpoint:** `POST /api/v1/compliance/scan`
* **Content-Type:** `application/json`
* **Function:** Ingests e-commerce metadata and product images to run the 8-stage image pipeline and deterministic rule engine [51].
* **Request Payload (JSON):**
```json
{
  "platform_id": "8f3b90a6-1234-4567-89ab-cdef12345678",
  "listing_url": "https://www.example.com/product/xyz-earbuds",
  "sku_name": "XYZ Wireless Earbuds Premium",
  "category": "electronics",
  "seller_gstin": "27AAAAA1111A1Z1",
  "images": [
    {
      "image_role": "front_pdp",
      "image_url": "https://storage.gov.in/lmd/scans/img_01_front.png",
      "has_calibration_card": true
    },
    {
      "image_role": "side_panel",
      "image_url": "https://storage.gov.in/lmd/scans/img_02_side.png",
      "has_calibration_card": false
    }
  ],
  "listing_text_payload": {
    "title": "XYZ Wireless Earbuds Premium Pack",
    "declared_price": 950.00,
    "declared_net_quantity": "2 Units",
    "declared_country_of_origin": "China",
    "declared_manufacturer": "XYZ Importers Pvt Ltd, Mumbai - 400001"
  }
}
```
* **Success Response (202 Accepted):**
```json
{
  "scan_job_id": "job_7c8d9e2b-ffab-4321-99ee-8a7b6c5d4e3f",
  "case_id_reserved": "LMD-EC-2026-90482",
  "status": "Processing",
  "submitted_at": "2026-09-06T07:31:46Z",
  "estimated_processing_time_sec": 4.5
}
```

### 2.2 Inspector Verification / Case State Modification
* **Endpoint:** `PUT /api/v1/cases/{case_id}`
* **Content-Type:** `application/json`
* **Authorization:** Bearer token (Inspector role required)
* **Function:** Enables manual verification of AI findings [101, 102]. Saves the "reason to believe" required by *ITC v. State of Karnataka 2025* [93].
* **Request Payload (JSON):**
```json
{
  "inspector_id": "a1b2c3d4-0000-1111-2222-333344445555",
  "action": "CONFIRM_VIOLATION | REJECT_FALSE_POSITIVE | REQUEST_EVIDENCE",
  "confirmed_violations": [
    {
      "rule_id": "LM-C04",
      "comment": "Confirmed missing country of origin online. Physical label clearly shows 'Made in China'."
    },
    {
      "rule_id": "LM-X04",
      "comment": "Confirmed listed price is Rs 950 whereas package printed MRP is Rs 900."
    }
  ],
  "reason_to_believe_note": "Direct visual inspection of the seller-uploaded PDP packaging image confirms a printed MRP of ₹900. The online active price charges consumers ₹950, resulting in overpricing in violation of Rule 18(2). Online listing also lacks the mandatory country of origin.",
  "status_escalation": "Notice Issued"
}
```
* **Success Response (200 OK):**
```json
{
  "case_id": "LMD-EC-2026-90482",
  "updated_status": "Notice Issued",
  "assigned_inspector_id": "a1b2c3d4-0000-1111-2222-333344445555",
  "verified_at": "2026-09-06T07:34:12Z",
  "audit_log_id": "f5e4d3c2-bbbb-aaaa-9999-888877776666"
}
```

### 2.3 Show-Cause Notice Generation & Despatch
* **Endpoint:** `POST /api/v1/notices`
* **Content-Type:** `application/json`
* **Function:** Triggers automated drafting and despatch of the SCN to the seller and platform grievance officer [103].
* **Request Payload (JSON):**
```json
{
  "case_id": "LMD-EC-2026-90482",
  "dispatch_channel": "Email",
  "statutory_response_days": 15,
  "recipient_email_seller": "compliance@suryodayfoods.com",
  "recipient_email_platform": "grievance.officer@marketplace.in"
}
```
* **Success Response (201 Created):**
```json
{
  "notice_id": "LMD-SCN-2026-004821",
  "case_id": "LMD-EC-2026-90482",
  "generated_pdf_url": "https://storage.gov.in/lmd/notices/scn_2026_004821.pdf",
  "sent_timestamp": "2026-09-06T07:35:00Z",
  "response_due_by": "2026-09-21"
}
```

### 2.4 National Seller Compliance Lookup
* **Endpoint:** `GET /api/v1/sellers/lookup`
* **Query Parameters:** `gstin` OR `registration_no`
* **Function:** Checks national registration status on eMaap and computes the offense sequence count across state boundaries [105].
* **Success Response (200 OK):**
```json
{
  "gstin": "27AAAAA1111A1Z1",
  "legal_name": "Suryoday Foods Pvt. Ltd.",
  "emaap_registration_no": "LM-REG-2021-MH48210",
  "registration_status": "Active",
  "historical_violations_count": 2,
  "last_offense_date": "2025-11-15T10:00:00Z",
  "offense_sequence_next": 3,
  "current_compliance_score_pct": 82.5
}
```

### 2.5 Public Transparency Dashboard Metrics
* **Endpoint:** `GET /api/v1/dashboard/metrics`
* **Query Parameters:** `state`, `district`, `platform`, `date_start`, `date_end`
* **Function:** Populates the filterable public dashboard with real-time aggregate statistics [108].
* **Success Response (200 OK):**
```json
{
  "aggregation_period": "2026-01-01 to 2026-09-06",
  "total_listings_scanned": 1428312,
  "violations_detected": 82413,
  "notices_issued": 15421,
  "cases_resolved": 11090,
  "compliance_rate_pct": 94.23,
  "top_violation_types": [
    { "category": "Country of Origin Missing", "count": 34102 },
    { "category": "MRP Mismatch / Overpricing", "count": 21841 },
    { "category": "Consumer Care Email Absent", "count": 12090 }
  ],
  "platform_distribution": [
    { "platform_name": "Marketplace_A", "violation_rate_pct": 5.82 },
    { "platform_name": "Marketplace_B", "violation_rate_pct": 4.11 }
  ]
}
```
