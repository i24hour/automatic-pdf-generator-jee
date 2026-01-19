"use client";

import React from "react";
import PostsFeed from "@/components/PostsFeed";
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
                <main className="flex-1 ml-[275px] min-h-screen">
                    <PostsFeed />
                </main>
            </div>
        </div>
    );
}
