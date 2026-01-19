"use client";

import React from "react";
import PostsFeed from "@/components/PostsFeed";
import TestGenerator from "@/components/TestGenerator";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";

export default function PostsPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile View: Show Posts Feed */}
            <div className="md:hidden pb-20">
                <PostsFeed />
                <MobileNav />
            </div>

            {/* Desktop View: Same as Home (3-Column Layout) */}
            <div className="hidden md:flex min-h-screen max-w-[1300px] mx-auto">
                {/* Left Sidebar: Navigation */}
                <DesktopSidebar />

                {/* Center Column: Posts Feed */}
                <main className="flex-1 ml-[275px] border-r border-gray-200 dark:border-[#2f3336] min-h-screen">
                    <PostsFeed />
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
