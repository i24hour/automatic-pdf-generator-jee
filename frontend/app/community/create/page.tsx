"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Sparkles, AlertCircle, ChevronLeft } from "lucide-react";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import { useCommunityApi } from "@/lib/community-api";

export default function CreatePublicTestPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile View */}
            <div className="md:hidden pb-20 p-4">
                <CreateForm />
                <MobileNav />
            </div>

            {/* Desktop View */}
            <div className="hidden md:flex min-h-screen max-w-[1300px] mx-auto">
                <DesktopSidebar />
                <main className="flex-1 ml-[275px] min-h-screen p-8">
                    <div className="max-w-2xl mx-auto">
                        <CreateForm />
                    </div>
                </main>
            </div>
        </div>
    );
}

function CreateForm() {
    const router = useRouter();
    const api = useCommunityApi();

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    // Form State
    const [topic, setTopic] = useState("");
    const [subject, setSubject] = useState("Physics");
    const [level, setLevel] = useState("JEE Mains");
    const [difficulty, setDifficulty] = useState("Medium");
    const [questionCount, setQuestionCount] = useState(15);
    const [duration, setDuration] = useState(30);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (!topic.trim()) {
            setError("Please enter a topic");
            return;
        }

        setLoading(true);
        try {
            const result = await api.createTest({
                subject,
                topic,
                total_questions: questionCount,
                level,
                difficulty,
                duration_minutes: duration
            });

            router.push(`/community/test/${result.id}`);
        } catch (err: any) {
            console.error(err);
            setError(err.message || "Failed to generate test. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <button
                onClick={() => router.back()}
                className="flex items-center gap-2 text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
                <ChevronLeft className="w-4 h-4" />
                Back to Community
            </button>

            <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-3">
                    <Sparkles className="w-8 h-8 text-indigo-500" />
                    Create Public Test
                </h1>
                <p className="text-gray-500 dark:text-gray-400">
                    Generate a new test using AI and share it with the community.
                </p>
            </div>

            <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-gray-200 dark:border-[#333] p-6 shadow-sm">
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Topic Input */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Topic / Concept *
                        </label>
                        <input
                            type="text"
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            placeholder="e.g. Rotational Motion, Organic Chemistry, Calculus"
                            className="w-full px-4 py-3 bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white transition-all"
                            required
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Subject */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Subject</label>
                            <select
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                                className="w-full px-4 py-3 bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white cursor-pointer"
                            >
                                {["Physics", "Chemistry", "Maths", "Biology"].map(s => (
                                    <option key={s} value={s}>{s}</option>
                                ))}
                            </select>
                        </div>

                        {/* Level */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Exam Level</label>
                            <select
                                value={level}
                                onChange={(e) => setLevel(e.target.value)}
                                className="w-full px-4 py-3 bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white cursor-pointer"
                            >
                                {["JEE Mains", "JEE Advanced", "NEET", "CBSE Board"].map(l => (
                                    <option key={l} value={l}>{l}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Difficulty */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Difficulty</label>
                            <select
                                value={difficulty}
                                onChange={(e) => setDifficulty(e.target.value)}
                                className="w-full px-4 py-3 bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white cursor-pointer"
                            >
                                <option value="Easy">Easy</option>
                                <option value="Medium">Medium</option>
                                <option value="Hard">Hard</option>
                            </select>
                        </div>

                        {/* Question Count */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Questions: <span className="text-indigo-600 font-bold">{questionCount}</span>
                            </label>
                            <input
                                type="range"
                                min="5"
                                max="50"
                                step="5"
                                value={questionCount}
                                onChange={(e) => {
                                    const val = parseInt(e.target.value);
                                    setQuestionCount(val);
                                    setDuration(Math.ceil(val * 2)); // Auto calc duration (2 min/q)
                                }}
                                className="w-full accent-indigo-600"
                            />
                        </div>
                    </div>

                    {/* Duration Input (Manual Override) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Duration (Minutes)
                        </label>
                        <input
                            type="number"
                            min="5"
                            max="180"
                            value={duration}
                            onChange={(e) => setDuration(parseInt(e.target.value))}
                            className="w-full px-4 py-3 bg-gray-50 dark:bg-[#111] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white"
                        />
                    </div>

                    {error && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl flex items-start gap-3 text-sm">
                            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <p>{error}</p>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-lg transition-all shadow-lg shadow-indigo-500/30 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="w-6 h-6 animate-spin" />
                                Generating Questions...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-6 h-6" />
                                Generate & Publish Test
                            </>
                        )}
                    </button>

                    <p className="text-xs text-center text-gray-500 dark:text-gray-400 mt-4">
                        This uses AI to generate unique questions. It may take 10-20 seconds.
                    </p>
                </form>
            </div>
        </div>
    );
}
