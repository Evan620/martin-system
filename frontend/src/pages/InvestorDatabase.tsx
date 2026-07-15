import React, { useState, useEffect } from 'react';
import { pipelineService } from '../services/pipelineService';
import { Investor } from '../types/pipeline';

function fmtTicket(min?: number, max?: number): string {
    const f = (n: number) => n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(0)}M` : `$${n.toLocaleString()}`;
    if (min != null && max != null) return `${f(min)} – ${f(max)}`;
    if (min != null) return `${f(min)}+`;
    if (max != null) return `up to ${f(max)}`;
    return '—';
}

const InvestorDatabase: React.FC = () => {
    const [investors, setInvestors] = useState<Investor[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [form, setForm] = useState({
        name: '',
        investor_type: '',
        sector_preferences: '',
        geographic_focus: '',
        ticket_size_min: '',
        ticket_size_max: '',
        investment_instruments: '',
        contact_name: '',
        contact_email: '',
    });
    const [saving, setSaving] = useState(false);

    useEffect(() => { loadInvestors(); }, []);

    const loadInvestors = async () => {
        setLoading(true);
        try {
            const data = await pipelineService.listInvestors();
            setInvestors(data);
        } catch (e) {
            console.error('Failed to load investors', e);
        } finally {
            setLoading(false);
        }
    };

    const splitList = (s: string) => s ? s.split(',').map(x => x.trim()).filter(Boolean) : undefined;

    const handleCreate = async () => {
        if (!form.name.trim()) return;
        setSaving(true);
        try {
            await pipelineService.createInvestor({
                name: form.name.trim(),
                investor_type: form.investor_type.trim() || undefined,
                sector_preferences: splitList(form.sector_preferences),
                geographic_focus: splitList(form.geographic_focus),
                ticket_size_min: form.ticket_size_min ? parseFloat(form.ticket_size_min) : undefined,
                ticket_size_max: form.ticket_size_max ? parseFloat(form.ticket_size_max) : undefined,
                investment_instruments: splitList(form.investment_instruments),
                contact_name: form.contact_name.trim() || undefined,
                contact_email: form.contact_email.trim() || undefined,
            });
            setShowAddModal(false);
            setForm({ name: '', investor_type: '', sector_preferences: '', geographic_focus: '', ticket_size_min: '', ticket_size_max: '', investment_instruments: '', contact_name: '', contact_email: '' });
            await loadInvestors();
        } catch (e) {
            console.error('Failed to create investor', e);
            alert('Failed to create investor. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const fieldStyle: React.CSSProperties = {
        width: '100%', background: 'var(--surface)', border: '1px solid var(--border)',
        color: 'var(--ink-800)', padding: '8px 10px', fontSize: 13, fontFamily: 'inherit',
        outline: 'none', boxSizing: 'border-box',
    };

    return (
        <div style={{ maxWidth: 1080, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', paddingBottom: 22, borderBottom: '1px solid var(--border)', marginBottom: 28 }}>
                <div>
                    <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8, fontWeight: 600, fontFamily: "'Geist Mono', monospace" }}>
                        Deal Pipeline / Capital
                    </div>
                    <h1 style={{ fontFamily: "'Geist', system-ui, sans-serif", fontWeight: 800, fontSize: 28, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        Investor Database
                    </h1>
                    <p style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 8 }}>
                        Registered investors for project–investor matchmaking
                    </p>
                </div>
                <button onClick={() => setShowAddModal(true)} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                    padding: '10px 18px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
                    Add investor
                </button>
            </div>

            {/* Content */}
            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
                    <div className="size-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
                </div>
            ) : investors.length === 0 ? (
                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '60px 24px', textAlign: 'center' }}>
                    <p style={{ fontSize: 14, color: 'var(--ink-400)', marginBottom: 16 }}>No investors registered yet.</p>
                    <button onClick={() => setShowAddModal(true)} style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '8px 16px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                        Register the first investor
                    </button>
                </div>
            ) : (
                <div className="resp-table-mobile" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
                    <div className="resp-thead" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1.4fr) 160px 120px', columnGap: 20, padding: '12px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                        {['Investor', 'Sectors / Geography', 'Ticket size', 'Instruments'].map(h => (
                            <div key={h} style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600 }}>{h}</div>
                        ))}
                    </div>
                    {investors.map((inv, i) => (
                        <div key={inv.id} className="resp-row qp-transition" style={{
                            display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1.4fr) 160px 120px', columnGap: 20,
                            padding: '14px 20px', alignItems: 'start', borderBottom: i < investors.length - 1 ? '1px solid var(--border)' : 'none',
                        }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                            <div data-label="primary">
                                <div style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500 }}>{inv.name}</div>
                                {inv.investor_type && (
                                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>{inv.investor_type}</div>
                                )}
                                {(inv.contact_name || inv.contact_email) && (
                                    <div style={{ fontSize: 11, color: 'var(--ink-400)', marginTop: 3 }}>
                                        {[inv.contact_name, inv.contact_email].filter(Boolean).join(' · ')}
                                    </div>
                                )}
                            </div>
                            <div data-label="Sectors">
                                {inv.sector_preferences?.length ? (
                                    <div style={{ fontSize: 12, color: 'var(--ink-700)' }}>{inv.sector_preferences.join(', ')}</div>
                                ) : <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>—</span>}
                                {inv.geographic_focus?.length ? (
                                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>{inv.geographic_focus.join(', ')}</div>
                                ) : null}
                            </div>
                            <div data-label="Ticket size" style={{ fontSize: 12, color: 'var(--ink-700)', fontFamily: "'Geist Mono', monospace" }}>
                                {fmtTicket(inv.ticket_size_min != null ? Number(inv.ticket_size_min) : undefined, inv.ticket_size_max != null ? Number(inv.ticket_size_max) : undefined)}
                            </div>
                            <div data-label="Instruments" style={{ fontSize: 11, color: 'var(--ink-700)' }}>
                                {inv.investment_instruments?.length ? inv.investment_instruments.join(', ') : '—'}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Add Investor Modal */}
            {showAddModal && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 520, margin: 16, maxHeight: '90vh', overflowY: 'auto' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0 }}>Add investor</h3>
                            <button onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>
                        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                            {([
                                { field: 'name' as const, label: 'Investor name *', placeholder: 'e.g. Africa Renewable Energy Fund' },
                                { field: 'investor_type' as const, label: 'Investor type', placeholder: 'e.g. DFI, Private Equity, VC, Commercial Bank' },
                                { field: 'sector_preferences' as const, label: 'Sector preferences', placeholder: 'Comma-separated, e.g. ENERGY, AGRICULTURE' },
                                { field: 'geographic_focus' as const, label: 'Geographic focus', placeholder: 'Comma-separated, e.g. NIGERIA, ECOWAS' },
                                { field: 'ticket_size_min' as const, label: 'Ticket size min (USD)', placeholder: 'e.g. 5000000' },
                                { field: 'ticket_size_max' as const, label: 'Ticket size max (USD)', placeholder: 'e.g. 50000000' },
                                { field: 'investment_instruments' as const, label: 'Investment instruments', placeholder: 'Comma-separated, e.g. EQUITY, DEBT, BLENDED' },
                                { field: 'contact_name' as const, label: 'Contact name', placeholder: 'e.g. Jane Doe' },
                                { field: 'contact_email' as const, label: 'Contact email', placeholder: 'e.g. jane@fund.com' },
                            ]).map(({ field, label, placeholder }) => (
                                <div key={field}>
                                    <label style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, display: 'block', marginBottom: 6 }}>
                                        {label}
                                    </label>
                                    <input
                                        value={form[field]}
                                        onChange={(e) => setForm(prev => ({ ...prev, [field]: e.target.value }))}
                                        placeholder={placeholder}
                                        style={fieldStyle}
                                    />
                                </div>
                            ))}
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                            <button onClick={() => setShowAddModal(false)} style={{ flex: 1, padding: '8px 16px', fontSize: 12, cursor: 'pointer', background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', fontFamily: 'inherit' }}>Cancel</button>
                            <button onClick={handleCreate} disabled={!form.name.trim() || saving} style={{ flex: 1, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: !form.name.trim() || saving ? 'default' : 'pointer', background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)', fontFamily: 'inherit', opacity: !form.name.trim() || saving ? 0.6 : 1 }}>
                                {saving ? 'Saving…' : 'Add investor'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default InvestorDatabase;
