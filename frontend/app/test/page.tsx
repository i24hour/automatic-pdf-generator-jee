'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app';

interface TestHistory {
    id: string;
    exam_type: string;
    total_questions: number;
    duration_minutes: number;
    status: string;
    total_score: number | null;
    max_score: number | null;
    created_at: string;
    submitted_at: string | null;
}

export default function TestPortalPage() {
    const router = useRouter();
    const [tests, setTests] = useState<TestHistory[]>([]);
    const [loading, setLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            router.push('/login?redirect=/test');
            return;
        }
        setIsAuthenticated(true);
        fetchTestHistory(token);
    }, [router]);

    const fetchTestHistory = async (token: string) => {
        try {
            const response = await fetch(`${API_BASE}/test/history`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setTests(data);
            }
        } catch (error) {
            console.error('Failed to fetch test history:', error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'SUBMITTED':
                return <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">Completed</span>;
            case 'IN_PROGRESS':
                return <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">In Progress</span>;
            case 'NOT_STARTED':
                return <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">Not Started</span>;
            default:
                return <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">{status}</span>;
        }
    };

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d]">
            {/* Header */}
            <header className="bg-white/80 dark:bg-[#16181c]/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            INFINITEST
                        </Link>
                        <span className="text-gray-500 dark:text-gray-400">|</span>
                        <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">Test Portal</span>
                    </div>
                    <Link
                        href="/generator"
                        className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                        ← Back to Generator
                    </Link>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                {/* Create Test Card */}
                <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 mb-12 text-white shadow-xl">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div>
                            <h1 className="text-3xl font-bold mb-2">🎯 Start a New Test</h1>
                            <p className="text-indigo-100 text-lg">
                                Create a custom test with AI-generated questions. Choose your subjects, topics, and difficulty.
                            </p>
                        </div>
                        <Link
                            href="/test/create"
                            className="px-8 py-4 bg-white text-indigo-600 font-semibold rounded-xl hover:bg-indigo-50 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                        >
                            Create Test →
                        </Link>
                    </div>
                </div>

                {/* Test History */}
                <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800">
                    <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">📝 Your Test History</h2>
                    </div>

                    {loading ? (
                        <div className="p-12 text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                            <p className="mt-4 text-gray-500 dark:text-gray-400">Loading tests...</p>
                        </div>
                    ) : tests.length === 0 ? (
                        <div className="p-12 text-center">
                            <div className="text-6xl mb-4">📚</div>
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No tests yet</h3>
                            <p className="text-gray-500 dark:text-gray-400 mb-6">Create your first test to get started!</p>
                            <Link
                                href="/test/create"
                                className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                            >
                                Create Your First Test
                            </Link>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 dark:bg-gray-800/50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Exam</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Questions</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Duration</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Score</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                    {tests.map((test) => (
                                        <tr key={test.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="font-medium text-gray-900 dark:text-white">{test.exam_type}</span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-gray-300">
                                                {test.total_questions}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-gray-300">
                                                {test.duration_minutes} min
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getStatusBadge(test.status)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {test.total_score !== null ? (
                                                    <span className="font-medium text-gray-900 dark:text-white">
                                                        {test.total_score}/{test.max_score}
                                                    </span>
                                                ) : (
                                                    <span className="text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-gray-600 dark:text-gray-300 text-sm">
                                                {new Date(test.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {test.status === 'SUBMITTED' ? (
                                                    <Link
                                                        href={`/test/${test.id}/result`}
                                                        className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                                                    >
                                                        View Result
                                                    </Link>
                                                ) : test.status === 'IN_PROGRESS' ? (
                                                    <Link
                                                        href={`/test/${test.id}`}
                                                        className="text-yellow-600 dark:text-yellow-400 hover:underline font-medium"
                                                    >
                                                        Continue
                                                    </Link>
                                                ) : (
                                                    <Link
                                                        href={`/test/${test.id}/instructions`}
                                                        className="text-green-600 dark:text-green-400 hover:underline font-medium"
                                                    >
                                                        Start
                                                    </Link>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}
