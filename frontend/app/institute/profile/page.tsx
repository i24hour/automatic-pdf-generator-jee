"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
    Building2,
    Loader2,
    CheckCircle2,
    AlertCircle,
    ArrowLeft,
    Save,
} from "lucide-react";
import { API_BASE_URL } from "@/lib/config";


interface InstituteProfile {
    id: string;
    email: string;
    institute_name?: string;
    contact_number?: string;
    institute_email?: string;
}

export default function InstituteProfilePage() {
    const router = useRouter();
    const [profile, setProfile] = useState<InstituteProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    // Form state
    const [instituteName, setInstituteName] = useState("");
    const [contactNumber, setContactNumber] = useState("");
    const [instituteEmail, setInstituteEmail] = useState("");

    useEffect(() => {
        const fetchProfile = async () => {
            const token = localStorage.getItem("institute_access_token");

            if (!token) {
                router.push("/institute/login");
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/api/institute/profile`, {
                    headers: { Authorization: `Bearer ${token}` },
                });

                if (!response.ok) {
                    throw new Error("Failed to fetch profile");
                }

                const data: InstituteProfile = await response.json();
                setProfile(data);
                setInstituteName(data.institute_name || "");
                setContactNumber(data.contact_number || "");
                setInstituteEmail(data.institute_email || "");
            } catch (err) {
                if (err instanceof Error && err.message.includes("401")) {
                    router.push("/institute/login");
                } else {
                    setError("Failed to load profile");
                }
            } finally {
                setIsLoading(false);
            }
        };

        fetchProfile();
    }, [router]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);
        setSuccess(false);

        const token = localStorage.getItem("institute_access_token");

        try {
            const response = await fetch(`${API_BASE_URL}/api/institute/profile`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    institute_name: instituteName,
                    contact_number: contactNumber,
                    institute_email: instituteEmail,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Failed to update profile");
            }

            const data: InstituteProfile = await response.json();
            setProfile(data);

            // Update local storage
            const storedUser = localStorage.getItem("institute_user");
            if (storedUser) {
                const user = JSON.parse(storedUser);
                user.institute_name = data.institute_name;
                user.contact_number = data.contact_number;
                user.institute_email = data.institute_email;
                localStorage.setItem("institute_user", JSON.stringify(user));
            }

            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError("An unknown error occurred");
            }
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-white animate-spin" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-4 md:p-8">
            <div className="max-w-xl mx-auto">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <button
                        onClick={() => router.push("/institute")}
                        className="p-2 text-gray-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center">
                            <Building2 className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">Institute Profile</h1>
                            <p className="text-gray-400 text-sm">This info will appear on your PDFs</p>
                        </div>
                    </div>
                </div>

                {/* Profile Form */}
                <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 md:p-8 border border-white/20">
                    <form onSubmit={handleSave} className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Login Email
                            </label>
                            <input
                                type="email"
                                value={profile?.email || ""}
                                disabled
                                className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-gray-400 cursor-not-allowed"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Institute Name
                            </label>
                            <input
                                type="text"
                                value={instituteName}
                                onChange={(e) => setInstituteName(e.target.value)}
                                className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                placeholder="e.g., ABC Coaching Classes"
                            />
                            <p className="text-gray-500 text-xs mt-1">
                                This will appear as the header on your test papers
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Contact Number
                            </label>
                            <input
                                type="tel"
                                value={contactNumber}
                                onChange={(e) => setContactNumber(e.target.value)}
                                className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                placeholder="e.g., 9876543210"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Institute Email
                            </label>
                            <input
                                type="email"
                                value={instituteEmail}
                                onChange={(e) => setInstituteEmail(e.target.value)}
                                className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                placeholder="e.g., info@abccoaching.com"
                            />
                            <p className="text-gray-500 text-xs mt-1">
                                This email will appear in the footer of your test papers
                            </p>
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-400/10 rounded-lg p-3">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}

                        {success && (
                            <div className="flex items-center gap-2 text-green-400 text-sm bg-green-400/10 rounded-lg p-3">
                                <CheckCircle2 className="w-4 h-4" />
                                Profile updated successfully!
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isSaving}
                            className="w-full py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save className="w-5 h-5" />
                                    Save Profile
                                </>
                            )}
                        </button>
                    </form>
                </div>

                {/* Footer */}
                <p className="text-center text-gray-500 text-sm mt-6">
                    INFINITEST - A Mentors Mantra Product
                </p>
            </div>
        </div>
    );
}
