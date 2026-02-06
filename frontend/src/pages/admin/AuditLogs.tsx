
import React, { useState, useEffect } from 'react';
import Card from '../../components/ui/Card';
import { auditLogs } from '../../services/api';
import { useAppSelector } from '../../hooks/useRedux';

interface AuditLog {
    id: string;
    action: string;
    user_id: string;
    resource_type: string;
    resource_id: string;
    details: any;
    ip_address: string;
    created_at: string;
}

const AuditLogs: React.FC = () => {
    const { user } = useAppSelector((state) => state.auth);
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchLogs();
    }, []);

    const fetchLogs = async () => {
        try {
            setLoading(true);
            const res = await auditLogs.list();
            setLogs(res.data);
        } catch (err: any) {
            console.error(err);
            setError("Failed to fetch audit logs");
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    const formatDetails = (details: any) => {
        if (!details) return '-';
        return JSON.stringify(details, null, 2);
    };

    const allowedRoles = ['ADMIN', 'SECRETARIAT_LEAD'];
    if (!allowedRoles.includes(user?.role || '')) {
        return (
            <div className="p-8">
                <Card className="bg-red-50 border-red-200">
                    <p className="text-red-600">Access Denied: Admin privileges required.</p>
                </Card>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white">System Audit Logs</h1>
                    <p className="text-slate-500 mt-1">Track all secure actions across the platform</p>
                </div>
                <button
                    onClick={fetchLogs}
                    className="p-2 text-slate-500 hover:text-blue-600 transition-colors"
                    title="Refresh Logs"
                >
                    🔄 Refresh
                </button>
            </header>

            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-100">
                    {error}
                </div>
            )}

            <Card className="overflow-hidden border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 font-medium border-b border-slate-200 dark:border-slate-700">
                            <tr>
                                <th className="p-4">Timestamp</th>
                                <th className="p-4">Action</th>
                                <th className="p-4">Resource</th>
                                <th className="p-4">Details</th>
                                <th className="p-4">IP Address</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {loading ? (
                                <tr>
                                    <td colSpan={5} className="p-8 text-center text-slate-500">Loading logs...</td>
                                </tr>
                            ) : logs.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="p-8 text-center text-slate-500">No logs found.</td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                        <td className="p-4 text-slate-500 whitespace-nowrap font-mono text-xs">
                                            {formatDate(log.created_at)}
                                        </td>
                                        <td className="p-4 font-medium text-slate-900 dark:text-white">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${log.action.includes('APPROVED') ? 'bg-green-100 text-green-700' :
                                                log.action.includes('CANCEL') ? 'bg-red-100 text-red-700' :
                                                    'bg-blue-100 text-blue-700'
                                                }`}>
                                                {log.action}
                                            </span>
                                        </td>
                                        <td className="p-4 text-slate-600 dark:text-slate-400">
                                            <div className="flex flex-col">
                                                <span className="uppercase text-xs font-bold text-slate-400">{log.resource_type}</span>
                                                <span className="font-mono text-xs">{log.resource_id ? log.resource_id.substring(0, 8) + '...' : '-'}</span>
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <pre className="text-xs font-mono text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 p-2 rounded max-w-xs overflow-x-auto">
                                                {formatDetails(log.details)}
                                            </pre>
                                        </td>
                                        <td className="p-4 text-slate-500 font-mono text-xs">
                                            {log.ip_address || '-'}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    );
};

export default AuditLogs;
