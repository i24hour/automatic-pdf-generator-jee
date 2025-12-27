"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, BookOpen, AlertTriangle } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { FloatingInput } from "@/components/FloatingInput";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [needsVerification, setNeedsVerification] = useState(false);

    const { login } = useAuth();
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

    return (
        <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-[#FAF9F6]">
            <div className="w-full max-w-md">
                {/* Card */}
                <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <div className="w-14 h-14 rounded-xl bg-indigo-600 flex items-center justify-center">
                            <BookOpen className="w-7 h-7 text-white" />
                        </div>
                    </div>

                    {/* Title */}
                    <h1 className="text-2xl font-semibold text-gray-900 text-center mb-2">Welcome Back</h1>
                    <p className="text-gray-500 text-center mb-8 text-sm">Sign in to continue</p>

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
