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

// --- Offline Sync Logic ---
const PENDING_LOGS_KEY = "offline_logs";
let pendingLogs: any[] = [];

// Load pending logs from storage on init
if (typeof window !== 'undefined') {
    try {
        const stored = localStorage.getItem(PENDING_LOGS_KEY);
        if (stored) {
            pendingLogs = JSON.parse(stored);
        }
    } catch {
        pendingLogs = [];
    }
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
 * Sync pending logs to backend
 */
export const syncLogs = async () => {
    if (pendingLogs.length === 0) return;
    if (typeof navigator !== 'undefined' && !navigator.onLine) return;

    originalConsole.log(`[Logger] Syncing ${pendingLogs.length} offline logs...`);

    const token = localStorage.getItem("auth_token");
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    // Process queue
    const remainingLogs = [];
    for (const logPayload of pendingLogs) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/log-error`, {
                method: "POST",
                headers,
                body: JSON.stringify(logPayload),
            });
            if (!response.ok) {
                // Keep if server error (5xx), discard if client error (4xx) to avoid infinite retry
                if (response.status >= 500) remainingLogs.push(logPayload);
            }
        } catch (e) {
            // Keep if network error
            remainingLogs.push(logPayload);
        }
    }

    pendingLogs = remainingLogs;
    localStorage.setItem(PENDING_LOGS_KEY, JSON.stringify(pendingLogs));

    if (pendingLogs.length === 0) {
        originalConsole.log("[Logger] All logs synced successfully");
    }
};

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

        try {
            const response = await fetch(`${API_BASE_URL}/api/log-error`, {
                method: "POST",
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                originalConsole.warn(`[Logger] Failed to send log: ${response.status}`);
            } else {
                // If successful, try to sync any other pending logs too
                syncLogs();
            }
        } catch (networkError) {
            // Network failed - Store locally
            originalConsole.warn("[Logger] Network failed. Saving log offline.");
            pendingLogs.push(payload);

            // Limit offline storage to 50 logs to prevent overflow
            if (pendingLogs.length > 50) pendingLogs.shift();

            localStorage.setItem(PENDING_LOGS_KEY, JSON.stringify(pendingLogs));
        }

    } catch (e) {
        // Fails silently intentionally
        originalConsole.warn("[Logger] Logging failed locally:", e);
    }
};

// Auto-sync when coming online
if (typeof window !== 'undefined') {
    window.addEventListener('online', syncLogs);
    // Try sync on load after small delay
    setTimeout(syncLogs, 2000);
}
