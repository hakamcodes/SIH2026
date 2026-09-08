/**
 * The backend returns four different error envelope shapes (confirmed by
 * reading backend/lmd/api/errors.py and every route's HTTPException calls):
 *
 *   1. {"detail": "<string>"}
 *      FastAPI's default HTTPException body. Used by every plain 400/401/
 *      404/500 in the app (e.g. scan.py:58, deps.py:50, images.py).
 *
 *   2. {"error": "reason_to_believe_required", "detail": "<string>",
 *       "legal_basis": "Section 15(4), Legal Metrology Act 2009"}
 *      The 422 hard gate (errors.py). Has a `legal_basis` no other error has.
 *
 *   3. {"error": "not_found", "detail": "<repr of a KeyError>"}
 *      errors.py's KeyError handler, reachable via
 *      repository.update_case_status.
 *
 *   4. {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
 *      FastAPI's request-validation 422. `detail` is an ARRAY here, not a
 *      string -- the one shape that breaks a naive `data.detail` read.
 *
 * Plus one shape this frontend's own proxy adds when the backend process
 * itself is unreachable (src/app/api/lmd/[...path]/route.ts): a 502 with
 * {"error": "backend_unreachable", "detail": "<string>"}.
 *
 * ApiError normalizes all five into one shape so components never branch on
 * envelope format themselves.
 */

export interface ValidationIssue {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export type ApiErrorKind =
  | "validation"
  | "reason_to_believe_required"
  | "not_found"
  | "backend_unreachable"
  | "generic";

export class ApiError extends Error {
  readonly status: number;
  readonly kind: ApiErrorKind;
  readonly legalBasis?: string;
  readonly validationIssues?: ValidationIssue[];

  constructor(params: {
    status: number;
    kind: ApiErrorKind;
    message: string;
    legalBasis?: string;
    validationIssues?: ValidationIssue[];
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.kind = params.kind;
    this.legalBasis = params.legalBasis;
    this.validationIssues = params.validationIssues;
  }
}

function isValidationIssueArray(value: unknown): value is ValidationIssue[] {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "msg" in item &&
        "loc" in item,
    )
  );
}

/** Parses a non-2xx JSON response body into an ApiError. Falls back to a
 *  generic message if the body doesn't match any known shape (e.g. an
 *  upstream proxy or load balancer error page, which is plain text/HTML). */
export function parseApiErrorBody(status: number, body: unknown): ApiError {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;

    if (record.error === "reason_to_believe_required") {
      return new ApiError({
        status,
        kind: "reason_to_believe_required",
        message: typeof record.detail === "string" ? record.detail : "Reason to believe required.",
        legalBasis: typeof record.legal_basis === "string" ? record.legal_basis : undefined,
      });
    }

    if (record.error === "not_found") {
      return new ApiError({
        status,
        kind: "not_found",
        message: typeof record.detail === "string" ? record.detail : "Not found.",
      });
    }

    if (record.error === "backend_unreachable") {
      return new ApiError({
        status,
        kind: "backend_unreachable",
        message: typeof record.detail === "string" ? record.detail : "Backend unreachable.",
      });
    }

    if (isValidationIssueArray(record.detail)) {
      const issues = record.detail;
      const summary = issues
        .map((issue) => `${issue.loc.join(".")}: ${issue.msg}`)
        .join("; ");
      return new ApiError({
        status,
        kind: "validation",
        message: summary || "Request validation failed.",
        validationIssues: issues,
      });
    }

    if (typeof record.detail === "string") {
      return new ApiError({ status, kind: "generic", message: record.detail });
    }
  }

  return new ApiError({
    status,
    kind: "generic",
    message: `Request failed with status ${status}.`,
  });
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** Human-readable fallback for anything that isn't an ApiError (network
 *  failure before a response was even received, a thrown non-Error, etc). */
export function describeUnknownError(error: unknown): string {
  if (isApiError(error)) return error.message;
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}
