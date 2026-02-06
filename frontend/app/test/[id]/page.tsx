'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Menu, X, User as UserIcon, Info } from 'lucide-react';
import MathText from '@/components/MathText';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    const [showPalette, setShowPalette] = useState(false);

    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    // Mock user name if not available
    const candidateName = "Candidate";

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
                setActiveSection(data.subject);
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
        if (timeRemaining <= 0) return;

        const interval = setInterval(() => {
            setTimeRemaining(prev => {
                if (prev <= 1) {
                    handleSubmit();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [timeRemaining]);

    const getTimeSpent = () => Math.floor((Date.now() - questionStartTime) / 1000);

    const handleAction = async (action: string, jumpIndex?: number) => {
        if (!question || actionLoading) return;

        // Prevent action if submitting
        if (showSubmitModal) return;

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
                await fetchTestState();
                await fetchQuestion(data.next_question_index);
            }
        } catch (error) {
            console.error('Action failed:', error);
        } finally {
            setActionLoading(false);
        }
    };

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

    const handleSubmit = async () => {
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/submit`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                router.push(data.redirect_url);
            }
        } catch (error) {
            console.error('Submit failed:', error);
        }
    };

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
                case '1': case 'a': case 'A': if (question?.options && Object.keys(question.options).length >= 1) setSelectedAnswer('A'); break;
                case '2': case 'b': case 'B': if (question?.options && Object.keys(question.options).length >= 2) setSelectedAnswer('B'); break;
                case '3': case 'c': case 'C': if (question?.options && Object.keys(question.options).length >= 3) setSelectedAnswer('C'); break;
                case '4': case 'd': case 'D': if (question?.options && Object.keys(question.options).length >= 4) setSelectedAnswer('D'); break;
                case 'ArrowLeft': if (question && question.question_index > 0) handleAction('BACK'); break;
                case 'ArrowRight': if (question && question.question_index < (testState?.total_questions || 0) - 1) handleAction('NEXT'); break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [question, testState, loading, showSubmitModal, selectedAnswer, handleAction]);

    // NTA Style Status Colors
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'NOT_VISITED': return 'bg-white border text-black'; // White box
            case 'NOT_ANSWERED': return 'bg-red-500 text-white clip-path-polygon-[0_0,100%_0,100%_80%,50%_100%,0_80%]'; // Red 
            case 'ANSWERED': return 'bg-green-500 text-white clip-path-polygon-[0_0,100%_0,100%_80%,50%_100%,0_80%]'; // Green
            case 'MARKED_REVIEW': return 'bg-purple-600 text-white rounded-full'; // Purple Circle
            case 'ANSWERED_MARKED': return 'bg-purple-600 text-white rounded-full relative after:content-[""] after:absolute after:bottom-0 after:right-0 after:w-2 after:h-2 after:bg-green-400 after:rounded-full'; // Purple + Green Dot
            default: return 'bg-white border text-black';
        }
    };

    // Simplified Status Legend Icon
    const StatusIcon = ({ status, count, label }: any) => (
        <div className="flex items-center gap-2 text-xs">
            <div className={`
                flex items-center justify-center w-8 h-8 font-bold border border-gray-300
                ${status === 'NOT_VISITED' ? 'bg-white text-black rounded-md' : ''}
                ${status === 'NOT_ANSWERED' ? 'bg-orange-500 text-white rounded-md' : ''}
                ${status === 'ANSWERED' ? 'bg-green-500 text-white clip-path-slant' : ''} 
                ${status === 'MARKED_REVIEW' ? 'bg-blue-600 text-white rounded-full' : ''}
                ${status === 'ANSWERED_MARKED' ? 'bg-blue-600 text-white rounded-full relative' : ''}
            `} style={status === 'ANSWERED' ? { clipPath: 'polygon(0 0, 100% 0, 100% 75%, 50% 100%, 0 75%)' } : {}}>
                {status === 'ANSWERED_MARKED' && <div className="absolute bottom-0 right-0 w-2 h-2 bg-green-400 rounded-full border border-white"></div>}
                {count}
            </div>
            <span className="text-gray-700 font-medium leading-tight">{label}</span>
        </div>
    );

    if (loading || !testState || !question) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    const filteredPalette = activeSection
        ? testState.palette.filter(p => p.subject === activeSection)
        : testState.palette;

    return (
        <div className="flex flex-col h-screen bg-gray-100 font-sans text-sm overflow-hidden select-none">
            {/* Top Header - White */}
            <div className="bg-white border-b border-gray-300 px-4 py-2 flex justify-between items-center h-16 shrink-0 z-20">
                <div className="flex items-center gap-4">
                    <div className="font-bold text-xl text-blue-900 tracking-wide">
                        NATIONAL TESTING AGENCY
                    </div>
                </div>

                {/* Candidate Info Block */}
                <div className="flex items-center gap-4">
                    <div className="hidden md:flex flex-col items-end">
                        <span className="font-bold text-gray-800">Candidate Name: <span className="text-orange-600">{candidateName}</span></span>
                        <span className="font-bold text-gray-800">Subject Name: <span className="text-black">{activeSection || "General"}</span></span>
                        <span className="font-bold text-gray-800">Remaining Time: <span className="bg-blue-500 text-white px-2 py-0.5 rounded-full">{formatTime(timeRemaining)}</span></span>
                    </div>
                    <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center text-gray-600">
                        <UserIcon className="w-6 h-6" />
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left: Question Area */}
                <div className="flex-1 flex flex-col bg-white overflow-hidden relative">

                    {/* Top Bar: Subject Tabs */}
                    <div className="bg-blue-600 text-white px-2 flex items-center gap-1 overflow-x-auto shrink-0 h-10">
                        {testState.subjects.map(subject => (
                            <button
                                key={subject}
                                onClick={() => {
                                    setActiveSection(subject);
                                    const firstQ = testState.palette.find(p => p.subject.trim() === subject.trim());
                                    if (firstQ && firstQ.index !== question.question_index) {
                                        handleAction('JUMP', firstQ.index);
                                    }
                                }}
                                className={`px-4 h-full flex items-center font-bold text-sm uppercase transition-colors
                                    ${activeSection === subject ? 'bg-white text-blue-800' : 'hover:bg-blue-700 text-white'}
                                `}
                            >
                                {subject}
                                <Info className="w-3 h-3 ml-2 opacity-50" />
                            </button>
                        ))}
                    </div>

                    {/* Blue Strip Title */}
                    <div className="bg-white border-b border-gray-300 px-4 py-2 flex justify-between items-center shadow-sm z-10">
                        <h2 className="font-bold text-lg text-red-600 underline decoration-red-600 underline-offset-4">
                            Question No. {question.question_index + 1}
                        </h2>

                        <div className="flex items-center gap-4">
                            <div className="text-gray-600 font-medium">
                                Marks: <span className="text-green-600 font-bold">+4</span> <span className="text-red-500 font-bold">-1</span>
                            </div>
                        </div>
                    </div>

                    {/* Scrollable Question Content */}
                    <div className="flex-1 overflow-auto p-8 relative">
                        {/* Right Side Divider Line (Visual) */}
                        <div className="absolute right-0 top-0 bottom-0 w-1 bg-gray-200"></div>

                        <div className="max-w-4xl">
                            {/* Question Text */}
                            <div className="text-lg text-gray-900 font-medium mb-8 leading-relaxed">
                                <MathText content={question.question_text} />
                            </div>

                            {/* Options */}
                            {question.options && (
                                <div className="space-y-4">
                                    {Object.entries(question.options).map(([key, value]) => (
                                        <label
                                            key={key}
                                            className="flex items-start gap-4 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors group"
                                        >
                                            <div className="relative flex items-center justify-center shrink-0 mt-1">
                                                <input
                                                    type="radio"
                                                    name="option"
                                                    checked={selectedAnswer === key}
                                                    onChange={() => setSelectedAnswer(key)}
                                                    className="peer w-5 h-5 appearance-none border-2 border-gray-400 rounded-full checked:border-blue-600 checked:bg-blue-600 transition-all"
                                                />
                                                <div className="absolute w-2 h-2 bg-white rounded-full opacity-0 peer-checked:opacity-100"></div>
                                            </div>

                                            <div className="flex-1">
                                                <span className="font-bold text-gray-700 mr-2">({key})</span>
                                                <span className="text-gray-800 text-lg"><MathText content={value} /></span>
                                            </div>
                                        </label>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Bottom Action Bar */}
                    <div className="bg-white border-t border-gray-300 p-2 flex flex-wrap gap-2 items-center justify-between shrink-0 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
                        <div className="flex gap-2">
                            <button
                                onClick={() => handleAction('SAVE_NEXT')}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white font-bold rounded-sm text-sm border border-green-600 shadow-sm"
                            >
                                SAVE & NEXT
                            </button>
                            <button
                                onClick={() => setSelectedAnswer(null)}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-white hover:bg-gray-50 text-black font-bold rounded-sm text-sm border border-gray-300 shadow-sm"
                            >
                                CLEAR RESPONSE
                            </button>
                            <button
                                onClick={() => handleAction('SAVE_MARK_NEXT')}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white font-bold rounded-sm text-sm border border-yellow-600 shadow-sm"
                            >
                                SAVE & MARK FOR REVIEW
                            </button>
                            <button
                                onClick={() => handleAction('MARK_NEXT')}
                                disabled={actionLoading}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-sm text-sm border border-blue-700 shadow-sm"
                            >
                                MARK FOR REVIEW & NEXT
                            </button>
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={() => handleAction('BACK')}
                                disabled={actionLoading || question.question_index === 0}
                                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-600 font-bold rounded-sm text-sm border border-gray-300"
                            >
                                &lt;&lt; BACK
                            </button>
                            <button
                                onClick={() => handleAction('NEXT')}
                                disabled={actionLoading || question.question_index === testState.total_questions - 1}
                                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-600 font-bold rounded-sm text-sm border border-gray-300"
                            >
                                NEXT &gt;&gt;
                            </button>

                            <button
                                onClick={() => { fetchSummary(); setShowSubmitModal(true); }}
                                className="px-6 py-2 bg-green-400/20 text-green-700 font-bold rounded-sm text-sm border border-green-200 ml-4 hover:bg-green-400/30"
                            >
                                SUBMIT
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right: Palette (Sidebar) */}
                <div className={`
                    w-80 bg-blue-50 border-l border-gray-300 flex flex-col shrink-0
                    ${showPalette ? 'fixed inset-y-0 right-0 z-50 shadow-2xl' : 'hidden md:flex'}
                `}>
                    {/* User Profile Mini Block */}
                    <div className="p-4 bg-white border-b border-gray-300 flex items-center gap-3">
                        <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                            <UserIcon className="w-6 h-6 text-gray-500" />
                        </div>
                        <div>
                            <div className="font-bold text-gray-800 text-sm">Review Your Questions</div>
                            <div className="text-xs text-gray-500">Click a number to jump</div>
                        </div>
                        <button onClick={() => setShowPalette(false)} className="ml-auto md:hidden p-1">
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Legend */}
                    <div className="p-4 grid grid-cols-2 gap-y-3 gap-x-2 bg-white border-b border-gray-300">
                        <StatusIcon status="NOT_VISITED" count={testState.palette.filter(p => p.status === 'NOT_VISITED').length} label="Not Visited" />
                        <StatusIcon status="NOT_ANSWERED" count={testState.palette.filter(p => p.status === 'NOT_ANSWERED').length} label="Not Answered" />
                        <StatusIcon status="ANSWERED" count={testState.palette.filter(p => p.status === 'ANSWERED').length} label="Answered" />
                        <StatusIcon status="MARKED_REVIEW" count={testState.palette.filter(p => p.status === 'MARKED_REVIEW').length} label="Marked for Review" />
                        <div className="col-span-2">
                            <StatusIcon status="ANSWERED_MARKED" count={testState.palette.filter(p => p.status === 'ANSWERED_MARKED').length} label="Ans & Marked for Review (Evaluated)" />
                        </div>
                    </div>

                    {/* Palette Grid Heading */}
                    <div className="bg-blue-600 text-white font-bold px-4 py-2 text-center text-sm">
                        {activeSection || "Questions"}
                    </div>

                    {/* Scrollable Palette Grid */}
                    <div className="flex-1 overflow-y-auto p-4 content-start">
                        <div className="grid grid-cols-5 gap-2">
                            {filteredPalette.map((item) => {
                                const current = item.index === question.question_index;
                                let btnClass = "bg-white border border-gray-300 text-black";
                                let shapeClass = "rounded-md";

                                // Specific NTA Colors
                                if (item.status === 'NOT_ANSWERED') {
                                    btnClass = "bg-orange-500 text-white border-orange-600";
                                    shapeClass = "rounded-b-xl"; // Approximation for NTA shape
                                } else if (item.status === 'ANSWERED') {
                                    btnClass = "bg-green-500 text-white border-green-600";
                                    // Custom clip path for "house" shape
                                    shapeClass = "clip-path-slant";
                                } else if (item.status === 'MARKED_REVIEW') {
                                    btnClass = "bg-blue-700 text-white border-blue-800";
                                    shapeClass = "rounded-full";
                                } else if (item.status === 'ANSWERED_MARKED') {
                                    btnClass = "bg-blue-700 text-white border-blue-800";
                                    shapeClass = "rounded-full relative";
                                }

                                return (
                                    <button
                                        key={item.index}
                                        onClick={() => {
                                            handleAction('JUMP', item.index);
                                            setShowPalette(false);
                                        }}
                                        className={`
                                            h-10 w-full flex items-center justify-center font-bold text-sm shadow-sm transition-transform hover:scale-105
                                            ${btnClass} ${shapeClass}
                                            ${current ? 'ring-2 ring-black transform scale-105 z-10' : ''}
                                        `}
                                        style={item.status === 'ANSWERED' ? { clipPath: 'polygon(0 0, 100% 0, 100% 75%, 50% 100%, 0 75%)' } : {}}
                                    >
                                        {item.index + 1}
                                        {item.status === 'ANSWERED_MARKED' && (
                                            <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-400 rounded-full border border-white"></div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Palette Footer Badge */}
                    <div className="bg-blue-100 p-2 text-center text-xs text-blue-800 font-bold border-t border-blue-200">
                        Infinitest Secure Browser
                    </div>
                </div>
            </div>

            {/* Mobile Toggle Button */}
            <button
                className="md:hidden fixed bottom-4 right-4 w-12 h-12 bg-blue-600 text-white rounded-full shadow-xl flex items-center justify-center z-50"
                onClick={() => setShowPalette(!showPalette)}
            >
                <Menu className="w-6 h-6" />
            </button>

            {/* Submit Modal */}
            {showSubmitModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 font-sans">
                    <div className="bg-white rounded-lg shadow-2xl max-w-lg w-full overflow-hidden">
                        <div className="bg-blue-600 text-white px-6 py-3 font-bold text-lg">
                            Exam Summary
                        </div>

                        <div className="p-6">
                            {examSummary && (
                                <div className="grid grid-cols-2 gap-x-8 gap-y-4 mb-8">
                                    <div className="flex justify-between border-b pb-1">
                                        <span className="text-gray-600">Total Questions:</span>
                                        <span className="font-bold">{examSummary.total}</span>
                                    </div>
                                    <div className="flex justify-between border-b pb-1">
                                        <span className="text-gray-600">Answered:</span>
                                        <span className="font-bold text-green-600">{examSummary.answered}</span>
                                    </div>
                                    <div className="flex justify-between border-b pb-1">
                                        <span className="text-gray-600">Not Answered:</span>
                                        <span className="font-bold text-orange-500">{examSummary.not_answered}</span>
                                    </div>
                                    <div className="flex justify-between border-b pb-1">
                                        <span className="text-gray-600">Marked for Review:</span>
                                        <span className="font-bold text-blue-600">{examSummary.marked_review}</span>
                                    </div>
                                    <div className="flex justify-between border-b pb-1">
                                        <span className="text-gray-600">Not Visited:</span>
                                        <span className="font-bold text-gray-400">{examSummary.not_visited}</span>
                                    </div>
                                </div>
                            )}

                            <p className="text-center text-gray-800 font-medium mb-2">
                                Are you sure you want to submit your test?
                            </p>
                            <p className="text-center text-sm text-red-600 mb-6 font-bold">
                                You cannot change your answers after submission.
                            </p>

                            <div className="flex justify-center gap-4">
                                <button
                                    onClick={handleSubmit}
                                    className="px-8 py-2 bg-green-600 text-white font-bold rounded shadow hover:bg-green-700"
                                >
                                    YES, SUBMIT
                                </button>
                                <button
                                    onClick={() => setShowSubmitModal(false)}
                                    className="px-8 py-2 bg-red-600 text-white font-bold rounded shadow hover:bg-red-700"
                                >
                                    NO, CANCEL
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
