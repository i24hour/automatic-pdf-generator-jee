"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Clock, BookOpen, BarChart, Play, Loader2, Share2, Trophy } from "lucide-react";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import LeaderboardTable from "@/components/LeaderboardTable";
import { useCommunityApi, TestDetail, LeaderboardEntry } from "@/lib/community-api";
import { useAuth } from "@/lib/auth-context";

export default function TestDetailedPage() {
    const { testId } = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const api = useCommunityApi();

    const [test, setTest] = useState<TestDetail | null>(null);
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [starting, setStarting] = useState(false);

    useEffect(() => {
        if (testId) {
            loadData();
        }
    }, [testId]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [testData, leaderboardData] = await Promise.all([
                api.getTestDetails(testId as string),
                api.getLeaderboard(testId as string)
            ]);
            setTest(testData);
            setLeaderboard(leaderboardData);
        } catch (error) {
            console.error("Failed to load test data", error);
        } finally {
            setLoading(false);
        }
    };

    const handleStartTest = async () => {
        setStarting(true);
        try {
            const { redirect_url } = await api.startTest(testId as string);
            router.push(redirect_url);
        } catch (error: any) {
            console.error("Failed to start test", error);
            alert(`Failed to start test: ${error.message || "An unknown error occurred."}`);
            setStarting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-white dark:bg-black">
                <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
            </div>
        );
    }

    if (!test) {
        return (
            <div className="flex h-screen items-center justify-center bg-white dark:bg-black flex-col gap-4">
                <h2 className="text-xl font-bold dark:text-white">Test not found</h2>
                <button onClick={() => router.back()} className="text-indigo-600 hover:underline">Go Back</button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile View */}
            <div className="md:hidden pb-20 p-4">
                <TestContent
                    test={test}
                    leaderboard={leaderboard}
                    handleStart={handleStartTest}
                    starting={starting}
                    user={user}
                />
                <MobileNav />
            </div>

            {/* Desktop View */}
            <div className="hidden md:flex min-h-screen max-w-[1300px] mx-auto">
                <DesktopSidebar />
                <main className="flex-1 ml-[275px] min-h-screen p-8">
                    <TestContent
                        test={test}
                        leaderboard={leaderboard}
                        handleStart={handleStartTest}
                        starting={starting}
                        user={user}
                    />
                </main>
            </div>
        </div>
    );
}

function TestContent({ test, leaderboard, handleStart, starting, user }: any) {
    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Hero Section */}
            <div className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
                <div className="relative z-10">
                    <div className="flex items-start justify-between mb-4">
                        <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-sm font-medium border border-white/10">
                            {test.subject} • {test.exam_type}
                        </span>
                        <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-sm font-medium border border-white/10">
                            {test.difficulty}
                        </span>
                    </div>

                    <h1 className="text-3xl md:text-4xl font-bold mb-4">{test.title}</h1>

                    <div className="flex flex-wrap gap-6 text-indigo-100 mb-8">
                        <div className="flex items-center gap-2">
                            <Clock className="w-5 h-5" />
                            <span>{test.duration_minutes} Minutes</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <BookOpen className="w-5 h-5" />
                            <span>{test.total_questions} Questions</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <BarChart className="w-5 h-5" />
                            <span>{test.total_marks} Marks</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Trophy className="w-5 h-5" />
                            <span>{test.attempt_count} Attempts</span>
                        </div>
                    </div>

                    <div className="flex gap-4">
                        <button
                            onClick={handleStart}
                            disabled={starting}
                            className="flex items-center gap-2 px-8 py-4 bg-white text-indigo-700 rounded-xl font-bold text-lg hover:bg-indigo-50 transition-colors disabled:opacity-70 disabled:cursor-not-allowed shadow-lg"
                        >
                            {starting ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Starting...
                                </>
                            ) : (
                                <>
                                    <Play className="w-5 h-5 fill-current" />
                                    Attempt Now
                                </>
                            )}
                        </button>

                        <button className="flex items-center gap-2 px-6 py-4 bg-white/10 backdrop-blur-md rounded-xl font-semibold hover:bg-white/20 transition-colors border border-white/10">
                            <Share2 className="w-5 h-5" />
                            Share
                        </button>
                    </div>
                </div>

                {/* Decorative BG */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-500/30 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
            </div>

            {/* Topics */}
            <div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3">Topics Covered</h3>
                <div className="flex flex-wrap gap-2">
                    {test.topics.map((topic: string, i: number) => (
                        <span key={i} className="px-3 py-1.5 bg-gray-100 dark:bg-[#222] text-gray-700 dark:text-gray-300 rounded-lg text-sm">
                            {topic}
                        </span>
                    ))}
                </div>
            </div>

            {/* Leaderboard */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Trophy className="w-6 h-6 text-yellow-500" />
                        Leaderboard
                    </h3>
                </div>

                <LeaderboardTable entries={leaderboard} currentUserId={user?.id} />
            </div>
        </div>
    );
}
