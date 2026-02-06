"use client";

import React, { useEffect, useState } from "react";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import MobileNav from "@/components/layout/MobileNav";
import TestGenerator from "@/components/TestGenerator";
import { DiscoveryContent } from "./community/page";
import { useCommunityApi, TestSummary } from "@/lib/community-api";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user } = useAuth();
  const api = useCommunityApi();
  const [tests, setTests] = useState<TestSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [subject, setSubject] = useState("");
  const [examType, setExamType] = useState("");
  const [sortBy, setSortBy] = useState("newest");

  useEffect(() => {
    loadTests();
  }, [search, subject, examType, sortBy]);

  const loadTests = async () => {
    setLoading(true);
    try {
      const data = await api.searchTests(search, subject, examType, sortBy);
      setTests(data);
    } catch (error) {
      console.error("Failed to load tests", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Mobile Layout (Standard Stack) */}
      <div className="md:hidden pb-20">
        <main className="p-4 space-y-8">
          <DiscoveryContent
            tests={tests}
            loading={loading}
            filters={{ search, subject, examType, sortBy }}
            setFilters={{ setSearch, setSubject, setExamType, setSortBy }}
          />
          <div className="border-t pt-8">
            <h2 className="text-xl font-bold mb-4">Create Test</h2>
            <TestGenerator />
          </div>
        </main>
        <MobileNav />
      </div>

      {/* Desktop Layout (3-Column) */}
      <div className="hidden md:flex min-h-screen">
        {/* Left: Sidebar (Fixed width handled inside component but we arrange it here) */}
        <DesktopSidebar />

        {/* Middle: Community Feed */}
        <main className="flex-1 ml-[275px] min-h-screen p-8 border-r border-gray-200 dark:border-[#2f3336]">
          <DiscoveryContent
            tests={tests}
            loading={loading}
            filters={{ search, subject, examType, sortBy }}
            setFilters={{ setSearch, setSubject, setExamType, setSortBy }}
          />
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
