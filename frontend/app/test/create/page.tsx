'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Minus, Plus, BookOpen, AlertCircle, CheckCircle2, Globe, Lock, School } from 'lucide-react';
import TopicSelector from '@/components/TopicSelector';

import { API_BASE_URL as API_BASE } from '@/lib/config';
import { useAuth } from '@/lib/auth-context';

interface DifficultyDist {
    easy: number;
    medium: number;
    hard: number;
}

interface SubjectConfig {
    enabled: boolean;
    count: number;
    difficulty: DifficultyDist;
    topics: string;
    selectedChapters: string[];
}

type ExamType = 'JEE_MAINS' | 'JEE_ADV' | 'NEET' | 'CUSTOM';
type VisibilityType = 'PRIVATE' | 'COMMUNITY' | 'CLASSROOM';

const DEFAULT_DIFFICULTY: DifficultyDist = { easy: 3, medium: 4, hard: 3 };

const INITIAL_SUBJECTS: Record<string, SubjectConfig> = {
    'Physics': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '', selectedChapters: [] },
    'Chemistry': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '', selectedChapters: [] },
    'Maths': { enabled: true, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '', selectedChapters: [] },
    'Biology': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '', selectedChapters: [] },
    'Botany': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '', selectedChapters: [] },
    'Zoology': { enabled: false, count: 10, difficulty: { ...DEFAULT_DIFFICULTY }, topics: '', selectedChapters: [] },
};

