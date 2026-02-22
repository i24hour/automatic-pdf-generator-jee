'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ChevronLeft, ChevronRight, Menu, X } from 'lucide-react';
import MathText from '@/components/MathText';
import DiagramRenderer from '@/components/test/DiagramRenderer';

import { API_BASE_URL as API_BASE } from '@/lib/config';

interface PaletteItem {
    index: number;
    status: string;
    subject: string;
}

interface QuestionData {
    question_index: number;
    total_questions: number;
    subject: string;
    topic: string;
    difficulty: string;
    question_type: string;
    question_text: string;
    options: Record<string, string> | null;
    status: string;
    user_answer: string | null;
    is_marked_for_review: boolean;
    time_remaining_seconds: number;
    diagram_json?: string;
}

interface TestState {
    test_id: string;
    exam_type: string;
    status: string;
    current_question_index: number;
    total_questions: number;
    duration_minutes: number;
    time_remaining_seconds: number;
    palette: PaletteItem[];
    subjects: string[];
}

export default function TestInterfacePage() {
    const router = useRouter();
    const params = useParams();
    const testId = params.id as string;

    const [testState, setTestState] = useState<TestState | null>(null);
    const [question, setQuestion] = useState<QuestionData | null>(null);
    const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
    const [timeRemaining, setTimeRemaining] = useState(0);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [showSubmitModal, setShowSubmitModal] = useState(false);
    const [examSummary, setExamSummary] = useState<{
        total: number;
        answered: number;
        not_answered: number;
        marked_review: number;
        answered_marked: number;
        not_visited: number;
    } | null>(null);
    const [activeSection, setActiveSection] = useState<string | null>(null);
    const [questionStartTime, setQuestionStartTime] = useState(Date.now());
    const [showPalette, setShowPalette] = useState(false); // Mobile palette toggle

    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

    // Fetch test state
    const fetchTestState = useCallback(async () => {
        if (!token) return;
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/state`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setTestState(data);
                setTimeRemaining(data.time_remaining_seconds);
                if (!activeSection && data.subjects.length > 0) {
                    setActiveSection(data.subjects[0]);
                }
            }
        } catch (error) {
            console.error('Failed to fetch test state:', error);
        }
    }, [testId, token, activeSection]);

    // Fetch question
    const fetchQuestion = useCallback(async (index: number) => {
        if (!token) return;
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/question/${index}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setQuestion(data);
                setSelectedAnswer(data.user_answer);
                setTimeRemaining(data.time_remaining_seconds);
                setQuestionStartTime(Date.now());
                // NOTE: Do NOT call setActiveSection here — the tab should only
                // change when the USER explicitly clicks a subject tab.
            }
        } catch (error) {
            console.error('Failed to fetch question:', error);
        }
    }, [testId, token]);

    // Initial load
    useEffect(() => {
        const load = async () => {
            await fetchTestState();
            await fetchQuestion(0);
            setLoading(false);
        };
        load();
    }, [fetchTestState, fetchQuestion]);

    // Timer countdown
    useEffect(() => {
        // If time is up, auto-submit
        if (timeRemaining <= 0) {
            if (testState?.status === 'IN_PROGRESS' && !actionLoading) {
                handleSubmit();
            }
            return;
        }

        const interval = setInterval(() => {
            setTimeRemaining(prev => Math.max(0, prev - 1));
        }, 1000);

        return () => clearInterval(interval);
    }, [timeRemaining, testState?.status, actionLoading]);

    // Calculate time spent on current question
    const getTimeSpent = () => Math.floor((Date.now() - questionStartTime) / 1000);

    // Handle action
    const handleAction = async (action: string, jumpIndex?: number) => {
        // For JUMP (subject switch), allow even if actionLoading to avoid blocking tab clicks
        if (!question || (actionLoading && action !== 'JUMP')) return;
        setActionLoading(true);

        try {
            const response = await fetch(`${API_BASE}/test/${testId}/action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    question_index: question.question_index,
                    action,
                    selected_answer: selectedAnswer,
                    time_spent_seconds: getTimeSpent(),
                    jump_to_index: jumpIndex
                })
            });

            if (response.ok) {
                const data = await response.json();

                // Update test state from combined response (no extra API call)
                if (data.palette && data.subjects) {
                    setTestState(prev => prev ? {
                        ...prev,
                        palette: data.palette,
                        subjects: data.subjects,
                        time_remaining_seconds: data.time_remaining_seconds,
                        current_question_index: data.next_question_index,
                    } : prev);
                    setTimeRemaining(data.time_remaining_seconds);
                }

                // Update question from combined response
                if (data.next_question) {
                    setQuestion(data.next_question);
                    setSelectedAnswer(data.next_question.user_answer);
                    setTimeRemaining(data.next_question.time_remaining_seconds);
                    setQuestionStartTime(Date.now());
                    setActiveSection(data.next_question.subject);
                } else {
                    console.error('Missing next_question in response - Backend update required');
                }
            }
        } catch (error) {
            console.error('Action failed:', error);
        } finally {
            setActionLoading(false);
        }
    };

    // Fetch exam summary for submit modal
    const fetchSummary = async () => {
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/summary`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setExamSummary(data);
            }
        } catch (error) {
            console.error('Failed to fetch summary:', error);
        }
    };

    // Handle submit
    const handleSubmit = async () => {
        if (actionLoading) return;
        setActionLoading(true);
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/submit`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                router.push(data.redirect_url);
            } else {
                setActionLoading(false);
            }
        } catch (error) {
            console.error('Submit failed:', error);
            setActionLoading(false);
        }
    };

    // Format time
    const formatTime = (seconds: number) => {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    // Keyboard Shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (loading || showSubmitModal) return;

            switch (e.key) {
                case '1':
                case 'a':
                case 'A':
                    if (question?.options && Object.keys(question.options).length >= 1) setSelectedAnswer('A');
                    break;
                case '2':
                case 'b':
                case 'B':
                    if (question?.options && Object.keys(question.options).length >= 2) setSelectedAnswer('B');
                    break;
                case '3':
                case 'c':
                case 'C':
                    if (question?.options && Object.keys(question.options).length >= 3) setSelectedAnswer('C');
                    break;
                case '4':
                case 'd':
                case 'D':
                    if (question?.options && Object.keys(question.options).length >= 4) setSelectedAnswer('D');
                    break;
                case 'ArrowLeft':
                    if (question && question.question_index > 0) handleAction('BACK');
                    break;
                case 'ArrowRight':
                    if (question && question.question_index < (testState?.total_questions || 0) - 1) handleAction('NEXT');
                    break;
                case 's':
                case 'S':
                    if (question) handleAction('SAVE_NEXT');
                    break;
                case 'm':
                case 'M':
                    if (question) handleAction('MARK_NEXT');
                    break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [question, testState, loading, showSubmitModal, selectedAnswer, handleAction]);

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'NOT_VISITED': return 'bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-300';
            case 'NOT_ANSWERED': return 'bg-red-500 text-white';
            case 'ANSWERED': return 'bg-green-500 text-white';
            case 'MARKED_REVIEW': return 'bg-purple-500 text-white';
            case 'ANSWERED_MARKED': return 'bg-purple-500 text-white ring-2 ring-green-400';
            default: return 'bg-gray-300 text-gray-700';
        }
    };

    if (loading || !testState || !question) {
        return (
            <div className="min-h-screen bg-gray-100 dark:bg-[#0a0b0d] flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    // Filter palette by active section
    const filteredPalette = activeSection
        ? testState.palette.filter(p => p.subject === activeSection)
        : testState.palette;

    return (
        <div className="min-h-screen bg-gray-100 dark:bg-[#0a0b0d] flex flex-col">
            {/* Header - NTA Style */}
            <header className="bg-gradient-to-r from-orange-500 to-orange-600 text-white py-2 px-4 shrink-0">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <button
                            className="md:hidden p-1 hover:bg-white/10 rounded"
                            onClick={() => setShowPalette(!showPalette)}
                        >
                            <Menu className="w-6 h-6" />
                        </button>
                        <span className="text-xl font-bold hidden md:inline">🎯 INFINITEST</span>
                        <span className="text-xl font-bold md:hidden">🎯</span>
                        <span className="text-sm opacity-80 truncate max-w-[120px] md:max-w-none">
                            {testState.exam_type.replace('_', ' ')}
                        </span>
                    </div>
                    <div className="flex items-center gap-4">
                        {actionLoading && (
                            <span className="text-sm font-medium animate-pulse text-white/80">Saving...</span>
                        )}
                        <span className="text-sm hidden md:inline">Remaining Time:</span>
                        <span className={`font-mono font-bold text-lg px-3 py-1 rounded ${timeRemaining < 300 ? 'bg-red-700 animate-pulse' : 'bg-green-600'
                            }`}>
                            {formatTime(timeRemaining)}
                        </span>
                    </div>
                </div>
            </header>

            {/* Section Tabs */}
            <div className="bg-white dark:bg-[#16181c] border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex gap-2 shrink-0 overflow-x-auto">
                {testState.subjects.map(subject => (
                    <button
                        key={subject}
                        onClick={() => {
                            setActiveSection(subject);
                            // Find first question of this subject to jump to
                            const subjectClean = subject.trim();
                            const firstQ = testState.palette.find(p => p.subject.trim() === subjectClean);

                            if (firstQ) {
                                console.log(`Switching to subject: ${subject}, Jumping to Q${firstQ.index}`);
                                if (firstQ.index !== question.question_index) {
                                    handleAction('JUMP', firstQ.index).catch(err => {
                                        console.error("Jump failed:", err);
                                        // alert("Failed to switch subject. Please checks your connection.");
                                    });
                                }
                            } else {
                                console.warn(`No questions found for subject: ${subject}`);
                                // alert(`No questions found for ${subject}`);
                            }
                        }}
                        className={`px-4 py-2 rounded-lg font-bold transition-colors whitespace-nowrap border-b-2 ${activeSection === subject
                            ? 'border-indigo-600 text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20'
                            : 'border-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                            }`}
                    >
                        {subject}
                    </button>
                ))}
            </div>

            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden relative">
                {/* Question Area */}
                <div className="flex-1 flex flex-col p-6 overflow-auto">
                    {/* Question Header */}
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                            Question {question.question_index + 1}:
                        </h2>
                        <span className={`px-3 py-1 rounded text-sm font-medium ${question.difficulty === 'Easy' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                            question.difficulty === 'Medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            }`}>
                            {question.difficulty}
                        </span>
                    </div>

                    {/* Question Text */}
                    <div className="bg-white dark:bg-[#16181c] rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6 flex-1">
                        <div className="text-lg mb-6">
                            <MathText content={question.question_text} />
                        </div>

                        {/* Diagram Display */}
                        {question.diagram_json && (
                            <div className="mb-6">
                                <DiagramRenderer diagramJson={question.diagram_json} />
                            </div>
                        )}

                        {/* Options or Numerical Input */}
                        {question.question_type === 'numerical' || (!question.options || Object.keys(question.options).length === 0) ? (
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Enter your numerical answer:
                                </label>
                                <input
                                    type="text"
                                    value={selectedAnswer || ''}
                                    onChange={(e) => setSelectedAnswer(e.target.value)}
                                    onKeyDown={(e) => {
                                        // Prevent event from bubbling to keyboard shortcuts if typing
                                        e.stopPropagation();
                                    }}
                                    placeholder="Type your answer here..."
                                    className="w-full max-w-sm px-4 py-3 rounded-lg border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-[#1e2025] text-gray-900 dark:text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors font-mono text-lg"
                                />
                            </div>
                        ) : question.options && (
                            <div className="space-y-3">
                                {Object.entries(question.options).map(([key, value]) => (
                                    <button
                                        key={key}
                                        onClick={() => setSelectedAnswer(key)}
                                        className={`w-full p-4 text-left rounded-lg border-2 transition-all ${selectedAnswer === key
                                            ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/30'
                                            : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold shrink-0 ${selectedAnswer === key
                                                ? 'bg-indigo-600 text-white'
                                                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                                                }`}>
                                                {key}
                                            </span>
                                            <div className="text-gray-900 dark:text-white flex-1">
                                                <MathText content={value} />
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Action Buttons - NTA Style */}
                    <div className="bg-white dark:bg-[#16181c] rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
                        <div className="flex flex-wrap gap-2">
                            <button
                                onClick={() => handleAction('SAVE_NEXT')}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-green-600 text-white font-medium rounded hover:bg-green-700 disabled:opacity-50"
                            >
                                SAVE & NEXT
                            </button>
                            <button
                                onClick={() => setSelectedAnswer(null)}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
                            >
                                CLEAR
                            </button>
                            <button
                                onClick={() => handleAction('SAVE_MARK_NEXT')}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-blue-600 text-white font-medium rounded hover:bg-blue-700 disabled:opacity-50"
                            >
                                SAVE & MARK FOR REVIEW
                            </button>
                            <button
                                onClick={() => handleAction('MARK_NEXT')}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-purple-600 text-white font-medium rounded hover:bg-purple-700 disabled:opacity-50"
                            >
                                MARK FOR REVIEW & NEXT
                            </button>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-gray-200 dark:border-gray-700">
                            <div className="flex gap-2">
                                <button
                                    onClick={() => handleAction('BACK')}
                                    disabled={actionLoading || question.question_index === 0}
                                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
                                >
                                    &lt;&lt; BACK
                                </button>
                                <button
                                    onClick={() => handleAction('NEXT')}
                                    disabled={actionLoading || question.question_index === testState.total_questions - 1}
                                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium rounded hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
                                >
                                    NEXT &gt;&gt;
                                </button>
                            </div>
                            <button
                                onClick={() => {
                                    fetchSummary();
                                    setShowSubmitModal(true);
                                }}
                                className="px-6 py-2 bg-red-600 text-white font-bold rounded hover:bg-red-700"
                            >
                                SUBMIT
                            </button>
                        </div>
                    </div>
                </div>

                {/* Question Palette - Mobile Drawer & Desktop Sidebar */}
                <div className={`
                    fixed inset-y-0 right-0 w-80 bg-white dark:bg-[#16181c] border-l border-gray-200 dark:border-gray-700 
                    transform transition-transform duration-300 ease-in-out z-40
                    ${showPalette ? 'translate-x-0' : 'translate-x-full'}
                    md:relative md:translate-x-0 md:w-72 md:shrink-0 md:flex md:flex-col
                `}>
                    <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="font-semibold text-gray-900 dark:text-white">Question Palette</h3>
                        <button
                            onClick={() => setShowPalette(false)}
                            className="md:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                        >
                            <X className="w-5 h-5 text-gray-500" />
                        </button>
                    </div>

                    <div className="p-4 overflow-auto flex-1">
                        {/* Legend */}
                        <div className="mb-4 space-y-2 text-xs">
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded bg-gray-300 dark:bg-gray-600"></div>
                                <span className="text-gray-600 dark:text-gray-400">{testState.palette.filter(p => p.status === 'NOT_VISITED').length} Not Visited</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded bg-red-500"></div>
                                <span className="text-gray-600 dark:text-gray-400">{testState.palette.filter(p => p.status === 'NOT_ANSWERED').length} Not Answered</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded bg-green-500"></div>
                                <span className="text-gray-600 dark:text-gray-400">{testState.palette.filter(p => p.status === 'ANSWERED').length} Answered</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded bg-purple-500"></div>
                                <span className="text-gray-600 dark:text-gray-400">{testState.palette.filter(p => p.status === 'MARKED_REVIEW').length} Marked Review</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded bg-purple-500 ring-2 ring-green-400"></div>
                                <span className="text-gray-600 dark:text-gray-400">{testState.palette.filter(p => p.status === 'ANSWERED_MARKED').length} Answered+Marked</span>
                            </div>
                        </div>

                        {/* Palette Grid */}
                        <div className="grid grid-cols-5 gap-2">
                            {filteredPalette.map((item) => (
                                <button
                                    key={item.index}
                                    onClick={() => {
                                        handleAction('JUMP', item.index);
                                        setShowPalette(false); // Close drawer on mobile selection
                                    }}
                                    className={`w-10 h-10 rounded font-bold text-sm ${getStatusColor(item.status)} ${item.index === question.question_index ? 'ring-2 ring-yellow-400' : ''
                                        } hover:opacity-80 transition-opacity`}
                                >
                                    {item.index + 1}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Overlay for mobile drawer */}
                {showPalette && (
                    <div
                        className="fixed inset-0 bg-black/50 z-30 md:hidden"
                        onClick={() => setShowPalette(false)}
                    />
                )}
            </div>

            {/* Submit Modal */}
            {showSubmitModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-[#16181c] rounded-xl max-w-lg w-full p-6">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Exam Summary</h2>

                        {examSummary && (
                            <table className="w-full mb-6">
                                <thead>
                                    <tr className="border-b border-gray-200 dark:border-gray-700">
                                        <th className="py-2 text-left text-sm text-gray-500 dark:text-gray-400">No of Questions</th>
                                        <th className="py-2 text-left text-sm text-gray-500 dark:text-gray-400">Answered</th>
                                        <th className="py-2 text-left text-sm text-gray-500 dark:text-gray-400">Not Answered</th>
                                        <th className="py-2 text-left text-sm text-gray-500 dark:text-gray-400">Marked</th>
                                        <th className="py-2 text-left text-sm text-gray-500 dark:text-gray-400">Not Visited</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td className="py-2 font-bold text-gray-900 dark:text-white">{examSummary.total}</td>
                                        <td className="py-2 font-bold text-green-600">{examSummary.answered + examSummary.answered_marked}</td>
                                        <td className="py-2 font-bold text-red-600">{examSummary.not_answered}</td>
                                        <td className="py-2 font-bold text-purple-600">{examSummary.marked_review}</td>
                                        <td className="py-2 font-bold text-gray-500">{examSummary.not_visited}</td>
                                    </tr>
                                </tbody>
                            </table>
                        )}

                        <p className="text-center text-gray-700 dark:text-gray-300 mb-2">
                            Are you sure you want to submit for final marking?
                        </p>
                        <p className="text-center text-sm text-red-500 mb-6">
                            No changes will be allowed after submission.
                        </p>

                        <div className="flex justify-center gap-4">
                            <button
                                onClick={handleSubmit}
                                className="px-8 py-2 bg-green-600 text-white font-bold rounded hover:bg-green-700"
                            >
                                YES
                            </button>
                            <button
                                onClick={() => setShowSubmitModal(false)}
                                className="px-8 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 font-bold rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                            >
                                NO
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
