"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://mentors-mantra-api-87253755436.us-central1.run.app";

interface InstituteUser {
    id: string;
    email: string;
    institute_name?: string;
    contact_number?: string;
    institute_email?: string;
}

interface InstituteAuthContextType {
    user: InstituteUser | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<{ user: InstituteUser }>;
    logout: () => void;
    refreshToken: () => Promise<boolean>;
    authFetch: (url: string, options?: RequestInit) => Promise<Response>;
    updateProfile: (profile: Partial<InstituteUser>) => Promise<void>;
}

const InstituteAuthContext = createContext<InstituteAuthContextType | undefined>(undefined);

// Token refresh interval (every 10 minutes)
const REFRESH_INTERVAL = 10 * 60 * 1000;

export function InstituteAuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<InstituteUser | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [refreshTokenValue, setRefreshTokenValue] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Track if refresh is in progress
    const isRefreshing = useRef(false);
    const refreshPromise = useRef<Promise<boolean> | null>(null);

    // Internal logout without server call
    const logoutInternal = useCallback(() => {
        setToken(null);
        setRefreshTokenValue(null);
        setUser(null);
        localStorage.removeItem("institute_access_token");
        localStorage.removeItem("institute_refresh_token");
        localStorage.removeItem("institute_user");
    }, []);

    // Refresh access token
    const refreshAccessToken = useCallback(async (): Promise<boolean> => {
        if (isRefreshing.current && refreshPromise.current) {
            return refreshPromise.current;
        }

        const storedRefreshToken = localStorage.getItem("institute_refresh_token");
        if (!storedRefreshToken) return false;

        isRefreshing.current = true;

        refreshPromise.current = (async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/institute/refresh`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ refresh_token: storedRefreshToken }),
                });

                if (!response.ok) {
                    logoutInternal();
                    return false;
                }

                const data = await response.json();
                setToken(data.access_token);
                localStorage.setItem("institute_access_token", data.access_token);
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
    }, [logoutInternal]);

    // Auth fetch wrapper that handles 401 and retries
    const authFetch = useCallback(async (url: string, options: RequestInit = {}): Promise<Response> => {
        const currentToken = localStorage.getItem("institute_access_token");

        const headers = new Headers(options.headers);
        if (currentToken) {
            headers.set("Authorization", `Bearer ${currentToken}`);
        }

        let response = await fetch(url, { ...options, headers });

        if (response.status === 401) {
            const refreshSuccess = await refreshAccessToken();

            if (refreshSuccess) {
                const newToken = localStorage.getItem("institute_access_token");
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
        const storedToken = localStorage.getItem("institute_access_token");
        const storedUser = localStorage.getItem("institute_user");
        const storedRefreshToken = localStorage.getItem("institute_refresh_token");

        if (storedToken && storedUser) {
            setToken(storedToken);
            try {
                setUser(JSON.parse(storedUser));
            } catch {
                logoutInternal();
            }
            setRefreshTokenValue(storedRefreshToken);
        }
        setIsLoading(false);
    }, [logoutInternal]);

    // Auto-refresh token periodically
    useEffect(() => {
        if (!refreshTokenValue) return;

        const interval = setInterval(() => {
            refreshAccessToken();
        }, REFRESH_INTERVAL);

        return () => clearInterval(interval);
    }, [refreshTokenValue, refreshAccessToken]);

    const login = async (email: string, password: string) => {
        const response = await fetch(`${API_BASE_URL}/api/institute/login`, {
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

        localStorage.setItem("institute_access_token", data.access_token);
        localStorage.setItem("institute_refresh_token", data.refresh_token);
        localStorage.setItem("institute_user", JSON.stringify(data.user));

        return { user: data.user };
    };

    const logout = () => {
        logoutInternal();
    };

    const updateProfile = async (profile: Partial<InstituteUser>) => {
        const response = await authFetch(`${API_BASE_URL}/api/institute/profile`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profile),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to update profile");
        }

        const updatedUser = await response.json();
        setUser(updatedUser);
        localStorage.setItem("institute_user", JSON.stringify(updatedUser));
    };

    return (
        <InstituteAuthContext.Provider
            value={{
                user,
                token,
                isLoading,
                isAuthenticated: !!token,
                login,
                logout,
                refreshToken: refreshAccessToken,
                authFetch,
                updateProfile,
            }}
        >
            {children}
        </InstituteAuthContext.Provider>
    );
}

export function useInstituteAuth() {
    const context = useContext(InstituteAuthContext);
    if (context === undefined) {
        throw new Error("useInstituteAuth must be used within an InstituteAuthProvider");
    }
    return context;
}
