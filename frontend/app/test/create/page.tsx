'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Minus, Plus, BookOpen, AlertCircle, CheckCircle2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

const DEFAULT_DIFFICULTY: DifficultyDist = { easy: 20, medium: 50, hard: 30 };

const INITIAL_SUBJECTS: Record<string, SubjectConfig> = {
    'Physics': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Chemistry': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Maths': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
    'Biology': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '' },
};

export default function CreateTestPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [examType, setExamType] = useState<ExamType>('JEE_MAINS');
    const [subjects, setSubjects] = useState<Record<string, SubjectConfig>>(INITIAL_SUBJECTS);
    const [duration, setDuration] = useState(60);

    // Update defaults based on exam type
    useEffect(() => {
        setSubjects(prev => {
            const next = { ...prev };
            if (examType === 'NEET') {
                next['Maths'].enabled = false;
                next['Biology'].enabled = true;
                next['Physics'].count = 10;
                next['Chemistry'].count = 10;
                next['Biology'].count = 20;
            } else {
                next['Maths'].enabled = true;
                next['Biology'].enabled = false;
                next['Physics'].count = 10;
                next['Chemistry'].count = 10;
                next['Maths'].count = 10;
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
            currentDist[type] = value;

            // Auto-balance if Easy changes
            if (type === 'easy') {
                const remaining = 100 - value;
                currentDist.medium = Math.round(remaining * 0.6);
                currentDist.hard = 100 - value - currentDist.medium;
            }

            return {
                ...prev,
                [subject]: { ...prev[subject], difficulty: currentDist }
            };
        });
    };

    const totalQuestions = Object.values(subjects)
        .filter(s => s.enabled)
        .reduce((sum, s) => sum + s.count, 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const token = localStorage.getItem('auth_token');
        if (!token) {
            router.push('/login?redirect=/test/create');
            return;
        }

        // Prepare payload
        const subjectInputs: Record<string, any> = {};

        for (const [subj, config] of Object.entries(subjects)) {
            if (!config.enabled || config.count <= 0) continue;

            // Validate difficulty sum
            const diffSum = config.difficulty.easy + config.difficulty.medium + config.difficulty.hard;
            if (diffSum !== 100) {
                setError(`${subj}: Difficulty percentages must sum to 100%`);
                setLoading(false);
                return;
            }

            subjectInputs[subj] = {
                count: config.count,
                difficulty: config.difficulty,
                topics: config.topics.split(',').map(t => t.trim()).filter(Boolean)
            };
        }

        try {
            const response = await fetch(`${API_BASE}/test/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    exam_type: examType,
                    subject_inputs: subjectInputs,
                    duration_minutes: duration
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to create test');
            }

            const data = await response.json();
            router.push(data.redirect_url);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to create test';
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#0a0b0d]">
            {/* Header */}
            <header className="bg-white/80 dark:bg-[#16181c]/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            INFINITEST
                        </Link>
                        <span className="text-gray-500 dark:text-gray-400">|</span>
                        <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Create Test</span>
                    </div>
                    <Link href="/test" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
                        ← Back to History
                    </Link>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <form onSubmit={handleSubmit} className="space-y-8">

                    {/* Top Configuration */}
                    <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">1. General Configuration</h2>

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
                    </div>

                    {/* Subject Configuration */}
                    <div className="space-y-4">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white px-2">2. Subject Configuration</h2>

                        {Object.entries(subjects).map(([subject, config]) => (
                            config.enabled && (
                                <div key={subject} className="bg-white dark:bg-[#16181c] rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 transition-all hover:border-indigo-200 dark:hover:border-indigo-900">
                                    <div className="flex flex-col md:flex-row gap-6">

                                        {/* Subject Info & Count */}
                                        <div className="md:w-1/4 space-y-4">
                                            <div className="flex items-center gap-2">
                                                <div className={`p-2 rounded-lg ${subject === 'Physics' ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30' :
                                                        subject === 'Chemistry' ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/30' :
                                                            subject === 'Biology' ? 'bg-green-100 text-green-600 dark:bg-green-900/30' :
                                                                'bg-orange-100 text-orange-600 dark:bg-orange-900/30'
                                                    }`}>
                                                    <BookOpen className="w-5 h-5" />
                                                </div>
                                                <h3 className="font-bold text-lg text-gray-900 dark:text-white">{subject}</h3>
                                            </div>

                                            <div>
                                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Questions</label>
                                                <div className="flex items-center mt-1">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleSubjectChange(subject, 'count', Math.max(0, config.count - 5))}
                                                        className="p-2 rounded-l-lg border border-r-0 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
                                                    >
                                                        <Minus className="w-4 h-4" />
                                                    </button>
                                                    <input
                                                        type="number"
                                                        value={config.count}
                                                        onChange={(e) => handleSubjectChange(subject, 'count', Number(e.target.value))}
                                                        className="w-16 text-center py-2 border-y border-gray-300 dark:border-gray-600 bg-transparent font-mono font-bold"
                                                    />
                                                    <button
                                                        type="button"
                                                        onClick={() => handleSubjectChange(subject, 'count', Math.min(50, config.count + 5))}
                                                        className="p-2 rounded-r-lg border border-l-0 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800"
                                                    >
                                                        <Plus className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Config details */}
                                        <div className="md:w-3/4 grid md:grid-cols-2 gap-6 pl-0 md:pl-6 md:border-l border-gray-100 dark:border-gray-800">

                                            {/* Topics Input */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    Topics <span className="text-gray-400 font-normal">(Optional)</span>
                                                </label>
                                                <textarea
                                                    value={config.topics}
                                                    onChange={(e) => handleSubjectChange(subject, 'topics', e.target.value)}
                                                    placeholder={`e.g. ${subject === 'Physics' ? 'Optics, Mechanics' : 'Organic, Electrochemistry'}`}
                                                    className="w-full h-24 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm bg-gray-50 dark:bg-[#0a0b0d] text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                                                />
                                                <p className="mt-1 text-xs text-gray-500">Comma-separated topics</p>
                                            </div>

                                            {/* Difficulty Sliders */}
                                            <div className="space-y-3">
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty Distribution</label>

                                                <div className="space-y-2">
                                                    <div className="flex items-center gap-2 text-sm">
                                                        <span className="w-16 text-green-600 dark:text-green-400 font-medium">Easy</span>
                                                        <input
                                                            type="range" min="0" max="100" step="10"
                                                            value={config.difficulty.easy}
                                                            onChange={(e) => handleDifficultyChange(subject, 'easy', Number(e.target.value))}
                                                            className="flex-1 accent-green-500 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                                        />
                                                        <span className="w-10 text-right font-mono">{config.difficulty.easy}%</span>
                                                    </div>

                                                    <div className="flex items-center gap-2 text-sm">
                                                        <span className="w-16 text-yellow-600 dark:text-yellow-400 font-medium">Medium</span>
                                                        <input
                                                            type="range" min="0" max="100" step="10"
                                                            value={config.difficulty.medium}
                                                            onChange={(e) => handleDifficultyChange(subject, 'medium', Number(e.target.value))}
                                                            className="flex-1 accent-yellow-500 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                                        />
                                                        <span className="w-10 text-right font-mono">{config.difficulty.medium}%</span>
                                                    </div>

                                                    <div className="flex items-center gap-2 text-sm">
                                                        <span className="w-16 text-red-600 dark:text-red-400 font-medium">Hard</span>
                                                        <input
                                                            type="range" min="0" max="100" step="10"
                                                            value={config.difficulty.hard}
                                                            onChange={(e) => handleDifficultyChange(subject, 'hard', Number(e.target.value))}
                                                            className="flex-1 accent-red-500 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                                                        />
                                                        <span className="w-10 text-right font-mono">{config.difficulty.hard}%</span>
                                                    </div>
                                                </div>

                                                {config.difficulty.easy + config.difficulty.medium + config.difficulty.hard !== 100 && (
                                                    <div className="flex items-center gap-1 text-xs text-red-500 mt-1">
                                                        <AlertCircle className="w-3 h-3" />
                                                        Sum must be 100% (Currently {config.difficulty.easy + config.difficulty.medium + config.difficulty.hard}%)
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )
                        ))}
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="fixed bottom-0 left-0 right-0 bg-white/80 dark:bg-[#16181c]/90 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 p-4 z-40">
                        <div className="max-w-5xl mx-auto flex justify-between items-center">
                            <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-8">
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Total Questions</span>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{totalQuestions}</p>
                                </div>
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Total Marks</span>
                                    <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{totalQuestions * 4}</p>
                                </div>
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Duration</span>
                                    <p className="text-2xl font-bold text-gray-900 dark:text-white">{duration}m</p>
                                </div>
                            </div>
                            <div className="w-full md:w-auto">
                                {error && (
                                    <p className="text-red-500 text-sm mb-2 text-right">{error}</p>
                                )}
                                <button
                                    type="submit"
                                    disabled={loading || totalQuestions < 1}
                                    className="w-full md:w-auto px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                                >
                                    {loading ? 'Creating...' : (
                                        <>
                                            <CheckCircle2 className="w-5 h-5" />
                                            Create Test
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                    {/* Spacer for fixed bottom bar */}
                    <div className="h-24"></div>
                </form>
            </main>
        </div>
    );
}
