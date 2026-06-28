/**
 * Ensures a date string from the backend (naive UTC) is parsed as UTC.
 * Backend sends ISO strings with 'Z' suffix via SchemaBase serializer,
 * but this handles any edge cases where the suffix is missing.
 */
export function parseUTCDate(dateStr: string): Date {
    if (!dateStr) return new Date();
    // If already has timezone info (Z, +, or - after the date portion), use as-is
    const s = dateStr.endsWith('Z') || dateStr.includes('+') || dateStr.includes('-', 10)
        ? dateStr : `${dateStr}Z`;
    return new Date(s);
}

/**
 * Converts a UTC date string to a value suitable for <input type="datetime-local">,
 * which expects local time in "YYYY-MM-DDTHH:MM" format.
 */
export function toLocalInputValue(dateStr: string): string {
    const d = parseUTCDate(dateStr);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Canonical event timezone for all meeting displays. Matches the backend
// email convention (Africa/Nairobi = EAT, UTC+3) so dashboard, detail,
// sidebar, calendar and invites all show the SAME labeled instant.
export const EVENT_TIME_ZONE = 'Africa/Nairobi';
export const EVENT_TZ_LABEL = 'EAT';

/** Time-of-day in the canonical event tz, e.g. "03:00 PM EAT". */
export function formatMeetingTime(dateStr: string): string {
    if (!dateStr) return '—';
    const t = parseUTCDate(dateStr).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', timeZone: EVENT_TIME_ZONE,
    });
    return `${t} ${EVENT_TZ_LABEL}`;
}

/** Date in the canonical event tz, e.g. "Jul 1, 2026". */
export function formatMeetingDate(dateStr: string): string {
    if (!dateStr) return '—';
    return parseUTCDate(dateStr).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', timeZone: EVENT_TIME_ZONE,
    });
}
