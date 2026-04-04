'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import MathText from '@/components/MathText';
import { API_BASE } from '@/lib/config';


interface SubjectAnalysis {
    correct: number;
    wrong: number;
    unattempted: number;
    score: number;
    max_score: number;
    time_spent: number;
    accuracy: number;
}

interface Question {
    index: number;
    subject: string;
    topic: string;
    difficulty: string;
    question_text: string;
    options: Record<string, string> | null;
    correct_answer: string;
    user_answer: string | null;
    is_correct: boolean | null;
    marks_obtained: number | null;
    time_spent_seconds: number;
    solution: string | null;
}

interface ResultData {
    test_id: string;
    exam_type: string;
    total_score: number;
    max_score: number;
    correct_count: number;
    wrong_count: number;
    unattempted_count: number;
    percentage: number;
    started_at: string;
    submitted_at: string;
    duration_taken_minutes: number;
    subject_analysis: Record<string, SubjectAnalysis>;
    questions: Question[];
}

export default function TestResultPage() {
    const router = useRouter();
    const params = useParams();
    const testId = params.id as string;

    const [result, setResult] = useState<ResultData | null>(null);
    const [loading, setLoading] = useState(true);
    const [showQuestions, setShowQuestions] = useState(false);
    const [filterType, setFilterType] = useState<'all' | 'correct' | 'wrong' | 'unattempted'>('all');

    useEffect(() => {
        const fetchResult = async () => {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                router.push('/login');
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/test/${testId}/result`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    setResult(data);
                } else {
                    router.push('/test');
                }
            } catch (error) {
                console.error('Failed to fetch result:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchResult();
    }, [testId, router]);

    if (loading || !result) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d] flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    const filteredQuestions = result.questions.filter(q => {
        if (filterType === 'correct') return q.is_correct === true;
        if (filterType === 'wrong') return q.is_correct === false;
        if (filterType === 'unattempted') return q.is_correct === null;
        return true;
    });

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d]">
            {/* Header */}
            <header className="bg-white/80 dark:bg-[#16181c]/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
                <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            INFINITEST
                        </Link>
                        <span className="text-gray-500 dark:text-gray-400">|</span>
                        <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Test Result</span>
                    </div>
                    <Link href="/test" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
                        ← Back to Tests
                    </Link>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Score Card */}
                <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-white shadow-xl mb-8">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div>
                            <h1 className="text-3xl font-bold mb-2">🎉 Test Completed!</h1>
                            <p className="text-indigo-100">{result.exam_type.replace('_', ' ')} • {new Date(result.submitted_at).toLocaleDateString()}</p>
                        </div>
                        <div className="text-center">
                            <div className="text-6xl font-bold">{result.total_score}</div>
                            <div className="text-indigo-100">out of {result.max_score}</div>
                            <div className="mt-2 text-2xl font-semibold">{result.percentage}%</div>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <div className="bg-white dark:bg-[#16181c] rounded-xl p-4 border border-green-200 dark:border-green-800">
                        <div className="text-3xl font-bold text-green-600">{result.correct_count}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Correct</div>
                    </div>
                    <div className="bg-white dark:bg-[#16181c] rounded-xl p-4 border border-red-200 dark:border-red-800">
                        <div className="text-3xl font-bold text-red-600">{result.wrong_count}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Wrong</div>
                    </div>
                    <div className="bg-white dark:bg-[#16181c] rounded-xl p-4 border border-gray-200 dark:border-gray-700">
                        <div className="text-3xl font-bold text-gray-500">{result.unattempted_count}</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Unattempted</div>
                    </div>
                    <div className="bg-white dark:bg-[#16181c] rounded-xl p-4 border border-indigo-200 dark:border-indigo-800">
                        <div className="text-3xl font-bold text-indigo-600">{result.duration_taken_minutes} min</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">Time Taken</div>
                    </div>
                </div>

                {/* Subject Analysis */}
                <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 p-6 mb-8">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">📊 Subject-wise Analysis</h2>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-gray-200 dark:border-gray-700">
                                    <th className="py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Subject</th>
                                    <th className="py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-400">Score</th>
                                    <th className="py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-400">Correct</th>
                                    <th className="py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-400">Wrong</th>
                                    <th className="py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-400">Unattempted</th>
                                    <th className="py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-400">Accuracy</th>
                                    <th className="py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-400">Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(result.subject_analysis).map(([subject, data]) => (
                                    <tr key={subject} className="border-b border-gray-100 dark:border-gray-800">
                                        <td className="py-3 font-medium text-gray-900 dark:text-white">{subject}</td>
                                        <td className="py-3 text-center text-gray-900 dark:text-white">
                                            {data.score}/{data.max_score}
                                        </td>
                                        <td className="py-3 text-center text-green-600 font-medium">{data.correct}</td>
                                        <td className="py-3 text-center text-red-600 font-medium">{data.wrong}</td>
                                        <td className="py-3 text-center text-gray-500">{data.unattempted}</td>
                                        <td className="py-3 text-center">
                                            <span className={`px-2 py-1 rounded text-sm font-medium ${data.accuracy >= 70 ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                                                data.accuracy >= 40 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                    'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                                                }`}>
                                                {data.accuracy}%
                                            </span>
                                        </td>
                                        <td className="py-3 text-center text-gray-600 dark:text-gray-400">
                                            {Math.floor(data.time_spent / 60)}m {data.time_spent % 60}s
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Question Review */}
                <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">📝 Question Review</h2>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setShowQuestions(!showQuestions)}
                                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
                            >
                                {showQuestions ? 'Hide Questions' : 'Show Questions'}
                            </button>
                        </div>
                    </div>

                    {showQuestions && (
                        <>
                            {/* Filter Tabs */}
                            <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800/50 flex gap-2">
                                {(['all', 'correct', 'wrong', 'unattempted'] as const).map(type => (
                                    <button
                                        key={type}
                                        onClick={() => setFilterType(type)}
                                        className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${filterType === type
                                            ? 'bg-indigo-600 text-white'
                                            : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                                            }`}
                                    >
                                        {type.charAt(0).toUpperCase() + type.slice(1)} ({
                                            type === 'all' ? result.questions.length :
                                                type === 'correct' ? result.correct_count :
                                                    type === 'wrong' ? result.wrong_count :
                                                        result.unattempted_count
                                        })
                                    </button>
                                ))}
                            </div>

                            {/* Questions List */}
                            <div className="divide-y divide-gray-200 dark:divide-gray-700">
                                {filteredQuestions.map((q) => (
                                    <div key={q.index} className="p-6">
                                        <div className="flex justify-between items-start mb-3">
                                            <div className="flex items-center gap-3">
                                                <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white ${q.is_correct === true ? 'bg-green-500' :
                                                    q.is_correct === false ? 'bg-red-500' :
                                                        'bg-gray-400'
                                                    }`}>
                                                    {q.index + 1}
                                                </span>
                                                <span className="text-sm text-gray-500 dark:text-gray-400">
                                                    {q.subject} • {q.topic} • {q.difficulty}
                                                </span>
                                            </div>
                                            <span className={`px-2 py-1 rounded text-sm font-medium ${q.marks_obtained !== null && q.marks_obtained > 0 ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                                                q.marks_obtained !== null && q.marks_obtained < 0 ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                                                    'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                                                }`}>
                                                {q.marks_obtained !== null ? (q.marks_obtained > 0 ? '+' : '') + q.marks_obtained : '0'} marks
                                            </span>
                                        </div>

                                        <div className="text-gray-900 dark:text-white mb-4">
                                            <MathText content={q.question_text} />
                                        </div>

                                        {q.options && (
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
                                                {Object.entries(q.options).map(([key, value]) => (
                                                    <div
                                                        key={key}
                                                        className={`p-3 rounded-lg border ${key === q.correct_answer
                                                            ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                                                            : key === q.user_answer && q.is_correct === false
                                                                ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                                                                : 'border-gray-200 dark:border-gray-700'
                                                            }`}
                                                    >
                                                        <span className={`font-bold mr-2 ${key === q.correct_answer ? 'text-green-600' :
                                                            key === q.user_answer && q.is_correct === false ? 'text-red-600' :
                                                                'text-gray-600 dark:text-gray-400'
                                                            }`}>
                                                            {key})
                                                        </span>
                                                        <div className="text-gray-700 dark:text-gray-300">
                                                            <MathText content={value} />
                                                        </div>
                                                        {key === q.correct_answer && <span className="ml-2 text-green-600">✓</span>}
                                                        {key === q.user_answer && q.is_correct === false && <span className="ml-2 text-red-600">✗</span>}
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                            Your answer: <span className={q.is_correct === true ? 'text-green-600' : q.is_correct === false ? 'text-red-600' : 'text-gray-600'}>
                                                {q.user_answer || 'Not attempted'}
                                            </span>
                                            {' • '}
                                            Correct: <span className="text-green-600">{q.correct_answer}</span>
                                            {' • '}
                                            Time: {q.time_spent_seconds}s
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>

                {/* Action Buttons */}
                <div className="mt-8 flex justify-center gap-4">
                    <Link
                        href="/test/create"
                        className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl hover:from-indigo-700 hover:to-purple-700 transition-all"
                    >
                        Take Another Test
                    </Link>
                    <Link
                        href="/test"
                        className="px-8 py-3 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-semibold rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all"
                    >
                        View All Tests
                    </Link>
                </div>
            </main>
        </div>
    );
}
