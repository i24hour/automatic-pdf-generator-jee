'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CreateTestPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Form state
    const [examType, setExamType] = useState('JEE_MAINS');
    const [topics, setTopics] = useState('');
    const [physicsCount, setPhysicsCount] = useState(10);
    const [chemistryCount, setChemistryCount] = useState(10);
    const [mathsCount, setMathsCount] = useState(10);
    const [biologyCount, setBiologyCount] = useState(0);
    const [easyPct, setEasyPct] = useState(20);
    const [mediumPct, setMediumPct] = useState(50);
    const [hardPct, setHardPct] = useState(30);
    const [duration, setDuration] = useState(60);

    const totalQuestions = physicsCount + chemistryCount + mathsCount + biologyCount;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const token = localStorage.getItem('auth_token');
        if (!token) {
            router.push('/login?redirect=/test/create');
            return;
        }

        const subjectDist: Record<string, number> = {};
        if (physicsCount > 0) subjectDist['Physics'] = physicsCount;
        if (chemistryCount > 0) subjectDist['Chemistry'] = chemistryCount;
        if (mathsCount > 0) subjectDist['Maths'] = mathsCount;
        if (biologyCount > 0) subjectDist['Biology'] = biologyCount;

        try {
            const response = await fetch(`${API_BASE}/test/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    exam_type: examType,
                    topics: topics.split(',').map(t => t.trim()).filter(Boolean),
                    subject_distribution: subjectDist,
                    difficulty_distribution: {
                        easy: easyPct,
                        medium: mediumPct,
                        hard: hardPct
                    },
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

    // Auto-adjust difficulty percentages
    const handleEasyChange = (val: number) => {
        setEasyPct(val);
        const remaining = 100 - val;
        setMediumPct(Math.round(remaining * 0.6));
        setHardPct(100 - val - Math.round(remaining * 0.6));
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d]">
            {/* Header */}
            <header className="bg-white/80 dark:bg-[#16181c]/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            INFINITEST
                        </Link>
                        <span className="text-gray-500 dark:text-gray-400">|</span>
                        <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Create Test</span>
                    </div>
                    <Link href="/test" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
                        ← Back to Tests
                    </Link>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 p-8">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">🎯 Configure Your Test</h1>
                    <p className="text-gray-600 dark:text-gray-400 mb-8">Set up your test parameters below</p>

                    {error && (
                        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-8">
                        {/* Exam Type */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                                Exam Type
                            </label>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {['JEE_MAINS', 'JEE_ADV', 'NEET', 'CUSTOM'].map((type) => (
                                    <button
                                        key={type}
                                        type="button"
                                        onClick={() => {
                                            setExamType(type);
                                            if (type === 'NEET') {
                                                setMathsCount(0);
                                                setBiologyCount(20);
                                            } else {
                                                setMathsCount(10);
                                                setBiologyCount(0);
                                            }
                                        }}
                                        className={`py-3 px-4 rounded-lg border-2 font-medium transition-all ${examType === type
                                                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                                : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-indigo-300'
                                            }`}
                                    >
                                        {type.replace('_', ' ')}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Topics */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Topics (comma-separated, optional)
                            </label>
                            <input
                                type="text"
                                value={topics}
                                onChange={(e) => setTopics(e.target.value)}
                                placeholder="e.g., Mechanics, Thermodynamics, Organic Chemistry"
                                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            />
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                Leave empty for mixed topics from all chapters
                            </p>
                        </div>

                        {/* Subject Distribution */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
                                Questions per Subject (Total: {totalQuestions})
                            </label>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div>
                                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Physics</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="50"
                                        value={physicsCount}
                                        onChange={(e) => setPhysicsCount(Number(e.target.value))}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Chemistry</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="50"
                                        value={chemistryCount}
                                        onChange={(e) => setChemistryCount(Number(e.target.value))}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                    />
                                </div>
                                {examType !== 'NEET' && (
                                    <div>
                                        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Maths</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="50"
                                            value={mathsCount}
                                            onChange={(e) => setMathsCount(Number(e.target.value))}
                                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                        />
                                    </div>
                                )}
                                {examType === 'NEET' && (
                                    <div>
                                        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Biology</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="50"
                                            value={biologyCount}
                                            onChange={(e) => setBiologyCount(Number(e.target.value))}
                                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                                        />
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Difficulty Distribution */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
                                Difficulty Distribution (must add to 100%)
                            </label>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs text-green-600 dark:text-green-400 mb-1 font-medium">Easy %</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="100"
                                        value={easyPct}
                                        onChange={(e) => handleEasyChange(Number(e.target.value))}
                                        className="w-full px-3 py-2 border border-green-300 dark:border-green-600 rounded-lg bg-green-50 dark:bg-green-900/20 text-gray-900 dark:text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-yellow-600 dark:text-yellow-400 mb-1 font-medium">Medium %</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="100"
                                        value={mediumPct}
                                        onChange={(e) => setMediumPct(Number(e.target.value))}
                                        className="w-full px-3 py-2 border border-yellow-300 dark:border-yellow-600 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 text-gray-900 dark:text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-red-600 dark:text-red-400 mb-1 font-medium">Hard %</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="100"
                                        value={hardPct}
                                        onChange={(e) => setHardPct(Number(e.target.value))}
                                        className="w-full px-3 py-2 border border-red-300 dark:border-red-600 rounded-lg bg-red-50 dark:bg-red-900/20 text-gray-900 dark:text-white"
                                    />
                                </div>
                            </div>
                            {easyPct + mediumPct + hardPct !== 100 && (
                                <p className="mt-2 text-sm text-red-500">Total must equal 100% (currently {easyPct + mediumPct + hardPct}%)</p>
                            )}
                        </div>

                        {/* Duration */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Duration (minutes)
                            </label>
                            <div className="flex gap-3">
                                {[30, 60, 90, 120, 180].map((mins) => (
                                    <button
                                        key={mins}
                                        type="button"
                                        onClick={() => setDuration(mins)}
                                        className={`px-4 py-2 rounded-lg border-2 font-medium transition-all ${duration === mins
                                                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                                : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-indigo-300'
                                            }`}
                                    >
                                        {mins} min
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Summary */}
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                            <h3 className="font-medium text-gray-900 dark:text-white mb-2">📋 Test Summary</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400">Exam:</span>
                                    <span className="ml-2 font-medium text-gray-900 dark:text-white">{examType.replace('_', ' ')}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400">Questions:</span>
                                    <span className="ml-2 font-medium text-gray-900 dark:text-white">{totalQuestions}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400">Duration:</span>
                                    <span className="ml-2 font-medium text-gray-900 dark:text-white">{duration} min</span>
                                </div>
                                <div>
                                    <span className="text-gray-500 dark:text-gray-400">Max Marks:</span>
                                    <span className="ml-2 font-medium text-gray-900 dark:text-white">{totalQuestions * 4}</span>
                                </div>
                            </div>
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            disabled={loading || totalQuestions < 1 || easyPct + mediumPct + hardPct !== 100}
                            className="w-full py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                    Creating Test...
                                </>
                            ) : (
                                <>🚀 Create Test</>
                            )}
                        </button>
                    </form>
                </div>
            </main>
        </div>
    );
}
