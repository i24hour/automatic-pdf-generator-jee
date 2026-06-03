"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
    Check,
    X,
    Zap,
    Globe,
    Infinity as InfinityIcon,
    Loader2,
    ArrowLeft,
} from "lucide-react";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import MobileNav from "@/components/layout/MobileNav";
import { useAuth } from "@/lib/auth-context";
import { API_BASE } from "@/lib/config";


// ---------------------------------------------------------
// Plan data (mirrors backend PLANS dict)
// ---------------------------------------------------------
interface PlanFeature {
    label: string;
    free: string | boolean;
    earth: string | boolean;
    universe: string | boolean;
}

const FEATURES: PlanFeature[] = [
    { label: "PDF generations / month",  free: "5",         earth: "10",        universe: "Unlimited" },
    { label: "Tests",                    free: "4",         earth: "Unlimited", universe: "Unlimited" },
    { label: "Institute PDF",            free: false,       earth: "1",         universe: "4"         },
    { label: "Video Generator",          free: false,       earth: false,       universe: true        },
    { label: "Bot Analysis Agent",       free: "Limited",   earth: "Unlimited", universe: "Unlimited" },
];

// ---------------------------------------------------------
// Component
// ---------------------------------------------------------
export default function PricingPage() {
    const router = useRouter();
    const { user, isAuthenticated, authFetch, refreshUser } = useAuth();
    const [loading, setLoading] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [planLoading, setPlanLoading] = useState(true);

    // Redirect immediately to home page since plans are now completely free
    useEffect(() => {
        router.replace("/");
        const fetchFreshPlan = async () => {
            try {
                await refreshUser();
            } finally {
                setPlanLoading(false);
            }
        };
        fetchFreshPlan();
    }, [router]);

    const currentPlan = (user as any)?.plan || "free";

    const handleBuy = async (planKey: string) => {
        if (!isAuthenticated) {
            router.push("/signup");
            return;
        }

        setLoading(planKey);
        setError(null);

        try {
            // 1. Create order on backend
            const res = await authFetch(`${API_BASE}/api/payments/create-order`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ plan_key: planKey }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Could not create order");
            }

            const data = await res.json();
            // data: { order_id, payment_session_id, amount, plan_name, cf_env }

            // 2. Load Cashfree SDK dynamically (avoids SSR issues)
            const { load } = await import("@cashfreepayments/cashfree-js");
            const cashfree = await load({ mode: data.cf_env as "sandbox" | "production" });

            // 3. Open Cashfree checkout modal
            cashfree.checkout({
                paymentSessionId: data.payment_session_id,
                returnUrl: `${window.location.origin}/payment/success?order_id=${data.order_id}`,
            });
        } catch (err: any) {
            setError(err.message || "Something went wrong. Please try again.");
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile */}
            <div className="md:hidden pb-20">
                {planLoading ? (
                    <div className="flex items-center justify-center h-screen">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                ) : (
                    <PricingContent
                        currentPlan={currentPlan}
                        loading={loading}
                        error={error}
                        onBuy={handleBuy}
                        onBack={() => router.back()}
                    />
                )}
                <MobileNav />
            </div>

            {/* Desktop */}
            <div className="hidden md:flex min-h-screen">
                <DesktopSidebar />
                <main className="flex-1 ml-[275px] min-h-screen p-8">
                    {planLoading ? (
                        <div className="flex items-center justify-center h-screen">
                            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                        </div>
                    ) : (
                        <PricingContent
                            currentPlan={currentPlan}
                            loading={loading}
                            error={error}
                            onBuy={handleBuy}
                            onBack={() => router.back()}
                        />
                    )}
                </main>
            </div>
        </div>
    );
}

// ---------------------------------------------------------
// Inner content (shared between mobile / desktop)
// ---------------------------------------------------------
interface PricingContentProps {
    currentPlan: string;
    loading: string | null;
    error: string | null;
    onBuy: (planKey: string) => void;
    onBack: () => void;
}

function PricingContent({ currentPlan, loading, error, onBuy, onBack }: PricingContentProps) {
    return (
        <div className="max-w-5xl mx-auto px-4 py-8">
            {/* Back */}
            <button
                onClick={onBack}
                className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6 transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                Back
            </button>

            {/* Header */}
            <div className="text-center mb-10">
                <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 dark:text-white mb-3">
                    Choose Your Plan
                </h1>
                <p className="text-gray-500 dark:text-gray-400 text-base max-w-xl mx-auto">
                    Unlock unlimited tests, PDFs, and more. Cancel anytime.
                </p>
            </div>

            {/* Error banner */}
            {error && (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-400 text-sm text-center">
                    {error}
                </div>
            )}

            {/* Plan cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
                {/* FREE */}
                <PlanCard
                    name="Free"
                    price={null}
                    priceLabel="₹0 / month"
                    icon={<Globe className="w-6 h-6" />}
                    highlight={false}
                    isCurrent={currentPlan === "free"}
                    planKey={null}
                    loading={loading}
                    onBuy={onBuy}
                    features={[
                        "5 PDFs per month",
                        "4 tests",
                        "Limited Bot Analysis",
                    ]}
                    badFeatures={["Institute PDF", "Video Generator"]}
                />

                {/* EARTH */}
                <PlanCard
                    name="Earth"
                    price="earth_monthly"
                    priceLabel="₹19 / month"
                    icon={<Zap className="w-6 h-6" />}
                    highlight={false}
                    isCurrent={currentPlan === "earth"}
                    planKey="earth_monthly"
                    loading={loading}
                    onBuy={onBuy}
                    features={[
                        "10 PDFs per month",
                        "Unlimited tests",
                        "1 Institute PDF",
                        "Unlimited Bot Analysis",
                    ]}
                    badFeatures={["Video Generator"]}
                />

                {/* UNIVERSE */}
                <PlanCard
                    name="Universe"
                    price="universe_monthly"
                    priceLabel="₹99 / month"
                    icon={<InfinityIcon className="w-6 h-6" />}
                    highlight={true}
                    isCurrent={currentPlan === "universe"}
                    planKey="universe_monthly"
                    loading={loading}
                    onBuy={onBuy}
                    features={[
                        "Unlimited PDFs",
                        "Unlimited tests",
                        "4 Institute PDFs",
                        "Video Generator",
                        "Unlimited Bot Analysis",
                    ]}
                    badFeatures={[]}
                />
            </div>

            {/* Full comparison table */}
            <ComparisonTable currentPlan={currentPlan} />
        </div>
    );
}

