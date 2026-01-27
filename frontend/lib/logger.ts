const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Interface for system error details
 */
export interface ErrorDetails {
    error_type: string;
    error_details: string;
    user_email?: string;
    metadata_info?: string;
}

/**
 * Logs a system error to the backend for tracking.
 * Safe to call even if backend is down (fails silently).
 */
export const logError = async (details: ErrorDetails) => {
    try {
        // Add browser metadata automatically
        if (!details.metadata_info) {
            details.metadata_info = JSON.stringify({
                userAgent: navigator.userAgent,
                timestamp_local: new Date().toString(),
                url: window.location.href
            });
        }

        // Try to get token for context (optional)
        const token = localStorage.getItem("auth_token");
        const headers: Record<string, string> = {
            "Content-Type": "application/json",
        };

        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/log-error`, {
            method: "POST",
            headers,
            body: JSON.stringify(details),
        });

        if (!response.ok) {
            // Just warn properly without throwing, so app flow isn't broken
            console.warn(`[Logger] Failed to send log: ${response.status}`);
        }
    } catch (e) {
        // Fails silently intentionally to not disturb user flow
        console.warn("[Logger] Logging failed locally:", e);
    }
};
