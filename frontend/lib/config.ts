// The LIVE backend is mentors-mantra-api in us-central1.
// The asia-south1 backend was never successfully deployed.
export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ||
    "https://mentors-mantra-api-7u7fjzfjhq-uc.a.run.app";
