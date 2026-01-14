"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
    Building2,
    Loader2,
    Download,
    CheckCircle2,
    AlertCircle,
    LogOut,
    User,
    Sparkles,
    BookOpen,
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChapterClassification {
    chapter: string;
    subject: string;
}

interface GenerateResponse {
    success: boolean;
    message: string;
    pdf_filename?: string;
    chapters_classified: ChapterClassification[];
    verification_stats?: {
        total_numerical: number;
        verified: number;
        corrected: number;
    };
}

interface InstituteUser {
    id: string;
    email: string;
    institute_name?: string;
    contact_number?: string;
    institute_email?: string;
}

const EXAM_LIMITS = {
    Mains: { Physics: 25, Chemistry: 25, Maths: 25 },
    NEET: { Physics: 45, Chemistry: 45, Zoology: 45, Botany: 45 },
    Advanced: { Physics: 18, Chemistry: 18, Maths: 18 },
};

export default function InstitutePage() {
    const router = useRouter();
    const [user, setUser] = useState<InstituteUser | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<GenerateResponse | null>(null);

    // Form state
    const [chapters, setChapters] = useState("");
    const [examType, setExamType] = useState<"Mains" | "NEET" | "Advanced">("Mains");
    const [difficulty, setDifficulty] = useState("Medium");
    const [physicsCount, setPhysicsCount] = useState(25);
    const [chemistryCount, setChemistryCount] = useState(25);
    const [mathsCount, setMathsCount] = useState(25);
    const [zoologyCount, setZoologyCount] = useState(45);
    const [botanyCount, setBotanyCount] = useState(45);

    useEffect(() => {
        const storedUser = localStorage.getItem("institute_user");
        const token = localStorage.getItem("institute_access_token");

        if (!storedUser || !token) {
            router.push("/institute/login");
            return;
        }

        setUser(JSON.parse(storedUser));
    }, [router]);

    useEffect(() => {
        // Update default counts when exam type changes
        const limits = EXAM_LIMITS[examType];
        setPhysicsCount(limits.Physics);
        setChemistryCount(limits.Chemistry);
        if (examType === "NEET") {
            setZoologyCount(limits.Zoology);
            setBotanyCount(limits.Botany);
        } else {
            setMathsCount(limits.Maths);
        }
    }, [examType]);

    const handleLogout = () => {
        localStorage.removeItem("institute_access_token");
        localStorage.removeItem("institute_refresh_token");
        localStorage.removeItem("institute_user");
        router.push("/institute/login");
    };

    const handleGenerate = async () => {
        if (!chapters.trim()) {
            setError("Please enter at least one chapter");
            return;
        }

        setIsLoading(true);
        setError(null);
        setResult(null);

        const token = localStorage.getItem("institute_access_token");

        try {
            const chapterList = chapters.split(",").map(c => c.trim()).filter(c => c);

            const requestBody: Record<string, unknown> = {
                chapters: chapterList,
                exam_type: examType,
                difficulty,
                physics_count: physicsCount,
                chemistry_count: chemistryCount,
            };

            if (examType === "NEET") {
                requestBody.zoology_count = zoologyCount;
                requestBody.botany_count = botanyCount;
            } else {
                requestBody.maths_count = mathsCount;
            }

            const response = await fetch(`${API_BASE_URL}/api/institute/generate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Generation failed");
            }

            const data: GenerateResponse = await response.json();
            setResult(data);
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("An unknown error occurred");
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleDownload = () => {
        if (result?.pdf_filename) {
            window.open(`${API_BASE_URL}/api/download/${result.pdf_filename}`, "_blank");
        }
    };

    if (!user) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-white animate-spin" />
            </div>
        );
    }

    const limits = EXAM_LIMITS[examType];

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-4 md:p-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center">
                            <Building2 className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-white">INFINITEST</h1>
                            <p className="text-gray-400 text-sm">Institute Portal</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => router.push("/institute/profile")}
                            className="p-2 text-gray-400 hover:text-white transition-colors"
                        >
                            <User className="w-5 h-5" />
                        </button>
                        <button
                            onClick={handleLogout}
                            className="p-2 text-gray-400 hover:text-white transition-colors"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Main Card */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 md:p-8 border border-white/20">
                    <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                        <BookOpen className="w-5 h-5" />
                        Generate Multi-Subject Test
                    </h2>

                    {/* Chapters Input */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Chapters (comma-separated)
                        </label>
                        <textarea
                            value={chapters}
                            onChange={(e) => setChapters(e.target.value)}
                            className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[100px]"
                            placeholder="e.g., Electrostatics, Magnetism, Solutions, Chemical Bonding, Sequences and Series"
                        />
                        <p className="text-gray-400 text-xs mt-1">
                            AI will automatically detect subjects for each chapter
                        </p>
                    </div>

                    {/* Exam Type */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Exam Type
                        </label>
                        <div className="grid grid-cols-3 gap-3">
                            {(["Mains", "NEET", "Advanced"] as const).map((exam) => (
                                <button
                                    key={exam}
                                    onClick={() => setExamType(exam)}
                                    className={`p-3 rounded-lg border transition-all ${examType === exam
                                            ? "bg-indigo-600 border-indigo-500 text-white"
                                            : "bg-white/5 border-white/20 text-gray-300 hover:border-white/40"
                                        }`}
                                >
                                    {exam}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Difficulty */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Difficulty
                        </label>
                        <div className="grid grid-cols-3 gap-3">
                            {["Easy", "Medium", "Hard"].map((d) => (
                                <button
                                    key={d}
                                    onClick={() => setDifficulty(d)}
                                    className={`p-3 rounded-lg border transition-all ${difficulty === d
                                            ? "bg-green-600 border-green-500 text-white"
                                            : "bg-white/5 border-white/20 text-gray-300 hover:border-white/40"
                                        }`}
                                >
                                    {d}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Question Counts */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Questions per Subject
                        </label>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                                <label className="text-xs text-gray-400">Physics (max {limits.Physics})</label>
                                <input
                                    type="number"
                                    min={0}
                                    max={limits.Physics}
                                    value={physicsCount}
                                    onChange={(e) => setPhysicsCount(Math.min(Number(e.target.value), limits.Physics))}
                                    className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-gray-400">Chemistry (max {limits.Chemistry})</label>
                                <input
                                    type="number"
                                    min={0}
                                    max={limits.Chemistry}
                                    value={chemistryCount}
                                    onChange={(e) => setChemistryCount(Math.min(Number(e.target.value), limits.Chemistry))}
                                    className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                />
                            </div>
                            {examType === "NEET" ? (
                                <>
                                    <div>
                                        <label className="text-xs text-gray-400">Zoology (max {limits.Zoology})</label>
                                        <input
                                            type="number"
                                            min={0}
                                            max={limits.Zoology}
                                            value={zoologyCount}
                                            onChange={(e) => setZoologyCount(Math.min(Number(e.target.value), limits.Zoology))}
                                            className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs text-gray-400">Botany (max {limits.Botany})</label>
                                        <input
                                            type="number"
                                            min={0}
                                            max={limits.Botany}
                                            value={botanyCount}
                                            onChange={(e) => setBotanyCount(Math.min(Number(e.target.value), limits.Botany))}
                                            className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        />
                                    </div>
                                </>
                            ) : (
                                <div>
                                    <label className="text-xs text-gray-400">Maths (max {limits.Maths})</label>
                                    <input
                                        type="number"
                                        min={0}
                                        max={limits.Maths}
                                        value={mathsCount}
                                        onChange={(e) => setMathsCount(Math.min(Number(e.target.value), limits.Maths))}
                                        className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Generate Button */}
                    <button
                        onClick={handleGenerate}
                        disabled={isLoading}
                        className="w-full py-4 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Generating Test Paper...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-5 h-5" />
                                Generate {examType} Test Paper
                            </>
                        )}
                    </button>

                    {/* Error */}
                    {error && (
                        <div className="mt-4 flex items-center gap-2 text-red-400 text-sm bg-red-400/10 rounded-lg p-3">
                            <AlertCircle className="w-4 h-4" />
                            {error}
                        </div>
                    )}

                    {/* Success */}
                    {result?.success && (
                        <div className="mt-6 space-y-4">
                            <div className="flex items-start gap-3 text-green-400 bg-green-400/10 border border-green-400/20 rounded-lg px-4 py-3">
                                <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-medium">{result.message}</p>
                                    <p className="text-sm text-green-300">
                                        AI classified {result.chapters_classified.length} chapters
                                    </p>
                                </div>
                            </div>

                            {/* Chapter Classifications */}
                            <div className="bg-white/5 rounded-lg p-4">
                                <p className="text-sm text-gray-400 mb-2">Chapter Classifications:</p>
                                <div className="flex flex-wrap gap-2">
                                    {result.chapters_classified.map((cc, i) => (
                                        <span
                                            key={i}
                                            className="px-2 py-1 rounded-full text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                                        >
                                            {cc.chapter}: {cc.subject}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Verification Stats */}
                            {result.verification_stats && result.verification_stats.total_numerical > 0 && (
                                <div className="flex items-start gap-3 text-blue-400 bg-blue-400/10 border border-blue-400/20 rounded-lg px-4 py-3">
                                    <Sparkles className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                    <div>
                                        <p className="font-medium">Answer Verification Complete</p>
                                        <p className="text-sm text-blue-300">
                                            {result.verification_stats.verified} numerical answers verified
                                            {result.verification_stats.corrected > 0 && (
                                                <span className="text-orange-400 ml-1">
                                                    ({result.verification_stats.corrected} corrected)
                                                </span>
                                            )}
                                        </p>
                                    </div>
                                </div>
                            )}

                            <button
                                onClick={handleDownload}
                                className="w-full py-3 border-2 border-indigo-500 text-indigo-400 font-medium rounded-lg hover:bg-indigo-500/10 transition-colors flex items-center justify-center gap-2"
                            >
                                <Download className="w-5 h-5" />
                                Download PDF
                            </button>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <p className="text-center text-gray-500 text-sm mt-6">
                    INFINITEST - A Mentors Mantra Product
                </p>
            </div>
        </div>
    );
}
