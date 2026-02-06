"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles, BookOpen, AlertCircle, ChevronLeft, CheckCircle2 } from "lucide-react";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import { useCommunityApi } from "@/lib/community-api";

// --- Types Reuse (Ideally shared) ---
interface DifficultyDist {
    easy: number;
    medium: number;
    hard: number;
}

interface SubjectConfig {
    enabled: boolean;
    count: number;
    difficulty: DifficultyDist;
    topics: string;
}

type ExamType = 'JEE_MAINS' | 'JEE_ADV' | 'NEET' | 'CUSTOM';

const DEFAULT_DIFFICULTY: DifficultyDist = { easy: 3, medium: 4, hard: 3 };

const INITIAL_SUBJECTS: Record<string, SubjectConfig> = {
    'Physics': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Chemistry': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Maths': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Biology': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Botany': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Zoology': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
};

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
                    <div className="max-w-4xl mx-auto">
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

    const [examType, setExamType] = useState<ExamType>('JEE_MAINS');
    const [subjects, setSubjects] = useState<Record<string, SubjectConfig>>(INITIAL_SUBJECTS);
    const [duration, setDuration] = useState(60);

    // Update defaults based on exam type
    useEffect(() => {
        setSubjects(prev => {
            const next = { ...prev };
            if (examType === 'NEET') {
                next['Maths'].enabled = false;
                next['Biology'].enabled = false; // Usually split into Botany/Zoology in this app
                next['Botany'].enabled = true;
                next['Zoology'].enabled = true;

                next['Physics'].count = 10;
                next['Physics'].enabled = true;
                next['Chemistry'].count = 10;
                next['Chemistry'].enabled = true;
                next['Botany'].count = 10;
                next['Zoology'].count = 10;
            } else {
                next['Maths'].enabled = true;
                next['Maths'].count = 10;
                next['Physics'].enabled = true;
                next['Physics'].count = 10;
                next['Chemistry'].enabled = true;
                next['Chemistry'].count = 10;

                next['Biology'].enabled = false;
                next['Botany'].enabled = false;
                next['Zoology'].enabled = false;
            }
            return next;
        });
    }, [examType]);

    const handleSubjectChange = (subject: string, field: keyof SubjectConfig, value: any) => {
        setSubjects(prev => ({
            ...prev,
            [subject]: { ...prev[subject], [field]: value }
        }));
    };

    const handleDifficultyChange = (subject: string, type: keyof DifficultyDist, value: number) => {
        setSubjects(prev => {
            const currentDist = { ...prev[subject].difficulty };
            currentDist[type] = Math.max(0, value);

            const newTotal = currentDist.easy + currentDist.medium + currentDist.hard;

            return {
                ...prev,
                [subject]: {
                    ...prev[subject],
                    difficulty: currentDist,
                    count: newTotal
                }
            };
        });
    };

    const totalQuestions = Object.values(subjects)
        .filter(s => s.enabled)
        .reduce((sum, s) => sum + s.count, 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (totalQuestions < 1) {
            setError("Please add at least one question.");
            return;
        }

        setLoading(true);
        try {
            // Prepare payload for public test creation
            const subjectInputs: Record<string, any> = {};

            for (const [subj, config] of Object.entries(subjects)) {
                if (!config.enabled || config.count <= 0) continue;

                subjectInputs[subj] = {
                    count: config.count,
                    difficulty: config.difficulty,
                    topics: config.topics.split(',').map(t => t.trim()).filter(Boolean)
                };
            }

            const payload = {
                exam_type: examType,
                subject_inputs: subjectInputs,
                duration_minutes: duration
            };

            const result = await api.createTest(payload);
            router.push(`/community/test/${result.id}`);
        } catch (err: any) {
            console.error(err);
            if (err.detail && Array.isArray(err.detail)) {
                setError(err.detail.map((e: any) => e.msg).join(', '));
            } else if (err.detail && typeof err.detail === 'string') {
                setError(err.detail);
            } else {
                setError(err.message || "Failed to generate test. Please try again.");
            }
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
                    Design a comprehensive test and share it with the community.
                </p>
            </div>

            <div className="bg-white dark:bg-[#1a1a1a] rounded-2xl border border-gray-200 dark:border-[#333] p-6 shadow-sm">
                <form onSubmit={handleSubmit} className="space-y-8">

                    {/* 1. General Config */}
                    <div className="grid md:grid-cols-2 gap-8">
                        {/* Exam Type */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Exam Type</label>
                            <div className="grid grid-cols-2 gap-2">
                                {(['JEE_MAINS', 'JEE_ADV', 'NEET', 'CUSTOM'] as ExamType[]).map((type) => (
                                    <button
                                        key={type}
                                        type="button"
                                        onClick={() => setExamType(type)}
                                        className={`py-2 px-3 rounded-lg border font-medium text-sm transition-all ${examType === type
                                            ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-indigo-300'
                                            }`}
                                    >
                                        {type.replace('_', ' ')}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Duration */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Duration</label>
                            <div className="flex flex-wrap gap-2">
                                {[30, 60, 90, 120, 180].map((mins) => (
                                    <button
                                        key={mins}
                                        type="button"
                                        onClick={() => setDuration(mins)}
                                        className={`px-4 py-2 rounded-lg border font-medium text-sm transition-all ${duration === mins
                                            ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-indigo-300'
                                            }`}
                                    >
                                        {mins}m
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="border-t border-gray-100 dark:border-gray-800 pt-6"></div>

                    {/* 2. Subject Config */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white">Subject Configuration</h2>

                        {Object.entries(subjects).map(([subject, config]) => (
                            config.enabled && (
                                <div key={subject} className="bg-gray-50 dark:bg-[#111] rounded-xl border border-gray-200 dark:border-[#333] p-6">
                                    <div className="flex flex-col md:flex-row gap-6">
                                        {/* Subject Summary */}
                                        <div className="md:w-1/4 space-y-2">
                                            <div className="flex items-center gap-2">
                                                <BookOpen className="w-5 h-5 text-indigo-500" />
                                                <h3 className="font-bold text-lg text-gray-900 dark:text-white">{subject}</h3>
                                            </div>
                                            <p className="text-3xl font-bold font-mono text-indigo-600">
                                                {config.count}
                                                <span className="text-sm font-normal text-gray-500 ml-1">qs</span>
                                            </p>
                                        </div>

                                        {/* Controls */}
                                        <div className="md:w-3/4 grid md:grid-cols-2 gap-6 md:pl-6 md:border-l border-gray-200 dark:border-gray-700">
                                            {/* Topics */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    Topics <span className="text-gray-400 font-normal">(Optional)</span>
                                                </label>
                                                <textarea
                                                    value={config.topics}
                                                    onChange={(e) => handleSubjectChange(subject, 'topics', e.target.value)}
                                                    placeholder={`e.g. ${subject === 'Physics' ? 'Optics, Mechanics' : 'Organic, Electrochemistry'}`}
                                                    className="w-full h-24 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-white dark:bg-[#0a0b0d] focus:ring-2 focus:ring-indigo-500 resize-none"
                                                />
                                            </div>

                                            {/* Difficulty */}
                                            <div className="space-y-3">
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty Distribution</label>
                                                <div className="grid grid-cols-3 gap-2">
                                                    <div>
                                                        <label className="block text-xs text-green-600 font-medium mb-1">Easy</label>
                                                        <input type="number" min="0" value={config.difficulty.easy} onChange={(e) => handleDifficultyChange(subject, 'easy', Number(e.target.value))} className="w-full px-2 py-1 text-sm border rounded bg-white dark:bg-black" />
                                                    </div>
                                                    <div>
                                                        <label className="block text-xs text-yellow-600 font-medium mb-1">Med</label>
                                                        <input type="number" min="0" value={config.difficulty.medium} onChange={(e) => handleDifficultyChange(subject, 'medium', Number(e.target.value))} className="w-full px-2 py-1 text-sm border rounded bg-white dark:bg-black" />
                                                    </div>
                                                    <div>
                                                        <label className="block text-xs text-red-600 font-medium mb-1">Hard</label>
                                                        <input type="number" min="0" value={config.difficulty.hard} onChange={(e) => handleDifficultyChange(subject, 'hard', Number(e.target.value))} className="w-full px-2 py-1 text-sm border rounded bg-white dark:bg-black" />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )
                        ))}
                    </div>

                    {error && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl flex items-start gap-3 text-sm">
                            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <p>{error}</p>
                        </div>
                    )}

                    <div className="flex items-center justify-between pt-6 border-t border-gray-100 dark:border-gray-800">
                        <div className="flex gap-8">
                            <div>
                                <span className="text-gray-500 text-xs uppercase tracking-wider">Total Qs</span>
                                <p className="text-2xl font-bold">{totalQuestions}</p>
                            </div>
                            <div>
                                <span className="text-gray-500 text-xs uppercase tracking-wider">Marks</span>
                                <p className="text-2xl font-bold text-indigo-600">{totalQuestions * 4}</p>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading || totalQuestions < 1}
                            className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Creating Public Test...
                                </>
                            ) : (
                                <>
                                    <CheckCircle2 className="w-5 h-5" />
                                    Create Test
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
