'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Filter, CheckCircle2, MessageSquare, ExternalLink, Loader2 } from 'lucide-react';

interface Ticket {
    id: string;
    category: string;
    description: string;
    status: string;
    attachment_url?: string;
    audio_url?: string;
    created_at: string;
    admin_response?: string;
    user_id: string;
}

export default function AdminTicketsPage() {
    const router = useRouter();
    const [tickets, setTickets] = useState<Ticket[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('ALL');

    // Action State
    const [selectedTicket, setSelectedTicket] = useState<string | null>(null);
    const [response, setResponse] = useState('');
    const [statusUpdate, setStatusUpdate] = useState('');
    const [updating, setUpdating] = useState(false);

    useEffect(() => {
        fetchTickets();
    }, []);

    const fetchTickets = async () => {
        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/support/admin/all`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setTickets(data);
            } else {
                if (res.status === 403) {
                    alert('Access Denied. Admins only.');
                    router.push('/');
                }
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (ticketId: string) => {
        setUpdating(true);
        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/support/${ticketId}/status`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    status: statusUpdate,
                    admin_response: response
                })
            });

            if (res.ok) {
                // Update local state
                setTickets(prev => prev.map(t => t.id === ticketId ? {
                    ...t,
                    status: statusUpdate,
                    admin_response: response || t.admin_response
                } : t));
                setSelectedTicket(null);
                setResponse('');
            }
        } catch (err) {
            console.error(err);
            alert('Failed to update ticket');
        } finally {
            setUpdating(false);
        }
    };

    const filteredTickets = filter === 'ALL'
        ? tickets
        : tickets.filter(t => t.status === filter);

    const getStatusBadge = (status: string) => {
        const colors: Record<string, string> = {
            'OPEN': 'bg-yellow-100 text-yellow-800',
            'IN_PROGRESS': 'bg-blue-100 text-blue-800',
            'RESOLVED': 'bg-green-100 text-green-800',
            'CLOSED': 'bg-gray-100 text-gray-800'
        };
        return (
            <span className={`px-2 py-1 rounded-full text-xs font-bold ${colors[status] || 'bg-gray-100'}`}>
                {status}
            </span>
        );
    };

    if (loading) return <div className="flex h-screen items-center justify-center">Loading Admin Panel...</div>;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#0a0b0d] p-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Ticket Management</h1>

                    <div className="flex items-center gap-2 bg-white dark:bg-[#16181c] p-1 rounded-lg border border-gray-200 dark:border-gray-800">
                        {['ALL', 'OPEN', 'RESOLVED'].map(f => (
                            <button
                                key={f}
                                onClick={() => setFilter(f)}
                                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${filter === f
                                        ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300'
                                        : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                {f}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="bg-white dark:bg-[#16181c] rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800">
                                <tr>
                                    <th className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">Status</th>
                                    <th className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">Category</th>
                                    <th className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">Created</th>
                                    <th className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">Description</th>
                                    <th className="px-6 py-4 font-semibold text-gray-700 dark:text-gray-300 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                {filteredTickets.map(ticket => (
                                    <tr key={ticket.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                                        <td className="px-6 py-4">{getStatusBadge(ticket.status)}</td>
                                        <td className="px-6 py-4 font-medium">{ticket.category}</td>
                                        <td className="px-6 py-4 text-gray-500">{new Date(ticket.created_at).toLocaleDateString()}</td>
                                        <td className="px-6 py-4 max-w-md">
                                            <p className="truncate text-gray-600 dark:text-gray-300">{ticket.description}</p>
                                            <div className="flex gap-2 mt-1">
                                                {ticket.attachment_url && <span className="text-xs text-indigo-500">📷 Image</span>}
                                                {ticket.audio_url && <span className="text-xs text-indigo-500">🎤 Audio</span>}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={() => {
                                                    setSelectedTicket(ticket.id);
                                                    setStatusUpdate(ticket.status);
                                                    setResponse(ticket.admin_response || '');
                                                }}
                                                className="px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 text-xs font-medium"
                                            >
                                                Manage
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Manage Modal */}
            {selectedTicket && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-[#16181c] rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-xl border border-gray-200 dark:border-gray-800">
                        <div className="flex justify-between items-start mb-6">
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Manage Ticket</h2>
                            <button onClick={() => setSelectedTicket(null)} className="text-gray-400 hover:text-gray-600">✕</button>
                        </div>

                        {tickets.find(t => t.id === selectedTicket) && (
                            <div className="space-y-6">
                                <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
                                    <p className="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
                                        {tickets.find(t => t.id === selectedTicket)?.description}
                                    </p>

                                    <div className="flex gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                                        {tickets.find(t => t.id === selectedTicket)?.attachment_url && (
                                            <a href={tickets.find(t => t.id === selectedTicket)?.attachment_url} target="_blank" className="flex items-center gap-2 text-indigo-600 text-sm hover:underline">
                                                <ExternalLink className="w-4 h-4" /> View Image
                                            </a>
                                        )}
                                        {tickets.find(t => t.id === selectedTicket)?.audio_url && (
                                            <a href={tickets.find(t => t.id === selectedTicket)?.audio_url} target="_blank" className="flex items-center gap-2 text-indigo-600 text-sm hover:underline">
                                                <ExternalLink className="w-4 h-4" /> Play Audio
                                            </a>
                                        )}
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-1">Update Status</label>
                                        <select
                                            value={statusUpdate}
                                            onChange={(e) => setStatusUpdate(e.target.value)}
                                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent"
                                        >
                                            <option value="OPEN">OPEN</option>
                                            <option value="IN_PROGRESS">IN_PROGRESS</option>
                                            <option value="RESOLVED">RESOLVED</option>
                                            <option value="CLOSED">CLOSED</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium mb-1">Admin Response</label>
                                        <textarea
                                            rows={4}
                                            value={response}
                                            onChange={(e) => setResponse(e.target.value)}
                                            placeholder="Write a response to the user..."
                                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent resize-none"
                                        />
                                    </div>
                                </div>

                                <button
                                    onClick={() => handleUpdate(selectedTicket)}
                                    disabled={updating}
                                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl flex items-center justify-center gap-2"
                                >
                                    {updating ? 'Updating...' : 'Save Changes'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
