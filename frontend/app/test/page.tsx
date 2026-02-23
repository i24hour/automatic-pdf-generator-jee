'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Sparkles, Globe, History, ChevronRight, PlayCircle, BookOpen, Trophy } from 'lucide-react';

import { API_BASE_URL as API_BASE } from '@/lib/config';

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
    const [userName, setUserName] = useState<string | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        const storedName = localStorage.getItem('user_name');
        if (storedName) setUserName(storedName);

        setIsAuthenticated(!!token);
        if (token) {
            fetchTestHistory(token);
        } else {
            setLoading(false);
        }
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
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">Completed</span>;
            case 'IN_PROGRESS':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">In Progress</span>;
            case 'NOT_STARTED':
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">Not Started</span>;
            default:
                return <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">{status}</span>;
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#0a0b0d]">
            {/* Header */}
            <header className="bg-white/80 dark:bg-[#16181c]/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            INFINITEST
                        </Link>
                        <span className="text-gray-300 dark:text-gray-600">|</span>
                        <span className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                            Student Portal
                        </span>
                    </div>
                    {/* User Profile / Logout Placeholder */}
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"></div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">

                {/* Hero Section */}
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Welcome back{userName ? `, ${userName}` : ''}! 👋
                    </h1>
                    <p className="mt-2 text-gray-500 dark:text-gray-400">
                        Ready to ace your exams? Choose a mode below to get started.
                    </p>
                </div>

                {/* Main Feature Grid */}
                <div className="grid md:grid-cols-2 gap-6">
                    {/* Infinite Practice Card */}
                    <Link href={isAuthenticated ? "/test/create" : "/signup"} className="group relative overflow-hidden bg-white dark:bg-[#16181c] rounded-2xl p-8 border border-gray-200 dark:border-gray-800 shadow-sm hover:shadow-xl hover:border-indigo-500/50 transition-all duration-300">
                        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                            <Sparkles className="w-32 h-32 text-indigo-600" />
                        </div>
                        <div className="relative z-10">
                            <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center mb-4 text-indigo-600 dark:text-indigo-400">
                                <Sparkles className="w-6 h-6" />
                            </div>
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Infinite Practice</h2>
                            <p className="text-gray-500 dark:text-gray-400 mb-6">
                                Generate unlimited custom mock tests for JEE, NEET, or Boards using AI. Tailor difficulty and topics.
                            </p>
                            <span className="inline-flex items-center text-sm font-semibold text-indigo-600 dark:text-indigo-400 group-hover:translate-x-1 transition-transform">
                                Create New Test <ChevronRight className="w-4 h-4 ml-1" />
                            </span>
                        </div>
                    </Link>

                    {/* Community Hub Card */}
                    <Link href="/community" className="group relative overflow-hidden bg-white dark:bg-[#16181c] rounded-2xl p-8 border border-gray-200 dark:border-gray-800 shadow-sm hover:shadow-xl hover:border-purple-500/50 transition-all duration-300">
                        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                            <Globe className="w-32 h-32 text-purple-600" />
                        </div>
                        <div className="relative z-10">
                            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center mb-4 text-purple-600 dark:text-purple-400">
                                <Globe className="w-6 h-6" />
                            </div>
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Community Hub</h2>
                            <p className="text-gray-500 dark:text-gray-400 mb-6">
                                Explore tests created by top students and educators. Compete on leaderboards and challenge yourself.
                            </p>
                            <span className="inline-flex items-center text-sm font-semibold text-purple-600 dark:text-purple-400 group-hover:translate-x-1 transition-transform">
                                Browse Community <ChevronRight className="w-4 h-4 ml-1" />
                            </span>
                        </div>
                    </Link>
                </div>

                {/* Test History Section */}
                <div className="bg-white dark:bg-[#16181c] rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
                    <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-800 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <History className="w-5 h-5 text-gray-500" />
                            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Recent Activity</h2>
                        </div>
                    </div>

                    {!isAuthenticated ? (
                        <div className="p-12 text-center">
                            <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                                <BookOpen className="w-8 h-8 text-indigo-500" />
                            </div>
                            <h3 className="text-base font-medium text-gray-900 dark:text-white mb-1">Sign up to track your progress</h3>
                            <p className="text-sm text-gray-500 mb-4">Create a free account to take tests and see your history here.</p>
                            <Link href="/signup" className="inline-flex items-center px-5 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors">
                                Create Free Account
                            </Link>
                        </div>
                    ) : loading ? (
                        <div className="p-12 text-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
                            <p className="mt-4 text-sm text-gray-500">Loading history...</p>
                        </div>
                    ) : tests.length === 0 ? (
                        <div className="p-12 text-center">
                            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                                <BookOpen className="w-8 h-8 text-gray-400" />
                            </div>
                            <h3 className="text-base font-medium text-gray-900 dark:text-white mb-1">No tests taken yet</h3>
                            <p className="text-sm text-gray-500 mb-4">Your test history and performance will appear here.</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 dark:bg-gray-800/50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Exam</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Score</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                                        <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                                    {tests.map((test) => (
                                        <tr key={test.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex flex-col">
                                                    <span className="font-semibold text-gray-900 dark:text-white">{test.exam_type}</span>
                                                    <span className="text-xs text-gray-500">{test.total_questions} Questions • {test.duration_minutes}m</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {test.total_score !== null ? (
                                                    <div className="flex items-center gap-1">
                                                        <Trophy className={`w-4 h-4 ${test.total_score > (test.max_score || 0) * 0.7 ? 'text-yellow-500' : 'text-gray-400'}`} />
                                                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                                                            {test.total_score}
                                                            <span className="text-gray-400 text-xs">/{test.max_score}</span>
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <span className="text-xs text-gray-400">-</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {getStatusBadge(test.status)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {new Date(test.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right">
                                                {test.status === 'SUBMITTED' ? (
                                                    <Link href={`/test/${test.id}/result`} className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 text-sm font-medium">
                                                        View Result
                                                    </Link>
                                                ) : test.status === 'IN_PROGRESS' ? (
                                                    <Link href={`/test/${test.id}`} className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-900 text-sm font-medium">
                                                        Resume
                                                    </Link>
                                                ) : (
                                                    <Link href={`/test/${test.id}/instructions`} className="text-green-600 dark:text-green-400 hover:text-green-900 text-sm font-medium">
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
