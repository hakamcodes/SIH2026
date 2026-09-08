import { ApiError, parseApiErrorBody } from "./errors";
import type {
  CaseAuditResponse,
  CaseDetail,
  CasesListResponse,
  CaseStatus,
  Case,
  DashboardMetrics,
  EvidenceType,
  EvidenceUploadResponse,
  LimitationsResponse,
  ReportGenerateResponse,
  RulesListResponse,
  RulesReloadResponse,
  ScanCreateResponse,
  ScanDetail,
} from "./types";

/**
 * Every call here targets this app's own /api/lmd/* proxy
 * (src/app/api/lmd/[...path]/route.ts), never the FastAPI backend directly --
 * that proxy is what keeps LMD_INSPECTOR_API_TOKEN server-side. Paths passed
 * in are relative to /api/v1 on the backend, matching backend/lmd/api/*.py's
 * router prefixes exactly.
 */
const PROXY_BASE = "/api/lmd";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  /** X-Inspector-Id is not a secret (backend/lmd/api/deps.py never verifies
   *  it against anything) -- it is fine to send from the browser as-is. */
  inspectorId?: string;
  body?: BodyInit;
  /** Set automatically for BodyInit that isn't FormData; pass explicitly to
   *  override (rarely needed). */
  contentType?: string;
  signal?: AbortSignal;
}

async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers();
  if (options.inspectorId) headers.set("X-Inspector-Id", options.inspectorId);
  // FormData bodies must NOT get an explicit Content-Type: fetch sets
  // multipart/form-data with the correct boundary itself when the body is a
  // FormData instance, and setting it manually here would drop the boundary.
  if (options.contentType) headers.set("Content-Type", options.contentType);

  const response = await fetch(`${PROXY_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body,
    signal: options.signal,
    cache: "no-store",
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    throw parseApiErrorBody(response.status, payload);
  }

  return payload as T;
}

// -- rules ------------------------------------------------------------------
/** GET /api/v1/rules — unauthenticated (backend/lmd/api/rules.py:18). */
export function fetchRules(signal?: AbortSignal): Promise<RulesListResponse> {
  return apiFetch<RulesListResponse>("/rules", { signal });
}

// -- cases --------------------------------------------------------------------
export interface FetchCasesParams {
  status?: CaseStatus;
  limit?: number;
  offset?: number;
}

/** GET /api/v1/cases — unauthenticated (backend/lmd/api/cases.py:43). */
export function fetchCases(
  params: FetchCasesParams = {},
  signal?: AbortSignal,
): Promise<CasesListResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<CasesListResponse>(`/cases${suffix}`, { signal });
}

/** GET /api/v1/cases/{case_id} — unauthenticated (backend/lmd/api/cases.py:53). */
export function fetchCase(caseId: string, signal?: AbortSignal): Promise<CaseDetail> {
  return apiFetch<CaseDetail>(`/cases/${encodeURIComponent(caseId)}`, { signal });
}

// -- scans --------------------------------------------------------------------
export interface CreateScanParams {
  image: File;
  scanSource?: string;
  scanDate?: string;
  commodityCategory?: string;
  commoditySubtype?: string;
  commodityIsImported?: boolean;
  commodityIsExempt?: boolean;
}

/** POST /api/v1/scans — unauthenticated (backend/lmd/api/scan.py:80). Field
 *  names below must match the FastAPI Form()/File() param names exactly:
 *  `image`, `scan_source`, `scan_date`, `commodity_category`,
 *  `commodity_subtype`, `commodity_is_imported`, `commodity_is_exempt`. */
function buildScanFormData(params: CreateScanParams): FormData {
  const formData = new FormData();
  formData.set("image", params.image);
  if (params.scanSource) formData.set("scan_source", params.scanSource);
  if (params.scanDate) formData.set("scan_date", params.scanDate);
  if (params.commodityCategory) formData.set("commodity_category", params.commodityCategory);
  if (params.commoditySubtype) formData.set("commodity_subtype", params.commoditySubtype);
  if (params.commodityIsImported !== undefined) {
    formData.set("commodity_is_imported", String(params.commodityIsImported));
  }
  if (params.commodityIsExempt !== undefined) {
    formData.set("commodity_is_exempt", String(params.commodityIsExempt));
  }
  return formData;
}

export function createScan(
  params: CreateScanParams,
  signal?: AbortSignal,
): Promise<ScanCreateResponse> {
  // FormData bodies must not get an explicit Content-Type: the browser sets
  // multipart/form-data with the correct boundary itself, and the proxy
  // route forwards that header through verbatim.
  return apiFetch<ScanCreateResponse>("/scans", {
    method: "POST",
    body: buildScanFormData(params),
    signal,
  });
}

/**
 * Same request as createScan, but over XMLHttpRequest instead of fetch so the
 * real upload progress (xhr.upload.onprogress, driven by bytes actually sent
 * over the wire) can be reported. fetch has no equivalent request-body
 * progress event. Used to show a genuine upload percentage before the
 * (unmeasurable) server-side OCR/rule-evaluation phase begins.
 */
export function createScanWithProgress(
  params: CreateScanParams,
  options: { onUploadProgress?: (percent: number) => void; signal?: AbortSignal } = {},
): Promise<ScanCreateResponse> {
  const formData = buildScanFormData(params);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${PROXY_BASE}/scans`);
    xhr.responseType = "json";

    if (options.onUploadProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          options.onUploadProgress!(Math.round((event.loaded / event.total) * 100));
        }
      };
    }

    xhr.onload = () => {
      const payload = xhr.response;
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload as ScanCreateResponse);
      } else {
        reject(parseApiErrorBody(xhr.status, payload));
      }
    };

    xhr.onerror = () => {
      reject(
        new ApiError({
          status: 0,
          kind: "backend_unreachable",
          message: "Network error while uploading the image.",
        }),
      );
    };

    if (options.signal) {
      if (options.signal.aborted) {
        xhr.abort();
        return;
      }
      options.signal.addEventListener("abort", () => xhr.abort());
    }

    xhr.send(formData);
  });
}

