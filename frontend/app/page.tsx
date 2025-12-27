"use client";

import { useState, useRef, useEffect } from "react";
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
  X,
  LogOut,
  Clock,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GenerateResponse {
  success: boolean;
  message: string;
  pdf_filename?: string;
  total_mcq: number;
  total_numerical: number;
  rate_limit_remaining: number;
  rate_limit_reset_hours: number;
}

interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset_hours: number;
  used: number;
}

export default function Home() {
  const { user, token, isLoading: authLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  const [subject, setSubject] = useState("Physics");
  const [topic, setTopic] = useState("");
  const [questionCount, setQuestionCount] = useState(20);
  const [level, setLevel] = useState("JEE Mains");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rateLimit, setRateLimit] = useState<RateLimitInfo | null>(null);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const subjects = [
    { name: "Physics", icon: Atom },
    { name: "Chemistry", icon: FlaskConical },
    { name: "Maths", icon: Calculator },
  ];

  const levels = [
    { name: "Boards", icon: GraduationCap, color: "text-green-400", bgColor: "bg-green-500/20", borderColor: "border-green-500" },
    { name: "JEE Mains", icon: Target, color: "text-blue-400", bgColor: "bg-blue-500/20", borderColor: "border-blue-500" },
    { name: "JEE Advanced", icon: Award, color: "text-purple-400", bgColor: "bg-purple-500/20", borderColor: "border-purple-500" },
    { name: "Olympiad", icon: Trophy, color: "text-yellow-400", bgColor: "bg-yellow-500/20", borderColor: "border-yellow-500" },
  ];

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Fetch rate limit on mount and after generation
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchRateLimit();
    }
  }, [isAuthenticated, token]);

  const fetchRateLimit = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/rate-limit`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setRateLimit(data);
      }
    } catch (err) {
      console.error("Failed to fetch rate limit:", err);
    }
  };

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError("Please enter a topic");
      return;
    }

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          subject,
          topic: topic.trim(),
          total_questions: questionCount,
          level,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate test paper");
      }

      const data: GenerateResponse = await response.json();
      setResult(data);

      // Update rate limit from response
      setRateLimit((prev) => prev ? {
        ...prev,
        remaining: data.rate_limit_remaining,
        reset_hours: data.rate_limit_reset_hours,
        used: prev.limit - data.rate_limit_remaining,
      } : null);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError("Generation cancelled");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong");
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleDownload = () => {
    if (result?.pdf_filename) {
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
      const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
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
      <main className="min-h-screen flex items-center justify-center py-12 px-4 bg-[#FAF9F6]">
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
                onClick={() => window.location.reload()}
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
    <main className="min-h-screen py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* User Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white font-semibold">
              {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U"}
            </div>
            <div>
              <p className="text-sm text-gray-400">Welcome back,</p>
              <p className="font-medium">{user?.name || user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-sm">Logout</span>
          </button>
        </div>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 mb-6 float-animation pulse-glow">
            <BookOpen className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="gradient-text">Mentors Mantra</span>
          </h1>
          <p className="text-xl text-gray-400">AI-Powered Test Paper Generator</p>
        </div>

        {/* Rate Limit Badge */}
        {rateLimit && (
          <div className="flex justify-center mb-6">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm ${rateLimit.remaining > 0
              ? "bg-green-500/20 text-green-400 border border-green-500/30"
              : "bg-red-500/20 text-red-400 border border-red-500/30"
              }`}>
              <Clock className="w-4 h-4" />
              <span>
                {rateLimit.remaining}/{rateLimit.limit} generations remaining
              </span>
              {rateLimit.reset_hours > 0 && (
                <span className="text-gray-400">
                  • Resets in {rateLimit.reset_hours.toFixed(1)}h
                </span>
              )}
            </div>
          </div>
        )}

        {/* Main Card */}
        <div className="glass-card p-8">
          {/* Subject Selection */}
          <div className="mb-6">
            <label className="form-label">Select Subject</label>
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
                      ? "border-indigo-500 bg-indigo-500/20 text-indigo-400"
                      : "border-gray-700 hover:border-gray-600 text-gray-400 hover:text-gray-300"
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
            <label className="form-label">Select Level</label>
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
                      ? `${lvl.borderColor} ${lvl.bgColor} ${lvl.color}`
                      : "border-gray-700 hover:border-gray-600 text-gray-400 hover:text-gray-300"
                      } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <IconComponent className="w-5 h-5" />
                    <span className="text-xs font-medium text-center">{lvl.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Topic Input */}
          <div className="mb-6">
            <label htmlFor="topic" className="form-label">Topic</label>
            <input
              type="text"
              id="topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Electrostatics, Organic Chemistry, Integration"
              className="form-input"
              disabled={isLoading}
            />
          </div>

          {/* Question Count */}
          <div className="mb-8">
            <label htmlFor="questionCount" className="form-label">
              Number of Questions:{" "}
              <span className="text-indigo-400 font-semibold">{questionCount}</span>
            </label>
            <input
              type="range"
              id="questionCount"
              min={5}
              max={50}
              value={questionCount}
              onChange={(e) => setQuestionCount(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              disabled={isLoading}
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>5</span>
              <span>50</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              <Zap className="w-3 h-3 inline mr-1" />
              Split: ~{Math.round(questionCount * 0.8)} MCQs + ~{Math.round(questionCount * 0.2)} Numerical
            </p>
          </div>

          {/* Generate/Cancel Buttons */}
          {isLoading ? (
            <div className="flex gap-3">
              <button disabled className="btn-primary flex-1 opacity-75">
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating {level} Paper...
              </button>
              <button onClick={handleCancel} className="btn-cancel px-6">
                <X className="w-5 h-5" />
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={!topic.trim() || (rateLimit && rateLimit.remaining === 0)}
              className="btn-primary w-full"
            >
              <Sparkles className="w-5 h-5" />
              Generate {level} Test Paper
            </button>
          )}

          {/* Rate limit exceeded message */}
          {rateLimit && rateLimit.remaining === 0 && !isLoading && (
            <div className="error-message mt-4">
              <Clock className="w-5 h-5 flex-shrink-0" />
              <span>Rate limit reached. Try again in {rateLimit.reset_hours.toFixed(1)} hours.</span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="error-message mt-6">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Success Message */}
          {result?.success && (
            <div className="mt-6 space-y-4">
              <div className="success-message">
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                <div>
                  <p className="font-medium">{result.message}</p>
                  <p className="text-sm opacity-80">
                    {result.total_mcq} MCQs + {result.total_numerical} Numerical Questions
                  </p>
                </div>
              </div>
              <button onClick={handleDownload} className="btn-secondary w-full">
                <Download className="w-5 h-5" />
                Download PDF
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-500 text-sm">
          <p className="flex items-center justify-center gap-2">
            <FileText className="w-4 h-4" />
            Powered by AI • Formatted for JEE
          </p>
        </div>
      </div>
    </main>
  );
}
