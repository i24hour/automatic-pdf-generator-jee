"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, Infinity as InfinityIcon, AlertTriangle } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { FloatingInput } from "@/components/FloatingInput";
import { GoogleLogin } from "@react-oauth/google";

import { API_BASE_URL as API_URL } from "@/lib/config";

function LoginPageContent() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isGoogleLoading, setIsGoogleLoading] = useState(false);
    const [needsVerification, setNeedsVerification] = useState(false);

    const { login, setTokens } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectUrl = searchParams.get("redirect") || "/";

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setNeedsVerification(false);
        setIsLoading(true);

        try {
            const result = await login(email, password);

            if (result && !result.user.is_verified) {
                setNeedsVerification(true);
            }

            router.push(redirectUrl);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleSuccess = async (credentialResponse: { credential?: string }) => {
        if (!credentialResponse.credential) {
            setError("Google login failed - no credential received");
            return;
        }

        setIsGoogleLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/auth/google`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credential: credentialResponse.credential }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Google login failed");
            }

            // Set tokens and user in auth context
            setTokens(data.access_token, data.refresh_token, data.user);
            router.push(redirectUrl);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Google login failed");
        } finally {
            setIsGoogleLoading(false);
        }
    };

    return (
        <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-white">
            <div className="w-full max-w-md">
                {/* Card */}
                <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <div className="w-14 h-14 rounded-xl bg-indigo-600 flex items-center justify-center">
                            <InfinityIcon className="w-7 h-7 text-white" />
                        </div>
                    </div>

                    {/* Title */}
                    <h1 className="text-2xl font-semibold text-gray-900 text-center mb-2">Welcome Back</h1>
                    <p className="text-gray-500 text-center text-sm">Sign in to continue</p>
                    <p className="text-gray-500 text-center mb-8 text-xs">
                        Topic select karke actual PDF test papers generate kar sakte ho.
                    </p>

                    {/* Google Sign In */}
                    <div className="mb-6">
                        <div className="flex justify-center">
                            {isGoogleLoading ? (
                                <div className="flex items-center justify-center gap-2 py-3 px-4 border border-gray-300 rounded-lg w-full">
                                    <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                                    <span className="text-gray-600">Signing in with Google...</span>
                                </div>
                            ) : (
                                <GoogleLogin
                                    onSuccess={handleGoogleSuccess}
                                    onError={() => setError("Google login failed")}
                                    theme="outline"
                                    size="large"
                                    text="signin_with"
                                />
                            )}
                        </div>
                    </div>

                    {/* Divider */}
                    <div className="relative my-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-4 bg-white text-gray-500">or continue with email</span>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Email */}
                        <FloatingInput
                            type="email"
                            label="Email"
                            value={email}
                            onChange={setEmail}
                            required
                            autoComplete="email"
                        />

                        {/* Password */}
                        <FloatingInput
                            type="password"
                            label="Password"
                            value={password}
                            onChange={setPassword}
                            required
                            autoComplete="current-password"
                        />

                        {/* Forgot Password */}
                        <div className="text-right -mt-2">
                            <Link
                                href="/forgot-password"
                                className="text-sm text-indigo-600 hover:text-indigo-700"
                            >
                                Forgot password?
                            </Link>
                        </div>

                        {/* Verification Warning */}
                        {needsVerification && (
                            <div className="flex items-start gap-2 text-amber-700 text-sm bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-medium">Email not verified</p>
                                    <p className="text-amber-600 text-xs">Check your email to verify your account.</p>
                                </div>
                            </div>
                        )}

                        {/* Error */}
                        {error && (
                            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Signing in...
                                </>
                            ) : (
                                "Sign In"
                            )}
                        </button>
                    </form>

                    {/* Sign up link */}
                    <p className="text-center text-gray-500 mt-6 text-sm">
                        Don&apos;t have an account?{" "}
                        <Link href="/signup" className="text-indigo-600 hover:text-indigo-700 font-medium">
                            Create account
                        </Link>
                    </p>
                </div>
            </div>
        </main>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-[#0a0b0d]"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" /></div>}>
            <LoginPageContent />
        </Suspense>
    );
}
