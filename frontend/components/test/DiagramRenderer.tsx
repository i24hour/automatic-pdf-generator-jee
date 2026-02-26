'use client';

import React from 'react';

interface DiagramRendererProps {
    /** New format: raw inline SVG string from the LLM */
    svgContent?: string | null;
    /** Legacy format: JSON string {type, params} for old TikZ-based renderer */
    diagramJson?: string | null;
}

/**
 * Renders NTA-style diagrams inline in the CBT interface.
 * New questions include a diagram_svg field (raw SVG string) — rendered directly.
 * Legacy questions use diagram_json (TikZ params) — those showed via old API, now shown as a fallback placeholder.
 */
export default function DiagramRenderer({ svgContent, diagramJson }: DiagramRendererProps) {
    // Priority: new SVG format over legacy TikZ format
    if (svgContent && svgContent.trim().startsWith('<svg')) {
        return (
            <div className="flex justify-center my-4">
                <div
                    className="bg-white rounded-lg border border-gray-200 shadow-sm p-4"
                    style={{ maxWidth: 440 }}
                    // SVG comes from our own backend/LLM. Sanitize in production if needed.
                    dangerouslySetInnerHTML={{ __html: svgContent }}
                />
            </div>
        );
    }

    // Legacy TikZ format — show a placeholder until old tests are regenerated
    if (diagramJson) {
        try {
            const parsed = JSON.parse(diagramJson);
            if (parsed?.type) {
                return (
                    <div className="flex justify-center my-4">
                        <div className="bg-gray-50 border border-dashed border-gray-300 rounded-lg px-6 py-3 text-xs text-gray-400 italic">
                            [Diagram: {parsed.type}]
                        </div>
                    </div>
                );
            }
        } catch {
            // invalid JSON — ignore
        }
    }

    return null;
}
