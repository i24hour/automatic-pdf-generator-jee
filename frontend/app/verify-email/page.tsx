"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2, BookOpen, ArrowRight } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function VerifyEmailPage() {
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
        <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-[#FAF9F6]">
            <div className="w-full max-w-md text-center">
                {/* Logo */}
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-indigo-600 mb-6">
                    <BookOpen className="w-7 h-7 text-white" />
                </div>

                <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
                    {status === "loading" && (
                        <>
                            <Loader2 className="w-14 h-14 mx-auto mb-4 text-indigo-600 animate-spin" />
                            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Verifying Email...</h1>
                            <p className="text-gray-500 text-sm">Please wait while we verify your email address.</p>
                        </>
                    )}

                    {status === "success" && (
                        <>
                            <CheckCircle2 className="w-14 h-14 mx-auto mb-4 text-green-500" />
                            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Email Verified!</h1>
                            <p className="text-gray-500 text-sm mb-6">{message}</p>
                            <Link
                                href="/login"
                                className="inline-flex items-center gap-2 py-3 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
                            >
                                Continue to Login
                                <ArrowRight className="w-4 h-4" />
                            </Link>
                        </>
                    )}

                    {status === "error" && (
                        <>
                            <XCircle className="w-14 h-14 mx-auto mb-4 text-red-500" />
                            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Verification Failed</h1>
                            <p className="text-gray-500 text-sm mb-6">{message}</p>
                            <Link
                                href="/login"
                                className="inline-block py-3 px-6 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
                            >
                                Back to Login
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </main>
    );
}
