import { useParams, useNavigate } from 'react-router-dom';

export default function ProjectDetails() {
    const { id } = useParams();
    const navigate = useNavigate();

    const handleGenerateMemo = () => {
        navigate(`/deal-pipeline/${id}/memo`);
    };

    // Mock data - replace with actual API call
    const project = {
        id: id || '8492',
        name: 'West African Rail Expansion',
        status: 'Feasibility Phase',
        fundingAsk: '$450M',
        fundingGrowth: '+5% vs last month',
        readinessScore: 85,
        currentPhase: 'Feasibility',
        nextPhase: 'Technical Design',
        twg: 'Infrastructure & Transport',
        lastUpdated: '2 hours ago',
        pillar: 'Infrastructure',
        leadCountry: 'Nigeria',
        leadCompany: 'RailCo Ltd.',
        investment: '$1.2B'
    };

    return (
        <div style={{ padding: '32px 40px', background: 'var(--bg)', minHeight: '100vh', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
            <div style={{ maxWidth: 1200, margin: '0 auto' }}>
                {/* Breadcrumbs */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--ink-500)', marginBottom: 24 }}>
                    <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)', fontSize: 12, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Home</button>
                    <span style={{ color: 'var(--ink-300)' }}>›</span>
                    <button onClick={() => navigate('/deal-pipeline')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-500)', fontSize: 12, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Deal Pipeline</button>
                    <span style={{ color: 'var(--ink-300)' }}>›</span>
                    <span style={{ color: 'var(--ink-900)', fontWeight: 500 }}>{project.name}</span>
                </div>

                {/* Page Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 32 }}>
                    <div>
                        <span style={{ fontSize: 10, color: 'var(--ink-500)', letterSpacing: '0.08em', textTransform: 'uppercase', display: 'block', marginBottom: 8, fontFamily: "'Geist Mono', monospace" }}>PROJECT / WORKSPACE</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                            <h1 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontSize: 32, fontWeight: 600, color: 'var(--ink-900)', margin: 0, lineHeight: 1.2 }}>{project.name}</h1>
                            <span style={{ fontSize: 11, color: 'var(--ink-600)', border: '1px solid var(--border)', padding: '2px 8px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{project.status}</span>
                        </div>
                        <p style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 6, fontFamily: "'Geist Mono', monospace" }}>
                            ID #{project.id} · Last updated {project.lastUpdated}
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button style={{ padding: '8px 16px', fontSize: 13, fontWeight: 500, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--ink-600)', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                            Edit Project
                        </button>
                        <button onClick={handleGenerateMemo} style={{ padding: '8px 16px', fontSize: 13, fontWeight: 500, border: 'none', background: 'var(--accent)', color: 'var(--accent-ink)', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>auto_awesome</span>
                            Generate Memo
                        </button>
                    </div>
                </div>

                {/* LedgerStat Strip */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', border: '1px solid var(--border)', background: 'var(--surface)', marginBottom: 32 }}>
                    <div style={{ padding: '20px 24px' }}>
                        <div style={{ fontSize: 28, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>{project.fundingAsk}</div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginTop: 6 }}>FUNDING ASK</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-400)', marginTop: 2 }}>USD</div>
                    </div>
                    <div style={{ padding: '20px 24px', borderLeft: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 28, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, color: 'var(--ink-900)', fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>{project.readinessScore}</div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginTop: 6 }}>READINESS SCORE</div>
                        <div style={{ marginTop: 6, height: 4, background: 'var(--ink-100)', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{ width: `${project.readinessScore}%`, height: '100%', background: 'var(--accent)', borderRadius: 2 }} />
                        </div>
                    </div>
                    <div style={{ padding: '20px 24px', borderLeft: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 28, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, color: 'var(--ink-900)', lineHeight: 1 }}>{project.currentPhase}</div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginTop: 6 }}>CURRENT PHASE</div>
                        <div style={{ fontSize: 11, color: 'var(--ink-400)', marginTop: 2 }}>Next: {project.nextPhase}</div>
                    </div>
                    <div style={{ padding: '20px 24px', borderLeft: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 18, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, color: 'var(--ink-900)', lineHeight: 1.2 }}>{project.twg}</div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginTop: 6 }}>ORIGINATING TWG</div>
                    </div>
                </div>

                {/* Tabs */}
                <div style={{ borderBottom: '1px solid var(--border)', display: 'flex', gap: 0, marginBottom: 32 }}>
                    {['Overview', 'Financials', 'Documents', 'History'].map((tab, i) => (
                        <button
                            key={tab}
                            style={{
                                paddingBottom: 12,
                                paddingTop: 12,
                                paddingLeft: 16,
                                paddingRight: 16,
                                fontSize: 13,
                                fontWeight: 500,
                                fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
                                background: 'none',
                                border: 'none',
                                borderBottom: i === 0 ? '2px solid var(--accent)' : '2px solid transparent',
                                color: i === 0 ? 'var(--accent)' : 'var(--ink-500)',
                                cursor: 'pointer',
                                marginBottom: -1,
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Main Content Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 24 }}>
                    {/* Left Column — spans 2 */}
                    <div style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: 24 }}>
                        {/* Executive Summary */}
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 32 }}>
                            <p style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginBottom: 16, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Executive Summary</p>
                            <div style={{ color: 'var(--ink-700)', fontSize: 15, lineHeight: 1.8, fontFamily: "'Source Serif 4', Georgia, serif" }}>
                                <p style={{ margin: '0 0 16px' }}>
                                    The West African Rail Expansion project aims to rehabilitate and extend the rail corridor connecting Lagos (Nigeria) to Cotonou (Benin), facilitating the movement of goods and passengers across the key economic hubs of the ECOWAS region. This project is a critical component of the broader West African Railway Master Plan.
                                </p>
                                <p style={{ margin: 0 }}>
                                    Currently in the Feasibility Study phase, the project has secured preliminary backing from the African Development Bank and local stakeholders. The technical survey indicates no major geographical impediments, though urban displacement in Lagos suburbs remains a key risk factor requiring mitigation.
                                </p>
                            </div>
                        </div>

                        {/* Strategic Rationale */}
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 32 }}>
                            <p style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginBottom: 20, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Strategic Rationale & Business Case</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                                {[
                                    { num: '01', title: 'Regional Connectivity', text: 'Directly supports ECOWAS Vision 2050 Goal 3: "Integrated Infrastructure". Expected to reduce transit times by 40%.' },
                                    { num: '02', title: 'Economic & Environmental Impact', text: 'Projected IRR of 14% over 25 years. Shifts 20% of road freight to rail, reducing regional carbon emissions by 150k tons annually.' },
                                    { num: '03', title: 'Trade Facilitation', text: 'Will streamline customs procedures at the border through integrated rail terminals, boosting intra-regional trade volume.' },
                                ].map(item => (
                                    <div key={item.num} style={{ display: 'flex', gap: 20, padding: '16px 0', borderBottom: '1px solid var(--border)' }}>
                                        <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: 12, color: 'var(--ink-400)', flexShrink: 0, paddingTop: 2 }}>{item.num}</span>
                                        <div>
                                            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', margin: '0 0 4px', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{item.title}</p>
                                            <p style={{ fontSize: 13, color: 'var(--ink-600)', margin: 0, lineHeight: 1.6, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{item.text}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Map Visual */}
                        <div style={{ background: 'var(--ink-50)', border: '1px solid var(--border)', height: 240, position: 'relative', overflow: 'hidden' }}>
                            <div style={{ position: 'absolute', bottom: 16, left: 16 }}>
                                <p style={{ fontWeight: 600, fontSize: 14, color: 'var(--ink-900)', margin: '0 0 2px', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Proposed Route</p>
                                <p style={{ fontSize: 12, color: 'var(--ink-600)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Lagos Terminus A › Cotonou Port</p>
                            </div>
                            <button style={{ position: 'absolute', top: 16, right: 16, background: 'var(--surface)', border: '1px solid var(--border)', padding: '4px 8px', cursor: 'pointer', color: 'var(--ink-600)' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>fullscreen</span>
                            </button>
                        </div>
                    </div>

                    {/* Right Column */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                        {/* Martin's Read */}
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderTop: '2px solid var(--accent)', padding: 20 }}>
                            <p style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginBottom: 12, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Martin's Read</p>
                            <p style={{ fontSize: 14, color: 'var(--ink-800)', lineHeight: 1.7, fontFamily: "'Source Serif 4', Georgia, serif", fontStyle: 'italic', margin: '0 0 12px' }}>
                                Readiness Score is high (85/100), but the "Environmental Impact Assessment" is older than 6 months.
                            </p>
                            <div style={{ borderLeft: '2px solid var(--accent)', paddingLeft: 12 }}>
                                <p style={{ fontSize: 12, color: 'var(--ink-600)', margin: 0, lineHeight: 1.6, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                    <strong style={{ color: 'var(--ink-900)' }}>Recommendation:</strong> Request an updated addendum from the TWG lead before the next investment committee review.
                                </p>
                            </div>
                            <button style={{ marginTop: 12, fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>
                                Ask AI Agent →
                            </button>
                        </div>

                        {/* Action Items */}
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 20 }}>
                            <p style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', marginBottom: 16, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Action Required</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                                    <div style={{ width: 6, height: 6, borderRadius: 6, background: 'var(--amber)', flexShrink: 0, marginTop: 5 }} />
                                    <div>
                                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', margin: '0 0 2px', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Missing Document</p>
                                        <p style={{ fontSize: 12, color: 'var(--ink-500)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Updated EIA Report pending upload.</p>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '12px 0' }}>
                                    <div style={{ width: 6, height: 6, borderRadius: 6, background: 'var(--ink-300)', flexShrink: 0, marginTop: 5 }} />
                                    <div>
                                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-900)', margin: '0 0 2px', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Sign-off Needed</p>
                                        <p style={{ fontSize: 12, color: 'var(--ink-500)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Finance Ministry approval for Phase 2 funding.</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Recent Attachments */}
                        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: 20 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <p style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--ink-500)', margin: 0, fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>Recent Attachments</p>
                                <button style={{ fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>View All</button>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                                {[
                                    { icon: 'picture_as_pdf', name: 'Feasibility_Study_v2.pdf', meta: '2.4 MB · 2 days ago' },
                                    { icon: 'table_view', name: 'Financial_Model_2024.xlsx', meta: '1.1 MB · 1 week ago' },
                                ].map(f => (
                                    <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--ink-400)' }}>{f.icon}</span>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <p style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink-800)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: "'Geist', 'Inter', system-ui, sans-serif" }}>{f.name}</p>
                                            <p style={{ fontSize: 10, color: 'var(--ink-400)', margin: '2px 0 0', fontFamily: "'Geist Mono', monospace" }}>{f.meta}</p>
                                        </div>
                                        <span style={{ fontSize: 16, color: 'var(--ink-300)' }}>›</span>
                                    </div>
                                ))}
                            </div>
                            <button style={{ marginTop: 12, width: '100%', padding: '8px 0', fontSize: 12, color: 'var(--ink-500)', border: '1px dashed var(--border)', background: 'none', cursor: 'pointer', fontFamily: "'Geist', 'Inter', system-ui, sans-serif", display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>upload_file</span>
                                Upload Document
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