function CreateTestForm() {
    const router = useRouter();
    const { authFetch } = useAuth();
    const searchParams = useSearchParams();
    const mode = searchParams.get('mode'); // 'public' or null

    // Default visibility based on mode query param (backward compatibility)
    const [visibility, setVisibility] = useState<VisibilityType>(mode === 'public' ? 'COMMUNITY' : 'PRIVATE');

    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [error, setError] = useState('');
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Check auth on mount
    useEffect(() => {
        const token = localStorage.getItem('auth_token');
        setIsAuthenticated(!!token);
    }, []);

    const [examType, setExamType] = useState<ExamType>('JEE_MAINS');
    const [subjects, setSubjects] = useState<Record<string, SubjectConfig>>(INITIAL_SUBJECTS);
    const [duration, setDuration] = useState(60);

    // Update defaults based on exam type
    useEffect(() => {
        setSubjects(prev => {
            const next = { ...prev };
            if (examType === 'NEET') {
                next['Maths'].enabled = false;
                next['Biology'].enabled = false;
                next['Botany'].enabled = true;
                next['Zoology'].enabled = true;

                next['Physics'].count = 10;
                next['Chemistry'].count = 10;
                next['Botany'].count = 10;
                next['Zoology'].count = 10;
            } else {
                next['Maths'].enabled = true;
                next['Biology'].enabled = false;
                next['Botany'].enabled = false;
                next['Zoology'].enabled = false;

                next['Physics'].count = 10;
                next['Chemistry'].count = 10;
                next['Maths'].count = 10;
            }
            return next;
        });
    }, [examType]);

    const handleSubjectChange = (subject: string, field: keyof SubjectConfig, value: any) => {
        setSubjects(prev => ({
            ...prev,
            [subject]: { ...prev[subject], [field]: value }
        }));
    };

    const handleDifficultyChange = (subject: string, type: keyof DifficultyDist, value: number) => {
        setSubjects(prev => {
            const currentDist = { ...prev[subject].difficulty };
            currentDist[type] = Math.max(0, value);

            const newTotal = currentDist.easy + currentDist.medium + currentDist.hard;

            return {
                ...prev,
                [subject]: {
                    ...prev[subject],
                    difficulty: currentDist,
                    count: newTotal
                }
            };
        });
    };

    const totalQuestions = Object.values(subjects)
        .filter(s => s.enabled)
        .reduce((sum, s) => sum + s.count, 0);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Check auth BEFORE starting any loading state
        const token = localStorage.getItem('auth_token');
        if (!token) {
            router.push(`/login?redirect=${encodeURIComponent('/test/create')}`);
            return;
        }

        setLoading(true);
        setProgress(0);
        setError('');

        const progressInterval = setInterval(() => {
            setProgress(prev => {
                // Simulate asymptotic progress up to 99%
                const increment = Math.max(1, (99 - prev) * 0.1);
                return prev >= 99 ? 99 : prev + increment;
            });
        }, 800);


        // Prepare payload
        const subjectInputs: Record<string, any> = {};

        for (const [subj, config] of Object.entries(subjects)) {
            if (!config.enabled || config.count <= 0) continue;

            if (config.count < 1) {
                setError(`${subj}: Must have at least 1 question`);
                setLoading(false);
                return;
            }

            // Check mandatory topics for Community Tests
            if (visibility === 'COMMUNITY' && !config.topics.trim()) {
                setError(`${subj}: At least one topic is required for Community Tests`);
                setLoading(false);
                return;
            }

            subjectInputs[subj] = {
                count: config.count,
                difficulty: config.difficulty,
                topics: config.topics.split(',').map(t => t.trim()).filter(Boolean)
            };
        }

        try {
            // UNIFIED ENDPOINT
            const endpoint = `${API_BASE}/api/tests/create`;

            // 1. Create Master Test (authFetch: refresh on 401 so mobile sessions don't fail as opaque "Failed to fetch")
            const response = await authFetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    exam_type: examType,
                    subject_inputs: subjectInputs,
                    duration_minutes: duration,
                    visibility: visibility,
                    classroom_id: null // Placeholder for future
                })
            });

            if (!response.ok) {
                let errMsg = 'Failed to create test';
                try {
                    const text = await response.text();
                    const data = JSON.parse(text);
                    if (data.detail) errMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
                } catch {
                    // Non-JSON error body (e.g. proxy timeout HTML page) — keep generic message
                }
                throw new Error(errMsg);
            }

            let data: { test_id: string };
            try {
                data = await response.json();
            } catch {
                throw new Error('Invalid response from server. Please try again.');
            }
            console.log('Master Test created:', data);

            // 2. Launch Attempt (Create Session)
            try {
                const launchResponse = await authFetch(`${API_BASE}/test/${data.test_id}/launch`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                if (!launchResponse.ok) {
                    throw new Error('Test created but failed to start session.');
                }

                let launchData: { redirect_url: string };
                try {
                    launchData = await launchResponse.json();
                } catch {
                    throw new Error('Test created but launch response was invalid. Please try again from My Tests.');
                }

                // 3. Redirect to Attempt Interface
                router.push(launchData.redirect_url);

            } catch (launchErr) {
                console.error('Launch failed:', launchErr);
                setError('Test created but launch failed. Please try again from My Tests/Community');
                clearInterval(progressInterval);
            }

        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to create test';
            setError(errorMessage);
            clearInterval(progressInterval);
        } finally {
            clearInterval(progressInterval);
            setProgress(100);
            setTimeout(() => {
                setLoading(false);
            }, 500); // Small delay to let user see 100%
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#0a0b0d]">
            {/* Header */}
            <header className="bg-white/80 dark:bg-[#16181c]/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            INFINITEST
                        </Link>
                        <span className="text-gray-500 dark:text-gray-400">|</span>
                        <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                            Create Test
                        </span>
                    </div>
                    <Link href="/test" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
                        ← Back to History
                    </Link>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <form onSubmit={handleSubmit} className="space-y-8">

                    {/* Step 0: Visibility Selection */}
                    <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Who is this test for?</h2>
                        <div className="grid md:grid-cols-3 gap-4">
                            <button
                                type="button"
                                onClick={() => setVisibility('PRIVATE')}
                                className={`p-4 rounded-xl border-2 text-left transition-all ${visibility === 'PRIVATE'
                                    ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300'
                                    }`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Lock className={`w-5 h-5 ${visibility === 'PRIVATE' ? 'text-indigo-600' : 'text-gray-500'}`} />
                                    <span className="font-bold text-gray-900 dark:text-white">Just Me</span>
                                </div>
                                <p className="text-sm text-gray-500">Private practice session. Not visible to others.</p>
                            </button>

                            <button
                                type="button"
                                onClick={() => setVisibility('COMMUNITY')}
                                className={`p-4 rounded-xl border-2 text-left transition-all ${visibility === 'COMMUNITY'
                                    ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300'
                                    }`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Globe className={`w-5 h-5 ${visibility === 'COMMUNITY' ? 'text-indigo-600' : 'text-gray-500'}`} />
                                    <span className="font-bold text-gray-900 dark:text-white">Everyone</span>
                                </div>
                                <p className="text-sm text-gray-500">Public community test. Visible on leaderboard.</p>
                            </button>

                            <button
                                type="button"
                                disabled
                                className="p-4 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-800 text-left opacity-60 cursor-not-allowed"
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <School className="w-5 h-5 text-gray-400" />
                                    <span className="font-bold text-gray-400">My Class</span>
                                </div>
                                <p className="text-sm text-gray-400">Classroom assignments. (Coming Soon)</p>
                            </button>
                        </div>
                    </div>

                    {/* Step 1: General Config */}
                    <div className="bg-white dark:bg-[#16181c] rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">1. General Configuration</h2>

                        <div className="grid md:grid-cols-2 gap-8">
                            {/* Exam Type */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Exam Type</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {(['JEE_MAINS', 'JEE_ADV', 'NEET', 'CUSTOM'] as ExamType[]).map((type) => (
                                        <button
                                            key={type}
                                            type="button"
                                            onClick={() => setExamType(type)}
                                            className={`py-2 px-3 rounded-lg border font-medium text-sm transition-all ${examType === type
                                                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                                : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-indigo-300'
                                                }`}
                                        >
                                            {type.replace('_', ' ')}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Duration */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Duration</label>
                                <div className="flex flex-wrap gap-2">
                                    {[30, 60, 90, 120, 180].map((mins) => (
                                        <button
                                            key={mins}
                                            type="button"
                                            onClick={() => setDuration(mins)}
                                            className={`px-4 py-2 rounded-lg border font-medium text-sm transition-all ${duration === mins
                                                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                                                : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-indigo-300'
                                                }`}
                                        >
                                            {mins}m
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Subject Configuration */}
                    <div className="space-y-4">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white px-2">2. Subject Configuration</h2>

                        {Object.entries(subjects).map(([subject, config]) => (
                            config.enabled && (
                                <div key={subject} className="bg-white dark:bg-[#16181c] rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 transition-all hover:border-indigo-200 dark:hover:border-indigo-900">
                                    <div className="flex flex-col md:flex-row gap-6">

                                        {/* Subject Info & Count */}
                                        <div className="md:w-1/4 space-y-4">
                                            <div className="flex items-center gap-2">
                                                <div className={`p-2 rounded-lg ${subject === 'Physics' ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30' :
                                                    subject === 'Chemistry' ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/30' :
                                                        subject === 'Biology' ? 'bg-green-100 text-green-600 dark:bg-green-900/30' :
                                                            subject === 'Botany' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30' :
                                                                subject === 'Zoology' ? 'bg-teal-100 text-teal-600 dark:bg-teal-900/30' :
                                                                    'bg-orange-100 text-orange-600 dark:bg-orange-900/30'
                                                    }`}>
                                                    <BookOpen className="w-5 h-5" />
                                                </div>
                                                <h3 className="font-bold text-lg text-gray-900 dark:text-white">{subject}</h3>
                                            </div>

                                            <div>
                                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Questions</label>
                                                <div className="flex items-center mt-1">
                                                    <span className="text-2xl font-bold font-mono text-gray-900 dark:text-white">
                                                        {config.count}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Config details */}
                                        <div className="md:w-3/4 grid md:grid-cols-2 gap-6 pl-0 md:pl-6 md:border-l border-gray-100 dark:border-gray-800">

                                            {/* Topics Input */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                    Topics {visibility === 'COMMUNITY' ? <span className="text-red-500">*</span> : <span className="text-gray-400 font-normal">(Optional)</span>}
                                                </label>
                                                <TopicSelector
                                                    subject={subject}
                                                    customTopic={config.topics}
                                                    selectedChapters={config.selectedChapters || []}
                                                    onCustomTopicChange={(val) => handleSubjectChange(subject, 'topics', val)}
                                                    onSelectionChange={(chapters) => {
                                                        const newTopics = chapters.join(', ');
                                                        setSubjects(prev => ({
                                                            ...prev,
                                                            [subject]: {
                                                                ...prev[subject],
                                                                selectedChapters: chapters,
                                                                topics: newTopics
                                                            }
                                                        }));
                                                    }}
                                                    placeholder={subject === 'Physics' ? 'e.g. Optics, Mechanics' : 'e.g. Organic, Electrochemistry'}
                                                    className="w-full"
                                                    error={visibility === 'COMMUNITY' && !config.topics.trim() && error.includes(subject)}
                                                />
                                                <p className="mt-1 text-xs text-gray-500">Comma-separated topics</p>
                                            </div>

                                            {/* Difficulty Sliders */}
                                            <div className="space-y-3">
                                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Difficulty Distribution (Questions)</label>

                                                <div className="grid grid-cols-3 gap-3">
                                                    <div>
                                                        <label className="block text-xs text-green-600 dark:text-green-400 font-medium mb-1">Easy</label>
                                                        <input
                                                            type="number" min="0" step="1"
                                                            value={config.difficulty.easy}
                                                            onChange={(e) => handleDifficultyChange(subject, 'easy', Number(e.target.value))}
                                                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-[#0a0b0d]"
                                                        />
                                                    </div>

                                                    <div>
                                                        <label className="block text-xs text-yellow-600 dark:text-yellow-400 font-medium mb-1">Medium</label>
                                                        <input
                                                            type="number" min="0" step="1"
                                                            value={config.difficulty.medium}
                                                            onChange={(e) => handleDifficultyChange(subject, 'medium', Number(e.target.value))}
                                                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-[#0a0b0d]"
                                                        />
                                                    </div>

                                                    <div>
                                                        <label className="block text-xs text-red-600 dark:text-red-400 font-medium mb-1">Hard</label>
                                                        <input
                                                            type="number" min="0" step="1"
                                                            value={config.difficulty.hard}
                                                            onChange={(e) => handleDifficultyChange(subject, 'hard', Number(e.target.value))}
                                                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-[#0a0b0d]"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )
                        ))}
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="fixed bottom-16 md:bottom-0 left-0 right-0 bg-white/95 dark:bg-[#16181c]/95 backdrop-blur-md border-t border-gray-200 dark:border-gray-800 px-4 py-3 z-40">
                        <div className="max-w-5xl mx-auto space-y-3 md:space-y-0 md:flex md:justify-between md:items-center">
                            {/* Stats row - always horizontal */}
                            <div className="flex items-center justify-between md:justify-start gap-4 md:gap-8">
                                <div className="text-center md:text-left">
                                    <span className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs uppercase tracking-wider">Questions</span>
                                    <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">{totalQuestions}</p>
                                </div>
                                <div className="text-center md:text-left">
                                    <span className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs uppercase tracking-wider">Marks</span>
                                    <p className="text-lg md:text-2xl font-bold text-indigo-600 dark:text-indigo-400">{totalQuestions * 4}</p>
                                </div>
                                <div className="text-center md:text-left">
                                    <span className="text-gray-500 dark:text-gray-400 text-[10px] md:text-xs uppercase tracking-wider">Duration</span>
                                    <p className="text-lg md:text-2xl font-bold text-gray-900 dark:text-white">{duration}m</p>
                                </div>
                            </div>
                                            {/* Create button */}
                            <div className="w-full md:w-auto">
                                {!isAuthenticated && (
                                    <p className="text-amber-500 text-xs mb-2 text-center md:text-right flex items-center justify-end gap-1">
                                        <AlertCircle className="w-3 h-3" />
                                        Not authenticated — you'll be redirected to login
                                    </p>
                                )}
                                {error && (
                                    <p className="text-red-500 text-sm mb-2 text-center md:text-right">{error}</p>
                                )}
                                <button
                                    type="submit"
                                    disabled={loading || totalQuestions < 1}
                                    className="w-full md:w-auto px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 relative overflow-hidden"
                                >
                                    {loading && (
                                        <div 
                                            className="absolute left-0 top-0 bottom-0 bg-white/20 transition-all duration-300"
                                            style={{ width: `${Math.round(progress)}%` }}
                                        />
                                    )}
                                    {loading ? (
                                        <span className="relative z-10 flex items-center gap-2">
                                            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                                            Creating... {Math.round(progress)}%
                                        </span>
                                    ) : (
                                        <>
                                            <CheckCircle2 className="w-5 h-5 relative z-10" />
                                            <span className="relative z-10">Create Test</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                    {/* Spacer for fixed bottom bar + mobile nav */}
                    <div className="h-40 md:h-24"></div>
                </form>
            </main>
        </div>
    );
}

export default function CreateTestPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            <CreateTestForm />
        </Suspense>
    );
}
