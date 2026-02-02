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
    Share2,
    ChevronDown,
    Keyboard,
    List
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { logError } from "@/lib/logger";
import PostModal from "@/components/PostModal";
import UsernameModal from "@/components/UsernameModal";
import { searchChapters, getChaptersForSubject, searchMultipleSubjects, getChaptersForMultipleSubjects, detectSubjectFromQuery } from "@/lib/ncert-chapters";

// API base URL
const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ||
    "https://mentors-mantra-api-87253755436.us-central1.run.app";



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

interface HistoryItem {
    id: string;
    subject: string;
    topic: string;
    level: string;
    question_count: number;
    pdf_filename: string | null;
    status: string;
    created_at: string;
}

export default function TestGenerator() {
    const { user, token, isLoading: authLoading, isAuthenticated, logout, authFetch, refreshUser } = useAuth();
    const router = useRouter();

    const [subject, setSubject] = useState<string[]>(["Physics"]);
    const [topic, setTopic] = useState("");
    const [questionCount, setQuestionCount] = useState(20);
    const [level, setLevel] = useState("JEE Mains");
    // Difficulty percentage distribution
    const [easyPercent, setEasyPercent] = useState(20);
    const [mediumPercent, setMediumPercent] = useState(50);
    const [hardPercent, setHardPercent] = useState(30);
    const [numMCQs, setNumMCQs] = useState(20);
    const [numNumericals, setNumNumericals] = useState(5);
    // GATE Pattern state
    const [gatePaper, setGatePaper] = useState("CSE");
    const [numMSQ, setNumMSQ] = useState(0);
    const [numNAT, setNumNAT] = useState(0);
    const [numGA, setNumGA] = useState(10); // Standard is 10, but user can change

    // CBSE Pattern state (for CBSE Board level)
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
    // Removed isDetectingSubject state as we use local detection now
    const [elapsedTime, setElapsedTime] = useState(0);
    const [progressStep, setProgressStep] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [progressMessage, setProgressMessage] = useState<string>("Ready to generate...");
    const [showPostModal, setShowPostModal] = useState(false);
    const [showUsernameModal, setShowUsernameModal] = useState(false);

    // NCERT Chapter Dropdown State
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [isCustomMode, setIsCustomMode] = useState(false);
    const [filteredChapters, setFilteredChapters] = useState<{ class: string; name: string; matchedTopic?: string }[]>([]);
    const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
    const [searchQuery, setSearchQuery] = useState(''); // Separate search from topic
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Existing Tests Check
    const [existingTestCount, setExistingTestCount] = useState<number>(0);

    // History (Last 3 PDFs)
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const checkTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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
        { name: "CBSE Board", icon: GraduationCap, color: "text-emerald-400", bgColor: "bg-emerald-500/20", borderColor: "border-emerald-500" },
        { name: "JEE Mains", icon: Target, color: "text-blue-400", bgColor: "bg-blue-500/20", borderColor: "border-blue-500" },
        { name: "JEE Advanced", icon: Award, color: "text-purple-400", bgColor: "bg-purple-500/20", borderColor: "border-purple-500" },
        { name: "Olympiad", icon: Trophy, color: "text-yellow-400", bgColor: "bg-yellow-500/20", borderColor: "border-yellow-500" },
        { name: "NEET", icon: Stethoscope, color: "text-pink-400", bgColor: "bg-pink-500/20", borderColor: "border-pink-500" },
    ];

    // Difficulty levels (kept for reference, now using percentage inputs)

    // Smart level filtering based on subject
    const getAvailableLevels = () => {
        if (subject.includes("Maths") && !subject.includes("Zoology") && !subject.includes("Botany")) {
            // Maths only (or with Physics/Chem) -> NO NEET
            return allLevels.filter(l => l.name !== "NEET");
        }
        if ((subject.includes("Zoology") || subject.includes("Botany")) && !subject.includes("Maths")) {
            // Biology subjects -> NEET Only
            return allLevels.filter(l => l.name === "NEET");
        }
        // If Just Physics/Chemistry -> All options
        // If Mixed (Maths + Bio) -> Show All (User responsibility? or Intersection?) 
        // Let's return allLevels if mixed, or maybe restrict? 
        // Simplest: If ANY Bio -> Show NEET. If ANY Maths -> Show JEE. 
        // If both present, show both?
        return allLevels;
    };


    const levels = getAvailableLevels();

    // Update split when level changes
    useEffect(() => {
        if (level === "NEET") {
            setNumMCQs(questionCount);
            setNumNumericals(0);
        } else if (level === "CBSE Board") {
            // CBSE Board uses subjective questions - set defaults
            setCbseVeryShort(4);
            setCbseShort(4);
            setCbseLong(2);
            setCbseCaseBased(1);
            setCbseNumericals(4);
            // Set MCQ/Numerical to 0 since we use CBSE-specific counts
            setNumMCQs(0);
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
            setLevel(availableLevelNames[0] || "CBSE Board");
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
            fetchHistory();
        }
    }, [isAuthenticated]);

    // Fetch history (Last 3 PDFs)
    const fetchHistory = async () => {
        if (!token) return;
        setHistoryLoading(true);
        try {
            const response = await authFetch(`${API_BASE_URL}/api/history`);
            if (response.ok) {
                const data = await response.json();
                setHistory(data.generations || []);
            }
        } catch (error) {
            console.error('Error fetching history:', error);
        } finally {
            setHistoryLoading(false);
        }
    };

    // Auto-detect subject when topic changes (Local Detection)
    useEffect(() => {
        // Only detect if topic has at least 4 characters
        if (topic.trim().length < 4) return;

        // Use local detection
        const detected = detectSubjectFromQuery(topic);
        if (detected.length > 0) {
            setSubject(prev => {
                // Merge new detected subjects
                const newSubjects = [...prev];
                let changed = false;
                detected.forEach(s => {
                    if (!newSubjects.includes(s)) {
                        newSubjects.push(s);
                        changed = true;
                    }
                });
                return changed ? newSubjects : prev;
            });
        }
    }, [topic]);

    // Update filtered chapters when searchQuery or subject changes (NOT topic)
    useEffect(() => {
        const chapters = searchQuery.trim()
            ? searchMultipleSubjects(subject, searchQuery.trim())
            : getChaptersForMultipleSubjects(subject);
        setFilteredChapters(chapters);
    }, [searchQuery, subject]);

    // Check for existing tests when topic/subject/level changes
    useEffect(() => {
        if (checkTimeoutRef.current) clearTimeout(checkTimeoutRef.current);

        if (topic.trim().length < 3) {
            setExistingTestCount(0);
            return;
        }

        checkTimeoutRef.current = setTimeout(async () => {
            try {
                const params = new URLSearchParams({
                    subject: subject.sort().join(', '),
                    level,
                    topic: topic.trim()
                });
                const response = await fetch(`${API_BASE_URL}/api/posts/check-existing?${params}`);
                if (response.ok) {
                    const data = await response.json();
                    setExistingTestCount(data.count);
                }
            } catch (err) {
                console.error("Failed to check existing tests:", err);
            }
        }, 800); // 800ms debounce

        return () => {
            if (checkTimeoutRef.current) clearTimeout(checkTimeoutRef.current);
        };
    }, [topic, subject, level]);

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

        // Validate difficulty distribution sums to 100%
        const totalPercent = easyPercent + mediumPercent + hardPercent;
        if (totalPercent !== 100) {
            setError(`Difficulty distribution should be equal to 100% (currently ${totalPercent}%)`);
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
                        metadata_info: JSON.stringify({ level, subject, easyPercent, mediumPercent, hardPercent })
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

            if (level === "CBSE Board") {
                // For CBSE Board: combine CBSE pattern with subjective questions
                // Very Short + Short + Long + Case-Based questions
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
                    subject: level === "GATE" ? gatePaper : subject.sort().join(', '), // Use GATE paper as subject or joined string
                    topic: topic.trim(),
                    total_questions: requestTotal,
                    level,
                    easy_percent: easyPercent,
                    medium_percent: mediumPercent,
                    hard_percent: hardPercent,
                    num_mcqs: requestMcqs,
                    num_numerical: requestNumericals,
                    include_solutions: includeSolutions,
                    // GATE Params
                    gate_paper: level === "GATE" ? gatePaper : undefined,
                    num_msq: level === "GATE" || level === "JEE Advanced" ? (level === "JEE Advanced" ? jeeMulti : numMSQ) : undefined,
                    num_nat: level === "GATE" ? numNAT : undefined,
                    num_ga: level === "GATE" ? numGA : undefined,
                    // CBSE Board Params
                    cbse_vsa: level === "CBSE Board" ? cbseVeryShort : undefined,
                    cbse_sa: level === "CBSE Board" ? cbseShort : undefined,
                    cbse_la: level === "CBSE Board" ? cbseLong : undefined,
                    cbse_case: level === "CBSE Board" ? cbseCaseBased : undefined,
                    cbse_numerical: level === "CBSE Board" ? cbseNumericals : undefined,
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
                metadata_info: JSON.stringify({ level, subject: subject.join(', '), topic })
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
            let filename = result.pdf_filename || 'test_paper.pdf';
            if (!filename.toLowerCase().endsWith('.pdf')) {
                filename += '.pdf';
            }
            a.download = filename;
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
                {/* Topic Input with NCERT Chapter Dropdown */}
                <div className="mb-6 relative" ref={dropdownRef}>
                    <label htmlFor="topic" className="block mb-3 font-medium text-gray-700 dark:text-gray-300">
                        Topic <span className="text-xs text-gray-400 font-normal">(Select from NCERT or type custom)</span>
                    </label>

                    {/* Selected chapters tags */}
                    {selectedChapters.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-2">
                            {selectedChapters.map((chapter, idx) => (
                                <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs rounded-full">
                                    {chapter}
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const newSelected = selectedChapters.filter((_, i) => i !== idx);
                                            setSelectedChapters(newSelected);
                                            setTopic(newSelected.join(', '));
                                        }}
                                        className="hover:text-red-500 ml-1"
                                    >
                                        ×
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}

                    <div className="relative">
                        <input
                            type="text"
                            id="topic"
                            value={searchQuery}
                            onChange={(e) => {
                                const val = e.target.value;
                                setSearchQuery(val);
                                if (isCustomMode) {
                                    setTopic(val);
                                } else {
                                    setIsDropdownOpen(true);
                                }
                            }}
                            onFocus={() => {
                                if (!isCustomMode) {
                                    setIsDropdownOpen(true);
                                    // Initialize chapters list on focus
                                    const chapters = searchQuery.trim()
                                        ? searchMultipleSubjects(subject, searchQuery.trim())
                                        : getChaptersForMultipleSubjects(subject);
                                    setFilteredChapters(chapters);
                                }
                            }}
                            placeholder={isCustomMode ? "Type your custom topic here..." : (selectedChapters.length > 0 ? "Search for more chapters..." : "Select from NCERT or switch to custom")}
                            className="w-full px-4 py-3 pr-20 bg-white dark:bg-black border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900"
                            disabled={isLoading}
                            autoComplete="off"
                        />
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                            {/* Toggle Mode Button */}
                            <button
                                type="button"
                                onClick={() => {
                                    const newMode = !isCustomMode;
                                    setIsCustomMode(newMode);
                                    if (newMode) {
                                        setIsDropdownOpen(false);
                                        setTopic(searchQuery); // Sync search query to topic immediately
                                    } else {
                                        // Switching back to NCERT mode
                                        setTopic(selectedChapters.join(', '));
                                        // If there was custom text that isn't a chapter, search query remains
                                    }
                                }}
                                className="p-1.5 text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                                title={isCustomMode ? "Switch to NCERT Selection" : "Switch to Custom Input"}
                            >
                                {isCustomMode ? <List className="w-5 h-5" /> : <Keyboard className="w-5 h-5" />}
                            </button>

                            {/* Dropdown Chevron (Only in NCERT Mode) */}
                            {!isCustomMode && (
                                <button
                                    type="button"
                                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                    className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                    disabled={isLoading}
                                >
                                    <ChevronDown className={`w-5 h-5 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
                                </button>
                            )}
                        </div>
                    </div>


                    {/* Existing Tests Alert */}
                    {existingTestCount > 0 && !isLoading && (
                        <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl flex items-center justify-between animate-in fade-in slide-in-from-top-2 duration-300">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                                    <Sparkles className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                                        Found {existingTestCount} existing {existingTestCount === 1 ? 'test' : 'tests'}!
                                    </h3>
                                    <p className="text-xs text-gray-600 dark:text-gray-400">
                                        Save time & credits by using an existing test.
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => {
                                    const params = new URLSearchParams();
                                    params.set('q', topic);
                                    params.set('subject', subject.join(', '));
                                    params.set('level', level);
                                    // Navigate to feed with filters
                                    router.push(`/posts?${params.toString()}`);
                                }}
                                className="px-4 py-2 bg-white dark:bg-black border border-amber-200 dark:border-amber-700 text-amber-700 dark:text-amber-400 text-sm font-medium rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors shrink-0 whitespace-nowrap"
                            >
                                View in Community →
                            </button>
                        </div>
                    )}

                    {/* Dropdown Menu - Multi-Select with Checkboxes */}
                    {isDropdownOpen && filteredChapters.length > 0 && (
                        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-[#16181c] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                            {/* Quick Select All Buttons */}
                            <div className="sticky top-0 z-10 bg-white dark:bg-[#16181c] border-b border-gray-200 dark:border-gray-700 p-2">
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const class11Chapters = filteredChapters
                                                .filter(c => c.class === 'Class 11')
                                                .map(c => c.matchedTopic || c.name);
                                            const allSelected = class11Chapters.every(c => selectedChapters.includes(c));
                                            let newSelected: string[];
                                            if (allSelected) {
                                                newSelected = selectedChapters.filter(c => !class11Chapters.includes(c));
                                            } else {
                                                newSelected = [...new Set([...selectedChapters, ...class11Chapters])];
                                            }
                                            setSelectedChapters(newSelected);
                                            setTopic(newSelected.join(', '));
                                        }}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${filteredChapters.filter(c => c.class === 'Class 11').length > 0 && filteredChapters.filter(c => c.class === 'Class 11').every(c => selectedChapters.includes(c.matchedTopic || c.name))
                                            ? 'bg-indigo-600 text-white border-indigo-600'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'
                                            }`}
                                    >
                                        📚 All Class 11
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const class12Chapters = filteredChapters
                                                .filter(c => c.class === 'Class 12')
                                                .map(c => c.matchedTopic || c.name);
                                            const allSelected = class12Chapters.every(c => selectedChapters.includes(c));
                                            let newSelected: string[];
                                            if (allSelected) {
                                                newSelected = selectedChapters.filter(c => !class12Chapters.includes(c));
                                            } else {
                                                newSelected = [...new Set([...selectedChapters, ...class12Chapters])];
                                            }
                                            setSelectedChapters(newSelected);
                                            setTopic(newSelected.join(', '));
                                        }}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${filteredChapters.filter(c => c.class === 'Class 12').length > 0 && filteredChapters.filter(c => c.class === 'Class 12').every(c => selectedChapters.includes(c.matchedTopic || c.name))
                                            ? 'bg-indigo-600 text-white border-indigo-600'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'
                                            }`}
                                    >
                                        📚 All Class 12
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const allChapters = filteredChapters.map(c => c.matchedTopic || c.name);
                                            const allSelected = allChapters.every(c => selectedChapters.includes(c));
                                            let newSelected: string[];
                                            if (allSelected) {
                                                newSelected = [];
                                            } else {
                                                newSelected = [...new Set(allChapters)];
                                            }
                                            setSelectedChapters(newSelected);
                                            setTopic(newSelected.join(', '));
                                        }}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${filteredChapters.length > 0 && filteredChapters.every(c => selectedChapters.includes(c.matchedTopic || c.name))
                                            ? 'bg-purple-600 text-white border-purple-600'
                                            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                                            }`}
                                    >
                                        🎯 All 11 + 12
                                    </button>
                                </div>
                            </div>
                            {/* Selected count header */}
                            {selectedChapters.length > 0 && (
                                <div className="px-3 py-2 bg-indigo-50 dark:bg-indigo-900/30 text-xs font-medium text-indigo-600 dark:text-indigo-400 flex justify-between items-center border-b border-indigo-200 dark:border-indigo-800">
                                    <span>{selectedChapters.length} chapter(s) selected</span>
                                    <button
                                        onClick={() => {
                                            setSelectedChapters([]);
                                            setTopic('');
                                        }}
                                        className="text-red-500 hover:text-red-600 text-xs"
                                    >
                                        Clear all
                                    </button>
                                </div>
                            )}
                            {/* Group by class */}
                            {['Class 11', 'Class 12'].map((className) => {
                                const classChapters = filteredChapters.filter(c => c.class === className);
                                if (classChapters.length === 0) return null;

                                return (
                                    <div key={className}>
                                        <div className="sticky top-0 px-3 py-2 bg-gray-100 dark:bg-gray-800 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                                            {className}
                                        </div>
                                        {classChapters.map((chapter, idx) => {
                                            const chapterKey = chapter.matchedTopic || chapter.name;
                                            const isSelected = selectedChapters.includes(chapterKey);
                                            return (
                                                <button
                                                    key={`${className}-${chapter.name}-${idx}`}
                                                    type="button"
                                                    onClick={() => {
                                                        let newSelected: string[];
                                                        if (isSelected) {
                                                            newSelected = selectedChapters.filter(c => c !== chapterKey);
                                                        } else {
                                                            newSelected = [...selectedChapters, chapterKey];
                                                        }
                                                        setSelectedChapters(newSelected);
                                                        // Update topic with all selected chapters
                                                        setTopic(newSelected.join(', '));
                                                    }}
                                                    className={`w-full px-4 py-2.5 text-left hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-gray-700 dark:text-gray-200 text-sm transition-colors flex items-center gap-3 ${isSelected ? 'bg-indigo-50 dark:bg-indigo-900/30' : ''}`}
                                                >
                                                    {/* Checkbox */}
                                                    <div className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 ${isSelected ? 'bg-indigo-600 border-indigo-600' : 'border-gray-300 dark:border-gray-600'}`}>
                                                        {isSelected && (
                                                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                                            </svg>
                                                        )}
                                                    </div>
                                                    <span className="truncate flex-1">
                                                        {chapter.name}
                                                        {chapter.matchedTopic && chapter.matchedTopic !== chapter.name && (
                                                            <span className="text-indigo-500 dark:text-indigo-400 text-xs ml-2">
                                                                → {chapter.matchedTopic}
                                                            </span>
                                                        )}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    {/* No results message */}
                    {isDropdownOpen && topic.trim() && filteredChapters.length === 0 && (
                        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-[#16181c] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 text-center">
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                No NCERT chapters match &quot;{topic}&quot;
                            </p>
                            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                You can use this as a custom topic
                            </p>
                        </div>
                    )}
                </div>

                {/* Click outside to close dropdown */}
                {isDropdownOpen && (
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => setIsDropdownOpen(false)}
                    />
                )}

                {/* Subject Selection - Hide for GATE */}
                {level !== "GATE" && (
                    <div className="mb-3 md:mb-4">
                        <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">Select Subject</label>
                        <div className="grid grid-cols-3 gap-2">
                            {subjects.map((sub) => {
                                const IconComponent = sub.icon;
                                const isSelected = subject.includes(sub.name);
                                return (
                                    <button
                                        key={sub.name}
                                        onClick={() => {
                                            if (isSelected) {
                                                if (subject.length > 1) {
                                                    setSubject(prev => prev.filter(s => s !== sub.name));
                                                }
                                            } else {
                                                setSubject(prev => [...prev, sub.name]);
                                            }
                                        }}
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

                {/* Difficulty Percentage Distribution */}
                <div className="mb-3 md:mb-4">
                    <label className="block mb-2 font-medium text-gray-700 dark:text-gray-300 text-sm">
                        Difficulty Distribution
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                            (Total: {easyPercent + mediumPercent + hardPercent}%)
                        </span>
                        {easyPercent + mediumPercent + hardPercent !== 100 && (
                            <span className="ml-2 text-xs text-red-500">Must equal 100%</span>
                        )}
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                        <div className="relative">
                            <label className="block text-xs text-green-600 dark:text-green-400 mb-1 font-medium">Easy %</label>
                            <input
                                type="number"
                                min="0"
                                max="100"
                                value={easyPercent}
                                onChange={(e) => {
                                    const val = Math.min(100, Math.max(0, parseInt(e.target.value) || 0));
                                    setEasyPercent(val);
                                    // Auto-fill hard percentage
                                    const remaining = 100 - val - mediumPercent;
                                    if (remaining >= 0) setHardPercent(remaining);
                                }}
                                disabled={isLoading}
                                className="w-full p-2 text-center rounded-xl border border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 focus:outline-none focus:ring-2 focus:ring-green-500 text-sm font-medium"
                            />
                        </div>
                        <div className="relative">
                            <label className="block text-xs text-green-600 dark:text-green-400 mb-1 font-medium">Medium %</label>
                            <input
                                type="number"
                                min="0"
                                max="100"
                                value={mediumPercent}
                                onChange={(e) => {
                                    const val = Math.min(100, Math.max(0, parseInt(e.target.value) || 0));
                                    setMediumPercent(val);
                                    // Auto-fill hard percentage
                                    const remaining = 100 - easyPercent - val;
                                    if (remaining >= 0) setHardPercent(remaining);
                                }}
                                disabled={isLoading}
                                className="w-full p-2 text-center rounded-xl border border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 focus:outline-none focus:ring-2 focus:ring-green-500 text-sm font-medium"
                            />
                        </div>
                        <div className="relative">
                            <label className="block text-xs text-green-600 dark:text-green-400 mb-1 font-medium">Hard %</label>
                            <input
                                type="number"
                                min="0"
                                max="100"
                                value={hardPercent}
                                onChange={(e) => {
                                    const val = Math.min(100, Math.max(0, parseInt(e.target.value) || 0));
                                    setHardPercent(val);
                                    // Adjust easy/medium if needed? No, usually hard is the last one adjusted.
                                    // Or simply set it.
                                }}
                                disabled={isLoading}
                                className="w-full p-2 text-center rounded-xl border border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 focus:outline-none focus:ring-2 focus:ring-green-500 text-sm font-medium"
                            />
                        </div>
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
                            {level === "CBSE Board" ? "CBSE Board Pattern" : `${level} Pattern`}
                        </span>
                        <span className="text-xs text-gray-400">
                            Total: {level === "CBSE Board"
                                ? cbseVeryShort + cbseShort + cbseLong + cbseCaseBased + cbseNumericals
                                : level === "GATE"
                                    ? numGA + numMCQs + numMSQ + numNAT
                                    : level === "JEE Advanced"
                                        ? jeeSingle + jeeMulti + jeeInteger
                                        : numMCQs + numNumericals} (max 50)
                        </span>
                    </div>

                    {/* CBSE Board Pattern */}
                    {level === "CBSE Board" && (
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
                    disabled={isLoading || !topic.trim() || (rateLimit?.remaining === 0)}
                    className={`w-full py-2.5 md:py-4 rounded-lg md:rounded-xl text-white font-semibold text-[11px] md:text-lg shadow-lg transition-all duration-300 flex items-center justify-center gap-1.5 md:gap-2 mb-4 btn-primary ${isLoading || !topic.trim() || (rateLimit?.remaining === 0)
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
                                <span>Generate {level} Test Paper</span>
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
                                        {level === "CBSE Board" ? (
                                            `${cbseVeryShort + cbseShort + cbseLong + cbseCaseBased} Theory + ${cbseNumericals} Numerical Questions`
                                        ) : (
                                            `${result.total_mcq} MCQs + ${result.total_numerical} Numerical Questions`
                                        )}
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

                {/* Recent Tests History */}
                {history.length > 0 && (
                    <div className="mt-8 p-5 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-100 dark:border-gray-700">
                        <div className="flex items-center gap-2 mb-4">
                            <Clock className="w-5 h-5 text-indigo-500" />
                            <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200">Recent Tests</h3>
                        </div>
                        <div className="space-y-3">
                            {history.map((item) => (
                                <div
                                    key={item.id}
                                    className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700"
                                >
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-gray-800 dark:text-gray-200 truncate">
                                            {item.topic}
                                        </p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            {item.subject} • {item.level} • {item.question_count} Qs
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {item.status === 'COMPLETED' && item.pdf_filename ? (
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                                                <CheckCircle2 className="w-3 h-3 mr-1" />
                                                Ready
                                            </span>
                                        ) : item.status === 'PENDING' || item.status === 'PROCESSING' ? (
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                                In Progress
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                                                <AlertCircle className="w-3 h-3 mr-1" />
                                                Failed
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

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
                        pdfFilename={result.pdf_filename || `${subject.join(', ')} - ${topic}`}
                        subject={subject.join(', ')}
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
