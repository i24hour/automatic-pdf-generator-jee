"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2, ArrowLeft, ArrowRight } from "lucide-react";
import { FloatingInput } from "@/components/ui/FloatingInput";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email }),
            });

            if (response.ok) {
                setSuccess(true);
            } else {
                const data = await response.json();
                setError(data.detail || "Something went wrong");
            }
        } catch {
            setError("Something went wrong. Please try again.");
        } finally {
            setIsLoading(false);
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

                    <h1 className="text-4xl font-black tracking-tight text-white mb-4 text-center">
                        Account Recovery
                    </h1>

                    <p className="text-gray-400 text-lg text-center max-w-sm">
                        Don't worry, we'll help you get back to your preparation in no time.
                    </p>
                </div>

                {/* Bottom gradient */}
                <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
            </div>

            {/* Right Panel - Form */}
            <div className="flex-1 lg:w-1/2 flex items-center justify-center py-12 px-6 bg-white">
                <div className="w-full max-w-md">
                    {success ? (
                        <div className="text-center">
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                <CheckCircle2 className="w-8 h-8 text-green-600" />
                            </div>
                            <h1 className="text-2xl font-bold text-gray-900 mb-2">Check Your Email</h1>
                            <p className="text-gray-500 mb-8">
                                If an account exists with this email, you will receive a password reset link shortly.
                            </p>
                            <Link
                                href="/login"
                                className="inline-flex items-center gap-2 text-gray-900 hover:text-gray-700 font-medium"
                            >
                                <ArrowLeft className="w-4 h-4" />
                                Back to Sign in
                            </Link>
                        </div>
                    ) : (
                        <>
                            <div className="mb-8 text-center">
                                <h1 className="text-3xl font-bold text-gray-900 mb-2">Forgot Password?</h1>
                                <p className="text-gray-500">Enter your email and we'll send you a reset link</p>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-6">
                                {/* Email */}
                                <FloatingInput
                                    type="email"
                                    label="Email address"
                                    value={email}
                                    onChange={setEmail}
                                    required
                                    autoComplete="email"
                                />

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
                                            Sending Link...
                                        </>
                                    ) : (
                                        <>
                                            Send Reset Link
                                            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                        </>
                                    )}
                                </button>
                            </form>

                            <div className="mt-8 text-center">
                                <Link
                                    href="/login"
                                    className="flex items-center justify-center gap-2 text-gray-500 hover:text-gray-900 transition-colors"
                                >
                                    <ArrowLeft className="w-4 h-4" />
                                    Back to Sign in
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </main>
    );
}
