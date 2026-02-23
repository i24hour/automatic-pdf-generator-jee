"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { CheckCircle2, XCircle, Loader2, Zap, Infinity as InfinityIcon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://mentors-mantra-api-87253755436.us-central1.run.app";

type PageStatus = "checking" | "success" | "failed" | "pending";

function PaymentSuccessInner() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const { authFetch, refreshUser } = useAuth();

    const [status, setStatus] = useState<PageStatus>("checking");
    const [plan, setPlan] = useState<string>("earth");
    const [attempts, setAttempts] = useState(0);

    useEffect(() => {
        const orderId = searchParams.get("order_id");
        if (!orderId) {
            router.replace("/");
            return;
        }
        pollStatus(orderId);
    }, []);

    const pollStatus = async (orderId: string) => {
        /**
         * Webhook usually fires within 2-5 seconds of payment.
         * We poll up to 8 times (every 2.5 s = 20 s total).
         */
        for (let i = 0; i < 8; i++) {
            await new Promise(r => setTimeout(r, 2500));
            setAttempts(i + 1);

            try {
                const res = await authFetch(`${API_BASE}/api/payments/order/${orderId}/status`);
                if (!res.ok) continue;

                const data = await res.json();

                if (data.status === "PAID") {
                    await refreshUser(); // sync is_premium + plan to auth context
                    setPlan(data.plan);
                    setStatus("success");
                    return;
                }

                if (data.status === "FAILED") {
                    setStatus("failed");
                    return;
                }
                // still PENDING — keep polling
            } catch {
                // network blip — keep polling
            }
        }
        // After 20s still pending
        setStatus("pending");
    };

    // ---- Checking ----
    if (status === "checking") {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-white dark:bg-black p-8 text-center">
                <div className="p-5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 mb-6">
                    <Loader2 className="w-12 h-12 text-indigo-600 animate-spin" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Verifying Payment…</h1>
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                    {attempts < 3
                        ? "Confirming with Cashfree…"
                        : `Still confirming… (${attempts}/8)`}
                </p>
            </div>
        );
    }

    // ---- Success ----
    if (status === "success") {
        const isUniverse = plan === "universe";
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-white dark:bg-black p-8 text-center">
                <div className={`p-5 rounded-full mb-6 ${isUniverse ? "bg-indigo-100 dark:bg-indigo-900/30" : "bg-green-100 dark:bg-green-900/30"}`}>
                    {isUniverse
                        ? <InfinityIcon className="w-12 h-12 text-indigo-600 dark:text-indigo-400" />
                        : <CheckCircle2 className="w-12 h-12 text-green-500" />
                    }
                </div>
                <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white mb-2">
                    🎉 Payment Successful!
                </h1>
                <p className="text-lg text-gray-600 dark:text-gray-300 mb-1">
                    You are now on the{" "}
                    <span className={`font-bold capitalize ${isUniverse ? "text-indigo-600 dark:text-indigo-400" : "text-green-600 dark:text-green-400"}`}>
                        {plan}
                    </span>{" "}
                    Plan.
                </p>
                <p className="text-sm text-gray-400 dark:text-gray-500 mb-8">
                    Your subscription is valid for 30 days.
                </p>
                <Link
                    href="/"
                    className="px-8 py-3 bg-black dark:bg-white text-white dark:text-black font-semibold rounded-xl hover:opacity-90 transition-opacity"
                >
                    Start Generating →
                </Link>
            </div>
        );
    }

    // ---- Failed ----
    if (status === "failed") {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-white dark:bg-black p-8 text-center">
                <div className="p-5 rounded-full bg-red-100 dark:bg-red-900/30 mb-6">
                    <XCircle className="w-12 h-12 text-red-500" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Payment Failed</h1>
                <p className="text-gray-500 dark:text-gray-400 mb-8">
                    Your payment was not completed. No money was deducted.
                </p>
                <Link
                    href="/pricing"
                    className="px-8 py-3 bg-black dark:bg-white text-white dark:text-black font-semibold rounded-xl hover:opacity-90 transition-opacity"
                >
                    Try Again
                </Link>
            </div>
        );
    }

    // ---- Pending (took too long) ----
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-white dark:bg-black p-8 text-center">
            <div className="p-5 rounded-full bg-yellow-100 dark:bg-yellow-900/30 mb-6">
                <Zap className="w-12 h-12 text-yellow-500" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Payment Pending</h1>
            <p className="text-gray-500 dark:text-gray-400 mb-2">
                We&apos;re still waiting for confirmation from Cashfree.
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mb-8">
                If money was deducted, your account will be upgraded within a few minutes.
                Refresh your profile to check.
            </p>
            <div className="flex gap-3">
                <button
                    onClick={() => window.location.reload()}
                    className="px-6 py-2.5 border border-gray-300 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                >
                    Refresh
                </button>
                <Link
                    href="/"
                    className="px-6 py-2.5 bg-black dark:bg-white text-white dark:text-black rounded-xl text-sm font-medium hover:opacity-90 transition-opacity"
                >
                    Go Home
                </Link>
            </div>
        </div>
    );
}

// Wrap in Suspense because useSearchParams requires it in Next.js app router
export default function PaymentSuccessPage() {
    return (
        <Suspense
            fallback={
                <div className="flex items-center justify-center min-h-screen">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                </div>
            }
        >
            <PaymentSuccessInner />
        </Suspense>
    );
}
