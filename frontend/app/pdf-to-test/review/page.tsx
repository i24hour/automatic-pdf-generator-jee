'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
    Loader2, AlertCircle, CheckCircle, Edit3, Trash2,
    Image as ImageIcon, Save, Play, ChevronLeft, ChevronRight
} from 'lucide-react';
import { API_BASE_URL as API_BASE } from '@/lib/config';

interface ReviewQuestion {
    question_number: number;
    text: string;
    options: Record<string, string>;
    answer: string | null;
    type: string;
    subject: string;
    image_urls: string[];
}

interface ReviewData {
    job_id: string;
    status: string;
    title: string;
    duration_minutes: number;
    exam_type: string;
    questions: ReviewQuestion[];
    subjects: string[];
    pages_total?: number;
    pages_done?: number;
}

function ReviewContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const jobId = searchParams.get('job_id');
    const { authFetch } = useAuth();

    const [data, setData] = useState<ReviewData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeQIndex, setActiveQIndex] = useState(0);

    // Fetch review data
    useEffect(() => {
        if (!jobId) {
            setError('No job ID provided');
            setLoading(false);
            return;
        }

        const fetchData = async () => {
            try {
                const res = await authFetch(`${API_BASE}/api/pdf-to-test/${jobId}/review`);
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to load review data');
                }
                const d = await res.json();
                setData(d);
                if (d.status !== 'parsing') {
                    setLoading(false);
                }
            } catch (err: any) {
                setError(err.message);
                setLoading(false);
            }
        };

        fetchData();
        // Poll every 2s while still parsing
        const interval = setInterval(async () => {
            if (data?.status === 'parsing' || loading) {
                await fetchData();
            }
        }, 2000);
        return () => clearInterval(interval);
    }, [jobId, authFetch, data?.status, loading]);

    const updateQuestion = (index: number, updates: Partial<ReviewQuestion>) => {
        if (!data) return;
        const newQuestions = [...data.questions];
        newQuestions[index] = { ...newQuestions[index], ...updates };
        setData({ ...data, questions: newQuestions });
    };

    const removeQuestion = (index: number) => {
        if (!data) return;
        const newQuestions = data.questions.filter((_, i) => i !== index);
        setData({ ...data, questions: newQuestions });
        if (activeQIndex >= newQuestions.length) {
            setActiveQIndex(Math.max(0, newQuestions.length - 1));
        }
    };

    const handleSave = async () => {
        if (!data || !jobId) return;
        setSaving(true);
        try {
            const res = await authFetch(`${API_BASE}/api/pdf-to-test/${jobId}/review`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    questions: data.questions,
                    title: data.title,
                    duration_minutes: data.duration_minutes,
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to save');
            }
            alert('Saved successfully');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleCreateTest = async () => {
        if (!jobId) return;
        setCreating(true);
        try {
            const res = await authFetch(`${API_BASE}/api/pdf-to-test/create-test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    visibility: 'PRIVATE',
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create test');
            }
            const result = await res.json();
            router.push(result.redirect_url);
        } catch (err: any) {
            setError(err.message);
            setCreating(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
                <div className="flex flex-col items-center gap-4 max-w-sm w-full px-6">
                    <div className="relative">
                        <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Connecting to AI...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
                <div className="max-w-md w-full bg-white dark:bg-gray-900 rounded-xl p-6 border border-red-200 dark:border-red-800">
                    <div className="flex items-center gap-2 text-red-600 dark:text-red-400 mb-3">
                        <AlertCircle className="w-5 h-5" />
                        <h2 className="font-semibold">PDF Processing Failed</h2>
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 text-sm mb-2">{error}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mb-4">
                        Make sure the PDF is not password-protected and contains readable exam content.
                        Both scanned and digital PDFs are supported.
                    </p>
                    <button
                        onClick={() => router.push('/pdf-to-test')}
                        className="mt-2 text-sm text-blue-600 hover:underline"
                    >
                        ← Go back to upload
                    </button>
                </div>
            </div>
        );
    }


    if (data?.status === 'parsing') {
        const done = data.pages_done ?? 0;
        const total = data.pages_total ?? 0;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
                <div className="max-w-sm w-full">
                    <div className="bg-white dark:bg-gray-900 rounded-2xl p-8 shadow-sm border border-gray-200 dark:border-gray-800 flex flex-col items-center gap-5">
                        {/* AI Brain Icon */}
                        <div className="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                        </div>

                        <div className="text-center">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Gemini AI is reading your PDF</h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                {total > 0
                                    ? `Analysing page ${done} of ${total}…`
                                    : 'Starting analysis…'}
                            </p>
                        </div>

                        {/* Progress bar */}
                        <div className="w-full">
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                                <div
                                    className="h-2.5 rounded-full bg-blue-600 transition-all duration-500"
                                    style={{ width: `${pct || 5}%` }}
                                />
                            </div>
                            <div className="flex justify-between mt-1.5">
                                <span className="text-xs text-gray-400">{total > 0 ? `${done}/${total} pages` : 'Starting…'}</span>
                                <span className="text-xs text-blue-600 font-medium">{pct}%</span>
                            </div>
                        </div>

                        <p className="text-xs text-gray-400 text-center">
                            Works for scanned &amp; digital PDFs · Usually takes 1–3 min
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    if (!data || data.questions.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
                <div className="text-center">
                    <p className="text-gray-600 dark:text-gray-400">No questions found in this PDF.</p>
                    <button
                        onClick={() => router.push('/pdf-to-test')}
                        className="mt-4 text-blue-600 hover:underline"
                    >
                        Upload another
                    </button>
                </div>
            </div>
        );
    }

    const q = data.questions[activeQIndex];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-6 px-4">
            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
                    <div>
                        <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                            Review Extracted Questions
                        </h1>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {data.questions.length} questions found • {data.subjects.join(', ')}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                        >
                            <Save className="w-4 h-4" />
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                        <button
                            onClick={handleCreateTest}
                            disabled={creating}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                        >
                            <Play className="w-4 h-4" />
                            {creating ? 'Creating...' : 'Create Test'}
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Sidebar: Question List */}
                    <div className="lg:col-span-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 h-fit max-h-[70vh] overflow-y-auto">
                        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                            Questions
                        </h3>
                        <div className="space-y-1">
                            {data.questions.map((question, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setActiveQIndex(idx)}
                                    className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                                        idx === activeQIndex
                                            ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                                            : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-400'
                                    }`}
                                >
                                    <span className="font-medium">Q{question.question_number}</span>
                                    <span className="truncate flex-1">{question.subject}</span>
                                    {question.image_urls.length > 0 && (
                                        <ImageIcon className="w-3 h-3 text-gray-400" />
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Main: Active Question Editor */}
                    <div className="lg:col-span-2 space-y-4">
                        {/* Navigation */}
                        <div className="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 px-4 py-3">
                            <button
                                onClick={() => setActiveQIndex(Math.max(0, activeQIndex - 1))}
                                disabled={activeQIndex === 0}
                                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg disabled:opacity-30"
                            >
                                <ChevronLeft className="w-5 h-5" />
                            </button>
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                Question {activeQIndex + 1} of {data.questions.length}
                            </span>
                            <button
                                onClick={() => setActiveQIndex(Math.min(data.questions.length - 1, activeQIndex + 1))}
                                disabled={activeQIndex === data.questions.length - 1}
                                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg disabled:opacity-30"
                            >
                                <ChevronRight className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Question Card */}
                        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 space-y-4">
                            {/* Subject + Type */}
                            <div className="flex items-center gap-3">
                                <select
                                    value={q.subject}
                                    onChange={(e) => updateQuestion(activeQIndex, { subject: e.target.value })}
                                    className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300"
                                >
                                    {data.subjects.map((s) => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                    <option value="Physics">Physics</option>
                                    <option value="Chemistry">Chemistry</option>
                                    <option value="Maths">Maths</option>
                                </select>
                                <span className="px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-xs text-gray-600 dark:text-gray-400 uppercase">
                                    {q.type}
                                </span>
                                {q.answer && (
                                    <span className="px-2 py-1 rounded-md bg-green-50 dark:bg-green-900/20 text-xs text-green-700 dark:text-green-400">
                                        Ans: {q.answer}
                                    </span>
                                )}
                            </div>

                            {/* Question Text */}
                            <div>
                                <label className="text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wide">
                                    Question Text
                                </label>
                                <textarea
                                    value={q.text}
                                    onChange={(e) => updateQuestion(activeQIndex, { text: e.target.value })}
                                    rows={4}
                                    className="w-full mt-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-y"
                                />
                            </div>

                            {/* Images */}
                            {q.image_urls.length > 0 && (
                                <div>
                                    <label className="text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                        <ImageIcon className="w-3 h-3" />
                                        Extracted Images
                                    </label>
                                    <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        {q.image_urls.map((url, i) => (
                                            <div key={i} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-gray-50 dark:bg-gray-850">
                                                <img
                                                    src={url}
                                                    alt={`Diagram ${i + 1}`}
                                                    className="w-full h-40 object-contain"
                                                />
                                                <div className="px-2 py-1 text-xs text-gray-500 truncate">
                                                    {url.split('/').pop()}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Options (for MCQ) */}
                            {q.type === 'mcq' && (
                                <div className="space-y-2">
                                    <label className="text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wide">
                                        Options
                                    </label>
                                    {Object.entries(q.options).map(([key, value]) => (
                                        <div key={key} className="flex items-center gap-2">
                                            <span className="w-8 text-center text-sm font-medium text-gray-600 dark:text-gray-400">
                                                {key})
                                            </span>
                                            <input
                                                type="text"
                                                value={value}
                                                onChange={(e) => {
                                                    const newOptions = { ...q.options, [key]: e.target.value };
                                                    updateQuestion(activeQIndex, { options: newOptions });
                                                }}
                                                className="flex-1 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                            />
                                            <button
                                                onClick={() => updateQuestion(activeQIndex, { answer: key })}
                                                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                                                    q.answer === key
                                                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                                                        : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-gray-200'
                                                }`}
                                            >
                                                {q.answer === key ? <CheckCircle className="w-3 h-3" /> : 'Mark'}
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Numerical Answer */}
                            {q.type === 'numerical' && (
                                <div>
                                    <label className="text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wide">
                                        Correct Answer
                                    </label>
                                    <input
                                        type="text"
                                        value={q.answer || ''}
                                        onChange={(e) => updateQuestion(activeQIndex, { answer: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                        placeholder="Enter correct numerical answer"
                                    />
                                </div>
                            )}

                            {/* Actions */}
                            <div className="pt-3 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                                <button
                                    onClick={() => removeQuestion(activeQIndex)}
                                    className="text-red-600 dark:text-red-400 hover:text-red-700 text-sm flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                    Remove Question
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function PDFToTestReviewPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
        }>
            <ReviewContent />
        </Suspense>
    );
}
