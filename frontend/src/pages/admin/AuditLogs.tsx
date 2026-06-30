
import React, { useState, useEffect } from 'react';
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
    const [hoveredRow, setHoveredRow] = useState<string | null>(null);

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

    const formatTime = (dateString: string) => {
        return new Date(dateString).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    };

    const formatDetails = (details: any) => {
        if (!details) return '-';
        return JSON.stringify(details, null, 2);
    };

    const getSeverityColor = (action: string) => {
        if (action.includes('DELETE') || action.includes('CANCEL') || action.includes('DENIED')) return 'var(--terra)';
        if (action.includes('UPDATE') || action.includes('CHANGE') || action.includes('WARN')) return 'var(--amber)';
        if (action.includes('APPROVED') || action.includes('CREATE') || action.includes('LOGIN')) return 'var(--sage)';
        return 'var(--ink-400)';
    };

    // Group logs by date
    const groupedLogs: Record<string, AuditLog[]> = {};
    logs.forEach(log => {
        const date = new Date(log.created_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        if (!groupedLogs[date]) groupedLogs[date] = [];
        groupedLogs[date].push(log);
    });

    const allowedRoles = ['ADMIN', 'SECRETARIAT_LEAD'];
    if (!allowedRoles.includes(user?.role || '')) {
        return (
            <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", padding: '32px 0' }}>
                <div style={{ background: 'var(--surface)', border: '1px solid var(--terra)', padding: 16 }}>
                    <p style={{ color: 'var(--terra)', margin: 0, fontSize: 13 }}>Access Denied: Admin privileges required.</p>
                </div>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1180, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            {/* Page header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 600, color: 'var(--ink-500)', marginBottom: 6 }}>
                    Management · trail
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <h1 style={{ fontFamily: "'Geist', system-ui, sans-serif", fontWeight: 800, fontSize: 18, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        Audit logs
                    </h1>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                            {logs.length} events
                        </span>
                        <button
                            onClick={fetchLogs}
                            style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', padding: '7px 14px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                        >
                            Refresh
                        </button>
                    </div>
                </div>
            </div>

            {/* Filter bar */}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 28, padding: '14px 16px', background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <span style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600, marginRight: 8 }}>Filter</span>
                {['All Actions', 'CREATE', 'UPDATE', 'DELETE', 'LOGIN'].map(f => (
                    <button key={f} style={{ fontSize: 11, padding: '4px 10px', background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-600)', cursor: 'pointer', fontFamily: 'inherit' }}>
                        {f}
                    </button>
                ))}
            </div>

            {error && (
                <div style={{ background: 'var(--surface)', borderLeft: '2px solid var(--terra)', padding: '12px 16px', marginBottom: 16 }}>
                    <p style={{ color: 'var(--terra)', margin: 0, fontSize: 13 }}>{error}</p>
                </div>
            )}

            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--accent)' }}></div>
                </div>
            ) : logs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '64px 0', color: 'var(--ink-400)' }}>
                    <p style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>No audit logs found</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
                    {Object.entries(groupedLogs).map(([date, dateLogs]) => (
                        <div key={date}>
                            {/* Date heading */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10 }}>
                                <h2 style={{ fontFamily: "'Geist', system-ui, sans-serif", fontWeight: 800, letterSpacing: '-0.02em', fontSize: 13, color: 'var(--ink-700)', margin: 0, whiteSpace: 'nowrap' }}>
                                    {date}
                                </h2>
                                <div style={{ flex: 1, height: 1, background: 'var(--border)' }}></div>
                                <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 10, color: 'var(--ink-400)' }}>{dateLogs.length} events</span>
                            </div>

                            {/* Group body */}
                            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
                                {/* Table header */}
                                <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr 160px 1fr 1fr 60px', gap: 0, background: 'var(--surface-2)', borderBottom: '1px solid var(--border)', padding: '10px 16px' }}>
                                    {['Time', 'Action', 'Resource', 'Details', 'IP Address', ''].map(col => (
                                        <div key={col} style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600 }}>{col}</div>
                                    ))}
                                </div>
                                {dateLogs.map((log, idx) => (
                                    <div
                                        key={log.id}
                                        onMouseEnter={() => setHoveredRow(log.id)}
                                        onMouseLeave={() => setHoveredRow(null)}
                                        style={{
                                            display: 'grid',
                                            gridTemplateColumns: '90px 1fr 160px 1fr 1fr 60px',
                                            gap: 0,
                                            padding: '11px 16px',
                                            borderBottom: idx < dateLogs.length - 1 ? '1px solid var(--border)' : 'none',
                                            background: hoveredRow === log.id ? 'var(--surface-2)' : 'transparent',
                                            alignItems: 'start',
                                        }}
                                    >
                                        {/* Time */}
                                        <div style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)', paddingTop: 1 }}>
                                            {formatTime(log.created_at)}
                                        </div>

                                        {/* Action */}
                                        <div>
                                            <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-700)', fontWeight: 500 }}>
                                                {log.action}
                                            </span>
                                        </div>

                                        {/* Resource */}
                                        <div>
                                            <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600 }}>{log.resource_type}</div>
                                            <div style={{ fontFamily: "'Geist Mono', monospace", fontSize: 10, color: 'var(--ink-500)', marginTop: 2 }}>{log.resource_id ? log.resource_id.substring(0, 8) + '...' : '-'}</div>
                                        </div>

                                        {/* Details */}
                                        <div style={{ overflow: 'hidden' }}>
                                            <pre style={{ fontFamily: "'Geist Mono', monospace", fontSize: 10, color: 'var(--ink-600)', background: 'var(--surface-2)', borderRadius: 6, padding: '4px 8px', margin: 0, overflowX: 'auto', maxWidth: 220, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                                                {formatDetails(log.details)}
                                            </pre>
                                        </div>

                                        {/* IP */}
                                        <div style={{ fontFamily: "'Geist Mono', monospace", fontSize: 11, color: 'var(--ink-500)' }}>
                                            {log.ip_address || '-'}
                                        </div>

                                        {/* Severity dot */}
                                        <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 4 }}>
                                            <div style={{ width: 7, height: 7, borderRadius: '50%', background: getSeverityColor(log.action) }}></div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default AuditLogs;
