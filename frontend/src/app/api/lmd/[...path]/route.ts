import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy to the FastAPI backend (backend/lmd/api/*.py). Every
 * browser call to /api/v1/* goes through here instead of hitting the backend
 * directly, for one reason: LMD_INSPECTOR_API_TOKEN (backend/lmd/api/deps.py
 * require_inspector) must never reach client-side code. This route reads it
 * from a server-only env var and injects it as the Authorization header;
 * only NEXT_PUBLIC_-prefixed vars are ever bundled into client JS, and this
 * one deliberately is not.
 *
 * `X-Inspector-Id` is NOT a secret -- it's a caller-asserted string the
 * backend uses only as an audit-log actor (no verification against a user
 * directory exists) -- so it is forwarded through from the browser as-is.
 */
const BACKEND_URL = process.env.LMD_BACKEND_URL ?? "http://localhost:8000";
const INSPECTOR_TOKEN = process.env.LMD_INSPECTOR_API_TOKEN;

// Headers that must not be forwarded verbatim: `host`/`connection` describe
// this proxy, not the backend, and `content-length` is recomputed by fetch
// from the body we actually send.
const HOP_BY_HOP_REQUEST_HEADERS = new Set([
  "host",
  "connection",
  "content-length",
  "authorization", // the client must never set this itself; the proxy owns it
]);

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const targetUrl = new URL(`/api/v1/${path.join("/")}`, BACKEND_URL);
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_REQUEST_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  if (INSPECTOR_TOKEN) {
    headers.set("Authorization", `Bearer ${INSPECTOR_TOKEN}`);
  }

  const hasBody = !["GET", "HEAD"].includes(request.method);

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      // The backend is a local/dev process; this proxy has no use for the
      // browser's own cache semantics for what is effectively a same-request
      // relay.
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      {
        error: "backend_unreachable",
        detail: `Could not reach the backend at ${BACKEND_URL}. Is uvicorn running?`,
      },
      { status: 502 },
    );
  }

  const responseBody = await response.arrayBuffer();
  const responseHeaders = new Headers();
  const contentType = response.headers.get("content-type");
  if (contentType) responseHeaders.set("content-type", contentType);

  return new NextResponse(responseBody, {
    status: response.status,
    headers: responseHeaders,
  });
}

interface RouteContext {
  params: Promise<{ path: string[] }>;
}

async function handle(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const DELETE = handle;
