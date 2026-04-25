import type { NextConfig } from "next";

// Keep in sync with `lib/backend-origin.ts` (for edge cases where the route handler is not used).
const DEFAULT_BACKEND = "https://q3vgjfnybq.ap-south-1.awsapprunner.com";

const UNSUPPORTED_API_HOSTS = new Set([
    "infinitest.tech",
    "www.infinitest.tech",
    "mentors-mantra-api-87253755436.us-central1.run.app",
]);

function rewriteTarget(): string {
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
            /* ignore */
        }
    }
    return DEFAULT_BACKEND.replace(/\/+$/, "");
}

const nextConfig: NextConfig = {
    async rewrites() {
        const base = rewriteTarget();
        return [
            {
                source: "/api/proxy/:path*",
                destination: `${base}/:path*`,
            },
        ];
    },
};

export default nextConfig;
