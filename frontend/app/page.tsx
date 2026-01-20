"use client";

import React, { useState, useCallback } from "react";
import TestGenerator from "@/components/TestGenerator";
import PostsFeed from "@/components/PostsFeed";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";

export default function Home() {
  const [sidebarWidth, setSidebarWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);

  const handleMouseDown = useCallback(() => {
    setIsResizing(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = window.innerWidth - e.clientX;
      // Clamp between 300px and 600px
      setSidebarWidth(Math.max(300, Math.min(600, newWidth)));
    },
    [isResizing]
  );

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  React.useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "ew-resize";
      document.body.style.userSelect = "none";
    } else {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Mobile View: Show Test Generator (Home) */}
      <div className="md:hidden bg-white dark:bg-black">
        <TestGenerator />
        <MobileNav />
      </div>

      {/* Desktop View: 3-Column Layout */}
      <div className="hidden md:flex min-h-screen w-full">
        {/* Left Sidebar: Navigation */}
        <DesktopSidebar />

        {/* Center Column: Posts Feed */}
        <main className="flex-1 ml-[275px] border-r border-gray-200 dark:border-[#2f3336] min-h-screen">
          <PostsFeed />
        </main>

        {/* Resize Handle */}
        <div
          onMouseDown={handleMouseDown}
          className="w-1 hover:w-2 bg-gray-200 dark:bg-[#2f3336] hover:bg-indigo-500 dark:hover:bg-indigo-500 cursor-ew-resize transition-all hidden lg:block"
          title="Drag to resize"
        />

        {/* Right Sidebar: Test Generator */}
        <aside
          style={{ width: sidebarWidth }}
          className="p-4 h-screen sticky top-0 overflow-y-auto bg-white dark:bg-black hidden lg:block"
        >
          <div className="mb-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white px-2">Generate Test</h2>
          </div>
          <TestGenerator />
        </aside>
      </div>
    </div>
  );
}
