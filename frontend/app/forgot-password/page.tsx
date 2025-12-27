"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, Loader2, AlertCircle, CheckCircle2, BookOpen, ArrowLeft } from "lucide-react";

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
        <main className="min-h-screen flex items-center justify-center py-12 px-4">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 mb-4">
                        <BookOpen className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text">Forgot Password?</h1>
                    <p className="text-gray-400 mt-2">Enter your email to receive a reset link</p>
                </div>

                <div className="glass-card p-8">
                    {success ? (
                        <div className="text-center">
                            <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-400" />
                            <h2 className="text-xl font-bold mb-2 text-green-400">Check Your Email!</h2>
                            <p className="text-gray-400 mb-6">
                                If an account exists with this email, you will receive a password reset link.
                            </p>
                            <Link href="/login" className="btn-secondary inline-flex">
                                <ArrowLeft className="w-5 h-5" />
                                Back to Login
                            </Link>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* Email */}
                            <div>
                                <label htmlFor="email" className="form-label">
                                    Email Address
                                </label>
                                <div className="relative">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="email"
                                        id="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="you@example.com"
                                        className="form-input pl-12"
                                        required
                                    />
                                </div>
                            </div>

                            {/* Error */}
                            {error && (
                                <div className="error-message">
                                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                    <span>{error}</span>
                                </div>
                            )}

                            {/* Submit */}
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="btn-primary w-full"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                        Sending...
                                    </>
                                ) : (
                                    <>
                                        <Mail className="w-5 h-5" />
                                        Send Reset Link
                                    </>
                                )}
                            </button>
                        </form>
                    )}

                    {!success && (
                        <p className="text-center text-gray-400 mt-6">
                            Remember your password?{" "}
                            <Link href="/login" className="text-indigo-400 hover:text-indigo-300 font-medium">
                                Sign in
                            </Link>
                        </p>
                    )}
                </div>
            </div>
        </main>
    );
}
