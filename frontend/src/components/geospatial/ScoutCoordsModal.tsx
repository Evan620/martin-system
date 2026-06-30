/**
 * ScoutCoordsModal — when a project has no coordinates, this modal asks the
 * LLM to infer them from the project text, shows the suggestion on a map
 * for the facilitator to confirm/nudge, then on Confirm saves coords and
 * triggers the satellite analysis.
 *
 * Dispatch is one click off the Site Analysis sidebar widget when
 * `project.site_lat` is null.
 */
import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { pipelineService } from '../../services/pipelineService';
import type { ScoutedCoordinates } from '../../types/pipeline';

// Same Leaflet icon fix as SiteLocationPicker
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

interface Props {
    projectId: string;
    onClose: () => void;
    onConfirm: (lat: number, lon: number, place_name: string) => Promise<void> | void;
}

function FlyTo({ lat, lon }: { lat: number; lon: number }) {
    const map = useMap();
    useEffect(() => { map.setView([lat, lon], 10, { animate: true }); }, [lat, lon, map]);
    return null;
}

function ClickHandler({ onPick }: { onPick: (lat: number, lon: number) => void }) {
    useMapEvents({ click(e) { onPick(e.latlng.lat, e.latlng.lng); } });
    return null;
}

export default function ScoutCoordsModal({ projectId, onClose, onConfirm }: Props) {
    const [scouted, setScouted] = useState<ScoutedCoordinates | null>(null);
    const [editedLat, setEditedLat] = useState<number | null>(null);
    const [editedLon, setEditedLon] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [confirming, setConfirming] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await pipelineService.scoutCoordinates(projectId);
                if (cancelled) return;
                setScouted(result);
                setEditedLat(result.lat);
                setEditedLon(result.lon);
            } catch (e: any) {
                if (cancelled) return;
                setError(e?.response?.data?.detail || e?.message || 'Scout failed');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [projectId]);

    const handlePick = (lat: number, lon: number) => {
        setEditedLat(+lat.toFixed(4));
        setEditedLon(+lon.toFixed(4));
    };

    const handleConfirm = async () => {
        if (editedLat == null || editedLon == null) return;
        setConfirming(true);
        try {
            await onConfirm(editedLat, editedLon, scouted?.place_name || '');
            onClose();
        } catch (e: any) {
            setError(e?.message || 'Failed to save coordinates');
        } finally {
            setConfirming(false);
        }
    };

    const wasNudged = scouted != null && (editedLat !== scouted.lat || editedLon !== scouted.lon);
    const confidencePct = scouted ? Math.round(scouted.confidence * 100) : 0;
    const confidenceColor = confidencePct >= 80 ? '#16a34a' : confidencePct >= 50 ? '#f59e0b' : '#dc2626';

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 16,
        }}>
            <div style={{
                background: 'var(--surface, #fff)', border: '1px solid var(--border, #d1d5db)',
                width: '100%', maxWidth: 720, maxHeight: '90vh', overflow: 'auto', borderRadius: 8,
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '16px 20px', borderBottom: '1px solid var(--border, #d1d5db)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--accent, #7c3aed)' }}>auto_awesome</span>
                        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--ink-900, #111)' }}>
                            Scout project coordinates
                        </h3>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                        color: 'var(--ink-500, #6b7280)',
                    }}>
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {loading && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '20px 0', justifyContent: 'center', color: 'var(--ink-500, #6b7280)' }}>
                            <div className="size-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--accent, #7c3aed)', borderTopColor: 'transparent' }} />
                            <span style={{ fontSize: 14 }}>Asking Martin to infer plausible coordinates from the project content…</span>
                        </div>
                    )}

                    {error && !loading && (
                        <div style={{
                            background: 'rgba(220, 38, 38, 0.12)', borderLeft: '3px solid #dc2626',
                            padding: '10px 12px', fontSize: 13, color: 'var(--ink-700, #374151)', borderRadius: 4,
                        }}>
                            <strong>Scout failed.</strong> {error} — try editing the project directly and dropping a pin on the map.
                        </div>
                    )}

                    {scouted && !loading && (
                        <>
                            {/* Reasoning + confidence */}
                            <div>
                                <div style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500, #6b7280)', marginBottom: 6 }}>
                                    Martin's read
                                </div>
                                <div style={{
                                    background: 'rgba(124,58,237,0.06)', border: '1px solid var(--border, #d1d5db)',
                                    padding: '10px 12px', borderRadius: 6,
                                    fontFamily: "'Geist', serif", fontSize: 14, color: 'var(--ink-800, #1f2937)', lineHeight: 1.5,
                                }}>
                                    {scouted.reasoning || '(no reasoning provided)'}
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 12, color: 'var(--ink-500, #6b7280)' }}>
                                    <span><strong style={{ color: 'var(--ink-900, #111)' }}>{scouted.place_name}</strong></span>
                                    <span>
                                        Confidence: <span style={{ color: confidenceColor, fontWeight: 600 }}>{confidencePct}%</span>
                                    </span>
                                </div>
                            </div>

                            {/* Map */}
                            <div>
                                <div style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-500, #6b7280)', marginBottom: 6 }}>
                                    Drag the pin or click anywhere to nudge
                                </div>
                                <div style={{ height: 340, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border, #d1d5db)' }}>
                                    <MapContainer center={[scouted.lat, scouted.lon]} zoom={9} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
                                        <TileLayer
                                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                                            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                                        />
                                        {editedLat != null && editedLon != null && (
                                            <Marker
                                                position={[editedLat, editedLon]}
                                                draggable
                                                eventHandlers={{
                                                    dragend: (e) => {
                                                        const ll = e.target.getLatLng();
                                                        handlePick(ll.lat, ll.lng);
                                                    },
                                                }}
                                            />
                                        )}
                                        <ClickHandler onPick={handlePick} />
                                        <FlyTo lat={scouted.lat} lon={scouted.lon} />
                                    </MapContainer>
                                </div>
                                <div style={{ marginTop: 6, fontSize: 11, color: 'var(--ink-500, #6b7280)' }}>
                                    {editedLat != null && editedLon != null && (
                                        <>
                                            Pin at {editedLat.toFixed(4)}, {editedLon.toFixed(4)}
                                            {wasNudged && <span style={{ marginLeft: 8, color: 'var(--accent, #7c3aed)' }}>(nudged from suggestion)</span>}
                                        </>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    display: 'flex', justifyContent: 'flex-end', gap: 10,
                    padding: '12px 20px', borderTop: '1px solid var(--border, #d1d5db)',
                }}>
                    <button
                        onClick={onClose}
                        disabled={confirming}
                        style={{
                            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border, #d1d5db)',
                            background: 'transparent', color: 'var(--ink-700, #374151)', cursor: 'pointer', fontSize: 13,
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={loading || confirming || editedLat == null || editedLon == null}
                        style={{
                            padding: '8px 16px', borderRadius: 6, border: 'none',
                            background: '#4f46e5', color: '#fff', cursor: confirming ? 'default' : 'pointer',
                            fontSize: 13, fontWeight: 500, opacity: (loading || confirming || editedLat == null) ? 0.5 : 1,
                        }}
                    >
                        {confirming ? 'Saving + analysing…' : 'Confirm & analyse'}
                    </button>
                </div>
            </div>
        </div>
    );
}
