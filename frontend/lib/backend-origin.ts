/**
 * Where the server-side proxy (Next rewrites or app/api/proxy) forwards to.
 * Must match the logic historically used in next.config rewrites.
 */
const DEFAULT_BACKEND_ORIGIN = "https://q3vgjfnybq.ap-south-1.awsapprunner.com";

const UNSUPPORTED_API_HOSTS = new Set([
    "infinitest.tech",
    "www.infinitest.tech",
    "mentors-mantra-api-87253755436.us-central1.run.app",
]);

export function getBackendOrigin(): string {
    const explicit = (process.env.API_PROXY_TARGET || "").trim();
    if (explicit) {
        return explicit.replace(/\/+$/, "");
    }
    const pub = (process.env.NEXT_PUBLIC_API_URL || "").trim();
    if (pub) {
        try {
            const u = new URL(pub.replace(/\/+$/, ""));
            if (!UNSUPPORTED_API_HOSTS.has(u.host)) {
                return u.origin;
            }
        } catch {
            /* invalid URL */
        }
    }
    return DEFAULT_BACKEND_ORIGIN;
}
