import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, X, Search, Check } from 'lucide-react';
import { searchChapters, getChaptersForSubject } from '@/lib/ncert-chapters';

interface TopicSelectorProps {
    subject: string;
    selectedChapters: string[];
    onSelectionChange: (chapters: string[]) => void;
    customTopic: string;
    onCustomTopicChange: (topic: string) => void;
    placeholder?: string;
    className?: string;
    error?: boolean;
}

export default function TopicSelector({
    subject,
    selectedChapters,
    onSelectionChange,
    customTopic,
    onCustomTopicChange,
    placeholder = "Select chapters or type custom topic...",
    className = "",
    error = false
}: TopicSelectorProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const wrapperRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Initial chapters list
    const [filteredChapters, setFilteredChapters] = useState<{ class: string; name: string; matchedTopic?: string }[]>([]);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Update filtered chapters when search query changes (or subject changes)
    useEffect(() => {
        const chapters = searchQuery.trim()
            ? searchChapters(subject, searchQuery.trim())
            : getChaptersForSubject(subject);

        setFilteredChapters(chapters);
    }, [searchQuery, subject]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
        setIsOpen(true);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent form submission
            if (searchQuery.trim()) {
                handleSelectChapter(searchQuery.trim());
            }
        }
    };

    const handleSelectChapter = (chapter: string) => {
        if (!selectedChapters.includes(chapter)) {
            const newSelection = [...selectedChapters, chapter];
            onSelectionChange(newSelection);
        }
        // Always clear search query after selection/addition
        setSearchQuery("");
        inputRef.current?.focus();
    };

    const handleRemoveChapter = (chapter: string) => {
        const newSelection = selectedChapters.filter(c => c !== chapter);
        onSelectionChange(newSelection);
    };

    return (
        <div className={`relative ${className}`} ref={wrapperRef}>
            {/* Selected Tags Area */}
            {selectedChapters.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2 p-1 bg-gray-50 dark:bg-[#0a0b0d]/50 rounded-lg border border-dashed border-gray-200 dark:border-gray-800">
                    {selectedChapters.map((chapter, idx) => (
                        <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs rounded-full border border-indigo-200 dark:border-indigo-800">
                            {chapter}
                            <button
                                type="button"
                                onClick={() => handleRemoveChapter(chapter)}
                                className="hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-full p-0.5 transition-colors"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </span>
                    ))}
                    <div className="text-xs text-gray-400 flex items-center px-2">
                        {selectedChapters.length} selected
                    </div>
                </div>
            )}

            <div className="relative group">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-500 transition-colors">
                    <Search className="w-4 h-4" />
                </div>
                <input
                    ref={inputRef}
                    type="text"
                    value={searchQuery}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    onFocus={() => setIsOpen(true)}
                    placeholder={selectedChapters.length > 0 ? "Add another topic..." : placeholder}
                    className={`w-full pl-9 pr-10 py-2.5 bg-white dark:bg-[#0a0b0d] border rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:outline-none focus:ring-2 transition-all ${error
                        ? "border-red-300 focus:border-red-500 focus:ring-red-100 dark:focus:ring-red-900/20"
                        : "border-gray-300 dark:border-gray-700 focus:border-indigo-500 focus:ring-indigo-100 dark:focus:ring-indigo-900/20"
                        }`}
                />
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                    <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                </button>
            </div>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="absolute z-50 w-full mt-1 bg-white dark:bg-[#16181c] border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-60 overflow-y-auto animate-in fade-in zoom-in-95 duration-100">

                    {/* Add Custom Option */}
                    {searchQuery.trim() && !filteredChapters.some(c => c.name.toLowerCase() === searchQuery.trim().toLowerCase()) && !selectedChapters.includes(searchQuery.trim()) && (
                        <button
                            type="button"
                            onClick={() => handleSelectChapter(searchQuery.trim())}
                            className="w-full text-left px-4 py-3 text-sm flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 border-b border-gray-100 dark:border-gray-800"
                        >
                            <span className="font-bold">+ Add "{searchQuery.trim()}"</span>
                            <span className="text-xs text-gray-500 font-normal ml-auto">Custom Topic</span>
                        </button>
                    )}

                    {filteredChapters.length === 0 && !searchQuery.trim() ? (
                        <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                            Type to add a custom topic
                        </div>
                    ) : (
                        <div className="py-1">
                            {/* Group by Class if needed, or just flat list */}
                            {["Class 11", "Class 12"].map(className => {
                                const classChapters = filteredChapters.filter(c => c.class === className);
                                if (classChapters.length === 0) return null;

                                return (
                                    <div key={className}>
                                        <div className="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 uppercase tracking-wider">
                                            {className}
                                        </div>
                                        {classChapters.map((chapter, idx) => {
                                            const isSelected = selectedChapters.includes(chapter.name);
                                            // Unique key combining class, name and matched topic
                                            const key = `${className}-${chapter.name}-${idx}`;

                                            return (
                                                <button
                                                    key={key}
                                                    type="button"
                                                    onClick={() => handleSelectChapter(chapter.name)}
                                                    className={`w-full text-left px-4 py-2 text-sm flex items-center justify-between transition-colors ${isSelected
                                                        ? "bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300"
                                                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                                                        }`}
                                                >
                                                    <div>
                                                        <span className="font-medium">{chapter.name}</span>
                                                        {chapter.matchedTopic && (
                                                            <span className="block text-xs text-gray-500 dark:text-gray-500 mt-0.5">
                                                                Matches: "{chapter.matchedTopic}"
                                                            </span>
                                                        )}
                                                    </div>
                                                    {isSelected && <Check className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />}
                                                </button>
                                            );
                                        })}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
            {error && <p className="mt-1 text-xs text-red-500">Please select at least one topic.</p>}
        </div>
    );
}
