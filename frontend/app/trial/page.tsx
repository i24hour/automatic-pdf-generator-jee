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
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GenerateResponse {
  success: boolean;
  message: string;
  pdf_filename?: string;
  pdf_base64?: string;
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

export default function TrialPage() {
  const { user, isLoading: authLoading, isAuthenticated, logout, authFetch, refreshUser } = useAuth();
  const router = useRouter();

  const [subject, setSubject] = useState("Physics");
  const [topic, setTopic] = useState("");
  const [questionCount, setQuestionCount] = useState(20);
  const [level, setLevel] = useState("JEE Mains");
  const [difficulty, setDifficulty] = useState("Medium");
  const [numMCQs, setNumMCQs] = useState(16);
  const [numNumericals, setNumNumericals] = useState(4);
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
  const abortControllerRef = useRef<AbortController | null>(null);

  const subjects = [
    { name: "Physics", icon: Atom },
    { name: "Chemistry", icon: FlaskConical },
    { name: "Maths", icon: Calculator },
    { name: "Zoology", icon: Dna },
    { name: "Botany", icon: Leaf },
  ];

  const allLevels = [
    { name: "CBSE Board", icon: GraduationCap, color: "text-emerald-400", bgColor: "bg-emerald-500/20", borderColor: "border-emerald-500" },
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
      // Zoology and Botany are only for NEET (no CBSE Board for biology subjects)
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
      <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-white">
        <div className="max-w-md w-full text-center">
          <div className="bg-white border border-gray-200 rounded-2xl p-10 shadow-lg">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100 flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-amber-600" />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">Verify Your Email</h1>
            <p className="text-gray-500 mb-6">
              We&apos;ve sent a verification email to <strong>{user.email}</strong>.
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
    <main className="min-h-screen py-12 px-4 bg-white">
      <div className="max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-semibold">
              {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U"}
            </div>
            <div>
              <p className="text-sm text-gray-500">Welcome back,</p>
              <p className="font-medium text-gray-900">{user?.name || user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-sm">Logout</span>
          </button>
        </div>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-indigo-600 mb-6">
            <BookOpen className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
            INFINITEST
          </h1>
          <div className="flex items-center justify-center gap-2 text-xl text-gray-500 font-medium">
            <span>Trained by IITians</span>
            <span className="text-gray-300">•</span>
            <span>NEET Rankers</span>
          </div>
          {/* TRIAL Badge */}
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-100 text-orange-700 border border-orange-200 text-sm font-medium">
            <Sparkles className="w-4 h-4" />
            TRIAL: Answer Verification Enabled
          </div>
        </div>

        {/* Rate Limit Badge */}
        {rateLimit && (
          <div className="flex justify-center mb-6">
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
        <div className="flex justify-center mb-6">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Gift className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Enter promo code"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                className="pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent w-48"
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
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-lg">
          {/* Subject Selection */}
          <div className="mb-6">
            <label className="block mb-3 font-medium text-gray-700">Select Subject</label>
            <div className="grid grid-cols-3 gap-3">
              {subjects.map((sub) => {
                const IconComponent = sub.icon;
                const isSelected = subject === sub.name;
                return (
                  <button
                    key={sub.name}
                    onClick={() => setSubject(sub.name)}
                    disabled={isLoading}
                    className={`p-4 rounded-xl border transition-all duration-300 flex flex-col items-center gap-2 ${isSelected
                      ? "border-indigo-500 bg-indigo-50 text-indigo-600"
                      : "border-gray-200 hover:border-gray-300 text-gray-600 hover:text-gray-800 bg-white"
                      } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <IconComponent className="w-6 h-6" />
                    <span className="text-sm font-medium">{sub.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Level Selection */}
          <div className="mb-6">
            <label className="block mb-3 font-medium text-gray-700">Select Exam Type</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {levels.map((lvl) => {
                const IconComponent = lvl.icon;
                const isSelected = level === lvl.name;
                return (
                  <button
                    key={lvl.name}
                    onClick={() => setLevel(lvl.name)}
                    disabled={isLoading}
                    className={`p-3 rounded-xl border transition-all duration-300 flex flex-col items-center gap-2 ${isSelected
                      ? "border-indigo-500 bg-indigo-50 text-indigo-600"
                      : "border-gray-200 hover:border-gray-300 text-gray-600 hover:text-gray-800 bg-white"
                      } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <IconComponent className="w-5 h-5" />
                    <span className="text-xs font-medium text-center">{lvl.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Difficulty Selection */}
          <div className="mb-6">
            <label className="block mb-3 font-medium text-gray-700">Select Difficulty</label>
            <div className="grid grid-cols-3 gap-3">
              {difficulties.map((diff) => {
                const isSelected = difficulty === diff.name;
                return (
                  <button
                    key={diff.name}
                    onClick={() => setDifficulty(diff.name)}
                    disabled={isLoading}
                    className={`p-3 rounded-xl border transition-all duration-300 flex items-center justify-center gap-2 ${isSelected
                      ? `${diff.borderColor} ${diff.bgColor} ${diff.color}`
                      : "border-gray-200 hover:border-gray-300 text-gray-600 hover:text-gray-800 bg-white"
                      } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <span className="text-sm font-medium">{diff.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Topic Input */}
          <div className="mb-6">
            <label htmlFor="topic" className="block mb-3 font-medium text-gray-700">Topic</label>
            <input
              type="text"
              id="topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Electrostatics, Organic Chemistry, Integration"
              className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              disabled={isLoading}
            />
          </div>

          {/* Question Count */}
          <div className="mb-8">
            <label htmlFor="questionCount" className="block mb-3 font-medium text-gray-700">
              Number of Questions:{" "}
              <span className="text-indigo-600 font-semibold">{questionCount}</span>
            </label>
            <input
              type="range"
              id="questionCount"
              min={5}
              max={50}
              value={questionCount}
              onChange={(e) => handleSliderChange(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              disabled={isLoading}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>5</span>
              <span>50</span>
            </div>
          </div>

          {/* Question Split Inputs */}
          <div className="grid grid-cols-2 gap-4 mb-8">
            <div>
              <label className="block mb-2 text-sm font-medium text-gray-700">MCQs (80%)</label>
              <input
                type="number"
                value={numMCQs}
                onChange={(e) => handleSplitChange('mcq', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                min={0}
                disabled={isLoading}
              />
            </div>
            <div>
              <label className="block mb-2 text-sm font-medium text-gray-700">Numerical (20%)</label>
              <input
                type="number"
                value={numNumericals}
                onChange={(e) => handleSplitChange('numerical', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                min={0}
                disabled={isLoading || level === "NEET"}
              />
              {level === "NEET" && <p className="text-xs text-gray-500 mt-1">Not available for NEET</p>}
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={isLoading || !topic.trim() || !!(rateLimit && rateLimit.remaining === 0)}
            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating... (this may take 30-60s)
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Generate {level} ({difficulty}) Test Paper
              </>
            )}
          </button>

          {/* Cancel Button - shows during loading */}
          {isLoading && (
            <button
              onClick={handleCancelGeneration}
              className="w-full py-2.5 mt-2 bg-gray-100 hover:bg-red-50 text-gray-700 hover:text-red-600 font-medium rounded-lg transition-colors flex items-center justify-center gap-2 border border-gray-200 hover:border-red-200"
            >
              <X className="w-4 h-4" />
              Cancel Generation
            </button>
          )}

          {/* Rate limit exceeded message */}
          {rateLimit && rateLimit.remaining === 0 && !isLoading && (
            <div className="flex items-center gap-2 text-amber-700 text-sm bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mt-4">
              <Clock className="w-5 h-5 flex-shrink-0" />
              <span>Rate limit reached. Try again in {rateLimit.reset_hours.toFixed(1)} hours.</span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3 mt-6">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
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



              <button onClick={handleDownload} className="w-full py-3.5 border-2 border-indigo-600 text-indigo-600 font-medium rounded-lg hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2">
                <Download className="w-5 h-5" />
                Download PDF
              </button>
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
    </main>
  );
}
