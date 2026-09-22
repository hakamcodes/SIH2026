import { ApiError, parseApiErrorBody } from "./errors";
import { resizeForUpload } from "./image-utils";
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
  ScanStreamEvent,
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

export async function createScan(
  params: CreateScanParams,
  signal?: AbortSignal,
): Promise<ScanCreateResponse> {
  // FormData bodies must not get an explicit Content-Type: the browser sets
  // multipart/form-data with the correct boundary itself, and the proxy
  // route forwards that header through verbatim.
  const image = await resizeForUpload(params.image);
  return apiFetch<ScanCreateResponse>("/scans", {
    method: "POST",
    body: buildScanFormData({ ...params, image }),
    signal,
  });
}

export interface ScanProgressOptions {
  onUploadProgress?: (percent: number) => void;
  /** Called for every stage/panel_done event as the backend's pipeline runs
   *  (backend/lmd/api/progress.py NDJSON stream). Never called for the
   *  terminal result/error events -- those resolve/reject the promise. */
  onStage?: (event: ScanStreamEvent) => void;
  signal?: AbortSignal;
}

/**
 * POSTs `formData` and resolves with the final ScanCreateResponse, over
 * XMLHttpRequest rather than fetch for two reasons: (1) real upload progress
 * (xhr.upload.onprogress, driven by bytes actually sent over the wire) has no
 * fetch equivalent, and (2) incremental access to a still-arriving response
 * body via xhr.responseText/onprogress, which is what makes reading the
 * backend's NDJSON stage stream possible before the request completes.
 *
 * The backend (lmd.api.progress) only streams NDJSON when the request sends
 * `Accept: application/x-ndjson`; each line is one JSON object with an
 * `event` field ("stage" | "panel_done" | "result" | "error"). Anything that
 * isn't a stage/panel_done event settles the promise.
 */
