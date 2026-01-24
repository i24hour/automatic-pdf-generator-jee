"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import {
    User,
    Mail,
    Phone,
    GraduationCap,
    AtSign,
    Save,
    Loader2,
    Sun,
    Moon,
    Sparkles,
    Lock,
    Globe,
    Link as LinkIcon,
    FileText,
    Copy,
    Check,
    ChevronRight,
    Download
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PDF {
    id: string;
    slug: string | null;
    pdf_url: string;
    pdf_filename: string;
    caption: string | null;
    subject: string;
    topic: string;
    level: string;
    difficulty: string;
    visibility: string;
    download_count: number;
    like_count: number;
    created_at: string | null;
}

export default function SettingsPage() {
    const { user, token, refreshUser } = useAuth();
    const { theme, toggleTheme } = useTheme();

    const [activeSection, setActiveSection] = useState<string>("profile");
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

    // Profile form
    const [formData, setFormData] = useState({
        name: "",
        phone: "",
        class_grade: "",
        username: "",
    });

    // Settings
    const [freshQuestionsEnabled, setFreshQuestionsEnabled] = useState(true);

    // PDFs
    const [privatePDFs, setPrivatePDFs] = useState<PDF[]>([]);
    const [publicPDFs, setPublicPDFs] = useState<PDF[]>([]);
    const [unlistedPDFs, setUnlistedPDFs] = useState<PDF[]>([]);
    const [loadingPDFs, setLoadingPDFs] = useState(false);
    const [copiedSlug, setCopiedSlug] = useState<string | null>(null);

    useEffect(() => {
        if (user) {
            setFormData({
                name: user.name || "",
                phone: user.phone || "",
                class_grade: (user as any).class_grade || "",
                username: user.username || "",
            });
            fetchSettings();
        }
    }, [user]);

    useEffect(() => {
        if (activeSection === "private" || activeSection === "public" || activeSection === "unlisted") {
            fetchPDFs(activeSection);
        }
    }, [activeSection, token]);

    const fetchSettings = async () => {
        try {
            const res = await fetch(`${API_URL}/auth/settings`, {
                headers: { "Authorization": `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setFreshQuestionsEnabled(data.fresh_questions_enabled ?? true);
            }
        } catch (error) {
            console.error("Failed to fetch settings:", error);
        }
    };

    const fetchPDFs = async (visibility: string) => {
        setLoadingPDFs(true);
        try {
            const res = await fetch(`${API_URL}/auth/me/pdfs?visibility=${visibility}`, {
                headers: { "Authorization": `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                if (visibility === "private") setPrivatePDFs(data.pdfs);
                else if (visibility === "public") setPublicPDFs(data.pdfs);
                else if (visibility === "unlisted") setUnlistedPDFs(data.pdfs);
            }
        } catch (error) {
            console.error("Failed to fetch PDFs:", error);
        } finally {
            setLoadingPDFs(false);
        }
    };

    const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleProfileSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setMessage(null);

        try {
            const res = await fetch(`${API_URL}/auth/profile`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                },
                body: JSON.stringify(formData),
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || "Failed to update profile");
            }

            await refreshUser();
            setMessage({ type: "success", text: "Profile updated successfully!" });
        } catch (error) {
            setMessage({ type: "error", text: error instanceof Error ? error.message : "An error occurred" });
        } finally {
            setIsLoading(false);
        }
    };

    const toggleFreshQuestions = async () => {
        const newValue = !freshQuestionsEnabled;
        setFreshQuestionsEnabled(newValue);

        try {
            const res = await fetch(`${API_URL}/auth/settings/fresh-questions`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                },
                body: JSON.stringify({ enabled: newValue }),
            });

            if (!res.ok) {
                setFreshQuestionsEnabled(!newValue);
                throw new Error("Failed to update setting");
            }
        } catch (error) {
            console.error("Failed to toggle fresh questions:", error);
            setFreshQuestionsEnabled(!newValue);
        }
    };

    const generateLink = async (pdfId: string) => {
        try {
            const res = await fetch(`${API_URL}/pdf/${pdfId}/generate-link`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                copyToClipboard(data.link, data.slug);
                fetchPDFs(activeSection);
            }
        } catch (error) {
            console.error("Failed to generate link:", error);
        }
    };

    const copyToClipboard = (link: string, slug: string) => {
        navigator.clipboard.writeText(link);
        setCopiedSlug(slug);
        setTimeout(() => setCopiedSlug(null), 2000);
    };

    if (!user) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    const sections = [
        { id: "profile", label: "Profile", icon: User },
        { id: "theme", label: "Theme", icon: theme === "dark" ? Moon : Sun },
        { id: "fresh", label: "Fresh Questions", icon: Sparkles },
        { id: "private", label: "Private PDFs", icon: Lock },
        { id: "public", label: "My Posts", icon: Globe },
        { id: "unlisted", label: "Unlisted PDFs", icon: LinkIcon },
    ];

    const renderPDFList = (pdfs: PDF[], showLink: boolean = false) => {
        if (loadingPDFs) {
            return (
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
                </div>
            );
        }

        if (pdfs.length === 0) {
            return (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No PDFs found
                </div>
            );
        }

        return (
            <div className="space-y-3">
                {pdfs.map((pdf) => (
                    <div
                        key={pdf.id}
                        className="bg-gray-50 dark:bg-[#1a1d21] rounded-xl p-4 border border-gray-200 dark:border-[#2f3336]"
                    >
                        <div className="flex items-start justify-between">
                            <div className="flex-1 cursor-pointer" onClick={() => window.open(pdf.pdf_url, '_blank')}>
                                <h3 className="font-medium text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                                    {pdf.topic}
                                </h3>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    {pdf.subject} • {pdf.level} • {pdf.difficulty}
                                </p>
                                <div className="flex gap-3 mt-2 text-xs text-gray-400">
                                    <span>❤️ {pdf.like_count}</span>
                                    <span>📥 {pdf.download_count}</span>
                                </div>
                            </div>
                            <div className="flex gap-2">
                                {/* Download Button */}
                                <button
                                    onClick={() => window.open(pdf.pdf_url, '_blank')}
                                    className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-lg text-sm hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                                    title="Download PDF"
                                >
                                    <Download className="w-4 h-4" />
                                </button>
                                {/* Copy Link Button (for unlisted) */}
                                {showLink && (
                                    <button
                                        onClick={() => pdf.slug
                                            ? copyToClipboard(`https://infinitest.tech/pdf/${pdf.slug}`, pdf.slug)
                                            : generateLink(pdf.id)
                                        }
                                        className="flex items-center gap-1 px-3 py-1.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg text-sm hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
                                    >
                                        {copiedSlug === pdf.slug ? (
                                            <>
                                                <Check className="w-4 h-4" />
                                                Copied!
                                            </>
                                        ) : (
                                            <>
                                                <Copy className="w-4 h-4" />
                                                {pdf.slug ? "Copy Link" : "Get Link"}
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div className="max-w-2xl mx-auto p-4 md:p-6 pb-24">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
            </div>

            {/* Navigation Tabs */}
            <div className="flex flex-col gap-2 mb-6">
                {sections.map((section) => (
                    <button
                        key={section.id}
                        onClick={() => setActiveSection(section.id)}
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeSection === section.id
                            ? "bg-indigo-600 text-white"
                            : "bg-gray-100 dark:bg-[#1a1d21] text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-[#2f3336]"
                            }`}
                    >
                        <section.icon className="w-5 h-5" />
                        <span className="text-sm font-medium">{section.label}</span>
                    </button>
                ))}
            </div>

            {/* Content Sections */}
            <div className="bg-white dark:bg-[#16181c] rounded-2xl border border-gray-200 dark:border-[#2f3336] p-6 shadow-sm">

                {/* Profile Section */}
                {activeSection === "profile" && (
                    <form onSubmit={handleProfileSubmit} className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                <User className="w-4 h-4" />
                                Full Name
                            </label>
                            <input
                                type="text"
                                name="name"
                                value={formData.name}
                                onChange={handleProfileChange}
                                className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-black border border-gray-200 dark:border-[#2f3336] focus:ring-2 focus:ring-indigo-500 outline-none transition-all dark:text-white"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                <AtSign className="w-4 h-4" />
                                Username
                            </label>
                            <input
                                type="text"
                                name="username"
                                value={formData.username}
                                onChange={handleProfileChange}
                                className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-black border border-gray-200 dark:border-[#2f3336] focus:ring-2 focus:ring-indigo-500 outline-none transition-all dark:text-white"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                <Phone className="w-4 h-4" />
                                Phone Number
                            </label>
                            <input
                                type="tel"
                                name="phone"
                                value={formData.phone}
                                onChange={handleProfileChange}
                                className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-black border border-gray-200 dark:border-[#2f3336] focus:ring-2 focus:ring-indigo-500 outline-none transition-all dark:text-white"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                <GraduationCap className="w-4 h-4" />
                                Class
                            </label>
                            <input
                                type="text"
                                name="class_grade"
                                value={formData.class_grade}
                                onChange={handleProfileChange}
                                className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-black border border-gray-200 dark:border-[#2f3336] focus:ring-2 focus:ring-indigo-500 outline-none transition-all dark:text-white"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                <Mail className="w-4 h-4" />
                                Email
                            </label>
                            <input
                                type="email"
                                value={user.email}
                                readOnly
                                className="w-full px-4 py-3 rounded-xl bg-gray-100 dark:bg-[#202327] border border-gray-200 dark:border-[#2f3336] text-gray-500 cursor-not-allowed"
                            />
                        </div>

                        {message && (
                            <div className={`p-4 rounded-xl ${message.type === 'success'
                                ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                                : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                                }`}>
                                {message.text}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                            {isLoading ? "Saving..." : "Save Changes"}
                        </button>
                    </form>
                )}

                {/* Theme Section */}
                {activeSection === "theme" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Appearance</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Choose your preferred color scheme
                        </p>

                        <div className="grid grid-cols-2 gap-4 mt-4">
                            <button
                                onClick={() => theme !== "light" && toggleTheme()}
                                className={`p-4 rounded-xl border-2 transition-all ${theme === "light"
                                    ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20"
                                    : "border-gray-200 dark:border-[#2f3336] hover:border-gray-300"
                                    }`}
                            >
                                <Sun className="w-8 h-8 mx-auto mb-2 text-orange-500" />
                                <p className="font-medium text-gray-900 dark:text-white">Light</p>
                            </button>

                            <button
                                onClick={() => theme !== "dark" && toggleTheme()}
                                className={`p-4 rounded-xl border-2 transition-all ${theme === "dark"
                                    ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20"
                                    : "border-gray-200 dark:border-[#2f3336] hover:border-gray-300"
                                    }`}
                            >
                                <Moon className="w-8 h-8 mx-auto mb-2 text-indigo-500" />
                                <p className="font-medium text-gray-900 dark:text-white">Dark</p>
                            </button>
                        </div>
                    </div>
                )}

                {/* Fresh Questions Section */}
                {activeSection === "fresh" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Fresh Questions</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            When enabled, the system remembers your past questions and generates new,
                            unique questions to avoid repetition.
                        </p>

                        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-[#1a1d21] rounded-xl">
                            <div className="flex items-center gap-3">
                                <Sparkles className="w-5 h-5 text-indigo-500" />
                                <span className="font-medium text-gray-900 dark:text-white">
                                    Generate Fresh Questions Always
                                </span>
                            </div>

                            <button
                                onClick={toggleFreshQuestions}
                                className={`relative w-14 h-7 rounded-full transition-colors ${freshQuestionsEnabled
                                    ? "bg-indigo-600"
                                    : "bg-gray-300 dark:bg-gray-600"
                                    }`}
                            >
                                <div
                                    className={`absolute top-1 w-5 h-5 bg-white rounded-full shadow transition-transform ${freshQuestionsEnabled ? "translate-x-8" : "translate-x-1"
                                        }`}
                                />
                            </button>
                        </div>

                        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-sm text-blue-700 dark:text-blue-300">
                            💡 The system stores your last 50 questions per topic to ensure variety
                        </div>
                    </div>
                )}

                {/* Private PDFs Section */}
                {activeSection === "private" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Private PDFs</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            PDFs only visible to you
                        </p>
                        {renderPDFList(privatePDFs)}
                    </div>
                )}

                {/* Public PDFs Section */}
                {activeSection === "public" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">My Posts</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            PDFs visible in the public feed
                        </p>
                        {renderPDFList(publicPDFs)}
                    </div>
                )}

                {/* Unlisted PDFs Section */}
                {activeSection === "unlisted" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Unlisted PDFs</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            PDFs accessible only via direct link
                        </p>
                        {renderPDFList(unlistedPDFs, true)}
                    </div>
                )}
            </div>
        </div>
    );
}
