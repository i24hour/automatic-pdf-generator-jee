const DEFAULT_API_BASE_URL = "https://q3vgjfnybq.ap-south-1.awsapprunner.com";

const UNSUPPORTED_API_HOSTS = new Set([
    "infinitest.tech",
    "www.infinitest.tech",
    "mentors-mantra-api-87253755436.us-central1.run.app",
]);

function resolveApiBaseUrl(rawUrl?: string): string {
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

export const API_BASE_URL = resolveApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);
export const API_URL = API_BASE_URL;
export const API_BASE = API_BASE_URL;
