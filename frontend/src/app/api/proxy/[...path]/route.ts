/**
 * Reverse-proxy from Next.js → FastAPI with HTTP Basic Auth attached.
 *
 * Client code calls `/api/proxy/<path>` and the request is forwarded to the
 * configured BACKEND_URL with the `Authorization: Basic ...` header. SSE works
 * because we stream the upstream response body unchanged.
 */
import type { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const BACKEND_USER = process.env.BACKEND_USER || "admin";
const BACKEND_PASS = process.env.BACKEND_PASS || "guardrails";

function authHeader() {
  return "Basic " + Buffer.from(`${BACKEND_USER}:${BACKEND_PASS}`).toString("base64");
}

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = new URL(BACKEND_URL);
  target.pathname = "/" + path.join("/");
  for (const [k, v] of req.nextUrl.searchParams) target.searchParams.append(k, v);

  const init: RequestInit = {
    method: req.method,
    headers: {
      Authorization: authHeader(),
      "Content-Type": req.headers.get("content-type") || "application/json",
      Accept: req.headers.get("accept") || "*/*",
    },
    cache: "no-store",
  };
  if (!["GET", "HEAD"].includes(req.method)) {
    init.body = await req.text();
  }
  const upstream = await fetch(target, init);
  const headers = new Headers(upstream.headers);
  headers.delete("content-encoding");
  headers.delete("content-length");
  return new Response(upstream.body, {
    status: upstream.status,
    headers,
  });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
export const PUT = forward;
