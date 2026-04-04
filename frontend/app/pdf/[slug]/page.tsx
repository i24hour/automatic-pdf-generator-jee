"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FileText, Download, Heart, Eye, Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://q3vgjfnybq.ap-south-1.awsapprunner.com';

interface PDFInfo {
    id: string;
    topic: string;
    subject: string;
    level: string;
    difficulty: string;
    question_count: number;
    has_solutions: boolean;
    visibility: string;
    download_count: number;
    like_count: number;
    view_count: number;
    created_at: string | null;
}

export default function PDFViewerPage() {
    const params = useParams();
    const slug = params.slug as string;

    const [pdfInfo, setPdfInfo] = useState<PDFInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (slug) {
            fetchPDFInfo();
        }
    }, [slug]);

    const fetchPDFInfo = async () => {
        try {
            const res = await fetch(`${API_URL}/pdf/${slug}/info`);
            if (!res.ok) {
                if (res.status === 404) {
                    setError("PDF not found or is private");
                } else {
                    setError("Failed to load PDF");
                }
                return;
            }
            const data = await res.json();
            setPdfInfo(data.pdf);
        } catch (err) {
            setError("Failed to load PDF");
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = () => {
        // Redirect to the PDF endpoint which will serve the file
        window.open(`${API_URL}/pdf/${slug}`, '_blank');
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-black">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400">Loading PDF...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-black">
                <div className="text-center max-w-md mx-auto p-6">
                    <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                        <FileText className="w-8 h-8 text-red-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                        {error}
                    </h1>
                    <p className="text-gray-500 dark:text-gray-400 mb-6">
                        The PDF you're looking for might be private or has been removed.
                    </p>
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        Go Home
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-black">
            <div className="max-w-2xl mx-auto p-4 md:p-6">
                {/* Header */}
                <div className="mb-6">
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-indigo-600 mb-4"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to Home
                    </Link>
                </div>

                {/* PDF Card */}
                <div className="bg-white dark:bg-[#16181c] rounded-2xl border border-gray-200 dark:border-[#2f3336] overflow-hidden shadow-sm">
                    {/* PDF Icon Header */}
                    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-8 text-center">
                        <div className="w-20 h-20 bg-white/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                            <FileText className="w-10 h-10 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white mb-1">
                            {pdfInfo?.topic}
                        </h1>
                        <p className="text-white/80">
                            {pdfInfo?.subject} • {pdfInfo?.level}
                        </p>
                    </div>

                    {/* PDF Details */}
                    <div className="p-6 space-y-4">
                        {/* Metadata Grid */}
                        <div className="grid grid-cols-2 gap-4">
                            <div className="bg-gray-50 dark:bg-[#1a1d21] rounded-xl p-4">
                                <p className="text-sm text-gray-500 dark:text-gray-400">Difficulty</p>
                                <p className="font-semibold text-gray-900 dark:text-white">{pdfInfo?.difficulty}</p>
                            </div>
                            <div className="bg-gray-50 dark:bg-[#1a1d21] rounded-xl p-4">
                                <p className="text-sm text-gray-500 dark:text-gray-400">Questions</p>
                                <p className="font-semibold text-gray-900 dark:text-white">{pdfInfo?.question_count}</p>
                            </div>
                            <div className="bg-gray-50 dark:bg-[#1a1d21] rounded-xl p-4">
                                <p className="text-sm text-gray-500 dark:text-gray-400">Solutions</p>
                                <p className="font-semibold text-gray-900 dark:text-white">
                                    {pdfInfo?.has_solutions ? "✓ Included" : "Not included"}
                                </p>
                            </div>
                            <div className="bg-gray-50 dark:bg-[#1a1d21] rounded-xl p-4">
                                <p className="text-sm text-gray-500 dark:text-gray-400">Visibility</p>
                                <p className="font-semibold text-gray-900 dark:text-white capitalize">{pdfInfo?.visibility}</p>
                            </div>
                        </div>

                        {/* Stats */}
                        <div className="flex items-center justify-center gap-6 py-4 border-t border-gray-200 dark:border-[#2f3336]">
                            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                                <Heart className="w-5 h-5" />
                                <span>{pdfInfo?.like_count} likes</span>
                            </div>
                            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                                <Download className="w-5 h-5" />
                                <span>{pdfInfo?.download_count} downloads</span>
                            </div>
                            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                                <Eye className="w-5 h-5" />
                                <span>{pdfInfo?.view_count} views</span>
                            </div>
                        </div>

                        {/* Download Button */}
                        <button
                            onClick={handleDownload}
                            className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                        >
                            <Download className="w-5 h-5" />
                            Download PDF
                        </button>
                    </div>
                </div>

                {/* Branding */}
                <div className="text-center mt-8">
                    <p className="text-gray-400 dark:text-gray-500 text-sm">
                        Created with <span className="text-indigo-500">INFINITEST</span>
                    </p>
                    <Link
                        href="/"
                        className="text-indigo-600 hover:underline text-sm"
                    >
                        Generate your own test →
                    </Link>
                </div>
            </div>
        </div>
    );
}
