import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL } from "@/lib/config";

export interface TestSummary {
    id: string;
    title: string;
    subject: string;
    topics: string[];
    exam_type: string;
    difficulty: string;
    total_questions: number;
    total_marks: number;
    duration_minutes: number;
    attempt_count: number;
    creator_name: string;
    created_at: string;
}

export interface TestDetail extends TestSummary {
    questions_data?: any[];
}

export interface LeaderboardEntry {
    rank: number;
    user_name: string;
    score: number;
    accuracy: number;
    time_taken_seconds: number;
    submitted_at: string;
    is_current_user: boolean;
}

export function useCommunityApi() {
    const { authFetch } = useAuth();

    return {
        // Search public tests
        searchTests: async (
            search?: string,
            subject?: string,
            examType?: string,
            sortBy: string = "newest"
        ): Promise<TestSummary[]> => {
            const params = new URLSearchParams();
            if (search) params.append("search", search);
            if (subject) params.append("subject", subject);
            if (examType) params.append("exam_type", examType);
            params.append("sort_by", sortBy);

            const res = await authFetch(`${API_BASE_URL}/api/community/tests?${params.toString()}`);
            if (!res.ok) throw new Error("Failed to search tests");
            return await res.json();
        },

        // Save a generated test as public
        createTest: async (data: any): Promise<{ id: string; message: string }> => {
            const res = await authFetch(`${API_BASE_URL}/api/community/tests/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to create test");
            }
            return await res.json();
        },

        // Get test details (pre-attempt)
        getTestDetails: async (testId: string): Promise<TestDetail> => {
            const res = await authFetch(`${API_BASE_URL}/api/community/tests/${testId}`);
            if (!res.ok) throw new Error("Failed to get test details");
            return await res.json();
        },

        // Start a test attempt
        startTest: async (testId: string): Promise<{ attempt_id: string; redirect_url: string }> => {
            const res = await authFetch(`${API_BASE_URL}/api/community/tests/${testId}/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
            if (!res.ok) throw new Error("Failed to start test");
            return await res.json();
        },

        // Get leaderboard
        getLeaderboard: async (testId: string): Promise<LeaderboardEntry[]> => {
            const res = await authFetch(`${API_BASE_URL}/api/community/tests/${testId}/leaderboard`);
            if (!res.ok) throw new Error("Failed to get leaderboard");
            return await res.json();
        }
    };
}
