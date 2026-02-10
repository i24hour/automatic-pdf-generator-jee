'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle, CheckCircle2, FileText, Image as ImageIcon, Mic, Loader2 } from 'lucide-react';
import VoiceRecorder from '@/components/VoiceRecorder';
import DesktopSidebar from '@/components/layout/DesktopSidebar';
import MobileNav from '@/components/layout/MobileNav';
import TestGenerator from '@/components/TestGenerator';

interface Ticket {
    id: string;
    category: string;
    description: string;
    status: string;
    attachment_url?: string;
    audio_url?: string;
    created_at: string;
    admin_response?: string;
}

const CATEGORIES = [
    "Bug Report",
    "Feature Request",
    "Content Issue (Question/Answer)",
    "Payment/Billing",
    "Account Issue",
    "Other"
];

// Extracted Content Component
function SupportContent({
    activeTab, setActiveTab, loading, tickets, handleSubmit,
    category, setCategory, description, setDescription,
    screenshot, setScreenshot, voiceNote, setVoiceNote,
    submitLoading, successMsg
}: any) {
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'OPEN': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
            case 'IN_PROGRESS': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
            case 'RESOLVED': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
            case 'CLOSED': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Help & Support</h1>
            <p className="text-gray-600 dark:text-gray-400 mb-8">Report issues, suggest features, or get help.</p>

            {/* Tabs */}
            <div className="flex gap-4 mb-8 border-b border-gray-200 dark:border-gray-800">
                <button
                    onClick={() => setActiveTab('create')}
                    className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${activeTab === 'create'
                            ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                        }`}
                >
                    Report an Issue
                </button>
                <button
                    onClick={() => setActiveTab('list')}
                    className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${activeTab === 'list'
                            ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                        }`}
                >
                    My Tickets
                </button>
            </div>

            {activeTab === 'create' ? (
                <div className="bg-white dark:bg-[#16181c] rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 md:p-8">
                    {successMsg ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="p-4 bg-green-100 dark:bg-green-900/30 text-green-600 rounded-full mb-4">
                                <CheckCircle2 className="w-12 h-12" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Ticket Submitted!</h3>
                            <p className="text-gray-600 dark:text-gray-400">{successMsg}</p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Category</label>
                                <select
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-[#0a0b0d] text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 transition-all"
                                >
                                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Description</label>
                                <textarea
                                    required
                                    rows={5}
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Please describe the issue in detail..."
                                    className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-[#0a0b0d] text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 transition-all resize-none"
                                />
                            </div>

                            <div className="grid md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Screenshot <span className="text-gray-400 font-normal">(Optional)</span>
                                    </label>
                                    <div className="relative border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 hover:border-indigo-500 transition-colors text-center cursor-pointer bg-gray-50 dark:bg-gray-800/50">
                                        <input
                                            type="file"
                                            accept="image/*"
                                            onChange={(e) => setScreenshot(e.target.files?.[0] || null)}
                                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                        />
                                        {screenshot ? (
                                            <div className="flex items-center justify-center gap-2 text-green-600">
                                                <CheckCircle2 className="w-5 h-5" />
                                                <span className="text-sm font-medium truncate">{screenshot.name}</span>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center gap-2 text-gray-500">
                                                <ImageIcon className="w-6 h-6" />
                                                <span className="text-sm">Click to upload image</span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Voice Note <span className="text-gray-400 font-normal">(Optional)</span>
                                    </label>
                                    <VoiceRecorder
                                        onRecordingComplete={setVoiceNote}
                                        onDelete={() => setVoiceNote(null)}
                                    />
                                </div>
                            </div>

                            <div className="pt-4">
                                <button
                                    type="submit"
                                    disabled={submitLoading}
                                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-lg shadow-indigo-500/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {submitLoading ? (
                                        <>
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                            Submitting...
                                        </>
                                    ) : 'Submit Ticket'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    {loading ? (
                        <div className="py-12 text-center text-gray-500">Loading tickets...</div>
                    ) : tickets.length === 0 ? (
                        <div className="py-12 text-center bg-white dark:bg-[#16181c] rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
                            <FileText className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                            <p className="text-gray-500">No tickets found.</p>
                            <button onClick={() => setActiveTab('create')} className="mt-2 text-indigo-600 hover:underline">Create one?</button>
                        </div>
                    ) : (
                        tickets.map((ticket: Ticket) => (
                            <div key={ticket.id} className="bg-white dark:bg-[#16181c] rounded-xl p-6 border border-gray-200 dark:border-gray-800 shadow-sm transition-all hover:border-indigo-200 dark:hover:border-indigo-900">
                                <div className="flex flex-col md:flex-row justify-between gap-4 mb-4">
                                    <div>
                                        <div className="flex items-center gap-3 mb-1">
                                            <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getStatusColor(ticket.status)}`}>
                                                {ticket.status}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                {new Date(ticket.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <h3 className="text-lg font-bold text-gray-900 dark:text-white">{ticket.category}</h3>
                                    </div>
                                    <div className="flex gap-2">
                                        {ticket.attachment_url && (
                                            <a href={ticket.attachment_url} target="_blank" rel="noreferrer" className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-300 hover:text-indigo-600" title="View Screenshot">
                                                <ImageIcon className="w-4 h-4" />
                                            </a>
                                        )}
                                        {ticket.audio_url && (
                                            <a href={ticket.audio_url} target="_blank" rel="noreferrer" className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-600 dark:text-gray-300 hover:text-indigo-600" title="Play Voice Note">
                                                <Mic className="w-4 h-4" />
                                            </a>
                                        )}
                                    </div>
                                </div>

                                <p className="text-gray-600 dark:text-gray-300 text-sm whitespace-pre-wrap mb-4">{ticket.description}</p>

                                {ticket.admin_response && (
                                    <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30 -mx-6 -mb-6 p-6 rounded-b-xl">
                                        <p className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-widest mb-1">Admin Response</p>
                                        <p className="text-sm text-gray-700 dark:text-gray-300">{ticket.admin_response}</p>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}

export default function SupportPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<'create' | 'list'>('create');
    const [loading, setLoading] = useState(false);
    const [submitLoading, setSubmitLoading] = useState(false);
    const [tickets, setTickets] = useState<Ticket[]>([]);

    // Form State
    const [category, setCategory] = useState(CATEGORIES[0]);
    const [description, setDescription] = useState('');
    const [screenshot, setScreenshot] = useState<File | null>(null);
    const [voiceNote, setVoiceNote] = useState<File | null>(null);
    const [successMsg, setSuccessMsg] = useState('');

    useEffect(() => {
        if (activeTab === 'list') {
            fetchTickets();
        }
    }, [activeTab]);

    const fetchTickets = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app'}/support/my`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setTickets(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitLoading(true);
        setSuccessMsg('');

        try {
            const token = localStorage.getItem('auth_token');
            const formData = new FormData();
            formData.append('category', category);
            formData.append('description', description);
            if (screenshot) formData.append('screenshot', screenshot);
            if (voiceNote) formData.append('voice_note', voiceNote);

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app'}/support/create`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (!res.ok) throw new Error('Failed to create ticket');

            setSuccessMsg('Ticket created successfully! We will get back to you soon.');
            setDescription('');
            setScreenshot(null);
            setVoiceNote(null);
            setTimeout(() => setActiveTab('list'), 2000);

        } catch (err) {
            console.error(err);
            alert('Something went wrong. Please try again.');
        } finally {
            setSubmitLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile View */}
            <div className="md:hidden pb-20">
                <SupportContent
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    loading={loading}
                    tickets={tickets}
                    handleSubmit={handleSubmit}
                    category={category}
                    setCategory={setCategory}
                    description={description}
                    setDescription={setDescription}
                    screenshot={screenshot}
                    setScreenshot={setScreenshot}
                    voiceNote={voiceNote}
                    setVoiceNote={setVoiceNote}
                    submitLoading={submitLoading}
                    successMsg={successMsg}
                />
                <MobileNav />
            </div>

            {/* Desktop View: 3-Column Layout */}
            <div className="hidden md:flex min-h-screen w-full">
                {/* Left Sidebar: Navigation */}
                <DesktopSidebar />

                {/* Center Column: Support Content */}
                <main className="flex-1 ml-[275px] border-r border-gray-200 dark:border-[#2f3336] min-h-screen bg-gray-50 dark:bg-[#0a0b0d]">
                    <SupportContent
                        activeTab={activeTab}
                        setActiveTab={setActiveTab}
                        loading={loading}
                        tickets={tickets}
                        handleSubmit={handleSubmit}
                        category={category}
                        setCategory={setCategory}
                        description={description}
                        setDescription={setDescription}
                        screenshot={screenshot}
                        setScreenshot={setScreenshot}
                        voiceNote={voiceNote}
                        setVoiceNote={setVoiceNote}
                        submitLoading={submitLoading}
                        successMsg={successMsg}
                    />
                </main>

                {/* Right Sidebar: Test Generator */}
                <aside className="w-[400px] p-4 h-screen sticky top-0 overflow-y-auto border-l border-gray-200 dark:border-[#2f3336] bg-white dark:bg-black hidden lg:block">
                    <div className="mb-4">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white px-2">Generate Test</h2>
                    </div>
                    <TestGenerator />
                </aside>
            </div>
        </div>
    );
}
