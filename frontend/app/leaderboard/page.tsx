"use client";

import React from "react";
import Leaderboard from "@/components/Leaderboard"; // Assuming we'll create/have this
import TestGenerator from "@/components/TestGenerator";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import PostsFeed from "@/components/PostsFeed"; // Optional: if we want feed in center on desktop for leaderboard page? 
// Actually, for Leaderboard page on desktop, usually the center column becomes the Leaderboard.
// Let's check if we have a Leaderboard component. I recall creating app/leaderboard/page.tsx but not a reusable component yet.
// I should extract Leaderboard logic to a component first. 
// For now, I'll assume I will extract it.

export default function LeaderboardPage() {
    return (
        <div className="min-h-screen bg-[#FAF9F6] dark:bg-black">
            {/* Mobile View: Show Leaderboard */}
            <div className="md:hidden pb-20">
                <Leaderboard />
                <MobileNav />
            </div>

            {/* Desktop View: 3-Column Layout with Leaderboard in Center */}
            <div className="hidden md:flex min-h-screen max-w-[1300px] mx-auto">
                {/* Left Sidebar: Navigation */}
                <DesktopSidebar />

                {/* Center Column: Leaderboard */}
                <main className="flex-1 ml-[275px] border-r border-gray-200 dark:border-[#2f3336] min-h-screen">
                    <Leaderboard />
                </main>

                {/* Right Sidebar: Test Generator */}
                <aside className="w-[400px] p-4 h-screen sticky top-0 overflow-y-auto border-l border-gray-200 dark:border-[#2f3336] bg-white dark:bg-black hidden lg:block">
                    <div className="mb-4">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white px-2">Generate Test</h2>
                    </div>
                    <TestGenerator />
                </aside>
            </div>
        </div>
    );
}