/** GET /api/v1/scans/{scan_id} — unauthenticated (backend/lmd/api/scan.py:159). */
export function fetchScan(scanId: string, signal?: AbortSignal): Promise<ScanDetail> {
  return apiFetch<ScanDetail>(`/scans/${encodeURIComponent(scanId)}`, { signal });
}

// -- case writes --------------------------------------------------------------
/** POST /api/v1/cases — inspector-gated (backend/lmd/api/cases.py:33). */
export function createCase(scanId: string, inspectorId: string): Promise<Case> {
  return apiFetch<Case>("/cases", {
    method: "POST",
    inspectorId,
    contentType: "application/json",
    body: JSON.stringify({ scan_id: scanId }),
  });
}

export interface UpdateCaseParams {
  status: CaseStatus;
  reasonToBelieveNote?: string;
}

/** PUT /api/v1/cases/{case_id} — inspector-gated. Advancing to
 *  CONFIRMED_VIOLATION / ESCALATED / CLOSED without a note 422s
 *  (Section 15(4)); this function does not pre-validate that client-side so
 *  the real gate is what the UI demonstrates. */
export function updateCase(
  caseId: string,
  params: UpdateCaseParams,
  inspectorId: string,
): Promise<Case> {
  return apiFetch<Case>(`/cases/${encodeURIComponent(caseId)}`, {
    method: "PUT",
    inspectorId,
    contentType: "application/json",
    body: JSON.stringify({
      status: params.status,
      reason_to_believe_note: params.reasonToBelieveNote || undefined,
    }),
  });
}

/** GET /api/v1/cases/{case_id}/audit — unauthenticated. */
export function fetchCaseAudit(caseId: string, signal?: AbortSignal): Promise<CaseAuditResponse> {
  return apiFetch<CaseAuditResponse>(`/cases/${encodeURIComponent(caseId)}/audit`, { signal });
}

export interface UploadEvidenceParams {
  file: File;
  evidenceType: EvidenceType;
  deviceIdentification: string;
}

/** POST /api/v1/cases/{case_id}/evidence — inspector-gated. `evidence_type`
 *  and `device_identification` are query params on the backend
 *  (backend/lmd/api/cases.py:82-83 lack Form(...)), NOT multipart fields --
 *  only the file itself goes in the body. */
export function uploadEvidence(
  caseId: string,
  params: UploadEvidenceParams,
  inspectorId: string,
): Promise<EvidenceUploadResponse> {
  const formData = new FormData();
  formData.set("file", params.file);
  const query = new URLSearchParams({
    evidence_type: params.evidenceType,
    device_identification: params.deviceIdentification,
  });
  return apiFetch<EvidenceUploadResponse>(
    `/cases/${encodeURIComponent(caseId)}/evidence?${query.toString()}`,
    { method: "POST", inspectorId, body: formData },
  );
}

/** POST /api/v1/cases/{case_id}/report — inspector-gated. Idempotent per
 *  case: regenerating overwrites the stored PDF with a new certificate
 *  (backend/lmd/api/reports.py). */
export function generateReport(
  caseId: string,
  inspectorId: string,
): Promise<ReportGenerateResponse> {
  return apiFetch<ReportGenerateResponse>(`/cases/${encodeURIComponent(caseId)}/report`, {
    method: "POST",
    inspectorId,
  });
}

/** Path for <a href> / window.open — GET /api/v1/cases/{case_id}/report is
 *  unauthenticated and returns the raw PDF bytes, proxied the same as every
 *  other call. */
export function reportDownloadPath(caseId: string): string {
  return `/api/lmd/cases/${encodeURIComponent(caseId)}/report`;
}

// -- rules ------------------------------------------------------------------
/** POST /api/v1/rules/reload — inspector-gated (backend/lmd/api/rules.py:33). */
export function reloadRules(inspectorId: string): Promise<RulesReloadResponse> {
  return apiFetch<RulesReloadResponse>("/rules/reload", { method: "POST", inspectorId });
}

// -- metrics / limitations --------------------------------------------------
/** GET /api/v1/metrics — unauthenticated. Both maps are sparse GROUP BY
 *  results; callers must zero-fill across every verdict/status themselves. */
export function fetchMetrics(signal?: AbortSignal): Promise<DashboardMetrics> {
  return apiFetch<DashboardMetrics>("/metrics", { signal });
}

/** GET /api/v1/limitations — unauthenticated. */
export function fetchLimitations(signal?: AbortSignal): Promise<LimitationsResponse> {
  return apiFetch<LimitationsResponse>("/limitations", { signal });
}
