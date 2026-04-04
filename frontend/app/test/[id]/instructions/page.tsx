'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { API_BASE } from '@/lib/config';


export default function TestInstructionsPage() {
    const router = useRouter();
    const params = useParams();
    const testId = params.id as string;

    const [accepted, setAccepted] = useState(false);
    const [loading, setLoading] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null); // null = checking

    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        setIsAuthenticated(!!token);
    }, []);

    const handleStart = async () => {
        if (!accepted) return;

        // Guard: redirect to login if not authenticated
        const token = localStorage.getItem('auth_token');
        if (!token) {
            router.push(`/signup?redirect=/test/${testId}/instructions`);
            return;
        }

        setLoading(true);

        try {
            const response = await fetch(`${API_BASE}/test/${testId}/start`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                router.push(`/test/${testId}`);
            } else {
                const data = await response.json();
                alert(data.detail || 'Failed to start test');
            }
        } catch (error) {
            console.error('Failed to start test:', error);
            alert('Failed to start test');
        } finally {
            setLoading(false);
        }
    };

    // Still checking auth
    if (isAuthenticated === null) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d] flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    // Not logged in — show friendly login prompt
    if (!isAuthenticated) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d] flex items-center justify-center px-4">
                <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 p-8 max-w-sm w-full text-center">
                    <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-3xl">🎯</span>
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                        Login to Attempt This Test
                    </h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                        Create a free account or login to start this test and track your score.
                    </p>
                    <Link
                        href={`/signup?redirect=/test/${testId}/instructions`}
                        className="block w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-colors mb-3"
                    >
                        Sign Up Free
                    </Link>
                    <Link
                        href={`/login?redirect=/test/${testId}/instructions`}
                        className="block w-full py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 font-semibold rounded-xl transition-colors"
                    >
                        Already have an account? Login
                    </Link>
                </div>
            </div>
        );
    }


    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-[#0a0b0d] dark:via-[#0d0f12] dark:to-[#0a0b0d]">
            {/* Header - NTA Style */}
            <header className="bg-gradient-to-r from-orange-500 to-orange-600 text-white py-3 px-4">
                <div className="max-w-6xl mx-auto flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <span className="text-2xl font-bold">🎯 INFINITEST</span>
                        <span className="text-sm opacity-80">AI-Powered Test Engine</span>
                    </div>
                    <Link href="/test" className="text-sm hover:underline">
                        ← Back to Tests
                    </Link>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 py-8">
                <div className="bg-white dark:bg-[#16181c] rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
                    {/* Title */}
                    <div className="bg-blue-600 text-white px-6 py-4">
                        <h1 className="text-xl font-bold">GENERAL INSTRUCTIONS</h1>
                    </div>

                    <div className="p-6 space-y-6">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            Please read the instructions carefully
                        </h2>

                        {/* General Instructions */}
                        <div className="space-y-4 text-gray-700 dark:text-gray-300">
                            <h3 className="font-semibold text-gray-900 dark:text-white">General Instructions:</h3>
                            <ol className="list-decimal list-inside space-y-2 ml-4">
                                <li>The clock will be set at the server. The countdown timer in the top right corner of screen will display the remaining time available for you to complete the examination.</li>
                                <li>When the timer reaches zero, the examination will end by itself. You will not be required to end or submit your examination.</li>
                                <li>The Questions Palette displayed on the right side of screen will show the status of each question using one of the following symbols:</li>
                            </ol>

                            {/* Status Legend */}
                            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 ml-8 space-y-3">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-gray-300 dark:bg-gray-600 flex items-center justify-center text-xs font-bold">1</div>
                                    <span>You have not visited the question yet.</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-red-500 text-white flex items-center justify-center text-xs font-bold">2</div>
                                    <span>You have not answered the question.</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-green-500 text-white flex items-center justify-center text-xs font-bold">3</div>
                                    <span>You have answered the question.</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-purple-500 text-white flex items-center justify-center text-xs font-bold">4</div>
                                    <span>You have NOT answered the question, but have marked it for review.</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-purple-500 text-white flex items-center justify-center text-xs font-bold relative">
                                        5
                                        <div className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-green-400 border border-white"></div>
                                    </div>
                                    <span>The question(s) &ldquo;Answered and Marked for Review&rdquo; will be considered for evaluation.</span>
                                </div>
                            </div>
                        </div>

                        {/* Navigation Instructions */}
                        <div className="space-y-4 text-gray-700 dark:text-gray-300">
                            <h3 className="font-semibold text-gray-900 dark:text-white">Navigating to a Question:</h3>
                            <ol className="list-decimal list-inside space-y-2 ml-4">
                                <li>Click on the question number in the Question Palette to go directly to that question.</li>
                                <li>Click on <strong>Save & Next</strong> to save your answer and go to the next question.</li>
                                <li>Click on <strong>Mark for Review & Next</strong> to save and mark for review, then go to next question.</li>
                            </ol>
                        </div>

                        {/* Answering Instructions */}
                        <div className="space-y-4 text-gray-700 dark:text-gray-300">
                            <h3 className="font-semibold text-gray-900 dark:text-white">Answering a Question:</h3>
                            <ol className="list-decimal list-inside space-y-2 ml-4">
                                <li>To select your answer, click on the button of one of the options.</li>
                                <li>To deselect your answer, click on the <strong>Clear Response</strong> button.</li>
                                <li>To save your answer, you MUST click on the <strong>Save & Next</strong> button.</li>
                                <li>To mark the question for review, click on the <strong>Mark for Review & Next</strong> button.</li>
                            </ol>
                        </div>

                        {/* Section Navigation */}
                        <div className="space-y-4 text-gray-700 dark:text-gray-300">
                            <h3 className="font-semibold text-gray-900 dark:text-white">Navigating through sections:</h3>
                            <ol className="list-decimal list-inside space-y-2 ml-4">
                                <li>Sections in this question paper are displayed on the top bar of the screen.</li>
                                <li>You can shuffle between sections and questions during the examination.</li>
                            </ol>
                        </div>

                        {/* Declaration */}
                        <div className="border-t border-gray-200 dark:border-gray-700 pt-6 mt-6">
                            <label className="flex items-start gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={accepted}
                                    onChange={(e) => setAccepted(e.target.checked)}
                                    className="mt-1 w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                />
                                <span className="text-sm text-gray-700 dark:text-gray-300">
                                    I have read and understood the instructions. All computer hardware allotted to me are in proper working condition.
                                    I agree that in case of not adhering to the instructions, I shall be liable to be debarred from this Test.
                                </span>
                            </label>
                        </div>

                        {/* Proceed Button */}
                        <button
                            onClick={handleStart}
                            disabled={!accepted || loading}
                            className="w-full py-4 bg-green-600 text-white font-bold text-lg rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                    Starting...
                                </>
                            ) : (
                                'PROCEED'
                            )}
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
}
