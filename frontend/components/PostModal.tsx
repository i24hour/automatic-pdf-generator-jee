'use client';

import { useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mentors-mantra-api-87253755436.us-central1.run.app';

interface PostModalProps {
    isOpen: boolean;
    onClose: () => void;
    sharedPdfId: string;
    pdfFilename: string;
    subject: string;
    topic: string;
    level: string;
    token: string;
    onSuccess?: () => void;
}

export default function PostModal({
    isOpen,
    onClose,
    sharedPdfId,
    pdfFilename,
    subject,
    topic,
    level,
    token,
    onSuccess
}: PostModalProps) {
    const [caption, setCaption] = useState('');
    const [visibility, setVisibility] = useState<'public' | 'unlisted' | 'private'>('public');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    if (!isOpen) return null;

    const handlePost = async () => {
        setLoading(true);
        setError('');

        try {
            const res = await fetch(`${API_URL}/api/posts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    pdf_id: sharedPdfId,
                    caption: caption.trim() || null,
                    visibility
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to post');
            }

            setSuccess(true);
            setTimeout(() => {
                onSuccess?.();
                onClose();
            }, 1500);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to post');
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
                    maxWidth: '480px',
                    padding: '24px',
                    animation: 'slideUp 0.3s ease'
                }}
            >
                {success ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <span style={{ fontSize: '3rem' }}>🎉</span>
                        <p style={{ fontSize: '1.2rem', fontWeight: 600, marginTop: '16px' }}>
                            Posted Successfully!
                        </p>
                        <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
                            Your PDF is now {visibility === 'public' ? 'visible to everyone' : visibility === 'unlisted' ? 'accessible via link' : 'in your private collection'}
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>
                                Share Your PDF 📤
                            </h2>
                            <button
                                onClick={onClose}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    fontSize: '1.5rem',
                                    cursor: 'pointer',
                                    color: 'var(--text-muted)'
                                }}
                            >
                                ×
                            </button>
                        </div>

                        {/* PDF Preview */}
                        <div style={{
                            background: 'var(--secondary)',
                            borderRadius: '12px',
                            padding: '16px',
                            marginBottom: '20px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px'
                        }}>
                            <div style={{
                                width: '40px',
                                height: '40px',
                                borderRadius: '8px',
                                background: 'linear-gradient(135deg, #ef4444, #f97316)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                fontSize: '1.1rem'
                            }}>
                                📄
                            </div>
                            <div>
                                <p style={{ fontWeight: 600, margin: 0, fontSize: '0.9rem' }}>{topic}</p>
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                                    {subject} • {level}
                                </p>
                            </div>
                        </div>

                        {/* Caption */}
                        <div style={{ marginBottom: '16px' }}>
                            <label className="form-label">Add a caption (optional)</label>
                            <textarea
                                value={caption}
                                onChange={(e) => setCaption(e.target.value)}
                                placeholder="Great practice for JEE Advanced! 🎯"
                                maxLength={280}
                                className="form-input"
                                style={{
                                    minHeight: '80px',
                                    resize: 'vertical',
                                    fontFamily: 'inherit'
                                }}
                            />
                            <p style={{
                                color: 'var(--text-muted)',
                                fontSize: '0.75rem',
                                textAlign: 'right',
                                margin: '4px 0 0'
                            }}>
                                {caption.length}/280
                            </p>
                        </div>

                        {/* Visibility */}
                        <div style={{ marginBottom: '20px' }}>
                            <label className="form-label">Visibility</label>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                {[
                                    { value: 'public', label: '🌍 Public', desc: 'Everyone can see' },
                                    { value: 'unlisted', label: '🔗 Unlisted', desc: 'Only with link' },
                                    { value: 'private', label: '🔒 Private', desc: 'Only you' },
                                ].map(opt => (
                                    <button
                                        key={opt.value}
                                        onClick={() => setVisibility(opt.value as typeof visibility)}
                                        style={{
                                            flex: 1,
                                            padding: '12px 8px',
                                            borderRadius: '10px',
                                            border: visibility === opt.value ? '2px solid var(--primary)' : '1px solid var(--border)',
                                            background: visibility === opt.value ? 'rgba(79, 70, 229, 0.1)' : 'white',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s'
                                        }}
                                    >
                                        <p style={{ margin: 0, fontWeight: 600, fontSize: '0.85rem' }}>{opt.label}</p>
                                        <p style={{ margin: '4px 0 0', fontSize: '0.7rem', color: 'var(--text-muted)' }}>{opt.desc}</p>
                                    </button>
                                ))}
                            </div>
                            {visibility === 'public' && (
                                <p style={{
                                    color: 'var(--text-muted)',
                                    fontSize: '0.75rem',
                                    marginTop: '8px',
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    padding: '8px 12px',
                                    borderRadius: '8px'
                                }}>
                                    ⚠️ Once public, this cannot be changed to private or unlisted
                                </p>
                            )}
                        </div>

                        {/* Error */}
                        {error && (
                            <div className="error-message" style={{ marginBottom: '16px' }}>
                                {error}
                            </div>
                        )}

                        {/* Actions */}
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button onClick={onClose} className="btn-secondary" style={{ flex: 1 }}>
                                Cancel
                            </button>
                            <button
                                onClick={handlePost}
                                disabled={loading}
                                className="btn-primary"
                                style={{ flex: 1 }}
                            >
                                {loading ? (
                                    <>
                                        <span className="spinner" />
                                        Posting...
                                    </>
                                ) : (
                                    `Post ${visibility === 'public' ? 'Publicly' : ''}`
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
