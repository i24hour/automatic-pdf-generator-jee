"use client";

import React, { useState, useEffect } from "react";
import { Trophy, Award, Star, Crown, Medal, Loader2, User } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LeaderboardEntry {
    user_id: string;
    username: string | null;
    value: number;
    rank: number;
}

interface LeaderboardResponse {
    category: string;
    entries: LeaderboardEntry[];
}

export default function Leaderboard() {
    const { authFetch } = useAuth();
    const [category, setCategory] = useState<"most_likes" | "most_posts">("most_likes");
    const [data, setData] = useState<LeaderboardEntry[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchLeaderboard();
    }, [category]);

    const fetchLeaderboard = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await authFetch(`${API_BASE_URL}/api/posts/leaderboard/${category}?limit=20`);
            if (response.ok) {
                const result: LeaderboardResponse = await response.json();
                setData(result.entries);
            } else {
                setError("Failed to load leaderboard");
            }
        } catch (err) {
            console.error("Error fetching leaderboard:", err);
            setError("Failed to load leaderboard");
        } finally {
            setIsLoading(false);
        }
    };

    const getRankIcon = (rank: number) => {
        switch (rank) {
            case 1:
                return <Crown className="w-6 h-6 text-yellow-500 fill-yellow-500" />;
            case 2:
                return <Medal className="w-6 h-6 text-gray-400 fill-gray-400" />;
            case 3:
                return <Medal className="w-6 h-6 text-amber-700 fill-amber-700" />;
            default:
                return <span className="text-gray-500 font-bold w-6 text-center">{rank}</span>;
        }
    };

    return (
        <div className="max-w-2xl mx-auto p-4">
            <div className="flex items-center gap-3 mb-6">
                <div className="bg-yellow-100 dark:bg-yellow-900/30 p-3 rounded-xl">
                    <Trophy className="w-8 h-8 text-yellow-600 dark:text-yellow-500" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Leaderboard</h1>
                    <p className="text-gray-500 dark:text-gray-400 text-sm">Top contributors and popular creators</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex bg-gray-100 dark:bg-[#16181c] p-1 rounded-xl mb-6">
                <button
                    onClick={() => setCategory("most_likes")}
                    className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${category === "most_likes"
                        ? "bg-white dark:bg-black text-indigo-600 dark:text-indigo-400 shadow-sm"
                        : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                        }`}
                >
                    <Star className="w-4 h-4" />
                    Most Liked
                </button>
                <button
                    onClick={() => setCategory("most_posts")}
                    className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${category === "most_posts"
                        ? "bg-white dark:bg-black text-indigo-600 dark:text-indigo-400 shadow-sm"
                        : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                        }`}
                >
                    <Award className="w-4 h-4" />
                    Most Active
                </button>
            </div>

            {/* Content */}
            <div className="bg-white dark:bg-[#16181c] border border-gray-200 dark:border-[#2f3336] rounded-2xl shadow-sm overflow-hidden">
                {isLoading ? (
                    <div className="p-12 flex justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                    </div>
                ) : error ? (
                    <div className="p-12 text-center text-red-500">{error}</div>
                ) : data.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                        No data available yet. Be the first to climb the leaderboard!
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100 dark:divide-gray-800">
                        <div className="grid grid-cols-12 gap-4 p-4 bg-gray-50 dark:bg-black/50 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                            <div className="col-span-2 text-center">Rank</div>
                            <div className="col-span-7">User</div>
                            <div className="col-span-3 text-right">{category === "most_likes" ? "Likes" : "Posts"}</div>
                        </div>
                        {data.map((entry) => (
                            <div key={entry.user_id} className="grid grid-cols-12 gap-4 p-4 items-center hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                                <div className="col-span-2 flex justify-center">
                                    {getRankIcon(entry.rank)}
                                </div>
                                <div className="col-span-7 flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs">
                                        {entry.username?.[0]?.toUpperCase() || <User className="w-4 h-4" />}
                                    </div>
                                    <span className="font-medium text-gray-900 dark:text-white truncate">
                                        {entry.username || "Anonymous User"}
                                    </span>
                                </div>
                                <div className="col-span-3 text-right font-bold text-gray-900 dark:text-white">
                                    {entry.value}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
