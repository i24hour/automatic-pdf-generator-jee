'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import MathText from '@/components/MathText';
import DiagramRenderer from '@/components/test/DiagramRenderer';
import { useExamSecurity } from '@/hooks/useExamSecurity';

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
    diagram_svg?: string;
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

const TimerComponent = React.memo(({ serverTime, isTestActive, onZero }: { serverTime: number, isTestActive: boolean, onZero: () => void }) => {
    const [timeLeft, setTimeLeft] = useState(serverTime);

    useEffect(() => {
        setTimeLeft(serverTime);
    }, [serverTime]);

    useEffect(() => {
        if (!isTestActive) return;
        if (timeLeft <= 0) {
            onZero();
            return;
        }
        const interval = setInterval(() => {
            setTimeLeft(prev => {
                if (prev <= 1) {
                    clearInterval(interval);
                    onZero();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [isTestActive]); // intentionally omitting timeLeft to avoid rebuilding interval

    const formatTime = (seconds: number) => {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    return <>{formatTime(timeLeft)}</>;
});

export default function TestInterfacePage() {
    const router = useRouter();
    const params = useParams();
    const testId = params.id as string;
    const { user } = useAuth(); // Gather user info for Mentors Mantra profile box

    const [testState, setTestState] = useState<TestState | null>(null);
    const [question, setQuestion] = useState<QuestionData | null>(null);
    const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
    const [serverTimeRemaining, setServerTimeRemaining] = useState(0);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);
    const [showSubmitModal, setShowSubmitModal] = useState(false);
    const [isForceSubmitted, setIsForceSubmitted] = useState(false);
    const [examSummary, setExamSummary] = useState<any>(null);
    const [activeSection, setActiveSection] = useState<string | null>(null);
    const [questionStartTime, setQuestionStartTime] = useState(Date.now());

    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

    const isExamActive = testState?.status === 'IN_PROGRESS' && !showSubmitModal && !loading && !isForceSubmitted;
    const { warningMessage, clearWarning, isFullscreen, enterFullscreen, securityLog } = useExamSecurity({
        isExamActive,
        onSubmitExam: () => {
            setIsForceSubmitted(true);
            handleSubmit(true);
        }
    });

    const fetchTestState = useCallback(async () => {
        if (!token) return;
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/state`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setTestState(data);
                setServerTimeRemaining(data.time_remaining_seconds);
                setActiveSection(prev => {
                    if (!prev && data.subjects?.length > 0) return data.subjects[0];
                    return prev;
                });
            }
        } catch (error) {
            console.error('Failed to fetch test state:', error);
        }
    }, [testId, token]);

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
                setServerTimeRemaining(data.time_remaining_seconds);
                setQuestionStartTime(Date.now());
            }
        } catch (error) {
            console.error('Failed to fetch question:', error);
        }
    }, [testId, token]);

    useEffect(() => {
        const load = async () => {
            await fetchTestState();
            await fetchQuestion(0);
            setLoading(false);
            setTimeout(() => enterFullscreen(), 1000);
        };
        load();
    }, [fetchTestState, fetchQuestion]);

    useEffect(() => {
        const handleFirstClick = () => { if (!isFullscreen && !loading) enterFullscreen(); };
        document.addEventListener('click', handleFirstClick);
        return () => document.removeEventListener('click', handleFirstClick);
    }, [isFullscreen, loading]);

    useEffect(() => {
        const handlePopState = (e: PopStateEvent) => {
            if (testState?.status === 'IN_PROGRESS' && !showSubmitModal) {
                window.history.pushState(null, '', window.location.href);
            }
        };
        window.history.pushState(null, '', window.location.href);
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, [testState?.status, showSubmitModal]);

    const getTimeSpent = () => Math.floor((Date.now() - questionStartTime) / 1000);

    const handleAction = async (action: string, jumpIndex?: number) => {
        if (!question || (actionLoading && action !== 'JUMP')) return;
        setActionLoading(true);
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
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
                if (data.palette && data.subjects) {
                    setTestState(prev => prev ? { ...prev, palette: data.palette, subjects: data.subjects, time_remaining_seconds: data.time_remaining_seconds, current_question_index: data.next_question_index } : prev);
                    setServerTimeRemaining(data.time_remaining_seconds);
                }
                if (data.next_question) {
                    setQuestion(data.next_question);
                    setSelectedAnswer(data.next_question.user_answer);
                    setServerTimeRemaining(data.next_question.time_remaining_seconds);
                    setQuestionStartTime(Date.now());
                    setActiveSection(data.next_question.subject);
                }
            }
        } catch (error) {
            console.error('Action failed:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const fetchSummary = async () => {
        try {
            const response = await fetch(`${API_BASE}/test/${testId}/summary`, { headers: { 'Authorization': `Bearer ${token}` } });
            if (response.ok) {
                const data = await response.json();
                setExamSummary(data);
            }
        } catch (error) {}
    };

    const handleSubmit = async (isViolation: boolean = false) => {
        if (actionLoading) return;
        setActionLoading(true);
        try {
            const endpoint = isViolation ? `/test/${testId}/violation-submit` : `/test/${testId}/submit`;
            const options: RequestInit = { method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } };
            if (isViolation) options.body = JSON.stringify(securityLog);
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            if (response.ok) {
                const data = await response.json();
                if (!isViolation) router.push(data.redirect_url);
            } else { setActionLoading(false); }
        } catch (error) { setActionLoading(false); }
    };

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
                case 's': case 'S': if (question) handleAction('SAVE_NEXT'); break;
                case 'm': case 'M': if (question) handleAction('MARK_NEXT'); break;
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [question, testState, loading, showSubmitModal, selectedAnswer, handleAction]);

    if (loading || !testState || !question) {
        return (
            <div className="min-h-screen bg-gray-100 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#38a9eb]"></div>
            </div>
        );
    }

    const filteredPalette = activeSection ? testState.palette.filter(p => p.subject === activeSection) : testState.palette;
    const currentQuestionSection = testState.palette.filter(p => p.subject === (question?.subject || activeSection));
    const sectionQuestionNumber = currentQuestionSection.findIndex(p => p.index === question?.question_index) + 1;

    // Sprite Mapping logic
    const getPaletteButtonStyle = (status: string) => {
        let bgPos = '-157px -4px'; // NOT_VISITED
        let height = '33px';
        let color = '#000';
        let padding = '6px 0 0 0';

        if (status === 'ANSWERED') { bgPos = '-4px -5px'; color = '#fff'; }
        else if (status === 'NOT_ANSWERED') { bgPos = '-57px -6px'; color = '#fff'; }
        else if (status === 'MARKED_REVIEW') { bgPos = '-108px -1px'; color = '#fff'; height = '40px'; padding = '13px 0 0 0'; }
        else if (status === 'ANSWERED_MARKED') { bgPos = '-66px -178px'; color = '#fff'; height = '40px'; padding = '13px 0 0 0'; }

        return {
            background: `url("https://www.digialm.com/OnlineAssessment/images/questions-sprite.png") no-repeat ${bgPos}`,
            width: '49px', height, color, padding,
            display: 'inline-block', textAlign: 'center' as const,
            cursor: 'pointer', fontSize: '15px', margin: '2px',
        };
    };

    const usernameDisplay = user?.name || (user as any)?.username || "Student";

    return (
        <div className="h-screen w-screen bg-white flex flex-col overflow-hidden text-sm font-sans relative">
            
            {/* Header 1 */}
            <div className="bg-[#1862a8] w-full flex items-center justify-center shrink-0 border-b-2 sm:border-b-0 border-[#38a9eb]" style={{ height: '50px' }}>
                <h1 className="text-white text-3xl font-extrabold tracking-widest" style={{ textShadow: '1px 1px 2px rgba(0,0,0,0.5)' }}>MENTORS MANTRA</h1>
            </div>

            {/* Header 2 */}
            <div className="flex justify-between items-center border-b border-[#c3c3c1] px-4 py-[6px] shrink-0 bg-white">
                <div className="bg-[#38a9eb] text-white px-[12px] py-[8px] font-normal rounded text-[14px]">
                    {testState.exam_type.replace('_', ' ')}
                </div>
                <div className="font-bold text-gray-700 text-[12px]">
                    Time Left: <span className="font-bold text-[12px] ml-1">
                        <TimerComponent 
                            serverTime={serverTimeRemaining} 
                            isTestActive={testState?.status === 'IN_PROGRESS' && !showSubmitModal && !actionLoading} 
                            onZero={() => { if (testState?.status === 'IN_PROGRESS' && !actionLoading) handleSubmit(); }} 
                        />
                    </span>
                </div>
            </div>

            {/* Header 3 (Subjects Tabs) */}
            <div className="flex border-b border-[#c3c3c1] shrink-0 bg-white h-[35px] overflow-x-auto">
                {testState.subjects.map(subject => (
                    <button
                        key={subject}
                        onClick={() => {
                            setActiveSection(subject);
                            const firstQ = testState.palette.find(p => p.subject === subject);
                            if (firstQ && firstQ.index !== question.question_index) {
                                handleAction('JUMP', firstQ.index);
                            }
                        }}
                        className={`px-[15px] py-[10px] font-bold border-r border-[#c3c3c1] whitespace-nowrap leading-none transition-colors ${
                            activeSection === subject ? 'bg-[#4e85c5] text-white' : 'text-[#36ace9] hover:bg-gray-50'
                        }`}
                        style={{ fontSize: '14px' }}
                    >
                        {subject}
                    </button>
                ))}
            </div>

            {/* Main Content Layout */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative pb-[50px] md:pb-0">
                
                {/* Left Side (Questions Area + Bottom Bar) */}
                <div className="flex-1 flex flex-col bg-white overflow-hidden pb-[60px] relative">
                    
                    {/* View in Lang Bar */}
                    <div className="bg-[#4e85c5] text-white px-2 py-2 flex justify-end items-center gap-2 shrink-0 text-[12px] font-bold border-b border-[#7E9DB9]">
                        <span>View in:</span>
                        <select className="text-black text-[13px] font-normal border border-[#7E9DB9] rounded-none py-[2px] pr-[15px] outline-none font-sans">
                            <option>English</option>
                        </select>
                    </div>

                    {/* Question Content Scrollable */}
                    <div className="flex-1 overflow-y-auto px-4 py-2 bg-[#f9f9f9] flex flex-col pt-4">
                        
                        {/* Question Title Header */}
                        <div className="border-b border-[#dbdbdb] pb-2 w-full flex justify-between items-center mb-0 mt-0 bg-white p-2 rounded-t-lg shadow-[0_-2px_4px_rgba(0,0,0,0.02)]">
                            <h2 className="text-[17px] font-bold text-black border-l-4 border-[#38a9eb] pl-2" style={{ fontFamily: 'Arial, sans-serif' }}>
                                Question no. {sectionQuestionNumber || question.question_index + 1}
                            </h2>
                            <button className="bg-[#38a9eb] hover:bg-[#2980b9] text-white text-[14px] px-3 py-1 rounded transition border-none font-sans cursor-pointer shadow-sm">
                                Hide Instructions
                            </button>
                        </div>

                        {/* Question Box Area with border */}
                        <div className="mb-6 w-full text-[17px] font-sans text-black leading-relaxed p-4 bg-white border border-[#dbdbdb] border-t-0 rounded-b-lg shadow-sm">
                            
                            <div className="mb-6 font-serif">
                                <MathText content={question.question_text} />
                            </div>

                            {/* Diagrams */}
                            {(question.diagram_svg || question.diagram_json) && (
                                <div className="mb-6 px-2">
                                    <DiagramRenderer svgContent={question.diagram_svg} diagramJson={question.diagram_json} />
                                </div>
                            )}

                            {/* Options */}
                            <div className="flex flex-col gap-2 mt-4 px-2 w-full max-w-4xl">
                                {question.question_type === 'numerical' || !question.options || Object.keys(question.options).length === 0 ? (
                                    <div className="mt-2 flex flex-col gap-2">
                                        <label className="text-[16px] text-black font-semibold">Enter your answer:</label>
                                        <input
                                            type="number"
                                            value={selectedAnswer || ''}
                                            onChange={(e) => setSelectedAnswer(e.target.value)}
                                            onKeyDown={(e) => e.stopPropagation()}
                                            className="w-[200px] h-[40px] px-[5px] font-sans text-[16px] border border-[#a9a9a9] outline-none rounded focus:ring-1 focus:ring-[#38a9eb]"
                                        />
                                    </div>
                                ) : (
                                    Object.entries(question.options).map(([key, value]) => (
                                        <label 
                                            key={key} 
                                            className="flex items-start gap-3 text-[19px] bg-white p-[10px] border border-[#ddd] rounded cursor-pointer transition-colors hover:shadow-sm"
                                        >
                                            <input
                                                type="radio"
                                                name="option"
                                                value={key}
                                                checked={selectedAnswer === key}
                                                onChange={() => setSelectedAnswer(key)}
                                                className="w-[16px] h-[16px] cursor-pointer mt-[5px]"
                                                style={{ marginRight: '10px' }}
                                            />
                                            <div className="text-black select-none font-serif flex-1">
                                                <MathText content={value} />
                                            </div>
                                        </label>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Left Bottom Action Bar */}
                    <div className="absolute left-0 right-0 bottom-0 border-t border-[#c3c3c1] bg-white flex flex-wrap justify-between items-center p-[6px] pl-[10px] shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
                        <div className="flex flex-wrap items-center">
                            <button onClick={() => setSelectedAnswer(null)} disabled={actionLoading} className="border border-[#c8c8c8] text-[#252525] bg-white hover:bg-[#0c7cd5] hover:text-white px-[20px] py-[8px] text-[15px] cursor-pointer font-sans m-[2px] disabled:opacity-50 transition-colors">Clear Response</button>
                            <button onClick={() => handleAction('SAVE_MARK_NEXT')} disabled={actionLoading} className="border border-[#c8c8c8] text-[#252525] bg-white hover:bg-[#0c7cd5] hover:text-white px-[20px] py-[8px] text-[15px] cursor-pointer font-sans m-[2px] disabled:opacity-50 transition-colors">Save & Mark for Review</button>
                            <button onClick={() => handleAction('MARK_NEXT')} disabled={actionLoading} className="border border-[#c8c8c8] text-[#252525] bg-white hover:bg-[#0c7cd5] hover:text-white px-[20px] py-[8px] text-[15px] cursor-pointer font-sans m-[2px] disabled:opacity-50 transition-colors">Mark for Review & Next</button>
                            <button onClick={() => handleAction('BACK')} disabled={actionLoading || question.question_index === 0} className="border border-[#c8c8c8] text-[#252525] bg-white hover:bg-[#0c7cd5] hover:text-white px-[20px] py-[8px] text-[15px] cursor-pointer font-sans m-[2px] disabled:opacity-50 transition-colors">Previous</button>
                            <button onClick={() => handleAction('NEXT')} disabled={actionLoading || question.question_index === testState.total_questions - 1} className="border border-[#c8c8c8] text-[#252525] bg-white hover:bg-[#0c7cd5] hover:text-white px-[20px] py-[8px] text-[15px] cursor-pointer font-sans m-[2px] disabled:opacity-50 transition-colors">Next</button>
                        </div>
                        <button onClick={() => handleAction('SAVE_NEXT')} disabled={actionLoading} className="border border-[#0c7cd5] bg-[#0c7cd5] text-white px-[20px] py-[8px] text-[15px] cursor-pointer font-sans m-[2px] mr-[10px] disabled:opacity-50 hover:bg-[#0a68b4] transition-colors rounded shadow-sm">Save and Next</button>
                    </div>
                </div>

                {/* Right Sidebar */}
                <div className="w-[280px] bg-white flex flex-col shrink-0 border-l border-gray-300 absolute right-0 top-0 bottom-[50px] md:bottom-0 md:relative">
                    
                    {/* User Info */}
                    <div className="bg-[#f8fbff] flex flex-row items-center overflow-auto p-0 border-b-2 border-gray-300 shrink-0">
                        <img 
                            src="https://www.digialm.com//OnlineAssessment/images/NewCandidateImage.jpg" 
                            className="w-[89px] h-[99px] border border-[#c3c3c1] rounded-[2px] m-[7px] inline-block align-middle bg-white shadow-sm" 
                            alt="Candidate"
                        />
                        <div className="m-[10px] font-bold text-[16px] inline-block font-sans break-words max-w-[130px] text-gray-800">
                            {usernameDisplay}
                        </div>
                    </div>

                    {/* Legend section */}
                    <div className="border border-r-0 border-b-0 mt-[5px] flex flex-col flex-1 overflow-hidden font-sans mx-1">
                        
                        {/* Legend Grid */}
                        <div className="w-full pl-[9px] pb-[12px] bg-white shrink-0 overflow-auto border-b border-gray-300">
                            <div className="w-[43%] mt-[10px] float-left flex">
                                <span className="float-left h-[26px] mr-[10px] w-[29px] text-white pt-[6px] text-center align-middle font-sans text-[12px] shrink-0" style={{ background: 'url("https://www.digialm.com/OnlineAssessment/images/questions-sprite.png") -7px -55px' }}>{testState.palette.filter(p => p.status === 'ANSWERED').length}</span>
                                <span className="font-sans text-[12px] leading-[1.2] pt-1">Answered</span>
                            </div>
                            <div className="w-[43%] mt-[10px] float-left flex">
                                <span className="float-left h-[26px] mr-[10px] w-[29px] text-white pt-[6px] text-center align-middle font-sans text-[12px] shrink-0" style={{ background: 'url("https://www.digialm.com/OnlineAssessment/images/questions-sprite.png") -42px -56px' }}>{testState.palette.filter(p => p.status === 'NOT_ANSWERED').length}</span>
                                <span className="font-sans text-[12px] leading-[1.2] pt-1">Not Answered</span>
                            </div>
                            <div className="w-[43%] mt-[10px] float-left flex">
                                <span className="float-left h-[26px] mr-[10px] w-[29px] text-white pt-[6px] text-center align-middle font-sans text-[12px] shrink-0" style={{ background: 'url("https://www.digialm.com/OnlineAssessment/images/questions-sprite.png") -107px -56px' }}>{testState.palette.filter(p => p.status === 'NOT_VISITED').length}</span>
                                <span className="font-sans text-[12px] leading-[1.2] pt-1">Not Visited</span>
                            </div>
                            <div className="w-[43%] mt-[10px] float-left flex">
                                <span className="float-left h-[26px] mr-[10px] w-[29px] text-white pt-[6px] text-center align-middle font-sans text-[12px] shrink-0" style={{ background: 'url("https://www.digialm.com/OnlineAssessment/images/questions-sprite.png") -75px -54px' }}>{testState.palette.filter(p => p.status === 'MARKED_REVIEW').length}</span>
                                <span className="font-sans text-[12px] leading-[1.2] pt-1">Marked for Review</span>
                            </div>
                            <div className="w-[90%] mt-[10px] float-left flex items-start">
                                <span className="float-left h-[26px] mr-[10px] w-[29px] text-white pt-[6px] text-center align-middle font-sans text-[12px] shrink-0" style={{ background: 'url("https://www.digialm.com/OnlineAssessment/images/questions-sprite.png") -9px -87px' }}>{testState.palette.filter(p => p.status === 'ANSWERED_MARKED').length}</span>
                                <span className="font-sans text-[12px] leading-tight mt-1 text-gray-700">Answered & Marked for Review <br/><span className="text-gray-500 text-[11px]">(will be considered for evaluation)</span></span>
                            </div>
                        </div>

                        {/* Question Palette Selection Box */}
                        <div className="bg-[#e5f6fd] font-bold overflow-auto p-[10px] py-[15px] flex-1 border-t border-blue-100 flex flex-col relative pb-[60px]">
                            <div className="bg-[#4e85c5] text-white absolute top-0 left-0 right-0 p-[8px] text-[13px] font-bold shadow-sm">
                                Choose a Question
                            </div>
                            
                            {/* Scrollable Palette Grid */}
                            <div className="flex flex-wrap justify-start content-start gap-[4px] mt-[30px] pt-[6px]">
                                {filteredPalette.map((item, sectionIdx) => {
                                    const isCurrent = item.index === question.question_index;
                                    const btnStyle = getPaletteButtonStyle(item.status);
                                    return (
                                        <div 
                                            key={item.index}
                                            onClick={() => handleAction('JUMP', item.index)}
                                            style={btnStyle}
                                            className={`${isCurrent ? 'ring-2 ring-offset-1 ring-[#0c7cd5] scale-105' : 'hover:opacity-90'} shadow-sm`}
                                        >
                                            {sectionIdx + 1}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Global Minimum Submit Bar matching Mentors Mantra bottom right */}
            <div className="absolute bottom-0 right-0 w-[280px] bg-[#e5f6fd] border-t border-[#c3c3c1] overflow-auto z-10 hidden md:block">
                 <button 
                    onClick={() => { fetchSummary(); setShowSubmitModal(true); }}
                    className="bg-[#0c7cd5] text-white mx-auto my-[8px] px-[30px] py-[10px] text-[15px] font-sans border border-[#0a68b4] rounded shadow-md cursor-pointer block hover:bg-[#0a68b4] active:bg-[#084b82] transition"
                 >
                    Submit
                 </button>
            </div>
            
            {/* Mobile Submit Button fallback */}
            <div className="md:hidden absolute bottom-0 right-0 w-full bg-[#e5f6fd] border border-[#c3c3c1] p-[6px] flex justify-end z-10 shadow-[0_-2px_10px_rgba(0,0,0,0.1)]">
                 <button 
                    onClick={() => { fetchSummary(); setShowSubmitModal(true); }}
                    className="bg-[#0c7cd5] text-white px-[20px] py-[8px] font-bold font-sans rounded shadow-sm border border-[#0a68b4]"
                 >
                    Submit Test
                 </button>
            </div>

            {/* Submit Modal */}
            {showSubmitModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 font-sans backdrop-blur-sm">
                    <div className="bg-white rounded max-w-lg w-full p-0 shadow-2xl border border-gray-300 overflow-hidden transform scale-100 transition-transform">
                        <h2 className="text-xl font-bold text-white mb-4 bg-[#38a9eb] p-4 text-center tracking-wide">Exam Summary</h2>
                        <div className="px-6">
                            {examSummary ? (
                                <table className="w-full mb-6 border-collapse text-center text-sm">
                                    <thead>
                                        <tr className="bg-gray-100 border-b border-gray-300">
                                            <th className="py-3 px-2 font-bold text-gray-700">No of Questions</th>
                                            <th className="py-3 px-2 font-bold text-gray-700">Answered</th>
                                            <th className="py-3 px-2 font-bold text-gray-700">Not Answered</th>
                                            <th className="py-3 px-2 font-bold text-gray-700">Marked</th>
                                            <th className="py-3 px-2 font-bold text-gray-700">Not Visited</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td className="py-4 border-b border-gray-200 font-bold text-[#0c7cd5] text-lg">{examSummary.total}</td>
                                            <td className="py-4 border-b border-gray-200 font-bold text-green-600 text-lg">{examSummary.answered + examSummary.answered_marked}</td>
                                            <td className="py-4 border-b border-gray-200 font-bold text-red-600 text-lg">{examSummary.not_answered}</td>
                                            <td className="py-4 border-b border-gray-200 font-bold text-purple-600 text-lg">{examSummary.marked_review}</td>
                                            <td className="py-4 border-b border-gray-200 font-bold text-gray-500 text-lg">{examSummary.not_visited}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            ) : (
                                <div className="py-8 text-center text-gray-500 font-medium">Loading summary...</div>
                            )}
                            <p className="text-center text-gray-800 mb-2 font-bold text-base">Are you sure you want to submit for final marking?</p>
                            <p className="text-center text-sm text-red-600 mb-6 font-bold bg-red-50 py-2 rounded">No changes will be allowed after submission.</p>
                            <div className="flex justify-center gap-4 pb-6">
                                <button onClick={() => handleSubmit(false)} className="px-10 py-3 bg-[#0c7cd5] hover:bg-[#0a68b4] text-white font-bold rounded shadow-md cursor-pointer transition">YES, Submit</button>
                                <button onClick={() => setShowSubmitModal(false)} className="px-10 py-3 border border-gray-300 bg-white hover:bg-gray-100 text-gray-700 font-bold rounded cursor-pointer transition">NO, Return</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Warning Message Modal */}
            {warningMessage && (
                <div className="fixed inset-0 bg-red-900/90 flex flex-col items-center justify-center z-[100] p-6 backdrop-blur-sm">
                    <div className="bg-white rounded max-w-xl w-full p-8 shadow-2xl border-4 border-red-600">
                        <div className="flex justify-center mb-4"><span className="text-5xl animate-bounce">⚠️</span></div>
                        <h2 className="text-2xl font-black text-center text-red-600 mb-4 uppercase tracking-wider">Rule Violation Detected</h2>
                        <p className="text-center text-gray-800 text-lg mb-8 font-medium bg-red-50 p-4 rounded text-red-900 border border-red-200">{warningMessage}</p>
                        <div className="flex justify-center">
                            <button onClick={clearWarning} className="px-8 py-4 bg-red-600 text-white font-bold rounded hover:bg-red-700 shadow-lg transition transform hover:scale-105 uppercase text-sm tracking-wide">I Understand, Return to Test</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Forced Submission UI */}
            {isForceSubmitted && (
                <div className="fixed inset-0 bg-black flex flex-col items-center justify-center z-[200] p-6 backdrop-blur-sm">
                    <div className="bg-white border-4 border-red-700 rounded max-w-2xl w-full p-10 text-center shadow-[0_0_50px_rgba(220,38,38,0.3)]">
                        <div className="mb-6 text-6xl animate-pulse">🛑</div>
                        <h1 className="text-4xl font-extrabold text-red-600 mb-4 uppercase tracking-widest">Exam Terminated</h1>
                        <p className="text-xl text-gray-800 mb-8 border-t border-b border-gray-200 py-4 bg-gray-50 font-medium">Your exam has been automatically submitted due to multiple security violations. This behavior has been logged.</p>
                        <button onClick={() => router.push(`/test/${testId}/result`)} className="px-10 py-4 bg-[#0c7cd5] hover:bg-[#0a68b4] text-white font-bold rounded shadow-lg uppercase tracking-wide text-sm transition">Proceed to Results</button>
                    </div>
                </div>
            )}
        </div>
    );
}
