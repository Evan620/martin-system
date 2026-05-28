/**
 * SiteLocationPicker — hybrid place-name + map pin picker for R8.
 *
 * Used in project intake (NewProject) and project edit (EditProject) forms.
 * Two input modes that stay in sync:
 *   1. Type a place name → Enter triggers OpenStreetMap Nominatim geocoding →
 *      lat/lon set, pin moves on the map.
 *   2. Click the map → pin moves to the clicked point, reverse-geocode fills
 *      the place-name field.
 *
 * The component is controlled — the parent owns `lat`, `lon`, `name` and
 * receives updates via `onChange({lat, lon, name})`.
 */
import { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';

// Leaflet's default marker icons reference relative URLs that break under
// Vite's bundler. Point them at the CDN copies instead.
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});


// West Africa default centre when nothing's set yet
const DEFAULT_CENTER: [number, number] = [9.0, -5.0];
const DEFAULT_ZOOM = 5;
const PINNED_ZOOM = 11;

const NOMINATIM = 'https://nominatim.openstreetmap.org';

export interface SiteLocationValue {
    lat: number | null;
    lon: number | null;
    name: string;
}

interface Props {
    value: SiteLocationValue;
    onChange: (next: SiteLocationValue) => void;
    height?: number;
    disabled?: boolean;
}

/** Re-centres the map when lat/lon change externally (e.g. after geocode). */
function FlyToValue({ lat, lon }: { lat: number | null; lon: number | null }) {
    const map = useMap();
    useEffect(() => {
        if (lat != null && lon != null) {
            map.setView([lat, lon], PINNED_ZOOM, { animate: true });
        }
    }, [lat, lon, map]);
    return null;
}

/** Captures map clicks and turns them into onChange events. */
function ClickHandler({ onPick }: { onPick: (lat: number, lon: number) => void }) {
    useMapEvents({
        click(e) {
            onPick(e.latlng.lat, e.latlng.lng);
        },
    });
    return null;
}

export default function SiteLocationPicker({ value, onChange, height = 320, disabled }: Props) {
    const [nameInput, setNameInput] = useState(value.name || '');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const lastReverseRef = useRef<string>('');

    // Keep input in sync when parent's name changes (e.g. on initial load)
    useEffect(() => {
        setNameInput(value.name || '');
    }, [value.name]);

    async function geocode(q: string) {
        if (!q.trim()) return;
        setBusy(true);
        setError(null);
        try {
            const url = `${NOMINATIM}/search?format=json&limit=1&q=${encodeURIComponent(q)}`;
            const r = await fetch(url, { headers: { 'Accept-Language': 'en' } });
            const results = await r.json();
            if (!results || results.length === 0) {
                setError('Location not found. Try a more specific query.');
                return;
            }
            const top = results[0];
            const lat = parseFloat(top.lat);
            const lon = parseFloat(top.lon);
            onChange({ lat: +lat.toFixed(4), lon: +lon.toFixed(4), name: q.trim() });
        } catch (e) {
            setError('Geocoding service unavailable.');
        } finally {
            setBusy(false);
        }
    }

    async function reverseGeocode(lat: number, lon: number) {
        const key = `${lat.toFixed(4)},${lon.toFixed(4)}`;
        if (key === lastReverseRef.current) return;
        lastReverseRef.current = key;
        try {
            const url = `${NOMINATIM}/reverse?format=json&lat=${lat}&lon=${lon}&zoom=10`;
            const r = await fetch(url, { headers: { 'Accept-Language': 'en' } });
            const data = await r.json();
            const display = data?.display_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
            // Compact the display name (Nominatim returns very long strings)
            const compact = display.split(',').slice(0, 3).join(', ');
            onChange({ lat: +lat.toFixed(4), lon: +lon.toFixed(4), name: compact });
        } catch {
            // Network failed — keep coords but leave name as-is
            onChange({ lat: +lat.toFixed(4), lon: +lon.toFixed(4), name: nameInput });
        }
    }

    function handlePin(lat: number, lon: number) {
        if (disabled) return;
        reverseGeocode(lat, lon);
    }

    const hasPin = value.lat != null && value.lon != null;
    const center: [number, number] = hasPin ? [value.lat!, value.lon!] : DEFAULT_CENTER;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
                <input
                    type="text"
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            geocode(nameInput);
                        }
                    }}
                    placeholder='Type a place — e.g. "Office du Niger, Mali" — and press Enter'
                    disabled={disabled || busy}
                    style={{
                        flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border, #d1d5db)',
                        background: 'var(--surface, #fff)', color: 'var(--ink-900, #111)', fontSize: 14,
                        outline: 'none',
                    }}
                />
                <button
                    type="button"
                    onClick={() => geocode(nameInput)}
                    disabled={disabled || busy || !nameInput.trim()}
                    style={{
                        padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border, #d1d5db)',
                        background: '#4f46e5', color: '#fff', cursor: 'pointer', fontSize: 13,
                    }}
                >
                    {busy ? 'Searching…' : 'Find'}
                </button>
            </div>

            <div style={{ height, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border, #d1d5db)' }}>
                <MapContainer center={center} zoom={hasPin ? PINNED_ZOOM : DEFAULT_ZOOM} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    {hasPin && (
                        <Marker
                            position={[value.lat!, value.lon!]}
                            draggable={!disabled}
                            eventHandlers={{
                                dragend: (e) => {
                                    const m = e.target;
                                    const ll = m.getLatLng();
                                    handlePin(ll.lat, ll.lng);
                                },
                            }}
                        />
                    )}
                    <ClickHandler onPick={handlePin} />
                    <FlyToValue lat={value.lat} lon={value.lon} />
                </MapContainer>
            </div>

            <div style={{ fontSize: 12, color: 'var(--ink-500, #6b7280)', display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <span>
                    {hasPin
                        ? `Pinned at ${value.lat!.toFixed(4)}, ${value.lon!.toFixed(4)}`
                        : 'Type a place above, or click anywhere on the map to drop a pin.'}
                </span>
                {error && <span style={{ color: '#dc2626' }}>{error}</span>}
            </div>
        </div>
    );
}