// ---------------------------------------------------------
// Plan card
// ---------------------------------------------------------
interface PlanCardProps {
    name: string;
    price: string | null;
    priceLabel: string;
    icon: React.ReactNode;
    highlight: boolean;
    isCurrent: boolean;
    planKey: string | null;
    loading: string | null;
    onBuy: (planKey: string) => void;
    features: string[];
    badFeatures: string[];
}

function PlanCard({
    name, priceLabel, icon, highlight, isCurrent, planKey, loading, onBuy, features, badFeatures,
}: PlanCardProps) {
    const isLoading = loading === planKey;

    return (
        <div
            className={`relative rounded-2xl border p-6 flex flex-col gap-4 transition-all
                ${highlight
                    ? "border-indigo-500 shadow-lg shadow-indigo-500/10 bg-indigo-50 dark:bg-indigo-950/30"
                    : "border-gray-200 dark:border-gray-800 bg-white dark:bg-[#111]"
                }`}
        >
            {highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-indigo-600 text-white text-xs font-bold rounded-full">
                    BEST VALUE
                </div>
            )}

            <div className={`p-3 rounded-xl w-fit ${highlight ? "bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600" : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"}`}>
                {icon}
            </div>

            <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">{name} Plan</h2>
                <p className={`text-2xl font-extrabold mt-1 ${highlight ? "text-indigo-600 dark:text-indigo-400" : "text-gray-900 dark:text-white"}`}>
                    {priceLabel}
                </p>
            </div>

            <ul className="space-y-2 flex-1">
                {features.map(f => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                        <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                        {f}
                    </li>
                ))}
                {badFeatures.map(f => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-600 line-through">
                        <X className="w-4 h-4 text-gray-300 flex-shrink-0" />
                        {f}
                    </li>
                ))}
            </ul>

            {/* CTA */}
            {isCurrent ? (
                <div className="w-full py-3 rounded-xl text-center text-sm font-semibold bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                    Current Plan
                </div>
            ) : planKey ? (
                <button
                    onClick={() => onBuy(planKey)}
                    disabled={!!loading}
                    className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-opacity disabled:opacity-60
                        ${highlight
                            ? "bg-indigo-600 hover:bg-indigo-700 text-white"
                            : "bg-black dark:bg-white text-white dark:text-black hover:opacity-90"
                        }`}
                >
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    {isLoading ? "Opening Payment..." : `Get ${name} Plan`}
                </button>
            ) : (
                <div className="w-full py-3 rounded-xl text-center text-sm font-semibold bg-gray-50 dark:bg-gray-900 text-gray-400">
                    Always Free
                </div>
            )}
        </div>
    );
}

// ---------------------------------------------------------
// Comparison table
// ---------------------------------------------------------
function FeatureCell({ value }: { value: string | boolean }) {
    if (value === true)  return <Check className="w-5 h-5 text-green-500 mx-auto" />;
    if (value === false) return <X className="w-5 h-5 text-gray-300 dark:text-gray-700 mx-auto" />;
    return <span className="text-sm text-gray-700 dark:text-gray-300">{value as string}</span>;
}

function ComparisonTable({ currentPlan }: { currentPlan: string }) {
    return (
        <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-gray-800">
            <table className="w-full text-center">
                <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-[#111]">
                        <th className="py-4 px-4 text-left text-sm font-semibold text-gray-500 dark:text-gray-400">Feature</th>
                        {["free", "earth", "universe"].map(p => (
                            <th key={p} className={`py-4 px-4 text-sm font-bold capitalize
                                ${currentPlan === p ? "text-indigo-600 dark:text-indigo-400" : "text-gray-900 dark:text-white"}`}>
                                {p === "free" ? "Free" : p === "earth" ? "Earth ₹19" : "Universe ₹99"}
                                {currentPlan === p && <span className="block text-xs font-normal text-indigo-500">Current</span>}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {FEATURES.map((f, i) => (
                        <tr key={f.label} className={`border-b border-gray-100 dark:border-gray-800/60 ${i % 2 === 0 ? "" : "bg-gray-50/50 dark:bg-white/[0.02]"}`}>
                            <td className="py-3 px-4 text-left text-sm text-gray-700 dark:text-gray-300 font-medium">{f.label}</td>
                            <td className="py-3 px-4"><FeatureCell value={f.free} /></td>
                            <td className="py-3 px-4"><FeatureCell value={f.earth} /></td>
                            <td className="py-3 px-4"><FeatureCell value={f.universe} /></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
