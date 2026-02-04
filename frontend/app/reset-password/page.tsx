"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { FloatingInput } from "@/components/ui/FloatingInput";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function ResetPasswordForm() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token");

    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        if (password.length < 6) {
            setError("Password must be at least 6 characters");
            return;
        }

        if (!token) {
            setError("Invalid reset link");
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token, new_password: password }),
            });

            if (response.ok) {
                setSuccess(true);
            } else {
                const data = await response.json();
                setError(data.detail || "Reset failed");
            }
        } catch {
            setError("Something went wrong. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    if (!token) {
        return (
            <div className="w-full max-w-md mx-auto text-center">
                <div className="bg-red-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6">
                    <AlertCircle className="w-8 h-8 text-red-500" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Invalid Link</h1>
                <p className="text-gray-500 mb-8">This password reset link is invalid or has expired.</p>
                <Link
                    href="/forgot-password"
                    className="inline-flex items-center justify-center py-3 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-colors w-full"
                >
                    Request New Link
                </Link>
            </div>
        );
    }

    if (success) {
        return (
            <div className="w-full max-w-md mx-auto text-center">
                <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle2 className="w-8 h-8 text-green-600" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Password Reset!</h1>
                <p className="text-gray-500 mb-8">
                    Your password has been reset successfully. You can now log in with your new password.
                </p>
                <Link
                    href="/login"
                    className="inline-flex items-center justify-center gap-2 py-3 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-colors w-full"
                >
                    Continue to Sign in
                    <ArrowRight className="w-4 h-4" />
                </Link>
            </div>
        );
    }

    return (
        <div className="w-full max-w-md mx-auto">
            {/* Mobile Logo - Simple */}
            <div className="lg:hidden flex flex-col items-center mb-8">
                <div className="w-16 h-16 mb-3">
                    <img src="/logo.png" alt="INFINITEST" className="w-full h-full object-contain" />
                </div>
                <h1 className="text-xl font-black tracking-tight text-gray-900">INFINITEST</h1>
            </div>

            <div className="mb-8 text-center">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Reset Password</h1>
                <p className="text-gray-500">Please enter a new password for your account</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                <FloatingInput
                    type="password"
                    label="New password"
                    value={password}
                    onChange={setPassword}
                    required
                />

                <FloatingInput
                    type="password"
                    label="Confirm new password"
                    value={confirmPassword}
                    onChange={setConfirmPassword}
                    required
                />

                {error && (
                    <div className="flex items-center gap-3 text-red-700 text-sm bg-red-50 border border-red-200 rounded-xl px-4 py-3.5">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <span className="font-medium">{error}</span>
                    </div>
                )}

                <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full py-4 bg-gray-900 hover:bg-gray-800 text-white font-semibold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-lg shadow-gray-900/20"
                >
                    {isLoading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Resetting...
                        </>
                    ) : (
                        <>
                            Reset Password
                            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}

export default function ResetPasswordPage() {
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

                    <h1 className="text-4xl font-black tracking-tight text-white mb-4 text-center">
                        Secure Your Account
                    </h1>

                    <p className="text-gray-400 text-lg text-center max-w-sm">
                        Create a strong password to keep your progress safe.
                    </p>
                </div>

                {/* Bottom gradient */}
                <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
            </div>

            {/* Right Panel - Form */}
            <div className="flex-1 lg:w-1/2 flex items-center justify-center py-12 px-6 bg-white">
                <Suspense fallback={
                    <div className="flex justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
                    </div>
                }>
                    <ResetPasswordForm />
                </Suspense>
            </div>
        </main>
    );
}
