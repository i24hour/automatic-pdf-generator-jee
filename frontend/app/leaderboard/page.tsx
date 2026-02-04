"use client";

import React from "react";
import Leaderboard from "@/components/features/leaderboard/Leaderboard";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import PostsFeed from "@/components/features/posts/PostsFeed";
// Actually, for Leaderboard page on desktop, usually the center column becomes the Leaderboard.
// Let's check if we have a Leaderboard component. I recall creating app/leaderboard/page.tsx but not a reusable component yet.
// I should extract Leaderboard logic to a component first. 
// For now, I'll assume I will extract it.

export default function LeaderboardPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black">
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
                <main className="flex-1 ml-[275px] min-h-screen">
                    <Leaderboard />
                </main>
            </div>
        </div>
    );
}
