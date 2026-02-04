"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, AlertTriangle, ArrowRight } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { FloatingInput } from "@/components/ui/FloatingInput";
import { GoogleLogin } from "@react-oauth/google";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://mentors-mantra-api-87253755436.us-central1.run.app";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isGoogleLoading, setIsGoogleLoading] = useState(false);
    const [needsVerification, setNeedsVerification] = useState(false);

    const { login, setTokens } = useAuth();
    const router = useRouter();

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

            router.push("/");
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
            router.push("/");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Google login failed");
        } finally {
            setIsGoogleLoading(false);
        }
    };

    return (
        <main className="min-h-screen flex flex-col lg:flex-row">
            {/* Left Panel - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-gray-900 via-gray-800 to-black relative overflow-hidden">
                {/* Decorative infinity curves */}
                <div className="absolute inset-0 opacity-5">
                    <svg className="w-full h-full" viewBox="0 0 800 800" fill="none">
                        <path
                            d="M200 400C200 300 300 200 400 300C500 400 600 300 600 400C600 500 500 600 400 500C300 400 200 500 200 400Z"
                            stroke="white"
                            strokeWidth="2"
                            fill="none"
                        />
                    </svg>
                </div>

                {/* Content */}
                <div className="relative z-10 flex flex-col justify-center items-center w-full px-12">
                    {/* Logo */}
                    <div className="w-32 h-32 mb-8">
                        <img
                            src="/logo.png"
                            alt="INFINITEST"
                            className="w-full h-full object-contain invert"
                        />
                    </div>

                    {/* Brand Name */}
                    <h1 className="text-5xl font-black tracking-tight text-white mb-4">
                        INFINITEST
                    </h1>

                    {/* Tagline */}
                    <p className="text-gray-400 text-lg text-center max-w-sm">
                        Infinite possibilities for your JEE & NEET preparation
                    </p>

                    {/* Features */}
                    <div className="mt-12 space-y-4">
                        <div className="flex items-center gap-3 text-gray-300">
                            <div className="w-2 h-2 rounded-full bg-white" />
                            <span>AI-Powered Test Generation</span>
                        </div>
                        <div className="flex items-center gap-3 text-gray-300">
                            <div className="w-2 h-2 rounded-full bg-white" />
                            <span>Trained by IITians & NEET Rankers</span>
                        </div>
                        <div className="flex items-center gap-3 text-gray-300">
                            <div className="w-2 h-2 rounded-full bg-white" />
                            <span>Unlimited Practice Papers</span>
                        </div>
                    </div>
                </div>

                {/* Bottom gradient */}
                <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
            </div>

            {/* Right Panel - Login Form */}
            <div className="flex-1 lg:w-1/2 flex items-center justify-center py-12 px-6 bg-white">
                <div className="w-full max-w-md">
                    {/* Mobile Logo - Simple */}
                    <div className="lg:hidden flex flex-col items-center mb-8">
                        <div className="w-16 h-16 mb-3">
                            <img src="/logo.png" alt="INFINITEST" className="w-full h-full object-contain" />
                        </div>
                        <h1 className="text-3xl font-black tracking-tight text-gray-900">INFINITEST</h1>
                    </div>

                    {/* Header */}
                    <div className="mb-8 text-center">
                        <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome back</h2>
                        <p className="text-gray-500">Sign in to continue your journey</p>
                    </div>

                    {/* Google Sign In */}
                    <div className="mb-6">
                        {isGoogleLoading ? (
                            <div className="flex items-center justify-center gap-2 py-3.5 px-4 border-2 border-gray-200 rounded-xl w-full bg-gray-50">
                                <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                                <span className="text-gray-600 font-medium">Signing in with Google...</span>
                            </div>
                        ) : (
                            <div className="flex justify-center">
                                <GoogleLogin
                                    onSuccess={handleGoogleSuccess}
                                    onError={() => setError("Google login failed")}
                                    theme="outline"
                                    size="large"
                                    text="signin_with"
                                />
                            </div>
                        )}
                    </div>

                    {/* Divider */}
                    <div className="relative my-8">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200"></div>
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-4 bg-white text-gray-400 font-medium">or continue with email</span>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        {/* Email */}
                        <FloatingInput
                            type="email"
                            label="Email address"
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
                        <div className="flex justify-end">
                            <Link
                                href="/forgot-password"
                                className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                            >
                                Forgot password?
                            </Link>
                        </div>

                        {/* Verification Warning */}
                        {needsVerification && (
                            <div className="flex items-start gap-3 text-amber-800 text-sm bg-amber-50 border border-amber-200 rounded-xl px-4 py-3.5">
                                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-semibold">Email not verified</p>
                                    <p className="text-amber-700 text-xs mt-0.5">Please check your email to verify your account.</p>
                                </div>
                            </div>
                        )}

                        {/* Error */}
                        {error && (
                            <div className="flex items-center gap-3 text-red-700 text-sm bg-red-50 border border-red-200 rounded-xl px-4 py-3.5">
                                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                <span className="font-medium">{error}</span>
                            </div>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-4 bg-gray-900 hover:bg-gray-800 text-white font-semibold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-lg shadow-gray-900/20"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Signing in...
                                </>
                            ) : (
                                <>
                                    Sign In
                                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>
                    </form>

                    {/* Sign up link */}
                    <p className="text-center text-gray-500 mt-8">
                        Don&apos;t have an account?{" "}
                        <Link href="/signup" className="text-gray-900 hover:underline font-semibold">
                            Create one
                        </Link>
                    </p>

                    {/* Footer */}
                    <p className="text-center text-gray-400 text-xs mt-8">
                        A Mentors Mantra Product
                    </p>
                </div>
            </div>
        </main>
    );
}
