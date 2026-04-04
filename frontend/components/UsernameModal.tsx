'use client';

import { useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://q3vgjfnybq.ap-south-1.awsapprunner.com';

interface UsernameModalProps {
    isOpen: boolean;
    onClose: () => void;
    token: string;
    currentUsername?: string | null;
    onSuccess?: (username: string) => void;
}

export default function UsernameModal({
    isOpen,
    onClose,
    token,
    currentUsername,
    onSuccess
}: UsernameModalProps) {
    const [username, setUsername] = useState(currentUsername || '');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    if (!isOpen) return null;

    const validateUsername = (value: string): string | null => {
        if (value.length < 3) return 'Username must be at least 3 characters';
        if (value.length > 20) return 'Username must be at most 20 characters';
        if (!/^[a-zA-Z0-9_]+$/.test(value)) return 'Only letters, numbers, and underscores allowed';
        return null;
    };

    const handleSubmit = async () => {
        const validationError = validateUsername(username);
        if (validationError) {
            setError(validationError);
            return;
        }

        setLoading(true);
        setError('');

        try {
            const res = await fetch(`${API_URL}/api/posts/set-username`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ username: username.toLowerCase() })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to set username');
            }

            const data = await res.json();
            setSuccess(true);
            onSuccess?.(data.username);

            setTimeout(() => {
                onClose();
            }, 1500);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to set username');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
                padding: '20px'
            }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                className="glass-card"
                style={{
                    width: '100%',
                    maxWidth: '400px',
                    padding: '24px',
                    animation: 'slideUp 0.3s ease'
                }}
            >
                {success ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <span style={{ fontSize: '3rem' }}>✨</span>
                        <p style={{ fontSize: '1.2rem', fontWeight: 600, marginTop: '16px' }}>
                            Username Set!
                        </p>
                        <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
                            You are now @{username.toLowerCase()}
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Header */}
                        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                            <span style={{ fontSize: '2.5rem' }}>👤</span>
                            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: '12px 0 8px' }}>
                                {currentUsername ? 'Update Username' : 'Set Your Username'}
                            </h2>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: 0 }}>
                                This will be shown publicly on your posts
                            </p>
                        </div>

                        {/* Input */}
                        <div style={{ marginBottom: '20px' }}>
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                background: 'white',
                                border: '1px solid var(--border)',
                                borderRadius: '10px',
                                padding: '0 16px',
                                transition: 'all 0.3s'
                            }}>
                                <span style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>@</span>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => {
                                        setUsername(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''));
                                        setError('');
                                    }}
                                    placeholder="username"
                                    maxLength={20}
                                    style={{
                                        flex: 1,
                                        padding: '14px 8px',
                                        border: 'none',
                                        outline: 'none',
                                        fontSize: '1rem',
                                        background: 'transparent'
                                    }}
                                />
                            </div>
                            <p style={{
                                color: 'var(--text-muted)',
                                fontSize: '0.75rem',
                                marginTop: '8px'
                            }}>
                                3-20 characters, letters, numbers, underscores only
                            </p>
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="error-message" style={{ marginBottom: '16px', padding: '12px 16px' }}>
                                {error}
                            </div>
                        )}

                        {/* Actions */}
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button onClick={onClose} className="btn-secondary" style={{ flex: 1 }}>
                                {currentUsername ? 'Cancel' : 'Skip for Now'}
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={loading || !username}
                                className="btn-primary"
                                style={{ flex: 1 }}
                            >
                                {loading ? (
                                    <>
                                        <span className="spinner" />
                                        Saving...
                                    </>
                                ) : (
                                    'Save Username'
                                )}
                            </button>
                        </div>
                    </>
                )}
            </div>

            <style jsx>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
        </div>
    );
}
