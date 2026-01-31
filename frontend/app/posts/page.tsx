"use client";

import React, { Suspense } from "react";
import PostsFeed from "@/components/PostsFeed";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";

function LoadingFeed() {
    return (
        <div className="flex items-center justify-center min-h-[200px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
        </div>
    );
}

export default function PostsPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile View: Show Posts Feed */}
            <div className="md:hidden pb-20">
                <Suspense fallback={<LoadingFeed />}>
                    <PostsFeed />
                </Suspense>
                <MobileNav />
            </div>

            {/* Desktop View: Same as Home (3-Column Layout) */}
            <div className="hidden md:flex min-h-screen max-w-[1300px] mx-auto">
                {/* Left Sidebar: Navigation */}
                <DesktopSidebar />

                {/* Center Column: Posts Feed */}
                <main className="flex-1 ml-[275px] min-h-screen">
                    <Suspense fallback={<LoadingFeed />}>
                        <PostsFeed />
                    </Suspense>
                </main>
            </div>
        </div>
    );
}

