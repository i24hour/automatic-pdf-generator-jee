"use client";

import React from "react";
import TestGenerator from "@/components/TestGenerator";

export default function GeneratorPage() {
    return (
        <div className="min-h-screen bg-white dark:bg-black py-8 px-4">
            <div className="max-w-3xl mx-auto">
                <TestGenerator />
            </div>
        </div>
    );
}
