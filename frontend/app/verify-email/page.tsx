"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2, BookOpen, ArrowRight } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://mentors-mantra-api-87253755436.us-central1.run.app";

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
        <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
            {status === "loading" && (
                <>
                    <Loader2 className="w-14 h-14 mx-auto mb-4 text-indigo-600 animate-spin" />
                    <h1 className="text-2xl font-semibold text-gray-900 mb-2 text-center">Verifying Email...</h1>
                    <p className="text-gray-500 text-sm text-center">Please wait while we verify your email address.</p>
                </>
            )}

            {status === "success" && (
                <div className="text-center">
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
                </div>
            )}

            {status === "error" && (
                <div className="text-center">
                    <XCircle className="w-14 h-14 mx-auto mb-4 text-red-500" />
                    <h1 className="text-2xl font-semibold text-gray-900 mb-2">Verification Failed</h1>
                    <p className="text-gray-500 text-sm mb-6">{message}</p>
                    <Link
                        href="/login"
                        className="inline-block py-3 px-6 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
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
        <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-white">
            <div className="w-full max-w-md text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-indigo-600 mb-6">
                    <BookOpen className="w-7 h-7 text-white" />
                </div>

                <Suspense fallback={
                    <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
                        <Loader2 className="w-14 h-14 mx-auto mb-4 text-indigo-600 animate-spin" />
                        <h1 className="text-2xl font-semibold text-gray-900 mb-2">Loading...</h1>
                    </div>
                }>
                    <VerifyEmailContent />
                </Suspense>
            </div>
        </main>
    );
}
