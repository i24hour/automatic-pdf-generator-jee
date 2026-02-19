export const API_BASE_URL = (() => {
    const envUrl = process.env.NEXT_PUBLIC_API_URL;
    const oldUrl = "https://mentors-mantra-api-87253755436.us-central1.run.app";
    const newUrl = "https://test-generator-backend-87253755436.asia-south1.run.app";

    // If env var is set and matches the old URL (or is missing), force the new URL.
    // This is a "Do it for me" fix to override stale Vercel config.
    if (!envUrl || envUrl === oldUrl || envUrl.includes("us-central1")) {
        console.warn("Overriding stale/missing API URL with new Asia-South1 Deployment");
        return newUrl;
    }

    return envUrl;
})();
