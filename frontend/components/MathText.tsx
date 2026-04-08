import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface MathTextProps {
    content: string;
    className?: string;
}

const MathText: React.FC<MathTextProps> = ({ content, className = '' }) => {
    // Basic preprocessing to ensure LaTeX block delimiters $$...$$ usually map to new lines
    // but in markdown they are block math.
    // Also, handle the user's specific case where $m_1 = 2$ might be used.

    return (
        <div className={`prose dark:prose-invert max-w-none ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    p: ({ children }) => <p className="mb-2 leading-relaxed text-gray-900 dark:text-gray-100">{children}</p>,
                    // Ensure block math is centered or handled well
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default React.memo(MathText);
