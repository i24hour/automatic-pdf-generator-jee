"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2, BookOpen, ArrowLeft } from "lucide-react";
import { FloatingInput } from "@/components/FloatingInput";

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
        <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-white">
            <div className="w-full max-w-md">
                {/* Card */}
                <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <div className="w-14 h-14 rounded-xl bg-indigo-600 flex items-center justify-center">
                            <BookOpen className="w-7 h-7 text-white" />
                        </div>
                    </div>

                    {success ? (
                        <div className="text-center">
                            <CheckCircle2 className="w-14 h-14 mx-auto mb-4 text-green-500" />
                            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Check Your Email</h1>
                            <p className="text-gray-500 text-sm mb-6">
                                If an account exists with this email, you will receive a password reset link.
                            </p>
                            <Link
                                href="/login"
                                className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-700 text-sm"
                            >
                                <ArrowLeft className="w-4 h-4" />
                                Back to Sign in
                            </Link>
                        </div>
                    ) : (
                        <>
                            <h1 className="text-2xl font-semibold text-gray-900 text-center mb-2">Forgot Password?</h1>
                            <p className="text-gray-500 text-center mb-8 text-sm">Enter your email to receive a reset link</p>

                            <form onSubmit={handleSubmit} className="space-y-5">
                                {/* Email */}
                                <FloatingInput
                                    type="email"
                                    label="Email"
                                    value={email}
                                    onChange={setEmail}
                                    required
                                    autoComplete="email"
                                />

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
                                            Sending...
                                        </>
                                    ) : (
                                        "Send Reset Link"
                                    )}
                                </button>
                            </form>

                            <p className="text-center text-gray-500 mt-6 text-sm">
                                Remember your password?{" "}
                                <Link href="/login" className="text-indigo-600 hover:text-indigo-700 font-medium">
                                    Sign in
                                </Link>
                            </p>
                        </>
                    )}
                </div>
            </div>
        </main>
    );
}
