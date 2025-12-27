"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Lock, Loader2, AlertCircle, CheckCircle2, BookOpen, ArrowRight } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ResetPasswordPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
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
            <main className="min-h-screen flex items-center justify-center py-12 px-4">
                <div className="glass-card p-8 text-center">
                    <AlertCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
                    <h1 className="text-2xl font-bold mb-2 text-red-400">Invalid Link</h1>
                    <p className="text-gray-400 mb-6">This password reset link is invalid or has expired.</p>
                    <Link href="/forgot-password" className="btn-primary inline-flex">
                        Request New Link
                    </Link>
                </div>
            </main>
        );
    }

    return (
        <main className="min-h-screen flex items-center justify-center py-12 px-4">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 mb-4">
                        <BookOpen className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text">Reset Password</h1>
                    <p className="text-gray-400 mt-2">Enter your new password</p>
                </div>

                <div className="glass-card p-8">
                    {success ? (
                        <div className="text-center">
                            <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-400" />
                            <h2 className="text-xl font-bold mb-2 text-green-400">Password Reset!</h2>
                            <p className="text-gray-400 mb-6">
                                Your password has been reset successfully. You can now login with your new password.
                            </p>
                            <Link href="/login" className="btn-primary inline-flex">
                                Continue to Login
                                <ArrowRight className="w-5 h-5 ml-2" />
                            </Link>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-5">
                            {/* Password */}
                            <div>
                                <label htmlFor="password" className="form-label">
                                    New Password
                                </label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="password"
                                        id="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Min. 6 characters"
                                        className="form-input pl-12"
                                        required
                                    />
                                </div>
                            </div>

                            {/* Confirm Password */}
                            <div>
                                <label htmlFor="confirmPassword" className="form-label">
                                    Confirm New Password
                                </label>
                                <div className="relative">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        type="password"
                                        id="confirmPassword"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="Confirm your password"
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
                                        Resetting...
                                    </>
                                ) : (
                                    <>
                                        <Lock className="w-5 h-5" />
                                        Reset Password
                                    </>
                                )}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </main>
    );
}
