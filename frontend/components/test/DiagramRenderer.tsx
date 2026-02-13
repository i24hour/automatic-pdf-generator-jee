import React, { useState, useEffect } from 'react';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';

interface DiagramRendererProps {
    diagramJson: string;
}

export default function DiagramRenderer({ diagramJson }: DiagramRendererProps) {
    const [svgContent, setSvgContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [retryCount, setRetryCount] = useState(0);

    useEffect(() => {
        let isMounted = true;

        const fetchDiagram = async () => {
            if (!diagramJson) return;

            try {
                setLoading(true);
                setError(null);

                const parsed = JSON.parse(diagramJson);
                const { type, params } = parsed;

                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/diagram/render`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // Add Authorization header if needed, but currently diagram API is public/user-based?
                        // Assuming cookie auth or token handled by global fetch or interceptor
                        // But here we use raw fetch, so might need token.
                        // Actually page.tsx usually handles protected data.
                        // Let's rely on cookies if SameSite, or we need token from localStorage.
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify({
                        diagram_type: type, // Ensure backend expects these keys
                        params: params
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail?.error || data.error || "Failed to render diagram");
                }

                if (data.success && data.svg) {
                    if (isMounted) setSvgContent(data.svg);
                } else {
                    throw new Error(data.error || "Unknown error");
                }

            } catch (err: any) {
                if (isMounted) setError(err.message);
                console.error("Diagram Render Error:", err);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchDiagram();

        return () => { isMounted = false; };
    }, [diagramJson, retryCount]);

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                <div className="flex flex-col items-center gap-2 text-gray-500 text-sm">
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
                    <span>Rendering Diagram...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center p-6 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-800/30">
                <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
                <p className="text-xs text-red-600 dark:text-red-400 text-center mb-3">
                    Failed to render diagram: {error}
                </p>
                <button
                    onClick={() => setRetryCount(c => c + 1)}
                    className="flex items-center gap-1.5 text-xs font-medium text-red-700 dark:text-red-300 hover:underline"
                >
                    <RefreshCw className="w-3 h-3" /> Retry
                </button>
                {/* Debug Info */}
                <details className="mt-2 w-full">
                    <summary className="text-[10px] text-gray-400 cursor-pointer">Raw Data</summary>
                    <pre className="text-[10px] bg-red-100 dark:bg-black p-2 rounded mt-1 overflow-auto max-h-20">
                        {diagramJson}
                    </pre>
                </details>
            </div>
        );
    }

    if (!svgContent) {
        return null;
    }

    return (
        <div className="flex justify-center my-6">
            <div
                className="overflow-hidden rounded-lg bg-white dark:bg-white p-4 border border-gray-200 shadow-sm"
                dangerouslySetInnerHTML={{ __html: svgContent }}
            // Note: svgContent comes from our own backend which sanitizes via pdf2svg, but still good to be careful.
            // Since it's SVG string, standard sanitization applies if user input was minimal.
            />
        </div>
    );
}
