"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, BookOpen } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { FloatingInput } from "@/components/FloatingInput";

export default function SignupPage() {
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const { register } = useAuth();
    const router = useRouter();

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

        setIsLoading(true);

        try {
            await register(email, password, name || undefined, phone || undefined);
            router.push("/");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Registration failed");
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
                    <h1 className="text-2xl font-semibold text-gray-900 text-center mb-2">Create Account</h1>
                    <p className="text-gray-500 text-center mb-8 text-sm">Join thousands of JEE aspirants</p>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        {/* Name */}
                        <FloatingInput
                            type="text"
                            label="Name (Optional)"
                            value={name}
                            onChange={setName}
                            autoComplete="name"
                        />

                        {/* Email */}
                        <FloatingInput
                            type="email"
                            label="Email"
                            value={email}
                            onChange={setEmail}
                            required
                            autoComplete="email"
                        />

                        {/* Phone */}
                        <FloatingInput
                            type="tel"
                            label="Phone Number (Optional)"
                            value={phone}
                            onChange={setPhone}
                            autoComplete="tel"
                        />

                        {/* Password */}
                        <FloatingInput
                            type="password"
                            label="Password"
                            value={password}
                            onChange={setPassword}
                            required
                            autoComplete="new-password"
                        />

                        {/* Confirm Password */}
                        <FloatingInput
                            type="password"
                            label="Confirm password"
                            value={confirmPassword}
                            onChange={setConfirmPassword}
                            required
                            autoComplete="new-password"
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
                                    Creating account...
                                </>
                            ) : (
                                "Create Account"
                            )}
                        </button>
                    </form>

                    {/* Login link */}
                    <p className="text-center text-gray-500 mt-6 text-sm">
                        Already have an account?{" "}
                        <Link href="/login" className="text-indigo-600 hover:text-indigo-700 font-medium">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </main>
    );
}
