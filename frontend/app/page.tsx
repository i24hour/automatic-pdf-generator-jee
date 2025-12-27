"use client";

import { useState, useRef } from "react";
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
} from "lucide-react";

// API base URL - change this for production
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GenerateResponse {
  success: boolean;
  message: string;
  pdf_filename?: string;
  total_mcq: number;
  total_numerical: number;
}

export default function Home() {
  const [subject, setSubject] = useState("Physics");
  const [topic, setTopic] = useState("");
  const [questionCount, setQuestionCount] = useState(20);
  const [level, setLevel] = useState("JEE Mains");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // AbortController for cancelling requests
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

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError("Please enter a topic");
      return;
    }

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
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
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
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

  return (
    <main className="min-h-screen py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-500 mb-6 float-animation pulse-glow">
            <BookOpen className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="gradient-text">Mentors Mantra</span>
          </h1>
          <p className="text-xl text-gray-400">
            AI-Powered Test Paper Generator
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Generate JEE Main/Advanced level test papers instantly
          </p>
        </div>

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
            <label htmlFor="topic" className="form-label">
              Topic
            </label>
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
              <button
                disabled
                className="btn-primary flex-1 opacity-75"
              >
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating {level} Paper...
              </button>
              <button
                onClick={handleCancel}
                className="btn-cancel px-6"
              >
                <X className="w-5 h-5" />
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={!topic.trim()}
              className="btn-primary w-full"
            >
              <Sparkles className="w-5 h-5" />
              Generate {level} Test Paper
            </button>
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
