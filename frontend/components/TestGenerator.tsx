"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
    FileText,
    Sparkles,
    Download,
    Loader2,
    BookOpen,
    Atom,
    Calculator,
    FlaskConical,
    CheckCircle2,
    AlertCircle,
    Zap,
    GraduationCap,
    Trophy,
    Target,
    Award,
    LogOut,
    Clock,
    Gift,
    Leaf,
    Dna,
    Stethoscope,
    X,
    Share2,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import PostModal from "@/components/PostModal";
import UsernameModal from "@/components/UsernameModal";

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GenerateResponse {
    success: boolean;
    message: string;
    pdf_filename?: string;
    pdf_base64?: string;
    shared_pdf_id?: string;
    total_mcq: number;
    total_numerical: number;
    rate_limit_remaining: number;
    rate_limit_reset_hours: number;
    verification_stats?: {
        total_numerical: number;
        verified: number;
        corrected: number;
    };
}

interface RateLimitInfo {
    limit: number;
    remaining: number;
    reset_hours: number;
    used: number;
}

export default function TestGenerator() {
    const { user, isLoading: authLoading, isAuthenticated, logout, authFetch, refreshUser } = useAuth();
    const router = useRouter();

    const [subject, setSubject] = useState("Physics");
    const [topic, setTopic] = useState("");
    const [questionCount, setQuestionCount] = useState(20);
    const [level, setLevel] = useState("JEE Mains");
    const [difficulty, setDifficulty] = useState("Medium");
    const [numMCQs, setNumMCQs] = useState(20);
    const [numNumericals, setNumNumericals] = useState(5);
    const [includeSolutions, setIncludeSolutions] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<GenerateResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);
    const [resendLoading, setResendLoading] = useState(false);
    const [resendMessage, setResendMessage] = useState<string | null>(null);
    const [promoCode, setPromoCode] = useState("");
    const [promoLoading, setPromoLoading] = useState(false);
    const [promoMessage, setPromoMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
    const [isDetectingSubject, setIsDetectingSubject] = useState(false);
    const detectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const [elapsedTime, setElapsedTime] = useState(0);
    const [progressStep, setProgressStep] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const [showPostModal, setShowPostModal] = useState(false);
    const [showUsernameModal, setShowUsernameModal] = useState(false);

    // Prompt for username if missing
    useEffect(() => {
        if (user && !user.username && !authLoading) {
            // Small delay to ensure smooth loading
            const timer = setTimeout(() => {
                setShowUsernameModal(true);
            }, 1000);
            return () => clearTimeout(timer);
        }
    }, [user, authLoading]);

    const subjects = [
        { name: "Physics", icon: Atom },
        { name: "Chemistry", icon: FlaskConical },
        { name: "Maths", icon: Calculator },
        { name: "Zoology", icon: Dna },
        { name: "Botany", icon: Leaf },
    ];

    const allLevels = [
        { name: "Boards", icon: GraduationCap, color: "text-green-400", bgColor: "bg-green-500/20", borderColor: "border-green-500" },
        { name: "JEE Mains", icon: Target, color: "text-blue-400", bgColor: "bg-blue-500/20", borderColor: "border-blue-500" },
        { name: "JEE Advanced", icon: Award, color: "text-purple-400", bgColor: "bg-purple-500/20", borderColor: "border-purple-500" },
        { name: "Olympiad", icon: Trophy, color: "text-yellow-400", bgColor: "bg-yellow-500/20", borderColor: "border-yellow-500" },
        { name: "NEET", icon: Stethoscope, color: "text-pink-400", bgColor: "bg-pink-500/20", borderColor: "border-pink-500" },
    ];

    const difficulties = [
        { name: "Easy", color: "text-green-600", bgColor: "bg-green-100", borderColor: "border-green-500" },
        { name: "Medium", color: "text-green-600", bgColor: "bg-green-100", borderColor: "border-green-500" },
        { name: "Hard", color: "text-green-600", bgColor: "bg-green-100", borderColor: "border-green-500" },
    ];

    // Smart level filtering based on subject
    const getAvailableLevels = () => {
        if (subject === "Maths") {
            // NEET doesn't have Maths
            return allLevels.filter(l => l.name !== "NEET");
        }
        if (subject === "Zoology" || subject === "Botany") {
            // Zoology and Botany are only for Boards and NEET
            return allLevels.filter(l => l.name === "Boards" || l.name === "NEET");
        }
        // Physics and Chemistry: all levels available
        return allLevels;
    };

    const levels = getAvailableLevels();

    // Update split when level changes
    useEffect(() => {
        if (level === "NEET") {
            setNumMCQs(questionCount);
            setNumNumericals(0);
        } else {
            // Recalculate based on current total
            const mcqs = Math.round(questionCount * 0.8);
            const numericals = questionCount - mcqs;
            setNumMCQs(mcqs);
            setNumNumericals(numericals);
        }
    }, [level]);

    const handleSliderChange = (val: number) => {
        setQuestionCount(val);
        if (level === "NEET") {
            setNumMCQs(val);
            setNumNumericals(0);
        } else {
            const mcqs = Math.round(val * 0.8);
            const numericals = val - mcqs;
            setNumMCQs(mcqs);
            setNumNumericals(numericals);
        }
    };

    const handleSplitChange = (type: 'mcq' | 'numerical', value: number) => {
        const newVal = Math.max(0, value);
        if (type === 'mcq') {
            setNumMCQs(newVal);
            setQuestionCount(newVal + numNumericals);
        } else {
            setNumNumericals(newVal);
            setQuestionCount(numMCQs + newVal);
        }
    };

    // Auto-switch level when subject changes to avoid invalid state
    useEffect(() => {
        const availableLevelNames = getAvailableLevels().map(l => l.name);
        if (!availableLevelNames.includes(level)) {
            // Switch to first available level
            setLevel(availableLevelNames[0] || "Boards");
        }
    }, [subject]);

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push("/login");
        }
    }, [authLoading, isAuthenticated, router]);

    // Fetch rate limit on mount and after generation
    useEffect(() => {
        if (isAuthenticated) {
            fetchRateLimit();
        }
    }, [isAuthenticated]);

    // Auto-detect subject when topic changes (debounced)
    useEffect(() => {
        // Clear any existing timeout
        if (detectTimeoutRef.current) {
            clearTimeout(detectTimeoutRef.current);
        }

        // Only detect if topic has at least 3 characters
        if (topic.trim().length < 3) {
            return;
        }

        // Debounce the API call by 500ms
        detectTimeoutRef.current = setTimeout(async () => {
            setIsDetectingSubject(true);
            try {
                const response = await fetch(`${API_BASE_URL}/api/detect-subject`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic: topic.trim() })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.subject && data.confidence !== 'low') {
                        // Auto-select the detected subject
                        setSubject(data.subject);
                    }
                }
            } catch (error) {
                console.error('Error detecting subject:', error);
            } finally {
                setIsDetectingSubject(false);
            }
        }, 500);

        // Cleanup on unmount
        return () => {
            if (detectTimeoutRef.current) {
                clearTimeout(detectTimeoutRef.current);
            }
        };
    }, [topic]);

    const fetchRateLimit = async () => {
        try {
            const response = await authFetch(`${API_BASE_URL}/api/rate-limit`);
            if (response.ok) {
                const data = await response.json();
                setRateLimit(data);
            }
        } catch (err) {
            console.error("Failed to fetch rate limit:", err);
        }
    };

    const handleApplyPromo = async () => {
        if (!promoCode.trim()) return;

        setPromoLoading(true);
        setPromoMessage(null);

        try {
            const response = await authFetch(`${API_BASE_URL}/api/apply-promo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: promoCode.trim() }),
            });

            const data = await response.json();

            if (response.ok) {
                setPromoMessage({ type: "success", text: data.message });
                setPromoCode("");
                // Refresh rate limit to show new limit
                fetchRateLimit();
            } else {
                setPromoMessage({ type: "error", text: data.detail || "Failed to apply promo code" });
            }
        } catch {
            setPromoMessage({ type: "error", text: "Failed to apply promo code" });
        } finally {
            setPromoLoading(false);
        }
    };

    const handleGenerate = async () => {
        if (!topic.trim()) {
            setError("Please enter a topic");
            return;
        }

        // Create new abort controller for this request
        abortControllerRef.current = new AbortController();

        setIsLoading(true);
        setError(null);
        setResult(null);
        setElapsedTime(0);
        setProgressStep(0);

        // Start timer
        timerRef.current = setInterval(() => {
            setElapsedTime(prev => prev + 1);
        }, 1000);

        try {
            const response = await authFetch(`${API_BASE_URL}/api/generate-verified`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    subject,
                    topic: topic.trim(),
                    total_questions: questionCount,
                    level,
                    difficulty,
                    num_mcqs: numMCQs,
                    num_numerical: numNumericals,
                    include_solutions: includeSolutions,
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to generate test paper");
            }

            const data: GenerateResponse = await response.json();
            setResult(data);

            // Update rate limit locally
            setRateLimit((prev) => prev ? {
                ...prev,
                remaining: data.rate_limit_remaining,
                used: prev.limit - data.rate_limit_remaining,
            } : null);

        } catch (err: unknown) {
            // Check if it was cancelled
            if (err instanceof Error && err.name === 'AbortError') {
                setError("Generation cancelled.");
                return;
            }
            // Log technical error to console for debugging
            console.error("Generation error:", err);
            // Show generic message to user
            setError("Failed to generate test paper. Please try again.");
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
            // Clear timer
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
        }
    };

    const handleCancelGeneration = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
    };


    const handleDownload = () => {
        if (result?.pdf_base64) {
            // Decode base64 and trigger download
            const binary = atob(result.pdf_base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = result.pdf_filename || 'test_paper.pdf';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else if (result?.pdf_filename) {
            // Fallback to API endpoint (for backwards compatibility)
            window.open(`${API_BASE_URL}/api/download/${result.pdf_filename}`, "_blank");
        }
    };

    const handleLogout = () => {
        logout();
        router.push("/login");
    };

    // Show loading while checking auth
    if (authLoading) {
        return (
            <main className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            </main>
        );
    }

    // Don't render if not authenticated (will redirect)
    if (!isAuthenticated) {
        return null;
    }

    const handleResendVerification = async () => {
        setResendLoading(true);
        setResendMessage(null);
        try {
            const response = await authFetch(`${API_BASE_URL}/auth/resend-verification`, {
                method: "POST",
            });
            if (response.ok) {
                setResendMessage("Verification email sent! Check your inbox.");
            } else {
                const data = await response.json();
                setResendMessage(data.detail || "Failed to send email");
            }
        } catch {
            setResendMessage("Failed to send email. Try again.");
        } finally {
            setResendLoading(false);
        }
    };

    // Show verification required screen if email not verified
    if (user && !user.is_verified) {
        return (
        return (
            <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-[#FAF9F6] dark:bg-black">
                <div className="max-w-md w-full text-center">
                    <div className="bg-white dark:bg-[#16181c] border border-gray-200 dark:border-[#2f3336] rounded-2xl p-10 shadow-lg">
                        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                            <AlertCircle className="w-8 h-8 text-amber-600" />
                        </div>
                        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">Verify Your Email</h1>
                        <p className="text-gray-500 dark:text-gray-400 mb-6">
                            We&apos;ve sent a verification email to <strong className="text-gray-900 dark:text-white">{user.email}</strong>.
                            Please check your inbox and click the verification link.
                        </p>

                        {resendMessage && (
                            <p className={`text-sm mb-4 ${resendMessage.includes("sent") ? "text-green-600" : "text-red-600"}`}>
                                {resendMessage}
                            </p>
                        )}

                        <div className="space-y-3">
                            <button
                                onClick={() => refreshUser()}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors"
                            >
                                I&apos;ve Verified My Email
                            </button>
                            <button
                                onClick={handleResendVerification}
                                disabled={resendLoading}
                                className="w-full py-3 border border-indigo-600 text-indigo-600 hover:bg-indigo-50 font-medium rounded-lg transition-colors disabled:opacity-50"
                            >
                                {resendLoading ? "Sending..." : "Resend Verification Email"}
                            </button>
                            <button
                                onClick={handleLogout}
                                className="w-full py-3 text-gray-600 hover:text-gray-800 font-medium transition-colors"
                            >
                                Sign out
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        );
    }

    return (
        <div className="w-full">
            <div className="max-w-2xl mx-auto">
                {/* Header */}
                <div className="text-center mb-4 md:mb-8">
                    <div className="inline-flex items-center justify-center w-14 h-14 md:w-20 md:h-20 rounded-2xl bg-indigo-600 mb-3 md:mb-6">
                        <BookOpen className="w-7 h-7 md:w-10 md:h-10 text-white" />
                    </div>
                </div>
                <h1 className="text-2xl md:text-5xl font-bold mb-2 md:mb-4 text-gray-900 dark:text-white">
                    INFINITEST
                </h1>
                <div className="flex items-center justify-center gap-2 text-sm md:text-xl text-gray-500 font-medium">
                    <span>Trained by IITians</span>
                    <span className="text-gray-300">•</span>
                    <span>NEET Rankers</span>
                </div>
            </div>

            {/* Rate Limit Badge */}
            {rateLimit && (
                <div className="flex justify-center mb-3 md:mb-6">
                    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm ${rateLimit.remaining > 0
                        ? "bg-green-100 text-green-700 border border-green-200"
                        : "bg-red-100 text-red-700 border border-red-200"
                        }`}>
                        <Clock className="w-4 h-4" />
                        <span>
                            {rateLimit.remaining}/{rateLimit.limit} generations remaining
                        </span>
                        {rateLimit.reset_hours > 0 && (
                            <span className="text-gray-500">
                                • Reset on 1st {new Date(new Date().setMonth(new Date().getMonth() + 1)).toLocaleString('default', { month: 'short' })}
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Promo Code Section */}
            <div className="flex justify-center mb-3 md:mb-6">
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Gift className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Enter promo code"
                            value={promoCode}
                            onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                            value={promoCode}
                            onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                            className="pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent w-48 bg-white dark:bg-black text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600"
                        />
                    </div>
                    <button
                        onClick={handleApplyPromo}
                        disabled={promoLoading || !promoCode.trim()}
                        className="px-4 py-2 bg-indigo-500 text-white rounded-lg text-sm font-medium hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {promoLoading ? "Applying..." : "Apply"}
                    </button>
                </div>
            </div>
            {promoMessage && (
                <div className={`flex justify-center mb-6`}>
                    <div className={`text-sm px-4 py-2 rounded-lg ${promoMessage.type === "success"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                        }`}>
                        {promoMessage.text}
                    </div>
                </div>
            )}

            {/* Main Card */}
            <div className="bg-white dark:bg-[#16181c] border border-gray-200 dark:border-[#2f3336] rounded-2xl p-4 md:p-6 shadow-lg">
                {/* Subject Selection */}
                <div className="mb-3 md:mb-4">
                    <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">Select Subject</label>
                    <div className="grid grid-cols-3 gap-2">
                        {subjects.map((sub) => {
                            const IconComponent = sub.icon;
                            const isSelected = subject === sub.name;
                            return (
                                <button
                                    key={sub.name}
                                    onClick={() => setSubject(sub.name)}
                                    disabled={isLoading}
                                    className={`p-2 md:p-3 rounded-xl border transition-all duration-300 flex flex-col items-center gap-1 ${isSelected
                                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400"
                                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-[#16181c]"
                                        } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                                >
                                    <IconComponent className="w-5 h-5" />
                                    <span className="text-xs font-medium">{sub.name}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Level Selection */}
                <div className="mb-3 md:mb-4">
                    <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">Select Exam Type</label>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                        {levels.map((lvl) => {
                            const IconComponent = lvl.icon;
                            const isSelected = level === lvl.name;
                            return (
                                <button
                                    key={lvl.name}
                                    onClick={() => {
                                        setLevel(lvl.name);
                                        // Set default MCQ/Numerical counts based on exam type
                                        if (lvl.name === "JEE Mains") {
                                            setNumMCQs(20);
                                            setNumNumericals(5);
                                        } else if (lvl.name === "JEE Advanced") {
                                            setNumMCQs(15);
                                            setNumNumericals(5);
                                        } else if (lvl.name === "NEET") {
                                            setNumMCQs(20);
                                            setNumNumericals(0);
                                        } else if (lvl.name === "Olympiad") {
                                            setNumMCQs(10);
                                            setNumNumericals(5);
                                        } else {
                                            setNumMCQs(15);
                                            setNumNumericals(5);
                                        }
                                    }}
                                    disabled={isLoading}
                                    className={`p-2 rounded-xl border transition-all duration-300 flex flex-col items-center gap-1 ${isSelected
                                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400"
                                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-[#16181c]"
                                        } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                                >
                                    <IconComponent className="w-4 h-4" />
                                    <span className="text-[10px] font-medium text-center">{lvl.name}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Difficulty Selection */}
                <div className="mb-3 md:mb-4">
                    <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">Select Difficulty</label>
                    <div className="grid grid-cols-3 gap-2">
                        {difficulties.map((diff) => {
                            const isSelected = difficulty === diff.name;
                            return (
                                <button
                                    key={diff.name}
                                    onClick={() => setDifficulty(diff.name)}
                                    disabled={isLoading}
                                    className={`p-2 rounded-xl border transition-all duration-300 flex items-center justify-center ${isSelected
                                        ? `${diff.borderColor} ${diff.bgColor} ${diff.color}`
                                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-[#16181c]"
                                        } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                                >
                                    <span className="text-xs font-medium">{diff.name}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Topic Input */}
                <div className="mb-4">
                    <label htmlFor="topic" className="block mb-3 font-medium text-gray-700 dark:text-gray-300">Topic</label>
                    <input
                        type="text"
                        id="topic"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g., Electrostatics, Organic Chemistry, Integration"
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g., Electrostatics, Organic Chemistry, Integration"
                        className="w-full px-4 py-3 bg-white dark:bg-black border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900"
                        disabled={isLoading}
                    />
                </div>

                {/* Solutions Toggle */}
                <div className="mb-4">
                    <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">Include Solutions</label>
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            onClick={() => setIncludeSolutions(false)}
                            disabled={isLoading}
                            className={`p-3 rounded-xl border transition-all duration-300 flex flex-col items-center gap-1 ${!includeSolutions
                                ? "border-green-500 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400"
                                : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-[#16181c]"
                                } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                            <span className="text-sm font-medium">Without Solutions</span>
                            <span className="text-[10px] text-green-600">Faster (~1-2 min)</span>
                        </button>
                        <button
                            onClick={() => setIncludeSolutions(true)}
                            disabled={isLoading}
                            className={`p-3 rounded-xl border transition-all duration-300 flex flex-col items-center gap-1 ${includeSolutions
                                ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400"
                                : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-[#16181c]"
                                } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                            <span className="text-sm font-medium">With Solutions</span>
                            <span className="text-[10px] text-indigo-600">Slower (~3-5 min)</span>
                        </button>
                    </div>
                    {includeSolutions && (
                        <p className="text-xs text-gray-500 mt-2 text-center">
                            Solutions are verified for accuracy before PDF generation
                        </p>
                    )}
                </div>

                {/* Dynamic Exam Pattern */}
                <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {level === "Boards" ? "CBSE Pattern" : `${level} Pattern`}
                        </span>
                        <span className="text-xs text-gray-400">Total: {numMCQs + numNumericals} (max 50)</span>
                    </div>

                    {/* Boards Pattern */}
                    {level === "Boards" && (
                        <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                                {[
                                    { label: "Very Short Answer (1-2M)", defaultVal: 4 },
                                    { label: "Short Answer (2-3M)", defaultVal: 4 },
                                    { label: "Long Answer (5M)", defaultVal: 2 },
                                    { label: "Case-Based", defaultVal: 1 },
                                ].map((item) => (
                                    <div key={item.label} className="relative">
                                        <input
                                            type="number"
                                            min={0}
                                            max={20}
                                            defaultValue={item.defaultVal}
                                            className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                            placeholder=" "
                                        />
                                        <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium transition-all peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-xs peer-placeholder-shown:text-gray-400 peer-placeholder-shown:font-normal peer-focus:top-1 peer-focus:text-[10px] peer-focus:text-indigo-600 peer-focus:font-medium">
                                            {item.label}
                                        </label>
                                    </div>
                                ))}
                            </div>
                            <div className="relative">
                                <input
                                    type="number"
                                    min={0}
                                    max={20}
                                    defaultValue={4}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                    placeholder=" "
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium transition-all peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-xs peer-placeholder-shown:text-gray-400 peer-placeholder-shown:font-normal peer-focus:top-1 peer-focus:text-[10px] peer-focus:text-indigo-600 peer-focus:font-medium">
                                    Numericals (3-5M)
                                </label>
                            </div>
                        </div>
                    )}

                    {/* JEE Mains Pattern */}
                    {level === "JEE Mains" && (
                        <div className="grid grid-cols-2 gap-3">
                            <div className="relative">
                                <input
                                    type="number"
                                    value={numMCQs}
                                    onChange={(e) => {
                                        const val = parseInt(e.target.value) || 0;
                                        if (val >= 0 && val + numNumericals <= 50) setNumMCQs(val);
                                    }}
                                    min={0}
                                    max={50 - numNumericals}
                                    disabled={isLoading}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                    placeholder=" "
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                    MCQs
                                </label>
                            </div>
                            <div className="relative">
                                <input
                                    type="number"
                                    value={numNumericals}
                                    onChange={(e) => {
                                        const val = parseInt(e.target.value) || 0;
                                        if (val >= 0 && numMCQs + val <= 50) setNumNumericals(val);
                                    }}
                                    min={0}
                                    max={50 - numMCQs}
                                    disabled={isLoading}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                    placeholder=" "
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                    Numerical
                                </label>
                            </div>
                        </div>
                    )}

                    {/* JEE Advanced Pattern */}
                    {level === "JEE Advanced" && (
                        <div className="space-y-3">
                            <div className="grid grid-cols-3 gap-3">
                                <div className="relative">
                                    <input
                                        type="number"
                                        defaultValue={10}
                                        min={0}
                                        max={30}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Single Correct
                                    </label>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        defaultValue={5}
                                        min={0}
                                        max={20}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Multi Correct
                                    </label>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        defaultValue={5}
                                        min={0}
                                        max={20}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Integer
                                    </label>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* NEET Pattern */}
                    {level === "NEET" && (
                        <div className="grid grid-cols-2 gap-3">
                            <div className="relative">
                                <input
                                    type="number"
                                    defaultValue={35}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                                    placeholder=" "
                                    readOnly
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                    Section A (Compulsory)
                                </label>
                            </div>
                            <div className="relative">
                                <input
                                    type="number"
                                    defaultValue={15}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                                    placeholder=" "
                                    readOnly
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                    Section B (Any 10)
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Olympiad Pattern */}
                    {level === "Olympiad" && (
                        <div className="grid grid-cols-2 gap-3">
                            <div className="relative">
                                <input
                                    type="number"
                                    defaultValue={10}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                                    placeholder=" "
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                    MCQs
                                </label>
                            </div>
                            <div className="relative">
                                <input
                                    type="number"
                                    defaultValue={5}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                    placeholder=" "
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                    Subjective
                                </label>
                            </div>
                        </div>
                    )}
                </div>

                {/* Generate Button */}
                <button
                    onClick={handleGenerate}
                    disabled={isLoading || isDetectingSubject}
                    className={`w-full py-4 rounded-xl text-white font-semibold text-lg shadow-lg transition-all duration-300 flex items-center justify-center gap-2 mb-4 btn-primary ${isLoading || isDetectingSubject
                        ? "bg-gray-400 cursor-not-allowed"
                        : "hover:shadow-xl transform hover:-translate-y-0.5"
                        }`}
                >
                    {isLoading ? (
                        <>
                            <Loader2 className="w-6 h-6 animate-spin" />
                            <span>Generating Test Paper...</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-6 h-6" />
                            <span>Generate {level} ({difficulty}) Test Paper</span>
                        </>
                    )}
                </button>

                {/* Progress Bar */}
                {isLoading && (
                    <div className="mb-6">
                        <div className="flex justify-between text-sm text-gray-600 mb-2">
                            <span>Generating...</span>
                            <span>{elapsedTime}s</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                            <div
                                className="bg-indigo-600 h-2.5 rounded-full transition-all duration-1000 ease-in-out"
                                style={{ width: `${Math.min((elapsedTime / 45) * 100, 95)}%` }}
                            ></div>
                        </div>
                        <p className="text-xs text-center text-gray-500 mt-2 animate-pulse">
                            {elapsedTime < 10 && "Analyzing topic and difficulty..."}
                            {elapsedTime >= 10 && elapsedTime < 20 && "Crafting questions with AI..."}
                            {elapsedTime >= 20 && elapsedTime < 30 && "Verifying solutions and answers..."}
                            {elapsedTime >= 30 && "Formatting PDF document..."}
                        </p>

                        <button
                            onClick={handleCancelGeneration}
                            className="w-full mt-3 py-2 text-sm text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                        >
                            Cancel Generation
                        </button>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 animate-in fade-in slide-in-from-top-2">
                        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                        <p>{error}</p>
                    </div>
                )}

                {/* Success Message */}
                {result?.success && (
                    <div className="mt-6 space-y-4">
                        <div className="flex items-start gap-3 text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                            <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="font-medium">{result.message}</p>
                                <p className="text-sm text-green-600">
                                    {result.total_mcq} MCQs + {result.total_numerical} Numerical Questions
                                </p>
                            </div>
                        </div>


                        <div className="flex gap-3">
                            <button onClick={handleDownload} className="flex-1 py-3.5 border-2 border-indigo-600 text-indigo-600 font-medium rounded-lg hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2">
                                <Download className="w-5 h-5" />
                                Download PDF
                            </button>

                            <button
                                onClick={() => setShowPostModal(true)}
                                className="flex-1 py-3.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
                            >
                                <Share2 className="w-5 h-5" />
                                Share
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="text-center mt-8 text-gray-500 text-sm">
                <div className="flex flex-col items-center justify-center gap-1">
                    <a href="https://www.mentorsmantra.co.in" target="_blank" rel="noopener noreferrer" className="hover:text-indigo-600 transition-colors font-medium">
                        www.mentorsmantra.co.in
                    </a>
                    <p>Contact: 9821040290 / 7982387231</p>
                    <p className="text-gray-400 mt-2 italic">A Mentors Mantra Product</p>
                </div>
            </div>
        </div>

            {/* Post Modal */ }
    {
        result?.shared_pdf_id && (
            <PostModal
                isOpen={showPostModal}
                onClose={() => setShowPostModal(false)}
                sharedPdfId={result.shared_pdf_id}
                pdfFilename={result.pdf_filename || `${subject} - ${topic}`}
                subject={subject}
                topic={topic}
                level={level}
                token={localStorage.getItem('token') || ''}
                onSuccess={() => {
                    // Optional: refresh feed or show success toast
                }}
            />
        )
    }

    {/* Username Modal */ }
    <UsernameModal
        isOpen={showUsernameModal}
        onClose={() => setShowUsernameModal(false)}
        token={localStorage.getItem('token') || ''}
        currentUsername={user?.username}
        onSuccess={(newUsername) => {
            refreshUser();
            setShowUsernameModal(false);
        }}
    />
        </div >
    );
}
