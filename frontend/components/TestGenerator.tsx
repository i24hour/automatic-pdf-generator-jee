"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
    FileText,
    Sparkles,
    Download,
    Loader2,
    Infinity as InfinityIcon,
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
    Share2
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { logError } from "@/lib/logger";
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
    const { user, token, isLoading: authLoading, isAuthenticated, logout, authFetch, refreshUser } = useAuth();
    const router = useRouter();

    const [subject, setSubject] = useState("Physics");
    const [topic, setTopic] = useState("");
    const [questionCount, setQuestionCount] = useState(20);
    const [level, setLevel] = useState("JEE Mains");
    const [difficulty, setDifficulty] = useState("Medium");
    const [numMCQs, setNumMCQs] = useState(20);
    const [numNumericals, setNumNumericals] = useState(5);
    // GATE Pattern state
    const [gatePaper, setGatePaper] = useState("CSE");
    const [numMSQ, setNumMSQ] = useState(0);
    const [numNAT, setNumNAT] = useState(0);
    const [numGA, setNumGA] = useState(10); // Standard is 10, but user can change

    // CBSE Pattern state (for Boards level)
    const [cbseVeryShort, setCbseVeryShort] = useState(4);
    const [cbseShort, setCbseShort] = useState(4);
    const [cbseLong, setCbseLong] = useState(2);
    const [cbseCaseBased, setCbseCaseBased] = useState(1);
    const [cbseNumericals, setCbseNumericals] = useState(4);

    // JEE Advanced Pattern state
    const [jeeSingle, setJeeSingle] = useState(10);
    const [jeeMulti, setJeeMulti] = useState(5);
    const [jeeInteger, setJeeInteger] = useState(5);

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
    const eventSourceRef = useRef<EventSource | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [progressMessage, setProgressMessage] = useState<string>("Ready to generate...");
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

    const gatePapers = [
        { name: "CSE", label: "Computer Science (CS)" },
        { name: "DA", label: "Data Science & AI (DA)" },
        { name: "ECE", label: "Electronics (EC)" },
        { name: "EE", label: "Electrical (EE)" },
        { name: "ME", label: "Mechanical (ME)" },
        { name: "CE", label: "Civil (CE)" },
        { name: "IN", label: "Instrumentation (IN)" },
    ];

    const allLevels = [
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
            // Zoology and Botany are only for NEET (Boards removed)
            return allLevels.filter(l => l.name === "NEET");
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

        setIsLoading(true);
        setError(null);
        setResult(null);
        setElapsedTime(0);
        setProgressStep(0);
        setProgressMessage("Starting generation...");
        setJobId(null);

        // Start timer
        // Start timer with 10-minute timeout check
        timerRef.current = setInterval(() => {
            setElapsedTime(prev => {
                if (prev >= 600) { // 600 seconds = 10 minutes
                    if (timerRef.current) clearInterval(timerRef.current);
                    cleanupGeneration();
                    setError("Generation timed out (limit: 10 mins). Please try again.");

                    // Log timeout error
                    logError({
                        error_type: "GENERATION_TIMEOUT",
                        error_details: `Generation timed out after 600s for topic: ${topic}`,
                        metadata_info: JSON.stringify({ level, subject, difficulty })
                    });

                    return prev;
                }
                return prev + 1;
            });
        }, 1000);

        try {
            // Calculate question counts based on level

            let requestMcqs = numMCQs;
            let requestNumericals = numNumericals;
            let requestTotal = questionCount;

            if (level === "Boards") {
                // For Boards: combine CBSE pattern
                // Very Short + Short + Long + Case-Based = MCQ-style (text answers)
                // Numericals stay as numericals
                requestMcqs = cbseVeryShort + cbseShort + cbseLong + cbseCaseBased;
                requestNumericals = cbseNumericals;
                requestTotal = requestMcqs + requestNumericals;
            } else if (level === "GATE") {
                // For GATE: combine all types
                requestMcqs = numMCQs; // Single correct MCQs
                requestNumericals = numNAT; // NATs are numericals
                requestTotal = numGA + numMCQs + numMSQ + numNAT;
            } else if (level === "JEE Advanced") {
                // For JEE Advanced: combine Single + Multi as MCQs, Integer as Numerical
                requestMcqs = jeeSingle + jeeMulti;
                requestNumericals = jeeInteger;
                requestTotal = requestMcqs + requestNumericals;
            }

            // Step 1: Start the job
            const startResponse = await authFetch(`${API_BASE_URL}/api/generate-sse/start`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    subject: level === "GATE" ? gatePaper : subject, // Use GATE paper as subject
                    topic: topic.trim(),
                    total_questions: requestTotal,
                    level,
                    difficulty,
                    num_mcqs: requestMcqs,
                    num_numerical: requestNumericals,
                    include_solutions: includeSolutions,
                    // GATE Params
                    gate_paper: level === "GATE" ? gatePaper : undefined,
                    num_msq: level === "GATE" || level === "JEE Advanced" ? (level === "JEE Advanced" ? jeeMulti : numMSQ) : undefined,
                    num_nat: level === "GATE" ? numNAT : undefined,
                    num_ga: level === "GATE" ? numGA : undefined,
                    // Boards Params
                    cbse_vsa: level === "Boards" ? cbseVeryShort : undefined,
                    cbse_sa: level === "Boards" ? cbseShort : undefined,
                    cbse_la: level === "Boards" ? cbseLong : undefined,
                    cbse_case: level === "Boards" ? cbseCaseBased : undefined,
                }),
            });

            if (!startResponse.ok) {
                const errorData = await startResponse.json();
                throw new Error(errorData.detail || "Failed to start generation");
            }

            const startData = await startResponse.json();
            const newJobId = startData.job_id;
            setJobId(newJobId);
            setProgressMessage("Connecting to progress stream...");

            // Step 2: Connect to SSE stream
            await connectToSSEStream(newJobId);

        } catch (err: unknown) {
            console.error("Generation error:", err);

            // Log generation error
            logError({
                error_type: "GENERATION_ERROR",
                error_details: err instanceof Error ? err.message : "Unknown generation error",
                metadata_info: JSON.stringify({ level, subject, topic })
            });

            if (err instanceof Error && err.message.includes("Rate limit")) {
                setError(err.message);
            } else {
                setError("Failed to generate test paper. Please try again.");
            }
            cleanupGeneration();
        }
    };

    const connectToSSEStream = (streamJobId: string): Promise<void> => {
        return new Promise((resolve, reject) => {
            // Close any existing connection
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }

            // SSE URL with token as query param (EventSource doesn't support headers)
            // Use localStorage to ensure we have the FRESH refreshed token
            const freshToken = localStorage.getItem("auth_token") || token;
            const sseUrl = `${API_BASE_URL}/api/generate-sse/${streamJobId}/stream?token=${encodeURIComponent(freshToken || '')}`;

            const eventSource = new EventSource(sseUrl);
            eventSourceRef.current = eventSource;

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log("SSE update:", data);

                    // Update progress
                    setProgressStep(data.progress || 0);
                    setProgressMessage(data.message || "Working...");

                    // Map status to progress step for visual
                    const statusToStep: Record<string, number> = {
                        "pending": 0,
                        "analyzing": 1,
                        "generating_mcqs": 2,
                        "generating_numericals": 3,
                        "verifying": 4,
                        "compiling_pdf": 5,
                        "uploading": 5,
                        "done": 6,
                        "failed": 0,
                    };
                    if (data.status in statusToStep) {
                        setProgressStep(statusToStep[data.status]);
                    }

                    // Check if done
                    if (data.status === "done" && data.result) {
                        setResult(data.result as GenerateResponse);
                        if (data.result.rate_limit_remaining !== undefined) {
                            setRateLimit((prev) => prev ? {
                                ...prev,
                                remaining: data.result.rate_limit_remaining,
                                used: prev.limit - data.result.rate_limit_remaining,
                            } : null);
                        }
                        cleanupGeneration();
                        resolve();
                    } else if (data.status === "failed") {
                        setError(data.error || "Generation failed");
                        cleanupGeneration();
                        reject(new Error(data.error || "Generation failed"));
                    }
                } catch (e) {
                    console.error("Error parsing SSE data:", e);
                }
            };

            eventSource.onerror = async (error) => {
                console.error("SSE connection error:", error);
                eventSource.close();

                // Try to reconnect
                setProgressMessage("Connection interrupted, reconnecting...");

                try {
                    // Wait a bit before reconnecting
                    await new Promise(r => setTimeout(r, 2000));

                    // Poll the status endpoint
                    const statusResponse = await authFetch(`${API_BASE_URL}/api/generate-sse/${streamJobId}/status`);

                    if (statusResponse.ok) {
                        const statusData = await statusResponse.json();

                        if (statusData.status === "done" && statusData.result) {
                            setResult(statusData.result as GenerateResponse);
                            cleanupGeneration();
                            resolve();
                            return;
                        } else if (statusData.status === "failed") {
                            setError(statusData.error || "Generation failed");
                            cleanupGeneration();
                            reject(new Error(statusData.error));
                            return;
                        }

                        // Job still in progress, reconnect to stream
                        setProgressMessage("Reconnecting to stream...");
                        await connectToSSEStream(streamJobId);
                        resolve();
                    } else {
                        throw new Error("Failed to get job status");
                    }
                } catch (reconnectError) {
                    console.error("Reconnection failed:", reconnectError);
                    setError("Connection lost. Please try again.");
                    cleanupGeneration();
                    reject(reconnectError);
                }
            };
        });
    };

    const cleanupGeneration = () => {
        setIsLoading(false);
        if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    };

    const handleCancelGeneration = () => {
        cleanupGeneration();
        setError("Generation cancelled.");
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
            <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-white dark:bg-black">
                <div className="max-w-md w-full text-center">
                    <div className="bg-white/80 backdrop-blur-xl dark:bg-[#16181c] border border-gray-200 dark:border-[#2f3336] rounded-2xl p-10 shadow-lg">
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
        <div className="w-full min-h-screen md:min-h-0 bg-white dark:bg-black pb-16 md:pb-0">
            <div className="max-w-2xl mx-auto px-4">
                {/* Mobile Header with Logout */}
                <div className="md:hidden flex justify-end px-4 pt-4">
                    <button
                        onClick={logout}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                    >
                        <LogOut className="w-4 h-4" />
                        <span>Logout</span>
                    </button>
                </div>

                {/* Header */}
                <div className="text-center mb-4 md:mb-8 pt-2 md:pt-0">
                    <div className="inline-flex items-center justify-center w-14 h-14 md:w-20 md:h-20 rounded-2xl bg-indigo-600 mb-3 md:mb-6">
                        <InfinityIcon className="w-7 h-7 md:w-10 md:h-10 text-white" />
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
                {/* Topic Input - Moved to Top */}
                <div className="mb-6">
                    <label htmlFor="topic" className="block mb-3 font-medium text-gray-700 dark:text-gray-300">Topic</label>
                    <input
                        type="text"
                        id="topic"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g., Electrostatics, Organic Chemistry, Integration"

                        className="w-full px-4 py-3 bg-white dark:bg-black border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900"
                        disabled={isLoading}
                    />
                </div>

                {/* Subject Selection - Hide for GATE */}
                {level !== "GATE" && (
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
                )}

                {/* GATE Paper Selection */}
                {level === "GATE" && (
                    <div className="mb-3 md:mb-4">
                        <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">Select GATE Paper</label>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {gatePapers.map((paper) => {
                                const isSelected = gatePaper === paper.name;
                                return (
                                    <button
                                        key={paper.name}
                                        onClick={() => setGatePaper(paper.name)}
                                        disabled={isLoading}
                                        className={`p-2 rounded-xl border transition-all duration-300 flex flex-col items-center gap-1 ${isSelected
                                            ? "border-orange-500 bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400"
                                            : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 bg-white dark:bg-[#16181c]"
                                            } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                                    >
                                        <span className="text-sm font-bold">{paper.name}</span>
                                        <span className="text-[10px] text-center opacity-70">{paper.label.split('(')[0]}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}

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
                        <span className="text-xs text-gray-400">
                            Total: {level === "Boards"
                                ? cbseVeryShort + cbseShort + cbseLong + cbseCaseBased + cbseNumericals
                                : level === "GATE"
                                    ? numGA + numMCQs + numMSQ + numNAT
                                    : level === "JEE Advanced"
                                        ? jeeSingle + jeeMulti + jeeInteger
                                        : numMCQs + numNumericals} (max 50)
                        </span>
                    </div>

                    {/* Boards Pattern */}
                    {level === "Boards" && (
                        <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="relative">
                                    <input
                                        type="number"
                                        min={0}
                                        max={20}
                                        value={cbseVeryShort}
                                        onChange={(e) => setCbseVeryShort(parseInt(e.target.value) || 0)}
                                        disabled={isLoading}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Very Short Answer (1-2M)
                                    </label>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        min={0}
                                        max={20}
                                        value={cbseShort}
                                        onChange={(e) => setCbseShort(parseInt(e.target.value) || 0)}
                                        disabled={isLoading}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Short Answer (2-3M)
                                    </label>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        min={0}
                                        max={20}
                                        value={cbseLong}
                                        onChange={(e) => setCbseLong(parseInt(e.target.value) || 0)}
                                        disabled={isLoading}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Long Answer (5M)
                                    </label>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        min={0}
                                        max={20}
                                        value={cbseCaseBased}
                                        onChange={(e) => setCbseCaseBased(parseInt(e.target.value) || 0)}
                                        disabled={isLoading}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Case-Based
                                    </label>
                                </div>
                            </div>
                            <div className="relative">
                                <input
                                    type="number"
                                    min={0}
                                    max={20}
                                    value={cbseNumericals}
                                    onChange={(e) => setCbseNumericals(parseInt(e.target.value) || 0)}
                                    disabled={isLoading}
                                    className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                    placeholder=" "
                                />
                                <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
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
                                        value={jeeSingle}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value) || 0;
                                            if (val >= 0 && val + jeeMulti + jeeInteger <= 50) setJeeSingle(val);
                                        }}
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
                                        value={jeeMulti}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value) || 0;
                                            if (val >= 0 && jeeSingle + val + jeeInteger <= 50) setJeeMulti(val);
                                        }}
                                        min={0}
                                        max={20}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Multi Correct
                                    </label>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        value={jeeInteger}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value) || 0;
                                            if (val >= 0 && jeeSingle + jeeMulti + val <= 50) setJeeInteger(val);
                                        }}
                                        min={0}
                                        max={20}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        Integer
                                    </label>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* NEET Pattern - Only MCQs (no numericals) */}
                    {
                        level === "NEET" && (
                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-gray-600 dark:text-gray-400">NEET Pattern (MCQ Only)</span>
                                    <span className="text-xs text-gray-500">Total: {numMCQs} (max 50)</span>
                                </div>
                                <div className="relative">
                                    <input
                                        type="number"
                                        value={numMCQs}
                                        onChange={(e) => {
                                            const val = parseInt(e.target.value) || 0;
                                            if (val >= 0 && val <= 50) setNumMCQs(val);
                                        }}
                                        min={0}
                                        max={50}
                                        disabled={isLoading}
                                        className="peer w-full px-3 pt-5 pb-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white dark:bg-black text-gray-900 dark:text-white"
                                        placeholder=" "
                                    />
                                    <label className="absolute left-3 top-1 text-[10px] text-indigo-600 font-medium">
                                        MCQs
                                    </label>
                                </div>
                                <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                                    NEET is MCQ-only. No numerical questions.
                                </p>
                            </div>
                        )
                    }

                    {/* Olympiad Pattern */}
                    {
                        level === "Olympiad" && (
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
                        )
                    }
                </div >

                {/* Generate Button */}
                < button
                    onClick={handleGenerate}
                    disabled={isLoading || isDetectingSubject || !topic.trim() || (rateLimit?.remaining === 0)}
                    className={`w-full py-2.5 md:py-4 rounded-lg md:rounded-xl text-white font-semibold text-[11px] md:text-lg shadow-lg transition-all duration-300 flex items-center justify-center gap-1.5 md:gap-2 mb-4 btn-primary ${isLoading || isDetectingSubject || !topic.trim() || (rateLimit?.remaining === 0)
                        ? "bg-gray-400 cursor-not-allowed"
                        : "hover:shadow-xl transform hover:-translate-y-0.5"
                        }`}
                >
                    {
                        isLoading ? (
                            <>
                                <Loader2 className="w-4 h-4 md:w-6 md:h-6 animate-spin" />
                                <span>Generating...</span>
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-4 h-4 md:w-6 md:h-6" />
                                <span>Generate {level} ({difficulty}) Test Paper</span>
                            </>
                        )}
                </button >

                {/* Progress Bar */}
                {/* Detailed Loading Steps */}
                {
                    isLoading && (
                        <div className="mb-6 bg-indigo-50 dark:bg-indigo-900/10 rounded-xl p-5 border border-indigo-100 dark:border-indigo-900/30">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-indigo-600 animate-pulse"></div>
                                    <span className="font-semibold text-indigo-900 dark:text-indigo-300">Working...</span>
                                </div>
                                <div className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400 bg-white dark:bg-black px-2 py-1 rounded-lg border border-indigo-100 dark:border-indigo-900/30 text-xs font-mono">
                                    <Clock className="w-3 h-3" />
                                    <span>{Math.floor(elapsedTime / 60)}:{String(elapsedTime % 60).padStart(2, '0')}</span>
                                </div>
                            </div>

                            <div className="space-y-3">
                                {[
                                    { text: "Analyzing topic and difficulty...", start: 0, end: 5 },
                                    { text: "Researching question patterns...", start: 5, end: 12 },
                                    ...(numMCQs > 0 ? [{ text: "Creating MCQ questions...", start: 12, end: 25 }] : []),
                                    ...(numNumericals > 0 ? [{ text: "Generating numerical problems...", start: 25, end: 35 }] : []),
                                    { text: "Verifying answers...", start: 35, end: 42 },
                                    { text: "Formatting PDF document...", start: 42, end: 1000 }
                                ].map((step, index) => {
                                    const isCompleted = elapsedTime > step.end;
                                    const isCurrent = elapsedTime >= step.start && elapsedTime <= step.end;
                                    const isPending = elapsedTime < step.start;

                                    return (
                                        <div key={index} className={`flex items-center gap-3 text-sm transition-all duration-300 ${isPending ? 'opacity-50' : 'opacity-100'}`}>
                                            {isCompleted ? (
                                                <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                                            ) : isCurrent ? (
                                                <Loader2 className="w-5 h-5 text-indigo-600 animate-spin flex-shrink-0" />
                                            ) : (
                                                <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600 flex-shrink-0" />
                                            )}
                                            <span className={`${isCompleted ? 'text-green-700 dark:text-green-400' : isCurrent ? 'text-indigo-700 dark:text-indigo-300 font-medium' : 'text-gray-500 dark:text-gray-400'}`}>
                                                {step.text}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>

                            <button
                                onClick={handleCancelGeneration}
                                className="w-full mt-6 py-2.5 bg-white dark:bg-black border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:text-red-600 hover:border-red-200 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2"
                            >
                                <X className="w-4 h-4" />
                                Cancel Generation
                            </button>
                        </div>
                    )
                }

                {/* Error Message */}
                {
                    error && (
                        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 animate-in fade-in slide-in-from-top-2">
                            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <p>{error}</p>
                        </div>
                    )
                }

                {/* Success Message */}
                {
                    result?.success && (
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

                                {result.shared_pdf_id && (
                                    <button
                                        onClick={() => setShowPostModal(true)}
                                        className="flex-1 py-3.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
                                    >
                                        <Share2 className="w-5 h-5" />
                                        Post
                                    </button>
                                )}
                            </div>
                        </div>
                    )
                }

                {/* Footer */}
                <div className="text-center mt-8 text-gray-500 dark:text-gray-400 text-sm pb-4">
                    <div className="flex flex-col items-center justify-center gap-1">
                        <a href="https://www.mentorsmantra.co.in" target="_blank" rel="noopener noreferrer" className="hover:text-indigo-600 transition-colors font-medium">
                            www.mentorsmantra.co.in
                        </a>
                        <p>Contact: 9821040290 / 7982387231</p>
                        <p className="text-gray-400 dark:text-gray-500 mt-2 italic">A Mentors Mantra Product</p>
                    </div>
                </div>
            </div >

            {/* Post Modal */}
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
                        token={token || ''}
                        onSuccess={() => {
                            // Optional: refresh feed or show success toast
                        }}
                    />
                )
            }

            {/* Username Modal */}
            <UsernameModal
                isOpen={showUsernameModal}
                onClose={() => setShowUsernameModal(false)}
                token={token || ''}
                currentUsername={user?.username}
                onSuccess={(newUsername) => {
                    refreshUser();
                    setShowUsernameModal(false);
                }}
            />
        </div >
    );
}
