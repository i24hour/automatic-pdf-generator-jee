"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2, BookOpen, ArrowRight } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function VerifyEmailPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
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
        <main className="min-h-screen flex items-center justify-center py-12 px-4">
            <div className="w-full max-w-md text-center">
                {/* Header */}
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 mb-6">
                    <BookOpen className="w-8 h-8 text-white" />
                </div>

                <div className="glass-card p-8">
                    {status === "loading" && (
                        <>
                            <Loader2 className="w-16 h-16 mx-auto mb-4 text-indigo-400 animate-spin" />
                            <h1 className="text-2xl font-bold mb-2">Verifying Email...</h1>
                            <p className="text-gray-400">Please wait while we verify your email address.</p>
                        </>
                    )}

                    {status === "success" && (
                        <>
                            <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-400" />
                            <h1 className="text-2xl font-bold mb-2 text-green-400">Email Verified!</h1>
                            <p className="text-gray-400 mb-6">{message}</p>
                            <Link href="/login" className="btn-primary inline-flex">
                                Continue to Login
                                <ArrowRight className="w-5 h-5 ml-2" />
                            </Link>
                        </>
                    )}

                    {status === "error" && (
                        <>
                            <XCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
                            <h1 className="text-2xl font-bold mb-2 text-red-400">Verification Failed</h1>
                            <p className="text-gray-400 mb-6">{message}</p>
                            <Link href="/login" className="btn-secondary inline-flex">
                                Back to Login
                            </Link>
                        </>
                    )}
                </div>
            </div>
        </main>
    );
}
