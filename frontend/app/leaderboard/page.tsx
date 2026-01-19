'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app';

interface LeaderboardEntry {
    user_id: string;
    username: string | null;
    value: number;
    rank: number;
}

export default function LeaderboardPage() {
    const [category, setCategory] = useState<'most_likes' | 'most_posts'>('most_likes');
    const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchLeaderboard = async () => {
            setLoading(true);
            setError('');
            try {
                const res = await fetch(`${API_URL}/api/posts/leaderboard/${category}?limit=20`);
                if (!res.ok) throw new Error('Failed to fetch leaderboard');
                const data = await res.json();
                setEntries(data.entries);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load');
            } finally {
                setLoading(false);
            }
        };

        fetchLeaderboard();
    }, [category]);

    const getRankBadge = (rank: number) => {
        switch (rank) {
            case 1: return { emoji: '🥇', color: '#ffd700' };
            case 2: return { emoji: '🥈', color: '#c0c0c0' };
            case 3: return { emoji: '🥉', color: '#cd7f32' };
            default: return { emoji: `#${rank}`, color: 'var(--text-muted)' };
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--background)' }}>
            {/* Header */}
            <header style={{
                position: 'sticky',
                top: 0,
                background: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(10px)',
                borderBottom: '1px solid var(--border)',
                zIndex: 100,
                padding: '16px 24px'
            }}>
                <div style={{ maxWidth: '600px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>
                        <span className="gradient-text">Leaderboard</span>
                    </h1>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <Link href="/posts" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>
                            Community
                        </Link>
                        <Link href="/" style={{ color: 'var(--primary)', fontWeight: 500, textDecoration: 'none' }}>
                            Generate
                        </Link>
                    </div>
                </div>
            </header>

            {/* Category Tabs */}
            <div style={{
                maxWidth: '600px',
                margin: '0 auto',
                padding: '16px 24px',
                display: 'flex',
                gap: '12px',
                borderBottom: '1px solid var(--border)'
            }}>
                <button
                    onClick={() => setCategory('most_likes')}
                    style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '10px',
                        border: 'none',
                        background: category === 'most_likes' ? 'var(--primary)' : 'var(--secondary)',
                        color: category === 'most_likes' ? 'white' : 'var(--foreground)',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    ❤️ Most Liked
                </button>
                <button
                    onClick={() => setCategory('most_posts')}
                    style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '10px',
                        border: 'none',
                        background: category === 'most_posts' ? 'var(--primary)' : 'var(--secondary)',
                        color: category === 'most_posts' ? 'white' : 'var(--foreground)',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                    }}
                >
                    📄 Most Posts
                </button>
            </div>

            {/* Leaderboard */}
            <main style={{ maxWidth: '600px', margin: '0 auto' }}>
                {loading ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <div className="spinner" style={{ margin: '0 auto', borderColor: 'var(--border)', borderTopColor: 'var(--primary)' }} />
                        <p style={{ marginTop: '16px', color: 'var(--text-muted)' }}>Loading leaderboard...</p>
                    </div>
                ) : error ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <p style={{ color: 'var(--error)' }}>{error}</p>
                    </div>
                ) : entries.length === 0 ? (
                    <div style={{ padding: '48px', textAlign: 'center' }}>
                        <p style={{ fontSize: '3rem', marginBottom: '16px' }}>🏆</p>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>No entries yet. Be the first!</p>
                        <Link href="/" className="btn-primary">Start Generating</Link>
                    </div>
                ) : (
                    <div style={{ padding: '12px 0' }}>
                        {entries.map((entry, index) => {
                            const badge = getRankBadge(entry.rank);
                            return (
                                <div
                                    key={entry.user_id}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '16px',
                                        padding: '16px 24px',
                                        borderBottom: index < entries.length - 1 ? '1px solid var(--border)' : 'none',
                                        transition: 'background 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--secondary)'}
                                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                    {/* Rank */}
                                    <div style={{
                                        width: '48px',
                                        height: '48px',
                                        borderRadius: '50%',
                                        background: entry.rank <= 3 ? `${badge.color}20` : 'var(--secondary)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: entry.rank <= 3 ? '1.5rem' : '1rem',
                                        fontWeight: 700,
                                        color: badge.color
                                    }}>
                                        {badge.emoji}
                                    </div>

                                    {/* User Info */}
                                    <div style={{ flex: 1 }}>
                                        <p style={{ fontWeight: 600, margin: 0, fontSize: '1rem' }}>
                                            @{entry.username || 'anonymous'}
                                        </p>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
                                            {category === 'most_likes'
                                                ? `${entry.value} likes received`
                                                : `${entry.value} posts shared`
                                            }
                                        </p>
                                    </div>

                                    {/* Value */}
                                    <div style={{
                                        padding: '8px 16px',
                                        borderRadius: '20px',
                                        background: entry.rank <= 3 ? 'var(--primary)' : 'var(--secondary)',
                                        color: entry.rank <= 3 ? 'white' : 'var(--foreground)',
                                        fontWeight: 700,
                                        fontSize: '0.9rem'
                                    }}>
                                        {entry.value}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>

            {/* Badges Section */}
            <section style={{
                maxWidth: '600px',
                margin: '24px auto',
                padding: '0 24px'
            }}>
                <h2 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>🏅 Badges</h2>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '12px'
                }}>
                    {[
                        { type: 'first_post', name: 'First Post', emoji: '🎯', desc: 'Share 1 PDF' },
                        { type: 'prolific', name: 'Prolific', emoji: '🔥', desc: 'Share 10 PDFs' },
                        { type: 'century', name: 'Century', emoji: '💯', desc: 'Share 100 PDFs' },
                        { type: 'popular', name: 'Popular', emoji: '⭐', desc: '10 likes on post' },
                        { type: 'viral', name: 'Viral', emoji: '🏆', desc: '100 likes on post' },
                    ].map(badge => (
                        <div
                            key={badge.type}
                            style={{
                                padding: '16px',
                                borderRadius: '12px',
                                border: '1px solid var(--border)',
                                textAlign: 'center',
                                background: 'var(--card-bg)'
                            }}
                        >
                            <span style={{ fontSize: '2rem' }}>{badge.emoji}</span>
                            <p style={{ fontWeight: 600, margin: '8px 0 4px', fontSize: '0.9rem' }}>{badge.name}</p>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: 0 }}>{badge.desc}</p>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
