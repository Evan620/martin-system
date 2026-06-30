import React, { useState, useEffect } from 'react';
import { pipelineService } from '../services/pipelineService';
import { Buyer } from '../types/pipeline';

const BuyerDatabase: React.FC = () => {
    const [buyers, setBuyers] = useState<Buyer[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [form, setForm] = useState({
        name: '',
        commodity_types: '',
        volume_mt_per_year: '',
        contract_term_years: '',
        price_floor_usd: '',
        geographic_focus: '',
        notes: '',
    });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        loadBuyers();
    }, []);

    const loadBuyers = async () => {
        setLoading(true);
        try {
            const data = await pipelineService.listBuyers();
            setBuyers(data);
        } catch (e) {
            console.error('Failed to load buyers', e);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        if (!form.name.trim()) return;
        setSaving(true);
        try {
            await pipelineService.createBuyer({
                name: form.name.trim(),
                commodity_types: form.commodity_types
                    ? form.commodity_types.split(',').map(s => s.trim()).filter(Boolean)
                    : undefined,
                volume_mt_per_year: form.volume_mt_per_year ? parseFloat(form.volume_mt_per_year) : undefined,
                contract_term_years: form.contract_term_years ? parseInt(form.contract_term_years) : undefined,
                price_floor_usd: form.price_floor_usd ? parseFloat(form.price_floor_usd) : undefined,
                geographic_focus: form.geographic_focus
                    ? form.geographic_focus.split(',').map(s => s.trim()).filter(Boolean)
                    : undefined,
                notes: form.notes || undefined,
            });
            setShowAddModal(false);
            setForm({ name: '', commodity_types: '', volume_mt_per_year: '', contract_term_years: '', price_floor_usd: '', geographic_focus: '', notes: '' });
            await loadBuyers();
        } catch (e) {
            console.error('Failed to create buyer', e);
            alert('Failed to create buyer. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const fieldStyle: React.CSSProperties = {
        width: '100%',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        color: 'var(--ink-800)',
        padding: '8px 10px',
        fontSize: 13,
        fontFamily: 'inherit',
        outline: 'none',
        boxSizing: 'border-box',
    };

    return (
        <div style={{ maxWidth: 1080, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            {/* Header */}
            <div style={{
                display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
                paddingBottom: 22, borderBottom: '1px solid var(--border)', marginBottom: 28,
            }}>
                <div>
                    <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8, fontWeight: 600, fontFamily: "'Geist Mono', monospace" }}>
                        Deal Pipeline / Offtake
                    </div>
                    <h1 style={{
                        fontFamily: "'Geist', system-ui, sans-serif", fontWeight: 800,
                        fontSize: 28, letterSpacing: '-0.02em', color: 'var(--ink-900)',
                        margin: 0, lineHeight: 1.1,
                    }}>
                        Buyer Database
                    </h1>
                    <p style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 8 }}>
                        Registered offtakers for Agribusiness project–buyer matching
                    </p>
                </div>
                <button onClick={() => setShowAddModal(true)} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)',
                    padding: '10px 18px', fontSize: 12, fontWeight: 500,
                    cursor: 'pointer', fontFamily: 'inherit',
                }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
                    Add buyer
                </button>
            </div>

            {/* Content */}
            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
                    <div className="size-8 border-2 border-t-transparent rounded-full animate-spin"
                        style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
                </div>
            ) : buyers.length === 0 ? (
                <div style={{
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    padding: '60px 24px', textAlign: 'center',
                }}>
                    <p style={{ fontSize: 14, color: 'var(--ink-400)', marginBottom: 16 }}>
                        No buyers registered yet.
                    </p>
                    <button onClick={() => setShowAddModal(true)} style={{
                        background: 'none', border: '1px solid var(--border)',
                        color: 'var(--ink-600)', padding: '8px 16px', fontSize: 12,
                        cursor: 'pointer', fontFamily: 'inherit',
                    }}>
                        Register the first buyer
                    </button>
                </div>
            ) : (
                <div className="resp-table-mobile" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
                    <div className="resp-thead" style={{
                        display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1.4fr) 140px 120px',
                        columnGap: 20,
                        padding: '12px 20px', borderBottom: '1px solid var(--border)',
                        background: 'var(--surface-2)',
                    }}>
                        {['Buyer', 'Commodities / Geography', 'Volume (MT/yr)', 'Price floor'].map(h => (
                            <div key={h} style={{
                                fontSize: 10, letterSpacing: '0.14em',
                                textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600,
                            }}>{h}</div>
                        ))}
                    </div>
                    {buyers.map((buyer, i) => (
                        <div key={buyer.id} className="resp-row qp-transition" style={{
                            display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1.4fr) 140px 120px',
                            columnGap: 20,
                            padding: '14px 20px', alignItems: 'start',
                            borderBottom: i < buyers.length - 1 ? '1px solid var(--border)' : 'none',
                        }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                            <div data-label="primary">
                                <div style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500 }}>{buyer.name}</div>
                                {buyer.contract_term_years && (
                                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3, fontFamily: "'Geist Mono', monospace" }}>
                                        {buyer.contract_term_years}yr contract term
                                    </div>
                                )}
                                {buyer.notes && (
                                    <div style={{ fontSize: 11, color: 'var(--ink-400)', marginTop: 3, lineHeight: 1.4 }}>
                                        {buyer.notes}
                                    </div>
                                )}
                            </div>
                            <div data-label="Commodities">
                                {buyer.commodity_types?.length ? (
                                    <div style={{ fontSize: 12, color: 'var(--ink-700)' }}>
                                        {buyer.commodity_types.join(', ')}
                                    </div>
                                ) : (
                                    <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>—</span>
                                )}
                                {buyer.geographic_focus?.length ? (
                                    <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>
                                        {buyer.geographic_focus.join(', ')}
                                    </div>
                                ) : null}
                            </div>
                            <div data-label="Volume (MT/yr)" style={{ fontSize: 12, color: 'var(--ink-700)', fontFamily: "'Geist Mono', monospace" }}>
                                {buyer.volume_mt_per_year != null
                                    ? buyer.volume_mt_per_year.toLocaleString()
                                    : '—'}
                            </div>
                            <div data-label="Price floor" style={{ fontSize: 12, color: 'var(--ink-700)', fontFamily: "'Geist Mono', monospace" }}>
                                {buyer.price_floor_usd != null
                                    ? `$${buyer.price_floor_usd.toLocaleString()}`
                                    : '—'}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Add Buyer Modal */}
            {showAddModal && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
                }}>
                    <div style={{
                        background: 'var(--surface)', border: '1px solid var(--border)',
                        width: '100%', maxWidth: 520, margin: 16,
                    }}>
                        <div style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '20px 24px', borderBottom: '1px solid var(--border)',
                        }}>
                            <h3 style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0 }}>
                                Add buyer / offtaker
                            </h3>
                            <button onClick={() => setShowAddModal(false)} style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                color: 'var(--ink-400)', padding: 4,
                            }}>
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>
                        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                            {([
                                { field: 'name' as const, label: 'Buyer name *', placeholder: 'e.g. AfriGrain Trading Ltd.' },
                                { field: 'commodity_types' as const, label: 'Commodity types', placeholder: 'Comma-separated, e.g. MAIZE, SORGHUM' },
                                { field: 'geographic_focus' as const, label: 'Geographic focus', placeholder: 'Comma-separated, e.g. GHANA, ECOWAS' },
                                { field: 'volume_mt_per_year' as const, label: 'Volume (MT/year)', placeholder: 'e.g. 50000' },
                                { field: 'price_floor_usd' as const, label: 'Price floor (USD/MT)', placeholder: 'e.g. 250' },
                                { field: 'notes' as const, label: 'Notes', placeholder: 'Additional context…' },
                            ]).map(({ field, label, placeholder }) => (
                                <div key={field}>
                                    <label style={{
                                        fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase',
                                        color: 'var(--ink-500)', fontWeight: 500,
                                        display: 'block', marginBottom: 6,
                                    }}>
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
                        <div style={{
                            padding: '16px 24px', borderTop: '1px solid var(--border)',
                            display: 'flex', gap: 8,
                        }}>
                            <button onClick={() => setShowAddModal(false)} style={{
                                flex: 1, padding: '8px 16px', fontSize: 12, cursor: 'pointer',
                                background: 'transparent', border: '1px solid var(--border)',
                                color: 'var(--ink-700)', fontFamily: 'inherit',
                            }}>Cancel</button>
                            <button
                                onClick={handleCreate}
                                disabled={!form.name.trim() || saving}
                                style={{
                                    flex: 1, padding: '8px 16px', fontSize: 12, fontWeight: 600,
                                    cursor: !form.name.trim() || saving ? 'default' : 'pointer',
                                    background: 'var(--accent)', border: 'none',
                                    color: 'var(--accent-ink)', fontFamily: 'inherit',
                                    opacity: !form.name.trim() || saving ? 0.6 : 1,
                                }}
                            >
                                {saving ? 'Saving…' : 'Add buyer'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default BuyerDatabase;
