"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
    id: string;
    email: string;
    name?: string;
    is_verified: boolean;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<{ user: User }>;
    register: (email: string, password: string, name?: string) => Promise<{ user: User }>;
    logout: () => void;
    refreshToken: () => Promise<boolean>;
    resendVerification: () => Promise<void>;
    authFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Token refresh interval (every 10 minutes)
const REFRESH_INTERVAL = 10 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [refreshTokenValue, setRefreshTokenValue] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Track if refresh is in progress to avoid multiple simultaneous refreshes
    const isRefreshing = useRef(false);
    const refreshPromise = useRef<Promise<boolean> | null>(null);

    // Refresh access token
    const refreshAccessToken = useCallback(async (): Promise<boolean> => {
        // If already refreshing, wait for that to complete
        if (isRefreshing.current && refreshPromise.current) {
            return refreshPromise.current;
        }

        const storedRefreshToken = localStorage.getItem("refresh_token");
        if (!storedRefreshToken) return false;

        isRefreshing.current = true;

        refreshPromise.current = (async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ refresh_token: storedRefreshToken }),
                });

                if (!response.ok) {
                    // Refresh token invalid, logout
                    logoutInternal();
                    return false;
                }

                const data = await response.json();
                setToken(data.access_token);
                localStorage.setItem("auth_token", data.access_token);
                return true;
            } catch {
                logoutInternal();
                return false;
            } finally {
                isRefreshing.current = false;
                refreshPromise.current = null;
            }
        })();

        return refreshPromise.current;
    }, []);

    // Internal logout without server call (for refresh failures)
    const logoutInternal = () => {
        setToken(null);
        setRefreshTokenValue(null);
        setUser(null);
        localStorage.removeItem("auth_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("auth_user");
    };

    // Auth fetch wrapper that handles 401 and retries with new token
    const authFetch = useCallback(async (url: string, options: RequestInit = {}): Promise<Response> => {
        const currentToken = localStorage.getItem("auth_token");

        // Add auth header
        const headers = new Headers(options.headers);
        if (currentToken) {
            headers.set("Authorization", `Bearer ${currentToken}`);
        }

        // First attempt
        let response = await fetch(url, { ...options, headers });

        // If 401, try to refresh and retry once
        if (response.status === 401) {
            const refreshSuccess = await refreshAccessToken();

            if (refreshSuccess) {
                // Get new token and retry
                const newToken = localStorage.getItem("auth_token");
                if (newToken) {
                    headers.set("Authorization", `Bearer ${newToken}`);
                    response = await fetch(url, { ...options, headers });
                }
            }
        }

        return response;
    }, [refreshAccessToken]);

    // Load tokens from localStorage on mount
    useEffect(() => {
        const storedToken = localStorage.getItem("auth_token");
        const storedUser = localStorage.getItem("auth_user");
        const storedRefreshToken = localStorage.getItem("refresh_token");

        if (storedToken && storedUser) {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
            setRefreshTokenValue(storedRefreshToken);
        }
        setIsLoading(false);
    }, []);

    // Auto-refresh token periodically
    useEffect(() => {
        if (!refreshTokenValue) return;

        const interval = setInterval(() => {
            refreshAccessToken();
        }, REFRESH_INTERVAL);

        return () => clearInterval(interval);
    }, [refreshTokenValue, refreshAccessToken]);

    const login = async (email: string, password: string) => {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Login failed");
        }

        const data = await response.json();

        setToken(data.access_token);
        setRefreshTokenValue(data.refresh_token);
        setUser(data.user);

        localStorage.setItem("auth_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("auth_user", JSON.stringify(data.user));

        return { user: data.user };
    };

    const register = async (email: string, password: string, name?: string) => {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, name }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Registration failed");
        }

        const data = await response.json();

        setToken(data.access_token);
        setRefreshTokenValue(data.refresh_token);
        setUser(data.user);

        localStorage.setItem("auth_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("auth_user", JSON.stringify(data.user));

        return { user: data.user };
    };

    const logout = async () => {
        // Revoke refresh token on server
        const storedRefreshToken = localStorage.getItem("refresh_token");
        if (storedRefreshToken) {
            try {
                await fetch(`${API_BASE_URL}/auth/logout`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ refresh_token: storedRefreshToken }),
                });
            } catch {
                // Ignore errors during logout
            }
        }

        logoutInternal();
    };

    const resendVerification = async () => {
        if (!token) throw new Error("Not authenticated");

        const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to send verification email");
        }
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                isLoading,
                isAuthenticated: !!token,
                login,
                register,
                logout,
                refreshToken: refreshAccessToken,
                resendVerification,
                authFetch,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}

