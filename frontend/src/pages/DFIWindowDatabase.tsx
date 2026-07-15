import React, { useState, useEffect } from 'react';
import { pipelineService } from '../services/pipelineService';
import { DFIWindow, DFIInstrumentType } from '../types/pipeline';

const INSTRUMENTS: { value: DFIInstrumentType; label: string }[] = [
    { value: DFIInstrumentType.GRANT, label: 'Grant' },
    { value: DFIInstrumentType.CONCESSIONAL_LOAN, label: 'Concessional loan' },
    { value: DFIInstrumentType.EQUITY, label: 'Equity' },
    { value: DFIInstrumentType.BLENDED, label: 'Blended' },
];

function fmtSize(min?: number, max?: number): string {
    const f = (n: number) => n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(0)}M` : `$${n.toLocaleString()}`;
    if (min != null && max != null) return `${f(min)} – ${f(max)}`;
    if (min != null) return `${f(min)}+`;
    if (max != null) return `up to ${f(max)}`;
    return '—';
}

const DFIWindowDatabase: React.FC = () => {
    const [windows, setWindows] = useState<DFIWindow[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        name: '', institution: '', instrument_type: DFIInstrumentType.BLENDED as DFIInstrumentType,
        sectors: '', geographies: '', min_size_usd: '', max_size_usd: '', eligible_stages: '',
        gender_focus: false, climate_focus: false, description: '', url: '',
    });

    useEffect(() => { loadWindows(); }, []);

    const loadWindows = async () => {
        setLoading(true);
        try {
            setWindows(await pipelineService.listDFIWindows());
        } catch (e) {
            console.error('Failed to load DFI windows', e);
        } finally {
            setLoading(false);
        }
    };

    const splitList = (s: string) => s ? s.split(',').map(x => x.trim()).filter(Boolean) : undefined;

    const handleCreate = async () => {
        if (!form.name.trim() || !form.institution.trim()) return;
        setSaving(true);
        try {
            await pipelineService.createDFIWindow({
                name: form.name.trim(),
                institution: form.institution.trim(),
                instrument_type: form.instrument_type,
                sectors: splitList(form.sectors),
                geographies: splitList(form.geographies),
                min_size_usd: form.min_size_usd ? parseFloat(form.min_size_usd) : undefined,
                max_size_usd: form.max_size_usd ? parseFloat(form.max_size_usd) : undefined,
                eligible_stages: splitList(form.eligible_stages),
                gender_focus: form.gender_focus,
                climate_focus: form.climate_focus,
                description: form.description.trim() || undefined,
                url: form.url.trim() || undefined,
            });
            setShowAddModal(false);
            setForm({ name: '', institution: '', instrument_type: DFIInstrumentType.BLENDED, sectors: '', geographies: '', min_size_usd: '', max_size_usd: '', eligible_stages: '', gender_focus: false, climate_focus: false, description: '', url: '' });
            await loadWindows();
        } catch (e) {
            console.error('Failed to create DFI window', e);
            alert('Failed to create DFI window. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const fieldStyle: React.CSSProperties = {
        width: '100%', background: 'var(--surface)', border: '1px solid var(--border)',
        color: 'var(--ink-800)', padding: '8px 10px', fontSize: 13, fontFamily: 'inherit',
        outline: 'none', boxSizing: 'border-box',
    };
    const label = (t: string) => (
        <label style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 500, display: 'block', marginBottom: 6 }}>{t}</label>
    );
    const text = (field: keyof typeof form, ph: string) => (
        <input value={form[field] as string} onChange={e => setForm(p => ({ ...p, [field]: e.target.value }))} placeholder={ph} style={fieldStyle} />
    );

    return (
        <div style={{ maxWidth: 1080, margin: '0 auto', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', paddingBottom: 22, borderBottom: '1px solid var(--border)', marginBottom: 28 }}>
                <div>
                    <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 8, fontWeight: 600, fontFamily: "'Geist Mono', monospace" }}>
                        Deal Pipeline / Blended Finance
                    </div>
                    <h1 style={{ fontFamily: "'Geist', system-ui, sans-serif", fontWeight: 800, fontSize: 28, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0, lineHeight: 1.1 }}>
                        DFI Windows
                    </h1>
                    <p style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 8 }}>
                        Development-finance funding windows projects are matched against
                    </p>
                </div>
                <button onClick={() => setShowAddModal(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)', padding: '10px 18px', fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
                    Add window
                </button>
            </div>

            {loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
                    <div className="size-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }} />
                </div>
            ) : windows.length === 0 ? (
                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '60px 24px', textAlign: 'center' }}>
                    <p style={{ fontSize: 14, color: 'var(--ink-400)', marginBottom: 16 }}>No DFI windows registered yet.</p>
                    <button onClick={() => setShowAddModal(true)} style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--ink-600)', padding: '8px 16px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}>
                        Register the first window
                    </button>
                </div>
            ) : (
                <div className="resp-table-mobile" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', overflow: 'hidden' }}>
                    <div className="resp-thead" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) 150px minmax(0, 1.3fr) 150px', columnGap: 20, padding: '12px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
                        {['Window / Institution', 'Instrument', 'Sectors / Geography', 'Size range'].map(h => (
                            <div key={h} style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--ink-500)', fontWeight: 600 }}>{h}</div>
                        ))}
                    </div>
                    {windows.map((w, i) => (
                        <div key={w.id} className="resp-row qp-transition" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) 150px minmax(0, 1.3fr) 150px', columnGap: 20, padding: '14px 20px', alignItems: 'start', borderBottom: i < windows.length - 1 ? '1px solid var(--border)' : 'none' }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                            <div data-label="primary">
                                <div style={{ fontSize: 13, color: 'var(--ink-900)', fontWeight: 500 }}>{w.name}</div>
                                <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>{w.institution}</div>
                                {(w.gender_focus || w.climate_focus) && (
                                    <div style={{ display: 'flex', gap: 4, marginTop: 5, flexWrap: 'wrap' }}>
                                        {w.gender_focus && <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 4, background: 'var(--green-50, #f0fdf4)', color: 'var(--green-700, #15803d)', border: '1px solid var(--green-200, #bbf7d0)' }}>Gender focus</span>}
                                        {w.climate_focus && <span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 4, background: 'var(--blue-50, #eff6ff)', color: 'var(--blue-700, #1d4ed8)', border: '1px solid var(--blue-200, #bfdbfe)' }}>Climate focus</span>}
                                    </div>
                                )}
                            </div>
                            <div data-label="Instrument" style={{ fontSize: 12, color: 'var(--ink-700)' }}>
                                {INSTRUMENTS.find(x => x.value === w.instrument_type)?.label || String(w.instrument_type)}
                            </div>
                            <div data-label="Sectors">
                                {w.sectors?.length ? <div style={{ fontSize: 12, color: 'var(--ink-700)' }}>{w.sectors.join(', ')}</div> : <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>—</span>}
                                {w.geographies?.length ? <div style={{ fontSize: 11, color: 'var(--ink-500)', marginTop: 3 }}>{w.geographies.join(', ')}</div> : null}
                            </div>
                            <div data-label="Size" style={{ fontSize: 12, color: 'var(--ink-700)', fontFamily: "'Geist Mono', monospace" }}>
                                {fmtSize(w.min_size_usd != null ? Number(w.min_size_usd) : undefined, w.max_size_usd != null ? Number(w.max_size_usd) : undefined)}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showAddModal && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
                    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', width: '100%', maxWidth: 540, margin: 16, maxHeight: '90vh', overflowY: 'auto' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
                            <h3 style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--ink-900)', margin: 0 }}>Add DFI window</h3>
                            <button onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)', padding: 4 }}>
                                <span className="material-symbols-outlined">close</span>
                            </button>
                        </div>
                        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                            <div>{label('Window name *')}{text('name', 'e.g. Scaling Up Renewable Energy Programme (SREP)')}</div>
                            <div>{label('Institution *')}{text('institution', 'e.g. Green Climate Fund (GCF)')}</div>
                            <div>
                                {label('Instrument type')}
                                <select value={form.instrument_type} onChange={e => setForm(p => ({ ...p, instrument_type: e.target.value as DFIInstrumentType }))} style={fieldStyle}>
                                    {INSTRUMENTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                </select>
                            </div>
                            <div>{label('Sectors')}{text('sectors', 'Comma-separated, e.g. Energy, Agriculture')}</div>
                            <div>{label('Geographies')}{text('geographies', 'Comma-separated, e.g. ECOWAS, West Africa')}</div>
                            <div style={{ display: 'flex', gap: 12 }}>
                                <div style={{ flex: 1 }}>{label('Min size (USD)')}{text('min_size_usd', 'e.g. 1000000')}</div>
                                <div style={{ flex: 1 }}>{label('Max size (USD)')}{text('max_size_usd', 'e.g. 50000000')}</div>
                            </div>
                            <div>{label('Eligible stages')}{text('eligible_stages', 'Comma-separated, e.g. Concept, Feasibility, Development')}</div>
                            <div style={{ display: 'flex', gap: 20 }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--ink-700)', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={form.gender_focus} onChange={e => setForm(p => ({ ...p, gender_focus: e.target.checked }))} /> Gender focus
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--ink-700)', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={form.climate_focus} onChange={e => setForm(p => ({ ...p, climate_focus: e.target.checked }))} /> Climate focus
                                </label>
                            </div>
                            <div>{label('Description')}{text('description', 'Short description of the facility')}</div>
                            <div>{label('URL')}{text('url', 'https://…')}</div>
                        </div>
                        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                            <button onClick={() => setShowAddModal(false)} style={{ flex: 1, padding: '8px 16px', fontSize: 12, cursor: 'pointer', background: 'transparent', border: '1px solid var(--border)', color: 'var(--ink-700)', fontFamily: 'inherit' }}>Cancel</button>
                            <button onClick={handleCreate} disabled={!form.name.trim() || !form.institution.trim() || saving} style={{ flex: 1, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: (!form.name.trim() || !form.institution.trim() || saving) ? 'default' : 'pointer', background: 'var(--accent)', border: 'none', color: 'var(--accent-ink)', fontFamily: 'inherit', opacity: (!form.name.trim() || !form.institution.trim() || saving) ? 0.6 : 1 }}>
                                {saving ? 'Saving…' : 'Add window'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DFIWindowDatabase;
