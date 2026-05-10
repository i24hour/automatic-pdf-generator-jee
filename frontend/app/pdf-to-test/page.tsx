'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Upload, FileText, Clock, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { API_BASE_URL as API_BASE } from '@/lib/config';

export default function PDFToTestUploadPage() {
    const router = useRouter();
    const { authFetch } = useAuth();

    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState('JEE Mains PDF Test');
    const [duration, setDuration] = useState(180);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const [jobId, setJobId] = useState<string | null>(null);

    const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0];
        if (selected && selected.type === 'application/pdf') {
            setFile(selected);
            setError(null);
        } else {
            setError('Please select a valid PDF file');
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const dropped = e.dataTransfer.files[0];
        if (dropped && dropped.type === 'application/pdf') {
            setFile(dropped);
            setError(null);
        } else {
            setError('Please drop a valid PDF file');
        }
    }, []);

    const handleUpload = async () => {
        if (!file) {
            setError('Please select a PDF file');
            return;
        }

        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', title);
        formData.append('duration_minutes', String(duration));

        try {
            const res = await authFetch(`${API_BASE}/api/pdf-to-test/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Upload failed');
            }

            const data = await res.json();
            setJobId(data.job_id);
            setSuccess(true);

            // Auto-redirect to review after a brief pause
            setTimeout(() => {
                router.push(`/pdf-to-test/review?job_id=${data.job_id}`);
            }, 1500);
        } catch (err: any) {
            setError(err.message || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-8 px-4">
            <div className="max-w-2xl mx-auto">
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <FileText className="w-6 h-6 text-blue-600" />
                        PDF to Test
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-1">
                        Upload a JEE Mains PDF and we’ll extract questions + images to create an interactive test.
                    </p>
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 space-y-6">
                    {/* Title + Duration */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Test Title
                            </label>
                            <input
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Duration (minutes)
                            </label>
                            <div className="flex items-center gap-2">
                                <Clock className="w-4 h-4 text-gray-500" />
                                <input
                                    type="number"
                                    value={duration}
                                    onChange={(e) => setDuration(Number(e.target.value))}
                                    min={10}
                                    max={300}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Dropzone */}
                    <div
                        onDrop={handleDrop}
                        onDragOver={(e) => e.preventDefault()}
                        className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-8 text-center hover:border-blue-500 dark:hover:border-blue-400 transition-colors bg-gray-50 dark:bg-gray-850"
                    >
                        <input
                            type="file"
                            accept="application/pdf"
                            onChange={handleFileChange}
                            className="hidden"
                            id="pdf-upload"
                        />
                        <label htmlFor="pdf-upload" className="cursor-pointer flex flex-col items-center gap-3">
                            <Upload className="w-10 h-10 text-gray-400" />
                            <div>
                                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {file ? file.name : 'Click or drag PDF here'}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">
                                    Only PDF files up to 50MB
                                </p>
                            </div>
                        </label>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="flex items-center gap-2 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-4 py-3 rounded-lg text-sm">
                            <AlertCircle className="w-4 h-4" />
                            {error}
                        </div>
                    )}

                    {/* Success */}
                    {success && jobId && (
                        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-4 py-3 rounded-lg text-sm">
                            <CheckCircle className="w-4 h-4" />
                            Upload successful! Redirecting to review...
                        </div>
                    )}

                    {/* Submit */}
                    <button
                        onClick={handleUpload}
                        disabled={uploading || !file}
                        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                    >
                        {uploading ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Uploading & Parsing...
                            </>
                        ) : (
                            <>
                                <Upload className="w-4 h-4" />
                                Upload & Parse PDF
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
