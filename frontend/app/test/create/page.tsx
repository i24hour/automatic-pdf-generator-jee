'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Minus, Plus, BookOpen, AlertCircle, CheckCircle2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app';

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
                next['Biology'].enabled = false;
                next['Botany'].enabled = true;
                next['Zoology'].enabled = true;

                next['Physics'].count = 10;
                next['Chemistry'].count = 10;
                next['Botany'].count = 10;
                next['Zoology'].count = 10;
            } else {
                next['Maths'].enabled = true;
                next['Biology'].enabled = false;
                next['Botany'].enabled = false;
                next['Zoology'].enabled = false;

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
            // Validate total count
            if (config.count < 1) {
                setError(`${subj}: Must have at least 1 question`);
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
                let errMsg = 'Failed to create test';
                if (data.detail) {
                    if (typeof data.detail === 'string') {
                        errMsg = data.detail;
                    } else if (Array.isArray(data.detail)) {
                        errMsg = data.detail.map((e: any) => e.msg).join(', ');
                    } else if (typeof data.detail === 'object') {
                        errMsg = JSON.stringify(data.detail);
                    }
                }
                throw new Error(errMsg);
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
                                                            subject === 'Botany' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30' :
                                                                subject === 'Zoology' ? 'bg-teal-100 text-teal-600 dark:bg-teal-900/30' :
                                                                    'bg-orange-100 text-orange-600 dark:bg-orange-900/30'
                                                    }`}>
                                                    <BookOpen className="w-5 h-5" />
                                                </div>
                                                <h3 className="font-bold text-lg text-gray-900 dark:text-white">{subject}</h3>
                                            </div>

                                            <div>
                                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Questions</label>
                                                <div className="flex items-center mt-1">
                                                    <span className="text-2xl font-bold font-mono text-gray-900 dark:text-white">
                                                        {config.count}
                                                    </span>
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
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty Distribution (Questions)</label>

                                                <div className="grid grid-cols-3 gap-3">
                                                    <div>
                                                        <label className="block text-xs text-green-600 dark:text-green-400 font-medium mb-1">Easy</label>
                                                        <input
                                                            type="number" min="0" step="1"
                                                            value={config.difficulty.easy}
                                                            onChange={(e) => handleDifficultyChange(subject, 'easy', Number(e.target.value))}
                                                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-[#0a0b0d]"
                                                        />
                                                    </div>

                                                    <div>
                                                        <label className="block text-xs text-yellow-600 dark:text-yellow-400 font-medium mb-1">Medium</label>
                                                        <input
                                                            type="number" min="0" step="1"
                                                            value={config.difficulty.medium}
                                                            onChange={(e) => handleDifficultyChange(subject, 'medium', Number(e.target.value))}
                                                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-[#0a0b0d]"
                                                        />
                                                    </div>

                                                    <div>
                                                        <label className="block text-xs text-red-600 dark:text-red-400 font-medium mb-1">Hard</label>
                                                        <input
                                                            type="number" min="0" step="1"
                                                            value={config.difficulty.hard}
                                                            onChange={(e) => handleDifficultyChange(subject, 'hard', Number(e.target.value))}
                                                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-[#0a0b0d]"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )
                        ))}
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="fixed bottom-16 md:bottom-0 left-0 right-0 bg-white/95 dark:bg-[#16181c]/95 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 px-4 py-3 z-40">
                        <div className="max-w-5xl mx-auto space-y-3 md:space-y-0 md:flex md:justify-between md:items-center">
                            {/* Stats row - always horizontal */}
                            <div className="flex items-center justify-between md:justify-start gap-4 md:gap-8">
                                <div className="text-center md:text-left">
                                    <span className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs uppercase tracking-wider">Questions</span>
                                    <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">{totalQuestions}</p>
                                </div>
                                <div className="text-center md:text-left">
                                    <span className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs uppercase tracking-wider">Marks</span>
                                    <p className="text-lg md:text-2xl font-bold text-indigo-600 dark:text-indigo-400">{totalQuestions * 4}</p>
                                </div>
                                <div className="text-center md:text-left">
                                    <span className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs uppercase tracking-wider">Duration</span>
                                    <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">{duration}m</p>
                                </div>
                            </div>
                            {/* Create button */}
                            <div className="w-full md:w-auto">
                                {error && (
                                    <p className="text-red-500 text-sm mb-2 text-center md:text-right">{error}</p>
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
                    {/* Spacer for fixed bottom bar + mobile nav */}
                    <div className="h-40 md:h-24"></div>
                </form>
            </main>
        </div>
    );
}
