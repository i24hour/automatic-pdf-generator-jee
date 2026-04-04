// Single source of truth for the backend API URL.
// We strip any trailing slash so URLs like `${API_BASE_URL}/auth/login`
// never produce a double-slash like `//auth/login`.
export const API_BASE_URL = (
    process.env.NEXT_PUBLIC_API_URL ||
    "https://q3vgjfnybq.ap-south-1.awsapprunner.com"
).replace(/\/+$/, "");
