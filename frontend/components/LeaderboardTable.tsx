import React from "react";
import { Trophy, Clock, Target, User } from "lucide-react";
import { LeaderboardEntry } from "@/lib/community-api";

interface LeaderboardTableProps {
    entries: LeaderboardEntry[];
    currentUserId?: string;
}

const LeaderboardTable: React.FC<LeaderboardTableProps> = ({ entries, currentUserId }) => {
    if (entries.length === 0) {
        return (
            <div className="text-center py-10 text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-[#111] rounded-xl border border-dashed border-gray-200 dark:border-[#333]">
                <Trophy className="w-10 h-10 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
                <p>No attempts yet. Be the first to top the leaderboard!</p>
            </div>
        );
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    };

    return (
        <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-[#333] bg-white dark:bg-[#1a1a1a]">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="bg-gray-50 dark:bg-[#111] border-b border-gray-200 dark:border-[#333]">
                        <th className="px-6 py-4 font-semibold text-gray-900 dark:text-white w-20">Rank</th>
                        <th className="px-6 py-4 font-semibold text-gray-900 dark:text-white">User</th>
                        <th className="px-6 py-4 font-semibold text-gray-900 dark:text-white text-right">Score</th>
                        <th className="px-6 py-4 font-semibold text-gray-900 dark:text-white text-right hidden sm:table-cell">Accuracy</th>
                        <th className="px-6 py-4 font-semibold text-gray-900 dark:text-white text-right hidden sm:table-cell">Time</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-[#2f3336]">
                    {entries.map((entry) => (
                        <tr
                            key={entry.rank}
                            className={`group transition-colors ${entry.is_current_user
                                    ? "bg-indigo-50 dark:bg-indigo-900/20"
                                    : "hover:bg-gray-50 dark:hover:bg-[#222]"
                                }`}
                        >
                            <td className="px-6 py-4">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold relative ${entry.rank === 1 ? "bg-yellow-100 text-yellow-700" :
                                        entry.rank === 2 ? "bg-gray-100 text-gray-700" :
                                            entry.rank === 3 ? "bg-orange-100 text-orange-700" :
                                                "text-gray-500"
                                    }`}>
                                    {entry.rank <= 3 && (
                                        <Trophy className={`w-3 h-3 absolute -top-1 -right-1 ${entry.rank === 1 ? "text-yellow-500 fill-current" :
                                                entry.rank === 2 ? "text-gray-400 fill-current" :
                                                    "text-orange-500 fill-current"
                                            }`} />
                                    )}
                                    {entry.rank}
                                </div>
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-medium text-xs">
                                        {entry.user_name[0].toUpperCase()}
                                    </div>
                                    <span className={`font-medium ${entry.is_current_user ? "text-indigo-600 dark:text-indigo-400" : "text-gray-900 dark:text-white"}`}>
                                        {entry.user_name}
                                        {entry.is_current_user && " (You)"}
                                    </span>
                                </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                                <span className="font-bold text-gray-900 dark:text-white">{entry.score}</span>
                            </td>
                            <td className="px-6 py-4 text-right hidden sm:table-cell">
                                <div className="flex items-center justify-end gap-1.5 text-gray-600 dark:text-gray-400">
                                    <Target className="w-4 h-4" />
                                    {entry.accuracy}%
                                </div>
                            </td>
                            <td className="px-6 py-4 text-right hidden sm:table-cell">
                                <div className="flex items-center justify-end gap-1.5 text-gray-600 dark:text-gray-400">
                                    <Clock className="w-4 h-4" />
                                    {formatTime(entry.time_taken_seconds)}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default LeaderboardTable;
