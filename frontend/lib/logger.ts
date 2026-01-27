const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Console Interception Logic ---
const MAX_LOGS = 50;
const consoleHistory: string[] = [];

// Store original methods
const originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
    info: console.info
};

// Safe argument serializer
const safeStringify = (args: any[]) => {
    return args.map(arg => {
        try {
            if (typeof arg === 'object') return JSON.stringify(arg);
            return String(arg);
        } catch {
            return '[Circular/Unserializable]';
        }
    }).join(' ');
};

// Interceptor function
const intercept = (type: string, ...args: any[]) => {
    try {
        const message = `[${type}] ${safeStringify(args)}`;
        if (consoleHistory.length >= MAX_LOGS) consoleHistory.shift();
        consoleHistory.push(message);
    } catch {
        // Ignore interception errors
    }
};

// Override console methods (only on client side)
if (typeof window !== 'undefined') {
    console.log = (...args) => { intercept('LOG', ...args); originalConsole.log(...args); };
    console.warn = (...args) => { intercept('WARN', ...args); originalConsole.warn(...args); };
    console.error = (...args) => { intercept('ERROR', ...args); originalConsole.error(...args); };
    console.info = (...args) => { intercept('INFO', ...args); originalConsole.info(...args); };
}

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
        // Prepare expanded metadata with Console History
        const metaObj = details.metadata_info ? JSON.parse(details.metadata_info) : {};

        metaObj.browser = {
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp_local: new Date().toString(),
        };

        // Attach last 50 console logs
        metaObj.console_logs = [...consoleHistory];

        // Final payload
        const payload = {
            ...details,
            metadata_info: JSON.stringify(metaObj)
        };

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
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            // Use original console to avoid infinite loop
            originalConsole.warn(`[Logger] Failed to send log: ${response.status}`);
        }
    } catch (e) {
        // Fails silently intentionally
        originalConsole.warn("[Logger] Logging failed locally:", e);
    }
};
