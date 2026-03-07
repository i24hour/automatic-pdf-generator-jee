"use client";

import React, { createContext, useContext, useState, useRef, useEffect, ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { logError } from "@/lib/logger";

// Types
interface GenerateResponse {
    success: boolean;
    message: string;
    pdf_filename?: string;
    pdf_base64?: string;
    shared_pdf_id?: string;
    total_mcq: number;
    total_numerical: number;
    rate_limit_remaining: number;
    rate_limit_reset_hours: number;
    verification_stats?: {
        total_numerical: number;
        verified: number;
        corrected: number;
    };
}

interface GenerationContextType {
    isGenerating: boolean;
    progressStep: number;
    progressMessage: string;
    result: GenerateResponse | null;
    error: string | null;
    elapsedTime: number;
    jobId: string | null;
    partialQuestions: any[];
    startGeneration: (params: any, isInstitute?: boolean) => Promise<void>;
    cancelGeneration: () => void;
    clearResult: () => void;
    downloadPDF: (res?: GenerateResponse) => void;
    updateResult: (updates: Partial<GenerateResponse>) => void;
}

const GenerationContext = createContext<GenerationContextType | undefined>(undefined);

import { API_BASE_URL } from "@/lib/config";

export function GenerationProvider({ children }: { children: ReactNode }) {
    const { token, authFetch } = useAuth();

    // State
    const [isGenerating, setIsGenerating] = useState(false);
    const [progressStep, setProgressStep] = useState(0);
    const [progressMessage, setProgressMessage] = useState("");
    const [result, setResult] = useState<GenerateResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [elapsedTime, setElapsedTime] = useState(0);
    const [jobId, setJobId] = useState<string | null>(null);
    const [partialQuestions, setPartialQuestions] = useState<any[]>([]);

    // Refs
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    // Cleanup on unmount (only if app closes, otherwise we want it to persist)
    useEffect(() => {
        return () => {
            // In a global context, unmount usually equals app close.
            // We can optionally leave it running, but cleaning up intervals is good.
            if (timerRef.current) clearInterval(timerRef.current);
            if (eventSourceRef.current) eventSourceRef.current.close();
        };
    }, []);

    const cleanupGeneration = () => {
        setIsGenerating(false);
        if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
    };

    const cancelGeneration = () => {
        cleanupGeneration();
        setError("Generation cancelled.");
        setResult(null);
    };

    const clearResult = () => {
        setResult(null);
        setError(null);
        setProgressStep(0);
        setProgressMessage("");
        setJobId(null);
        setElapsedTime(0);
        setPartialQuestions([]);
    };

    const startTimer = () => {
        setElapsedTime(0);
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
            setElapsedTime(prev => {
                if (prev >= 900) { // 15 mins timeout
                    cleanupGeneration();
                    setError("Generation timed out (limit: 15 mins).");
                    logError({ error_type: "GENERATION_TIMEOUT", error_details: "Timeout inside context" });
                    return prev;
                }
                return prev + 1;
            });
        }, 1000);
    };

    const connectToSSEStream = (streamJobId: string): Promise<void> => {
        return new Promise((resolve, reject) => {
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }

            const freshToken = localStorage.getItem("auth_token") || token;
            const sseUrl = `${API_BASE_URL}/api/generate-sse/${streamJobId}/stream?token=${encodeURIComponent(freshToken || '')}`;

            const eventSource = new EventSource(sseUrl);
            eventSourceRef.current = eventSource;

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // Progressive display: capture questions as soon as they're ready
                    if (Array.isArray(data.partial_questions) && data.partial_questions.length > 0) {
                        setPartialQuestions(data.partial_questions);
                    }

                    // Update progress
                    if (data.progress !== undefined) setProgressStep(data.progress);
                    if (data.message) setProgressMessage(data.message);

                    const statusToStep: Record<string, number> = {
                        "pending": 0, "analyzing": 1, "generating_mcqs": 2,
                        "generating_numericals": 3, "verifying": 4,
                        "compiling_pdf": 5, "uploading": 5, "done": 6, "failed": 0
                    };
                    if (data.status in statusToStep) {
                        setProgressStep(statusToStep[data.status]);
                    }

                    if (data.status === "done" && data.result) {
                        setResult(data.result as GenerateResponse);
                        cleanupGeneration();
                        resolve();
                    } else if (data.status === "failed") {
                        setError(data.error || "Generation failed");
                        cleanupGeneration();
                        reject(new Error(data.error));
                    }
                } catch (e) {
                    console.error("Context: Error parsing SSE", e);
                }
            };

            eventSource.onerror = async (err) => {
                console.error("Context: SSE Error", err);
                eventSource.close();
                setProgressMessage("Connection interrupted, reconnecting...");

                // Simple reconnection strategy
                try {
                    await new Promise(r => setTimeout(r, 2000));
                    const statusRes = await authFetch(`${API_BASE_URL}/api/generate-sse/${streamJobId}/status`);
                    if (statusRes.ok) {
                        const statusData = await statusRes.json();
                        // Pick up any questions that arrived before reconnect
                        if (Array.isArray(statusData.partial_questions) && statusData.partial_questions.length > 0) {
                            setPartialQuestions(statusData.partial_questions);
                        }
                        if (statusData.status === "done" && statusData.result) {
                            setResult(statusData.result);
                            cleanupGeneration();
                            resolve();
                        } else if (statusData.status === "failed") {
                            setError(statusData.error);
                            cleanupGeneration();
                            reject(new Error(statusData.error));
                        } else {
                            // Reconnect
                            connectToSSEStream(streamJobId).then(resolve).catch(reject);
                        }
                    } else {
                        throw new Error("Failed to check status");
                    }
                } catch (reconnectErr) {
                    setError("Connection lost.");
                    cleanupGeneration();
                    reject(reconnectErr);
                }
            };
        });
    };

    const startGeneration = async (params: any, isInstitute: boolean = false) => {
        setIsGenerating(true);
        setError(null);
        setResult(null);
        setPartialQuestions([]);
        setProgressStep(0);
        setProgressMessage("Starting generation...");

        startTimer();

        try {
            const startUrl = isInstitute
                ? `${API_BASE_URL}/api/institute/generate-sse/start`
                : `${API_BASE_URL}/api/generate-sse/start`;

            const startResponse = await authFetch(startUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(params),
            });

            if (!startResponse.ok) {
                const errData = await startResponse.json();
                throw new Error(errData.detail || "Failed to start");
            }

            const startData = await startResponse.json();
            setJobId(startData.job_id);
            setProgressMessage("Connecting to stream...");

            await connectToSSEStream(startData.job_id);
        } catch (err: any) {
            console.error("Start Generation Error:", err);
            setError(err.message || "Failed to start generation");
            cleanupGeneration();
        }
    };

    const downloadPDF = (res: GenerateResponse | null = result) => {
        if (!res) return;

        if (res.pdf_base64) {
            const binary = atob(res.pdf_base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: 'application/pdf' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            let filename = res.pdf_filename || 'test_paper.pdf';
            if (!filename.toLowerCase().endsWith('.pdf')) filename += '.pdf';
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else if (res.pdf_filename) {
            window.open(`${API_BASE_URL}/api/download/${res.pdf_filename}`, "_blank");
        }
    };

    const updateResult = (updates: Partial<GenerateResponse>) => {
        setResult(prev => prev ? { ...prev, ...updates } : null);
    };

    return (
        <GenerationContext.Provider value={{
            isGenerating,
            progressStep,
            progressMessage,
            result,
            error,
            elapsedTime,
            jobId,
            partialQuestions,
            startGeneration,
            cancelGeneration,
            clearResult,
            downloadPDF,
            updateResult
        }}>
            {children}
        </GenerationContext.Provider>
    );
}

export function useGeneration() {
    const context = useContext(GenerationContext);
    if (context === undefined) {
        throw new Error("useGeneration must be used within a GenerationProvider");
    }
    return context;
}