function postFormDataWithProgress(
  url: string,
  formData: FormData,
  options: ScanProgressOptions,
  networkErrorMessage: string,
): Promise<ScanCreateResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("Accept", "application/x-ndjson");
    xhr.responseType = "text";

    let cursor = 0;
    let settled = false;
    // Set once any stage/panel_done event arrives, i.e. the backend actually
    // started the CV pipeline for this request (as opposed to failing before
    // it ever got there). On Render's 512MB free tier the process gets
    // OOM-killed mid-scan with no error event -- the connection just drops --
    // so a mid-stream failure here is almost always that, not a generic bug.
    let scanStarted = false;
    const OOM_MESSAGE =
      "The server ran out of memory while scanning (Render's free-tier 512MB limit). " +
      "This is a hosting limit, not a bug in the scan itself. Try again with a smaller " +
      "image, or scan one panel at a time instead of all at once.";

    if (options.onUploadProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          options.onUploadProgress!(Math.round((event.loaded / event.total) * 100));
        }
      };
    }

    function drainAvailableLines() {
      const text = xhr.responseText;
      let newlineAt = text.indexOf("\n", cursor);
      while (newlineAt !== -1 && !settled) {
        const line = text.slice(cursor, newlineAt).trim();
        cursor = newlineAt + 1;
        newlineAt = text.indexOf("\n", cursor);
        if (!line) continue;

        let parsed: ScanStreamEvent;
        try {
          parsed = JSON.parse(line) as ScanStreamEvent;
        } catch {
          continue; // a line split across two onprogress ticks is handled by the cursor, not here
        }

        if (parsed.event === "result") {
          settled = true;
          const { event: _event, ...result } = parsed;
          resolve(result as ScanCreateResponse);
        } else if (parsed.event === "error") {
          settled = true;
          reject(parseApiErrorBody(parsed.status, { detail: parsed.detail }));
        } else {
          scanStarted = true;
          options.onStage?.(parsed);
        }
      }
    }

    // NDJSON lines arrive across multiple onprogress ticks as the backend's
    // pipeline runs -- this is the only place a still-streaming body can be
    // read incrementally with XMLHttpRequest.
    xhr.onprogress = () => {
      if (!settled) drainAvailableLines();
    };

    xhr.onload = () => {
      if (settled) return;
      drainAvailableLines();
      if (settled) return;
      // The stream ended with no terminal event -- either a validation error
      // that never opened the NDJSON stream (backend returns plain JSON for
      // that), or the connection closed early.
      if (xhr.status >= 200 && xhr.status < 300) {
        reject(
          new ApiError({
            status: xhr.status,
            kind: scanStarted ? "server_out_of_memory" : "generic",
            message: scanStarted ? OOM_MESSAGE : "The scan stream ended without a result.",
          }),
        );
        return;
      }
      // 502/503/504 here is Render's proxy reporting the app process died --
      // on the free tier that is overwhelmingly the OOM killer, not a bug.
      if (scanStarted && [502, 503, 504].includes(xhr.status)) {
        reject(new ApiError({ status: xhr.status, kind: "server_out_of_memory", message: OOM_MESSAGE }));
        return;
      }
      let payload: unknown = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch {
        // not JSON (e.g. an upstream proxy error page) -- parseApiErrorBody falls back cleanly
      }
      reject(parseApiErrorBody(xhr.status, payload));
    };

    xhr.onerror = () => {
      reject(
        scanStarted
          ? new ApiError({ status: 0, kind: "server_out_of_memory", message: OOM_MESSAGE })
          : new ApiError({ status: 0, kind: "backend_unreachable", message: networkErrorMessage }),
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

/**
 * Same request as createScan, but streams real progress: upload percentage
 * from xhr.upload.onprogress, then per-stage events from the backend's NDJSON
 * pipeline stream (backend/lmd/api/progress.py) via onStage.
 */
export async function createScanWithProgress(
  params: CreateScanParams,
  options: ScanProgressOptions = {},
): Promise<ScanCreateResponse> {
  const image = await resizeForUpload(params.image);
  const formData = buildScanFormData({ ...params, image });
  return postFormDataWithProgress(
    `${PROXY_BASE}/scans`,
    formData,
    options,
    "Network error while uploading the image.",
  );
}

export interface CreateMultiScanParams {
  front?: File;
  back?: File;
  side?: File;
  other?: File;
  scanSource?: string;
  scanDate?: string;
  commodityCategory?: string;
  commoditySubtype?: string;
  commodityIsImported?: boolean;
  commodityIsExempt?: boolean;
}

function buildMultiScanFormData(params: CreateMultiScanParams): FormData {
  const fd = new FormData();
  if (params.front) fd.set("image_front", params.front);
  if (params.back) fd.set("image_back", params.back);
  if (params.side) fd.set("image_side", params.side);
  if (params.other) fd.set("image_other", params.other);
  if (params.scanSource) fd.set("scan_source", params.scanSource);
  if (params.scanDate) fd.set("scan_date", params.scanDate);
  if (params.commodityCategory) fd.set("commodity_category", params.commodityCategory);
  if (params.commoditySubtype) fd.set("commodity_subtype", params.commoditySubtype);
  if (params.commodityIsImported !== undefined)
    fd.set("commodity_is_imported", String(params.commodityIsImported));
  if (params.commodityIsExempt !== undefined)
    fd.set("commodity_is_exempt", String(params.commodityIsExempt));
  return fd;
}

/** POST /api/v1/scans/multi — accepts up to 4 panel images, processes them
 *  sequentially on the server (one panel's memory at a time), returns same
 *  shape as createScanWithProgress plus panel_sources and panels_processed.
 *  Streams per-panel stage events the same way createScanWithProgress does. */
export async function createMultiScanWithProgress(
  params: CreateMultiScanParams,
  options: ScanProgressOptions = {},
): Promise<ScanCreateResponse> {
  const [front, back, side, other] = await Promise.all([
    params.front ? resizeForUpload(params.front) : Promise.resolve(undefined),
    params.back ? resizeForUpload(params.back) : Promise.resolve(undefined),
    params.side ? resizeForUpload(params.side) : Promise.resolve(undefined),
    params.other ? resizeForUpload(params.other) : Promise.resolve(undefined),
  ]);
  const formData = buildMultiScanFormData({ ...params, front, back, side, other });
  return postFormDataWithProgress(
    `${PROXY_BASE}/scans/multi`,
    formData,
    options,
    "Network error while uploading multi-panel images.",
  );
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
