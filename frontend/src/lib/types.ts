/**
 * Transcribed by hand from the backend Python models. Hand-written rather than
 * generated because no FastAPI endpoint declares a `response_model`, so the
 * OpenAPI document carries empty `{}` response schemas and codegen would
 * produce nothing usable.
 *
 * Sources:
 *   backend/lmd/engine/models.py        Severity / RuleStatus / Verdict / RuleResult
 *   backend/lmd/store/models.py         CaseStatus / EvidenceType / Case / Evidence
 *   backend/lmd/extraction/contract.py  ExtractionEnvelope
 *   backend/lmd/api/*.py                response shapes
 */

// -- engine/models.py ------------------------------------------------------
export const VERDICTS = ["COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"] as const;
export type Verdict = (typeof VERDICTS)[number];

export const RULE_STATUSES = [
  "PASS",
  "FAIL",
  "REVIEW",
  "NOT_APPLICABLE",
  "NOT_IN_FORCE",
  "NOT_EVALUABLE",
] as const;
export type RuleStatus = (typeof RULE_STATUSES)[number];

export const SEVERITIES = ["BLOCKER", "MAJOR", "MINOR", "DIAGNOSTIC"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const RULE_CATEGORIES = [
  "COMPLETENESS",
  "FORMAT",
  "MATH",
  "CONFLICT",
  "TEMPORAL",
  "UNCERTAINTY",
] as const;
export type RuleCategory = (typeof RULE_CATEGORIES)[number];

// -- store/models.py ------------------------------------------------------
export const CASE_STATUSES = [
  "QUEUED",
  "UNDER_REVIEW",
  "CONFIRMED_VIOLATION",
  "REJECTED_FALSE_POSITIVE",
  "ESCALATED",
  "CLOSED",
] as const;
export type CaseStatus = (typeof CASE_STATUSES)[number];

/** Advancing into one of these without a note is refused by both the sqlite
 *  CHECK constraint and the API (422, Section 15(4)).
 *  Mirrors REASON_TO_BELIEVE_GATED_STATUSES in backend/lmd/store/models.py. */
export const REASON_TO_BELIEVE_GATED_STATUSES: readonly CaseStatus[] = [
  "CONFIRMED_VIOLATION",
  "ESCALATED",
  "CLOSED",
];

export const EVIDENCE_TYPES = [
  "PACKAGE_PHOTO",
  "CALIBRATION_FRAME",
  "ANNOTATED_OVERLAY",
] as const;
export type EvidenceType = (typeof EVIDENCE_TYPES)[number];

// -- rule results ---------------------------------------------------------
export interface RuleResult {
  status: RuleStatus;
  severity: Severity;
  category: string;
  on_fail_code: string | null;
  message: string;
  legal_basis: string;
  citation_verified: boolean;
}

/** GET /api/v1/rules item. */
export interface RuleDefinition {
  rule_id: string;
  category: string;
  description: string;
  legal_basis: string;
  severity: Severity;
  effective_from: string;
  effective_to: string | null;
  citation_verified: boolean;
}

/** GET /api/v1/rules response envelope. */
export interface RulesListResponse {
  rule_count: number;
  rules: RuleDefinition[];
}

// -- extraction/contract.py ----------------------------------------------
export interface NetQuantity {
  value?: number | null;
  unit?: string | null;
}

export interface Mrp {
  value?: number | null;
  currency_marker?: string | null;
  raw_text?: string | null;
  computed_value?: number | null;
}

export interface PipelineReading {
  numeric_val?: number | null;
  text_val?: string | null;
}

export interface ExtractionEnvelope {
  schema_version: "1.0";
  scan_source?: string | null;
  scan_date?: string | null;
  commodity?: {
    category?: string | null;
    subtype?: string | null;
    is_imported?: boolean | null;
    is_exempt?: boolean | null;
  } | null;
  net_quantity?: NetQuantity | null;
  mrp?: Mrp | null;
  mrp_candidates?: number[] | null;
  usp_declared?: number | null;
  mfg_date?: string | null;
  best_before_date?: string | null;
  use_by_date?: string | null;
  expiry_date?: string | null;
  manufacturer_or_packer_or_importer?: {
    name?: string | null;
    address?: string | null;
  } | null;
  common_or_generic_name?: string | null;
  brand_name?: string | null;
  consumer_care?: { phone?: string | null; email?: string | null } | null;
  country_of_origin?: string | null;
  dimensions?: { length?: number | null; width?: number | null } | null;
  mfg_or_pack_or_import_month_year?: string | null;
  /** Keyed by TOP-LEVEL field name only, not dotted path -- the engine does
   *  `path.split(".")[0]` (backend/lmd/engine/engine.py). */
  field_confidences?: Record<string, number> | null;
  ocr_pipeline?: PipelineReading | null;
  llm_pipeline?: PipelineReading | null;
  [key: string]: unknown;
}

// -- Phase 0 additions ----------------------------------------------------
/** Absolute source-image pixels, Nx2 point list (NOT xyxy, NOT normalized).
 *  From TextField.polygon in backend/lmd/cv/pipeline_a.py. */
export type Polygon = [number, number][];

export interface FontMetrics {
  box_h_px: number;
  /** Row-wise ink projection, not the OCR box height. */
  ink_h_px: number | null;
  /** null whenever px_per_mm is null -- never a guessed scale. */
  height_mm: number | null;
  measurable: boolean;
  reason: string | null;
}

export interface OcrBox {
  text: string;
  confidence: number;
  polygon: Polygon;
  enhanced: boolean;
  font_metrics: FontMetrics;
}

export interface Calibration {
  px_per_mm: number;
  card_width_px: number;
  card_height_px: number;
  /** xywh, pixels, from cv2.boundingRect. */
  bounding_box: [number, number, number, number];
}

// -- API response shapes --------------------------------------------------
export interface ScanCreateResponse {
  scan_id: string;
  overall_verdict: Verdict;
  extraction_envelope: ExtractionEnvelope;
  image_sha256: string;
  image_width: number;
  image_height: number;
  ocr_boxes: OcrBox[];
  barcodes: Barcode[];
  calibration: Calibration | null;
  rule_results: Record<string, RuleResult>;
  /** Only present on multi-panel scans (/api/v1/scans/multi). */
  panel_sources?: Record<string, string>;
  panels_processed?: string[];
}

/** One row of GET /api/v1/scans/{id}'s `rule_results` array. NOT the same
 *  shape as ScanCreateResponse.rule_results: this is an array (not keyed by
 *  rule_id) and `citation_verified` is sqlite's raw 0|1, not a JSON bool --
 *  backend/lmd/api/scan.py's two handlers deliberately return different
 *  shapes for the same data. */
export interface RuleResultRow {
  scan_id: string;
  rule_id: string;
  category: string;
  severity: Severity;
  status: RuleStatus;
  on_fail_code: string | null;
  message: string;
  legal_basis: string;
  citation_verified: 0 | 1;
}

/** GET /api/v1/scans/{scan_id} response. */
export interface ScanDetail {
  scan_id: string;
  scan_date: string;
  scan_source: string;
  ruleset_version: string;
  overall_verdict: Verdict;
  created_at: string;
  extraction_envelope: ExtractionEnvelope;
  images_base64: { original?: string; overlay?: string };
  ocr_boxes: OcrBox[];
  rule_results: RuleResultRow[];
}

export interface Case {
  case_id: string;
  scan_id: string;
  status: CaseStatus;
  assigned_inspector_id: string | null;
  reason_to_believe_note: string | null;
  created_at: string;
  verified_at: string | null;
  closed_at: string | null;
}

/** GET /api/v1/cases row: case columns + the joined scan verdict. */
export interface CaseQueueRow extends Case {
  scan_overall_verdict: Verdict;
}

/** GET /api/v1/cases response envelope. */
export interface CasesListResponse {
  cases: CaseQueueRow[];
}

/** GET /api/v1/cases/{case_id} response: case columns + evidence[]. */
export interface CaseDetail extends Case {
  evidence: Evidence[];
}

export interface Evidence {
  evidence_id: string;
  case_id: string;
  evidence_type: EvidenceType;
  file_base64: string;
  sha256_hash: string;
  capture_timestamp: string;
  captured_by: string;
  bsa_s63_certificate_id: string | null;
}

export interface Bsa63Certificate {
  certificate_id: string;
  device_identification: string;
  production_process_description: string;
  certifying_officer: string;
  generated_at: string;
  record_sha256: string;
  hmac_signature: string;
  disclaimer: string;
}

export interface Barcode {
  format: string;
  text: string;
}

/** Both maps are GROUP BY results, so an absent key means zero. Always
 *  zero-fill across all verdicts / all statuses before rendering. */
export interface DashboardMetrics {
  total_scans: number;
  scans_by_verdict: Partial<Record<Verdict, number>>;
  cases_by_status: Partial<Record<CaseStatus, number>>;
  top_failed_rules: Array<{ rule_id: string; fail_count: number }>;
  top_missing_fields: Array<{ field: string; missing_count: number }>;
  compliance_by_category: Record<string, Partial<Record<Verdict, number>>>;
  recent_scans: Array<{
    scan_id: string | null;
    scan_date: string | null;
    overall_verdict: Verdict | null;
    created_at: string | null;
  }>;
}

export interface Limitation {
  area: string;
  status: string;
  detail: string;
}

/** GET /api/v1/limitations response envelope. */
export interface LimitationsResponse {
  limitations: Limitation[];
}

/** POST /api/v1/cases/{case_id}/evidence response. */
export interface EvidenceUploadResponse {
  evidence_id: string;
  sha256_hash: string;
  certificate: Bsa63Certificate;
}

/** POST /api/v1/cases/{case_id}/report response. */
export interface ReportGenerateResponse {
  case_id: string;
  document_sha256: string;
  certificate: Bsa63Certificate;
  download_url: string;
}

// -- NDJSON stage-progress streaming (lmd.api.progress) --------------------
/** One pipeline stage completing, streamed while POST /api/v1/scans or
 *  /scans/multi is still in flight. `index`/`total` are exact, not a guess --
 *  the backend always emits the same fixed set of stage events regardless of
 *  which branch a scan takes (e.g. a skipped vision call still emits one
 *  "vision" event), so total is fixed before the stream opens. */
export interface ScanStageEvent {
  event: "stage";
  stage: string;
  label: string;
  index: number;
  total: number;
  /** Present for scans/multi events tied to one panel; absent for
   *  whole-request stages (rules, compress, persist, ...). */
  panel?: string;
  detail?: string;
}

/** One panel finished processing (scans/multi only). */
export interface ScanPanelDoneEvent {
  event: "panel_done";
  panel: string;
  fields: number;
}

/** Terminal failure mid-stream. The HTTP status was already committed as 200
 *  when the stream opened, so a real failure has to be signalled in-band
 *  instead of as an HTTP error status. */
export interface ScanErrorEvent {
  event: "error";
  status: number;
  detail: string;
}

/** Terminal success: exactly the plain-JSON ScanCreateResponse, tagged. */
export type ScanResultEvent = ScanCreateResponse & { event: "result" };

export type ScanStreamEvent =
  | ScanStageEvent
  | ScanPanelDoneEvent
  | ScanErrorEvent
  | ScanResultEvent;

/** POST /api/v1/rules/reload response. */
export interface RulesReloadResponse {
  reloaded: boolean;
  rule_count: number;
}

/** GET /api/v1/cases/{case_id}/audit response. */
export interface AuditEntry {
  log_id: string;
  case_id: string;
  actor_id: string;
  action: string;
  timestamp: string;
  prev_hash: string;
  entry_hash: string;
}

export interface CaseAuditResponse {
  entries: AuditEntry[];
  chain_verified: boolean;
}
