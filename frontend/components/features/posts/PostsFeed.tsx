'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app';

interface Post {
    id: string;
    user_id: string;
    username: string | null;
    pdf_url: string;
    pdf_filename: string;
    caption: string | null;
    subject: string;
    topic: string;
    level: string;
    difficulty: string;
    question_count: number;
    has_solutions: boolean;
    visibility: string;
    download_count: number;
    like_count: number;
    view_count: number;
    created_at: string;
    is_liked: boolean;
}

interface FeedResponse {
    posts: Post[];
    has_more: boolean;
    next_cursor: string | null;
}

export default function PostsFeed() {
    const { token, user } = useAuth();
    const searchParams = useSearchParams();

    // Initial state from URL params
    const [posts, setPosts] = useState<Post[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasMore, setHasMore] = useState(false);
    const [nextCursor, setNextCursor] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'feed' | 'my'>('feed');
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const [filter, setFilter] = useState({
        subject: searchParams.get('subject') || '',
        level: searchParams.get('level') || ''
    });

    const [error, setError] = useState('');
    const [searchInput, setSearchInput] = useState(searchParams.get('q') || '');
    const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');

    const fetchPosts = useCallback(async (cursor?: string) => {
        try {
            const params = new URLSearchParams();
            if (filter.subject) params.append('subject', filter.subject);
            if (filter.level) params.append('level', filter.level);
            if (cursor) params.append('cursor', cursor);
            params.append('limit', '20');

            const headers: Record<string, string> = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            let url = `${API_URL}/api/posts`;
            if (viewMode === 'my') {
                url = `${API_URL}/api/posts/my`;
                // My posts endpoint might return list directly, not paginated struct?
                // Checking backend: /api/posts/my returns List[PostResponse] directly.
                // So we need to handle that.
            }

            const res = await fetch(`${url}${viewMode === 'feed' ? `?${params}` : ''}`, { headers });
            if (!res.ok) throw new Error('Failed to fetch posts');

            const data = await res.json();

            if (viewMode === 'my') {
                // Backend returns array for /my
                setPosts(data);
                setHasMore(false);
            } else {
                // Feed returns { posts, has_more }
                if (cursor) {
                    setPosts(prev => [...prev, ...data.posts]);
                } else {
                    setPosts(data.posts);
                }
                setHasMore(data.has_more);
                setNextCursor(data.next_cursor);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load posts');
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [token, filter, viewMode]);

    // Re-fetch when filter changes
    useEffect(() => {
        setLoading(true);
        setPosts([]);
        fetchPosts();
    }, [fetchPosts]);

    // Handle URL param updates (e.g. navigation from generator)
    useEffect(() => {
        const subject = searchParams.get('subject');
        const level = searchParams.get('level');
        const q = searchParams.get('q');

        if (subject || level || q) {
            if (subject) setFilter(prev => ({ ...prev, subject }));
            if (level) setFilter(prev => ({ ...prev, level }));
            if (q) {
                setSearchInput(q);
                setSearchQuery(q);
            }
        }
    }, [searchParams]);

    const applySearch = () => {
        setSearchQuery(searchInput.trim());
    };

    const filteredPosts = useMemo(() => {
        if (!searchQuery) return posts;
        const query = searchQuery.toLowerCase();
        return posts.filter(post => {
            const values = [
                post.topic,
                post.subject,
                post.caption,
                post.username,
                post.pdf_filename
            ];
            return values.some(value => value && value.toLowerCase().includes(query));
        });
    }, [posts, searchQuery]);

    const loadMore = () => {
        if (loadingMore || !hasMore || !nextCursor) return;
        setLoadingMore(true);
        fetchPosts(nextCursor);
    };

    const handleLike = async (postId: string, isLiked: boolean) => {
        if (!token) {
            alert('Please login to like posts');
            return;
        }

        try {
            const method = isLiked ? 'DELETE' : 'POST';
            const res = await fetch(`${API_URL}/api/posts/${postId}/like`, {
                method,
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                setPosts(prev => prev.map(p =>
                    p.id === postId
                        ? { ...p, is_liked: !isLiked, like_count: data.like_count }
                        : p
                ));
            }
        } catch (err) {
            console.error('Like failed:', err);
        }
    };

    const handleDelete = async (postId: string) => {
        if (!confirm("Are you sure you want to delete this post?")) return;
        setDeletingId(postId);
        try {
            const res = await fetch(`${API_URL}/api/posts/${postId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (res.ok) {
                setPosts(prev => prev.filter(p => p.id !== postId));
            } else {
                alert("Failed to delete post");
            }
        } catch (error) {
            console.error(error);
            alert("Error deleting post");
        } finally {
            setDeletingId(null);
        }
    };

    const handleDownload = async (post: Post) => {
        // Track download
        try {
            await fetch(`${API_URL}/api/posts/${post.id}/download`, { method: 'POST' });
        } catch (err) {
            console.error('Track download failed:', err);
        }

        // Open PDF in new tab
        window.open(post.pdf_url, '_blank');
    };

    const formatTimeAgo = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    const getLevelColor = (level: string) => {
        switch (level) {
            case 'JEE Advanced': return '#ef4444';
            case 'JEE Mains': return '#f59e0b';
            case 'NEET': return '#10b981';
            default: return '#6b7280';
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--background)' }}>
            {/* Header */}
            {/* Header */}
            <header className="sticky top-0 bg-white/95 dark:bg-black/95 backdrop-blur-md border-b border-gray-200 dark:border-[#2f3336] z-50 px-6 py-4">
                <div className="w-full flex justify-between items-center">
                    <h1 className="text-2xl font-bold m-0">
                        <span className="gradient-text">Community</span>
                    </h1>
                </div>
            </header>

            {/* View Tabs */}
            {user && (
                <div className="flex p-1 bg-gray-100 dark:bg-gray-800 rounded-xl mx-4 mt-4">
                    <button
                        onClick={() => { setViewMode('feed'); setPosts([]); setLoading(true); }}
                        className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${viewMode === 'feed'
                            ? 'bg-white dark:bg-gray-700 shadow-sm text-indigo-600'
                            : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                            }`}
                    >
                        Community Feed
                    </button>
                    <button
                        onClick={() => { setViewMode('my'); setPosts([]); setLoading(true); }}
                        className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${viewMode === 'my'
                            ? 'bg-white dark:bg-gray-700 shadow-sm text-indigo-600'
                            : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                            }`}
                    >
                        My Posts
                    </button>
                </div>
            )}

            {/* Filters */}
            <div style={{
                padding: '16px 24px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap'
            }}>
                <select
                    className="form-select"
                    value={filter.subject}
                    onChange={(e) => setFilter(f => ({ ...f, subject: e.target.value }))}
                    style={{ flex: 1, padding: '10px 36px 10px 16px', minWidth: '110px' }}
                >
                    <option value="">Subject</option>
                    <option value="Physics">Physics</option>
                    <option value="Chemistry">Chemistry</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Biology">Biology</option>
                </select>
                <select
                    className="form-select"
                    value={filter.level}
                    onChange={(e) => setFilter(f => ({ ...f, level: e.target.value }))}
                    style={{ flex: 1, padding: '10px 36px 10px 16px', minWidth: '100px' }}
                >
                    <option value="">Level</option>
                    <option value="JEE Mains">JEE Mains</option>
                    <option value="JEE Advanced">JEE Advanced</option>
                    <option value="NEET">NEET</option>
                </select>
                <div style={{ flex: 2, display: 'flex', gap: '8px', minWidth: '220px' }}>
                    <input
                        type="text"
                        placeholder="Search by topic, subject, caption, or username"
                        value={searchInput}
                        onChange={(e) => {
                            setSearchInput(e.target.value);
                            // Debounce search
                            const timeoutId = setTimeout(() => {
                                setSearchQuery(e.target.value.trim());
                            }, 500);
                            return () => clearTimeout(timeoutId);
                        }}
                        className="form-input"
                        style={{ flex: 1, padding: '10px 14px' }}
                    />
                </div>
            </div>

            {/* Posts Feed */}
            <main>
                {loading ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <div className="spinner" style={{ margin: '0 auto', borderColor: 'var(--border)', borderTopColor: 'var(--primary)' }} />
                        <p style={{ marginTop: '16px', color: 'var(--text-muted)' }}>Loading posts...</p>
                    </div>
                ) : error ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <p style={{ color: 'var(--error)' }}>{error}</p>
                    </div>
                ) : posts.length === 0 ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <p style={{ fontSize: '3rem', marginBottom: '16px' }}>📚</p>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>No posts yet. Be the first to share!</p>
                        <Link href="/" className="btn-primary">Generate & Share</Link>
                    </div>
                ) : filteredPosts.length === 0 ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <p style={{ fontSize: '2.5rem', marginBottom: '16px' }}>🔎</p>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '8px' }}>No results found.</p>
                        <p style={{ color: 'var(--text-muted)' }}>Try a different keyword or clear your search.</p>
                    </div>
                ) : (
                    <>
                        {filteredPosts.map(post => (
                            <article
                                key={post.id}
                                style={{
                                    padding: '20px 24px',
                                    borderBottom: '1px solid var(--border)',
                                    transition: 'background 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = 'var(--secondary)'}
                                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                            >
                                {/* Header */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <div style={{
                                            width: '40px',
                                            height: '40px',
                                            borderRadius: '50%',
                                            background: 'linear-gradient(135deg, var(--primary), #06b6d4)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: 'white',
                                            fontWeight: 600,
                                            fontSize: '1rem'
                                        }}>
                                            {post.username?.[0]?.toUpperCase() || '?'}
                                        </div>
                                        <div>
                                            <p style={{ fontWeight: 600, margin: 0, fontSize: '0.95rem' }}>
                                                @{post.username || 'anonymous'}
                                            </p>
                                            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                                                {formatTimeAgo(post.created_at)}
                                            </p>
                                        </div>
                                    </div>
                                    <span style={{
                                        padding: '4px 10px',
                                        borderRadius: '20px',
                                        fontSize: '0.75rem',
                                        fontWeight: 600,
                                        color: 'white',
                                        background: getLevelColor(post.level)
                                    }}>
                                        {post.level}
                                    </span>
                                </div>

                                {/* Content */}
                                {post.caption && (
                                    <p style={{ marginBottom: '12px', lineHeight: 1.5 }}>{post.caption}</p>
                                )}

                                {/* PDF Card */}
                                <div
                                    onClick={() => handleDownload(post)}
                                    style={{
                                        background: 'var(--background)',
                                        border: '1px solid var(--border)',
                                        borderRadius: '12px',
                                        padding: '16px',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.borderColor = 'var(--primary)';
                                        e.currentTarget.style.boxShadow = '0 2px 8px rgba(79, 70, 229, 0.1)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.borderColor = 'var(--border)';
                                        e.currentTarget.style.boxShadow = 'none';
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                        <div style={{
                                            width: '48px',
                                            height: '48px',
                                            borderRadius: '8px',
                                            background: 'linear-gradient(135deg, #ef4444, #f97316)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: 'white',
                                            fontSize: '1.2rem'
                                        }}>
                                            📄
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <p style={{ fontWeight: 600, margin: 0, fontSize: '0.9rem' }}>
                                                {post.topic}
                                            </p>
                                            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                                                {post.subject} • {post.question_count} questions • {post.difficulty}
                                                {post.has_solutions && ' • With Solutions'}
                                            </p>
                                        </div>
                                        <span style={{ color: 'var(--primary)', fontSize: '1.2rem' }}>↓</span>
                                    </div>
                                </div>

                                {/* Actions */}
                                <div style={{
                                    display: 'flex',
                                    gap: '24px',
                                    marginTop: '16px',
                                    paddingLeft: '4px'
                                }}>
                                    <button
                                        onClick={() => handleLike(post.id, post.is_liked)}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            color: post.is_liked ? '#ef4444' : 'var(--text-muted)',
                                            fontSize: '0.9rem',
                                            padding: '4px 8px',
                                            borderRadius: '8px',
                                            transition: 'all 0.2s'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
                                        onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
                                    >
                                        <span style={{ fontSize: '1.1rem' }}>{post.is_liked ? '❤️' : '🤍'}</span>
                                        <span>{post.like_count}</span>
                                    </button>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        color: 'var(--text-muted)',
                                        fontSize: '0.9rem'
                                    }}>
                                        <span>⬇️</span>
                                        <span>{post.download_count}</span>
                                    </div>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        color: 'var(--text-muted)',
                                        fontSize: '0.9rem'
                                    }}>
                                        <span>👁️</span>
                                        <span>{post.view_count}</span>
                                    </div>

                                    {/* Delete Button (Owner Only) */}
                                    {user && user.id === post.user_id && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation(); // Prevent card click
                                                handleDelete(post.id);
                                            }}
                                            disabled={deletingId === post.id}
                                            style={{
                                                marginLeft: 'auto',
                                                background: '#fee2e2',
                                                border: '1px solid #ef4444',
                                                borderRadius: '8px',
                                                padding: '4px 8px',
                                                cursor: 'pointer',
                                                color: '#b91c1c',
                                                fontSize: '0.8rem',
                                                fontWeight: 600,
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '4px'
                                            }}
                                        >
                                            {deletingId === post.id ? 'Deleting...' : '🗑️ Delete'}
                                        </button>
                                    )}
                                </div>
                            </article>
                        ))}

                        {/* Load More */}
                        {hasMore && (
                            <div style={{ padding: '24px', textAlign: 'center' }}>
                                <button
                                    onClick={loadMore}
                                    disabled={loadingMore}
                                    className="btn-secondary"
                                    style={{ padding: '10px 24px' }}
                                >
                                    {loadingMore ? 'Loading...' : 'Load More'}
                                </button>
                            </div>
                        )}
                    </>
                )}
            </main>
        </div>
    );
}
