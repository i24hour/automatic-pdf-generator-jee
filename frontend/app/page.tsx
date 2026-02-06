"use client";

import React, { Suspense } from "react";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import MobileNav from "@/components/layout/MobileNav";
import TestGenerator from "@/components/TestGenerator";
import PostsFeed from "@/components/PostsFeed"; // Importing the Feed component

function LoadingFeed() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Mobile Layout (Standard Stack) */}
      <div className="md:hidden pb-20">
        <main className="min-h-screen">
          {/* Mobile Header with Generator */}
          <div className="bg-gray-50 dark:bg-black/50 p-4 border-b border-gray-200 dark:border-gray-800">
            <div className="mb-4">
              <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">
                Infinite Test Generator
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Create your custom test instantly</p>
            </div>
            <TestGenerator />
          </div>

          {/* Feed Section */}
          <div className="space-y-4 pt-2 px-2">
            <h2 className="px-2 text-lg font-bold text-gray-900 dark:text-white">Community Feed</h2>
            <Suspense fallback={<LoadingFeed />}>
              <PostsFeed />
            </Suspense>
          </div>
        </main>
        <MobileNav />
      </div>

      {/* Desktop Layout (3-Column) */}
      <div className="hidden md:flex min-h-screen">
        {/* Left: Sidebar (Fixed width handled inside component but we arrange it here) */}
        <DesktopSidebar />

        {/* Middle: Community Feed */}
        <main className="flex-1 ml-[275px] min-h-screen border-r border-gray-200 dark:border-[#2f3336]">
          <Suspense fallback={<LoadingFeed />}>
            <PostsFeed />
          </Suspense>
        </main>

        {/* Right: Infinitest Generator */}
        <aside className="w-[400px] xl:w-[450px] p-6 h-screen sticky top-0 overflow-y-auto bg-gray-50 dark:bg-[#16181c] hidden lg:block scrollbar-hide">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <span>⚡ Quick Generator</span>
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Create a custom test instantly
            </p>
          </div>
          <TestGenerator />
        </aside>
      </div>
    </div>
  );
}
