import { NextRequest, NextResponse } from "next/server";
import { getBackendOrigin } from "@/lib/backend-origin";

/**
 * Forwards the browser to the real FastAPI host.
 * - Avoids depending on `next.config` rewrites only (Vercel can mis-apply them;
 *   this route is explicit and always hits the same origin as the build env).
 * - Preserves long-lived SSE (EventSource) and streaming.
 */
export const dynamic = "force-dynamic";
export const maxDuration = 300;
export const runtime = "nodejs";

const HOP_BY_HOP = new Set([
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
]);

function buildTargetUrl(
    request: NextRequest,
    pathSegments: string[] | undefined
): string {
    const base = getBackendOrigin();
    const sub =
        pathSegments && pathSegments.length
            ? pathSegments.map(encodeURI).join("/")
            : "";
    const target = sub ? `${base}/${sub}` : base;
    const out = new URL(target);
    request.nextUrl.searchParams.forEach((v, k) => {
        out.searchParams.set(k, v);
    });
    return out.toString();
}

function forwardRequestHeaders(incoming: NextRequest): Headers {
    const out = new Headers();
    incoming.headers.forEach((value, key) => {
        if (HOP_BY_HOP.has(key.toLowerCase())) return;
        out.set(key, value);
    });
    return out;
}

async function proxy(
    request: NextRequest,
    pathSegments: string[] | undefined
) {
    const targetUrl = buildTargetUrl(request, pathSegments);
    const headers = forwardRequestHeaders(request);
    const method = request.method;

    const isBody = !["GET", "HEAD", "OPTIONS"].includes(method);
    const body = isBody ? await request.arrayBuffer() : undefined;

    const res = await fetch(targetUrl, {
        method,
        headers,
        body: isBody ? (body && body.byteLength > 0 ? body : undefined) : undefined,
    });
    return new NextResponse(res.body, {
        status: res.status,
        statusText: res.statusText,
        headers: res.headers,
    });
}

type RouteCtx = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, ctx: RouteCtx) {
    const { path } = await ctx.params;
    return proxy(request, path);
}
export async function POST(request: NextRequest, ctx: RouteCtx) {
    const { path } = await ctx.params;
    return proxy(request, path);
}
export async function PUT(request: NextRequest, ctx: RouteCtx) {
    const { path } = await ctx.params;
    return proxy(request, path);
}
export async function PATCH(request: NextRequest, ctx: RouteCtx) {
    const { path } = await ctx.params;
    return proxy(request, path);
}
export async function DELETE(request: NextRequest, ctx: RouteCtx) {
    const { path } = await ctx.params;
    return proxy(request, path);
}
export async function OPTIONS(request: NextRequest, ctx: RouteCtx) {
    const { path } = await ctx.params;
    return proxy(request, path);
}
