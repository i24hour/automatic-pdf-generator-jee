// Single source of truth for the backend API URL.
// All components that hardcode a fallback URL should use this file instead.
export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ||
    "https://mentors-mantra-api-87253755436.us-central1.run.app";
