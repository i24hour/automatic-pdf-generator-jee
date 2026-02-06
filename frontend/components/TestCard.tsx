import React from "react";
import { BookOpen, Clock, Users, BarChart } from "lucide-react";
import Link from "next/link";
import { TestSummary } from "@/lib/community-api";

interface TestCardProps {
    test: TestSummary;
}

const TestCard: React.FC<TestCardProps> = ({ test }) => {
    // Format difficulty color
    const difficultyColor = {
        Easy: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        Medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
        Hard: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    }[test.difficulty] || "bg-gray-100 text-gray-700";

    return (
        <div className="bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-800 rounded-xl p-5 hover:shadow-lg transition-all duration-200 md:hover:scale-[1.02]">
            {/* Header: Subject & Difficulty */}
            <div className="flex justify-between items-start mb-3">
                <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400 border border-blue-100 dark:border-blue-800">
                    {test.subject}
                </span>
                <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${difficultyColor} border border-transparent`}>
                    {test.difficulty}
                </span>
            </div>

            {/* Title & Exam Type */}
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1 line-clamp-1" title={test.title}>
                {test.title}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 flex items-center gap-2">
                <span className="font-medium text-purple-600 dark:text-purple-400">{test.exam_type}</span>
                <span>•</span>
                <span>by {test.creator_name}</span>
            </p>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm text-gray-600 dark:text-gray-400 mb-5">
                <div className="flex items-center gap-1.5">
                    <BookOpen className="w-4 h-4 text-gray-400" />
                    <span>{test.total_questions} Qs</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span>{test.duration_minutes} mins</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Users className="w-4 h-4 text-gray-400" />
                    <span>{test.attempt_count} attempts</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <BarChart className="w-4 h-4 text-gray-400" />
                    <span>{test.total_marks} Marks</span>
                </div>
            </div>

            {/* Action Button */}
            <Link
                href={`/community/test/${test.id}`}
                className="block w-full text-center py-2.5 bg-black dark:bg-white text-white dark:text-black font-semibold rounded-lg hover:opacity-90 transition-opacity"
            >
                View & Attempt
            </Link>
        </div>
    );
};

export default TestCard;
