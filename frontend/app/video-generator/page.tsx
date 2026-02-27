"use client";

import React, { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
    Video,
    Upload,
    Sparkles,
    ChevronDown,
    X,
    Play,
    Loader2,
    Image as ImageIcon,
    Mic,
    Globe,
    Zap
} from "lucide-react";
import DesktopSidebar from "@/components/layout/DesktopSidebar";
import MobileNav from "@/components/layout/MobileNav";
import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL as API_URL } from "@/lib/config";

const TOPICS = [
    "Algebra",
    "Geometry",
    "Calculus",
    "Trigonometry",
    "Coordinate Geometry",
    "Vectors",
    "Probability",
    "Statistics",
    "Number Theory",
    "Complex Numbers"
];

const LANGUAGES = [
    { code: "en", name: "English", flag: "🇺🇸" },
    { code: "hi", name: "Hindi", flag: "🇮🇳" }
];

const EXAMPLE_PROMPTS = [
    "Explain the Pythagorean theorem with visual proof",
    "Show how to solve quadratic equations step by step",
    "Visualize the derivative of sin(x)",
    "Explain the concept of limits with animations",
    "Demonstrate vector addition graphically"
];

export default function VideoGeneratorPage() {
    const router = useRouter();
    const { user, isAuthenticated } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Form state
    const [prompt, setPrompt] = useState("");
    const [selectedTopic, setSelectedTopic] = useState("Geometry");
    const [selectedLanguage, setSelectedLanguage] = useState("en");
    const [uploadedImage, setUploadedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [showTopicDropdown, setShowTopicDropdown] = useState(false);
    const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);

    // Progress state
    const [generationProgress, setGenerationProgress] = useState(0);
    const [currentStep, setCurrentStep] = useState("");
    const [jobId, setJobId] = useState<string | null>(null);

    // Handle image upload
    const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setUploadedImage(file);
            const reader = new FileReader();
            reader.onloadend = () => {
                setImagePreview(reader.result as string);
            };
            reader.readAsDataURL(file);
        }
    }, []);

    const removeImage = () => {
        setUploadedImage(null);
        setImagePreview(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    // Handle generation
    const handleGenerate = async () => {
        if (!prompt.trim() && !uploadedImage) return;
        if (!isAuthenticated) {
            router.push("/login");
            return;
        }

        setIsGenerating(true);
        setGenerationProgress(0);
        setCurrentStep("Initializing...");

        const token = localStorage.getItem("auth_token");

        try {
            // 1. Start video generation
            const generateRes = await fetch(`${API_URL}/api/video/generate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    prompt: prompt.trim(),
                    topic: selectedTopic,
                    language: selectedLanguage,
                    tts_provider: "edge",
                    max_duration: 60
                })
            });

            if (!generateRes.ok) {
                const err = await generateRes.json();
                throw new Error(err.detail || "Failed to start video generation");
            }

            const { job_id, status } = await generateRes.json();
            setJobId(job_id);
            setCurrentStep("Job queued, starting processing...");
            setGenerationProgress(5);

            // 2. Poll for status updates
            let completed = false;
            let pollCount = 0;
            const maxPolls = 120; // 10 minutes max (5s interval)

            while (!completed && pollCount < maxPolls) {
                await new Promise(resolve => setTimeout(resolve, 5000)); // 5 second intervals
                pollCount++;

                const statusRes = await fetch(`${API_URL}/api/video/status/${job_id}`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });

                if (!statusRes.ok) {
                    throw new Error("Failed to get job status");
                }

                const jobStatus = await statusRes.json();
                setGenerationProgress(jobStatus.progress);
                setCurrentStep(jobStatus.current_step);

                if (jobStatus.status === "completed") {
                    completed = true;
                    // Show video or navigate to result
                    if (jobStatus.video_url) {
                        // Open video in new tab for now
                        window.open(jobStatus.video_url, "_blank");
                        setCurrentStep("Video ready! Opening...");
                    }
                } else if (jobStatus.status === "failed") {
                    throw new Error(jobStatus.error || "Video generation failed");
                }
            }

            if (!completed) {
                throw new Error("Video generation timed out. Please try again.");
            }

        } catch (error) {
            console.error("Generation failed:", error);
            setCurrentStep(error instanceof Error ? error.message : "Generation failed");
            // Keep showing error for 3 seconds
            await new Promise(resolve => setTimeout(resolve, 3000));
        } finally {
            setIsGenerating(false);
            setGenerationProgress(0);
        }
    };

    const handleExampleClick = (example: string) => {
        setPrompt(example);
    };

    return (
        <div className="min-h-screen bg-white dark:bg-black">
            {/* Mobile Layout */}
            <div className="md:hidden pb-20">
                <MobileNav />
                <main className="p-4">
                    <VideoGeneratorContent
                        prompt={prompt}
                        setPrompt={setPrompt}
                        selectedTopic={selectedTopic}
                        setSelectedTopic={setSelectedTopic}
                        selectedLanguage={selectedLanguage}
                        setSelectedLanguage={setSelectedLanguage}
                        showTopicDropdown={showTopicDropdown}
                        setShowTopicDropdown={setShowTopicDropdown}
                        showLanguageDropdown={showLanguageDropdown}
                        setShowLanguageDropdown={setShowLanguageDropdown}
                        imagePreview={imagePreview}
                        removeImage={removeImage}
                        fileInputRef={fileInputRef}
                        handleImageUpload={handleImageUpload}
                        isGenerating={isGenerating}
                        generationProgress={generationProgress}
                        currentStep={currentStep}
                        handleGenerate={handleGenerate}
                        handleExampleClick={handleExampleClick}
                    />
                </main>
            </div>

            {/* Desktop Layout */}
            <div className="hidden md:flex min-h-screen">
                <DesktopSidebar />
                <main className="flex-1 ml-[275px] flex items-center justify-center p-8">
                    <div className="w-full max-w-3xl">
                        <VideoGeneratorContent
                            prompt={prompt}
                            setPrompt={setPrompt}
                            selectedTopic={selectedTopic}
                            setSelectedTopic={setSelectedTopic}
                            selectedLanguage={selectedLanguage}
                            setSelectedLanguage={setSelectedLanguage}
                            showTopicDropdown={showTopicDropdown}
                            setShowTopicDropdown={setShowTopicDropdown}
                            showLanguageDropdown={showLanguageDropdown}
                            setShowLanguageDropdown={setShowLanguageDropdown}
                            imagePreview={imagePreview}
                            removeImage={removeImage}
                            fileInputRef={fileInputRef}
                            handleImageUpload={handleImageUpload}
                            isGenerating={isGenerating}
                            generationProgress={generationProgress}
                            currentStep={currentStep}
                            handleGenerate={handleGenerate}
                            handleExampleClick={handleExampleClick}
                        />
                    </div>
                </main>
            </div>
        </div>
    );
}

// Separate content component for reuse
interface ContentProps {
    prompt: string;
    setPrompt: (value: string) => void;
    selectedTopic: string;
    setSelectedTopic: (value: string) => void;
    selectedLanguage: string;
    setSelectedLanguage: (value: string) => void;
    showTopicDropdown: boolean;
    setShowTopicDropdown: (value: boolean) => void;
    showLanguageDropdown: boolean;
    setShowLanguageDropdown: (value: boolean) => void;
    imagePreview: string | null;
    removeImage: () => void;
    fileInputRef: React.RefObject<HTMLInputElement | null>;
    handleImageUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
    isGenerating: boolean;
    generationProgress: number;
    currentStep: string;
    handleGenerate: () => void;
    handleExampleClick: (example: string) => void;
}

function VideoGeneratorContent({
    prompt,
    setPrompt,
    selectedTopic,
    setSelectedTopic,
    selectedLanguage,
    setSelectedLanguage,
    showTopicDropdown,
    setShowTopicDropdown,
    showLanguageDropdown,
    setShowLanguageDropdown,
    imagePreview,
    removeImage,
    fileInputRef,
    handleImageUpload,
    isGenerating,
    generationProgress,
    currentStep,
    handleGenerate,
    handleExampleClick
}: ContentProps) {
    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="text-center space-y-4">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 shadow-lg shadow-purple-500/25">
                    <Video className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white">
                    Math Video Generator
                </h1>
                <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                    Transform any math concept into an animated educational video with AI-powered explanations
                </p>
            </div>

            {/* Main Input Card - Grok-like style */}
            <div className="relative">
                <div className="bg-gray-50 dark:bg-[#16181c] rounded-3xl border border-gray-200 dark:border-[#2f3336] overflow-hidden shadow-xl">
                    {/* Image Preview */}
                    {imagePreview && (
                        <div className="relative p-4 border-b border-gray-200 dark:border-[#2f3336]">
                            <div className="relative inline-block">
                                <img
                                    src={imagePreview}
                                    alt="Uploaded"
                                    className="max-h-40 rounded-xl object-contain"
                                />
                                <button
                                    onClick={removeImage}
                                    className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center text-white transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Text Input */}
                    <div className="p-4">
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Describe the math concept you want to visualize..."
                            className="w-full bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 text-lg resize-none focus:outline-none min-h-[120px]"
                            disabled={isGenerating}
                        />
                    </div>

                    {/* Bottom Actions Bar */}
                    <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-[#2f3336]">
                        {/* Left Actions */}
                        <div className="flex items-center gap-2">
                            {/* Image Upload */}
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleImageUpload}
                                className="hidden"
                            />
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isGenerating}
                                className="p-2 rounded-xl hover:bg-gray-200 dark:hover:bg-[#2f3336] text-gray-500 dark:text-gray-400 transition-colors disabled:opacity-50"
                                title="Upload image"
                            >
                                <ImageIcon className="w-5 h-5" />
                            </button>

                            {/* Topic Dropdown */}
                            <div className="relative">
                                <button
                                    onClick={() => setShowTopicDropdown(!showTopicDropdown)}
                                    disabled={isGenerating}
                                    className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-gray-200 dark:hover:bg-[#2f3336] text-gray-700 dark:text-gray-300 text-sm transition-colors disabled:opacity-50"
                                >
                                    <Zap className="w-4 h-4" />
                                    {selectedTopic}
                                    <ChevronDown className="w-4 h-4" />
                                </button>
                                {showTopicDropdown && (
                                    <>
                                        <div
                                            className="fixed inset-0 z-40"
                                            onClick={() => setShowTopicDropdown(false)}
                                        />
                                        <div className="absolute bottom-full left-0 mb-2 w-48 bg-white dark:bg-[#16181c] rounded-xl border border-gray-200 dark:border-[#2f3336] shadow-xl z-50 py-2 max-h-60 overflow-y-auto">
                                            {TOPICS.map((topic) => (
                                                <button
                                                    key={topic}
                                                    onClick={() => {
                                                        setSelectedTopic(topic);
                                                        setShowTopicDropdown(false);
                                                    }}
                                                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-[#2f3336] transition-colors ${selectedTopic === topic
                                                        ? "text-indigo-600 dark:text-indigo-400 font-medium"
                                                        : "text-gray-700 dark:text-gray-300"
                                                        }`}
                                                >
                                                    {topic}
                                                </button>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Language Dropdown */}
                            <div className="relative">
                                <button
                                    onClick={() => setShowLanguageDropdown(!showLanguageDropdown)}
                                    disabled={isGenerating}
                                    className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-gray-200 dark:hover:bg-[#2f3336] text-gray-700 dark:text-gray-300 text-sm transition-colors disabled:opacity-50"
                                >
                                    <Globe className="w-4 h-4" />
                                    {LANGUAGES.find(l => l.code === selectedLanguage)?.flag}
                                    <ChevronDown className="w-4 h-4" />
                                </button>
                                {showLanguageDropdown && (
                                    <>
                                        <div
                                            className="fixed inset-0 z-40"
                                            onClick={() => setShowLanguageDropdown(false)}
                                        />
                                        <div className="absolute bottom-full left-0 mb-2 w-40 bg-white dark:bg-[#16181c] rounded-xl border border-gray-200 dark:border-[#2f3336] shadow-xl z-50 py-2">
                                            {LANGUAGES.map((lang) => (
                                                <button
                                                    key={lang.code}
                                                    onClick={() => {
                                                        setSelectedLanguage(lang.code);
                                                        setShowLanguageDropdown(false);
                                                    }}
                                                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-[#2f3336] transition-colors flex items-center gap-2 ${selectedLanguage === lang.code
                                                        ? "text-indigo-600 dark:text-indigo-400 font-medium"
                                                        : "text-gray-700 dark:text-gray-300"
                                                        }`}
                                                >
                                                    <span>{lang.flag}</span>
                                                    {lang.name}
                                                </button>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Generate Button */}
                        <button
                            onClick={handleGenerate}
                            disabled={isGenerating || (!prompt.trim() && !imagePreview)}
                            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25"
                        >
                            {isGenerating ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Generating...
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-5 h-5" />
                                    Generate
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Progress Overlay */}
                {isGenerating && (
                    <div className="absolute inset-0 bg-white/80 dark:bg-black/80 backdrop-blur-sm rounded-3xl flex flex-col items-center justify-center gap-4 z-10">
                        <div className="w-64 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500 ease-out"
                                style={{ width: `${generationProgress}%` }}
                            />
                        </div>
                        <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>{currentStep}</span>
                        </div>
                        <span className="text-2xl font-bold text-gray-900 dark:text-white">
                            {generationProgress}%
                        </span>
                    </div>
                )}
            </div>

            {/* Example Prompts */}
            {!isGenerating && (
                <div className="space-y-3">
                    <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                        Try an example:
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                        {EXAMPLE_PROMPTS.map((example, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleExampleClick(example)}
                                className="px-4 py-2 rounded-full bg-gray-100 dark:bg-[#2f3336] text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-200 dark:hover:bg-[#3f4346] transition-colors"
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Features Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8">
                <FeatureCard
                    icon={<Sparkles className="w-6 h-6" />}
                    title="AI-Powered"
                    description="Uses advanced LLMs to understand and visualize math concepts"
                />
                <FeatureCard
                    icon={<Video className="w-6 h-6" />}
                    title="Math Animations"
                    description="Professional-quality mathematical animations"
                />
                <FeatureCard
                    icon={<Mic className="w-6 h-6" />}
                    title="Voice Narration"
                    description="Natural voice-over explanations in English or Hindi"
                />
            </div>
        </div>
    );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
    return (
        <div className="p-4 rounded-2xl bg-gray-50 dark:bg-[#16181c] border border-gray-200 dark:border-[#2f3336]">
            <div className="flex items-center gap-3 mb-2">
                <div className="text-indigo-500">
                    {icon}
                </div>
                <h3 className="font-medium text-gray-900 dark:text-white">{title}</h3>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
        </div>
    );
}
