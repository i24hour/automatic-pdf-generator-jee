"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2, BookOpen, ArrowRight } from "lucide-react";
import { FloatingInput } from "@/components/FloatingInput";

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
            <div className="bg-white border border-gray-200 rounded-2xl p-10 text-center shadow-lg">
                <AlertCircle className="w-14 h-14 mx-auto mb-4 text-red-500" />
                <h1 className="text-2xl font-semibold text-gray-900 mb-2">Invalid Link</h1>
                <p className="text-gray-500 text-sm mb-6">This password reset link is invalid or has expired.</p>
                <Link
                    href="/forgot-password"
                    className="inline-block py-3 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
                >
                    Request New Link
                </Link>
            </div>
        );
    }

    return (
        <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
            <div className="flex justify-center mb-6">
                <div className="w-14 h-14 rounded-xl bg-indigo-600 flex items-center justify-center">
                    <BookOpen className="w-7 h-7 text-white" />
                </div>
            </div>

            {success ? (
                <div className="text-center">
                    <CheckCircle2 className="w-14 h-14 mx-auto mb-4 text-green-500" />
                    <h1 className="text-2xl font-semibold text-gray-900 mb-2">Password Reset!</h1>
                    <p className="text-gray-500 text-sm mb-6">
                        Your password has been reset successfully.
                    </p>
                    <Link
                        href="/login"
                        className="inline-flex items-center gap-2 py-3 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
                    >
                        Continue to Sign in
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            ) : (
                <>
                    <h1 className="text-2xl font-semibold text-gray-900 text-center mb-2">Reset Password</h1>
                    <p className="text-gray-500 text-center mb-8 text-sm">Enter your new password</p>

                    <form onSubmit={handleSubmit} className="space-y-5">
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
                            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Resetting...
                                </>
                            ) : (
                                "Reset Password"
                            )}
                        </button>
                    </form>
                </>
            )}
        </div>
    );
}

export default function ResetPasswordPage() {
    return (
        <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-white">
            <div className="w-full max-w-md">
                <Suspense fallback={
                    <div className="flex justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                    </div>
                }>
                    <ResetPasswordForm />
                </Suspense>
            </div>
        </main>
    );
}
