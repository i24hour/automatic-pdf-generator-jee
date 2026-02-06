"use client";

import React, { useEffect, useState } from "react";
import { Search, Filter, Trophy, ArrowUpDown, Loader2, Plus } from "lucide-react";
import Link from "next/link";
import MobileNav from "@/components/layout/MobileNav";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import TestCard from "@/components/TestCard";
import { useCommunityApi, TestSummary } from "@/lib/community-api";
import { useAuth } from "@/lib/auth-context";

export default function CommunityPage() {
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
            // Debounce search could be added here, but for now simple
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
            {/* Mobile Nav */}
            <div className="md:hidden pb-20">
                <main className="p-4">
                    <DiscoveryContent
                        tests={tests}
                        loading={loading}
                        filters={{ search, subject, examType, sortBy }}
                        setFilters={{ setSearch, setSubject, setExamType, setSortBy }}
                    />
                </main>
                <MobileNav />
            </div>

            {/* Desktop Layout */}
            <div className="hidden md:flex min-h-screen max-w-[1300px] mx-auto">
                <DesktopSidebar />
                <main className="flex-1 ml-[275px] min-h-screen p-8">
                    <DiscoveryContent
                        tests={tests}
                        loading={loading}
                        filters={{ search, subject, examType, sortBy }}
                        setFilters={{ setSearch, setSubject, setExamType, setSortBy }}
                    />
                </main>
            </div>
        </div>
    );
}

// Extracted for reuse in mobile/desktop
export interface DiscoveryContentProps {
    tests: TestSummary[];
    loading: boolean;
    filters: {
        search: string;
        subject: string;
        examType: string;
        sortBy: string;
    };
    setFilters: {
        setSearch: (val: string) => void;
        setSubject: (val: string) => void;
        setExamType: (val: string) => void;
        setSortBy: (val: string) => void;
    };
}

export function DiscoveryContent({ tests, loading, filters, setFilters }: DiscoveryContentProps) {
    const subjects = ["Physics", "Chemistry", "Maths", "Biology"];
    const exams = ["JEE Mains", "JEE Advanced", "NEET", "CBSE Board", "GATE"];

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                        <Trophy className="w-8 h-8 text-yellow-500" />
                        Community Tests
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                        Attempt tests created by top rankers and educators
                    </p>
                </div>
                <Link
                    href="/community/create"
                    className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold transition-colors shadow-lg shadow-indigo-500/30"
                >
                    <Plus className="w-5 h-5" />
                    Create Public Test
                </Link>
            </div>

            {/* Search & Filter Bar */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 bg-gray-50 dark:bg-[#111] p-4 rounded-2xl border border-gray-100 dark:border-[#222]">
                {/* Search */}
                <div className="md:col-span-5 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search by topic (e.g. Rotation, Optics)..."
                        className="w-full pl-10 pr-4 py-3 bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white transition-all"
                        value={filters.search}
                        onChange={(e) => setFilters.setSearch(e.target.value)}
                    />
                </div>

                {/* Filters */}
                <div className="md:col-span-2 relative">
                    <select
                        className="w-full pl-3 pr-8 py-3 bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white appearance-none cursor-pointer"
                        value={filters.subject}
                        onChange={(e) => setFilters.setSubject(e.target.value)}
                    >
                        <option value="">All Subjects</option>
                        {subjects.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>

                <div className="md:col-span-2 relative">
                    <select
                        className="w-full pl-3 pr-8 py-3 bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-[#333] rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:text-white appearance-none cursor-pointer"
                        value={filters.examType}
                        onChange={(e) => setFilters.setExamType(e.target.value)}
                    >
                        <option value="">All Exams</option>
                        {exams.map(e => <option key={e} value={e}>{e}</option>)}
                    </select>
                    <Filter className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                </div>

                {/* Sort */}
                <div className="md:col-span-3 relative">
                    <div className="flex bg-white dark:bg-[#1a1a1a] p-1 rounded-xl border border-gray-200 dark:border-[#333]">
                        {["newest", "popular", "trending"].map(sort => (
                            <button
                                key={sort}
                                onClick={() => setFilters.setSortBy(sort)}
                                className={`flex-1 py-2 text-sm font-medium rounded-lg capitalize transition-all ${filters.sortBy === sort
                                    ? "bg-gray-100 dark:bg-[#333] text-black dark:text-white shadow-sm"
                                    : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                                    }`}
                            >
                                {sort}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Content Grid */}
            {loading ? (
                <div className="flex flex-col items-center justify-center py-20 text-gray-500 animate-pulse">
                    <Loader2 className="w-12 h-12 mb-4 animate-spin text-indigo-500" />
                    <p>Fetching community tests...</p>
                </div>
            ) : tests.length === 0 ? (
                <div className="text-center py-20 bg-gray-50 dark:bg-[#111] rounded-3xl border border-dashed border-gray-200 dark:border-[#333]">
                    <div className="w-20 h-20 bg-gray-100 dark:bg-[#222] rounded-full flex items-center justify-center mx-auto mb-6">
                        <Search className="w-10 h-10 text-gray-400" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">No tests found</h3>
                    <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto mb-8">
                        We couldn't find any public tests matching your filters. Why not create one?
                    </p>
                    <Link
                        href="/community/create"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        Create First Test
                    </Link>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {tests.map(test => (
                        <TestCard key={test.id} test={test} />
                    ))}
                </div>
            )}
        </div>
    );
}
