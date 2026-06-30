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
// EAT (Africa/Nairobi) is UTC+3 year-round — Kenya observes no DST — so the
// canonical event offset is a fixed +03:00.
export const EVENT_UTC_OFFSET = '+03:00';

/**
 * Convert an EAT wall-clock entered in a form (date 'YYYY-MM-DD' + time 'HH:MM')
 * into the UTC ISO string we persist — independent of the creator's browser
 * timezone. This is the inverse of formatMeetingTime (which renders stored UTC
 * back into EAT), so a "3:00 PM" entry stores 12:00Z and displays 3:00 PM EAT
 * for everyone, no matter where it was created.
 */
export function eventLocalToUTCISO(date: string, time: string): string {
    return new Date(`${date}T${time}:00${EVENT_UTC_OFFSET}`).toISOString();
}

/**
 * Stored UTC ISO -> a 'YYYY-MM-DDTHH:MM' string in the canonical event tz
 * (Africa/Nairobi / EAT), suitable for pre-filling an <input type="datetime-local">.
 * Browser-independent: renders the EAT wall-clock regardless of the viewer's
 * local timezone. Inverse of eventInputToUTCISO.
 */
export function toEventInputValue(dateStr: string): string {
    if (!dateStr) return '';
    const d = parseUTCDate(dateStr);
    const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: EVENT_TIME_ZONE,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(d);
    const get = (type: string) => parts.find(p => p.type === type)?.value ?? '00';
    // Intl can emit '24' for midnight hour in some engines; normalize to '00'.
    let hour = get('hour');
    if (hour === '24') hour = '00';
    return `${get('year')}-${get('month')}-${get('day')}T${hour}:${get('minute')}`;
}

/**
 * An EAT 'YYYY-MM-DDTHH:MM' (datetime-local) -> UTC ISO string we persist.
 * Browser-independent: interprets the entered wall-clock as EAT (fixed +03:00).
 * Inverse of toEventInputValue.
 */
export function eventInputToUTCISO(datetimeLocal: string): string {
    return new Date(`${datetimeLocal}:00${EVENT_UTC_OFFSET}`).toISOString();
}

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
