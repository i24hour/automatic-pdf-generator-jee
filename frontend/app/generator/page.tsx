"use client";

import React from "react";
import TestGenerator from "@/components/TestGenerator";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import MobileNav from "@/components/layout/MobileNav";

export default function GeneratorPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile View */}
            <div className="md:hidden pb-20 py-8 px-4">
                <div className="max-w-3xl mx-auto">
                    <TestGenerator />
                </div>
                <MobileNav />
            </div>

            {/* Desktop View */}
            <div className="hidden md:flex min-h-screen w-full">
                <DesktopSidebar />
                <main className="flex-1 ml-[275px] min-h-screen py-8 px-8">
                    <div className="max-w-3xl mx-auto">
                        <TestGenerator />
                    </div>
                </main>
            </div>
        </div>
    );
}
