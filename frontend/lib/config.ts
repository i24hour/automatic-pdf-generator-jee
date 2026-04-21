const DEFAULT_API_BASE_URL = "https://q3vgjfnybq.ap-south-1.awsapprunner.com";

const UNSUPPORTED_API_HOSTS = new Set([
    "infinitest.tech",
    "www.infinitest.tech",
    "mentors-mantra-api-87253755436.us-central1.run.app",
]);

/** Backend reached by the Next.js server (rewrites / server-side). Same resolution as next.config.ts. */
function resolveRemoteApiBaseUrl(rawUrl?: string): string {
    const candidate = (rawUrl || "").trim();
    if (!candidate) {
        return DEFAULT_API_BASE_URL;
    }

    try {
        const normalized = candidate.replace(/\/+$/, "");
        const parsed = new URL(normalized);
        if (UNSUPPORTED_API_HOSTS.has(parsed.host)) {
            return DEFAULT_API_BASE_URL;
        }
        return normalized;
    } catch {
        return DEFAULT_API_BASE_URL;
    }
}

export const REMOTE_API_BASE_URL = resolveRemoteApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);

/**
 * Base URL for browser fetch/EventSource.
 * In the browser, use same-origin `/api/proxy` (Next rewrites → backend) so calls are
 * never cross-origin (Brave / strict mobile clients / CORS edge cases on errors).
 * Server-side / RSC uses the real backend URL.
 */
export const API_BASE_URL: string =
    typeof window !== "undefined"
        ? `${window.location.origin.replace(/\/+$/, "")}/api/proxy`
        : REMOTE_API_BASE_URL;

export const API_URL = API_BASE_URL;
export const API_BASE = API_BASE_URL;
