"use client";

import React from "react";
import TestGenerator from "@/components/TestGenerator";
import { ArrowLeft } from "lucide-react";

export default function GeneratorPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black py-8 px-4">
            <div className="max-w-3xl mx-auto">
                <div className="flex items-center gap-4 mb-6">
                    <button
                        onClick={() => window.history.back()}
                        className="p-2 -ml-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#1a1d21] transition-colors"
                        aria-label="Go back"
                    >
                        <ArrowLeft className="w-6 h-6 text-gray-900 dark:text-white" />
                    </button>
                </div>
                <TestGenerator />
            </div>
        </div>
    );
}
