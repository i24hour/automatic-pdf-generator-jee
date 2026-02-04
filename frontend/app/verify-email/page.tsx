"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2, ArrowRight } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function VerifyEmailContent() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token");

    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [message, setMessage] = useState("");

    useEffect(() => {
        if (!token) {
            setStatus("error");
            setMessage("No verification token provided");
            return;
        }

        verifyEmail();
    }, [token]);

    const verifyEmail = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token }),
            });

            const data = await response.json();

            if (response.ok) {
                setStatus("success");
                setMessage(data.message);
            } else {
                setStatus("error");
                setMessage(data.detail || "Verification failed");
            }
        } catch {
            setStatus("error");
            setMessage("Something went wrong. Please try again.");
        }
    };

    return (
        <div className="w-full max-w-md mx-auto">
            {/* Mobile Logo - Simple */}
            <div className="lg:hidden flex flex-col items-center mb-8">
                <div className="w-16 h-16 mb-3">
                    <img src="/logo.png" alt="INFINITEST" className="w-full h-full object-contain" />
                </div>
                <h1 className="text-xl font-black tracking-tight text-gray-900">INFINITEST</h1>
            </div>

            {status === "loading" && (
                <div className="text-center">
                    <Loader2 className="w-14 h-14 mx-auto mb-6 text-gray-900 animate-spin" />
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Verifying Email...</h1>
                    <p className="text-gray-500">Please wait while we verify your email address.</p>
                </div>
            )}

            {status === "success" && (
                <div className="text-center">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                        <CheckCircle2 className="w-8 h-8 text-green-600" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Email Verified!</h1>
                    <p className="text-gray-500 mb-8">{message}</p>
                    <Link
                        href="/login"
                        className="inline-flex items-center justify-center gap-2 py-3 px-6 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-colors w-full"
                    >
                        Continue to Login
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            )}

            {status === "error" && (
                <div className="text-center">
                    <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-6">
                        <XCircle className="w-8 h-8 text-red-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h1>
                    <p className="text-gray-500 mb-8">{message}</p>
                    <Link
                        href="/login"
                        className="inline-flex items-center justify-center gap-2 py-3 px-6 bg-gray-100 hover:bg-gray-200 text-gray-900 font-medium rounded-xl transition-colors w-full"
                    >
                        Back to Login
                    </Link>
                </div>
            )}
        </div>
    );
}

export default function VerifyEmailPage() {
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
                        Almost There
                    </h1>

                    <p className="text-gray-400 text-lg text-center max-w-sm">
                        Just one more step to unlock your infinite potential.
                    </p>
                </div>

                {/* Bottom gradient */}
                <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
            </div>

            {/* Right Panel - Content */}
            <div className="flex-1 lg:w-1/2 flex items-center justify-center py-12 px-6 bg-white">
                <Suspense fallback={
                    <div className="flex justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
                    </div>
                }>
                    <VerifyEmailContent />
                </Suspense>
            </div>
        </main>
    );
}
