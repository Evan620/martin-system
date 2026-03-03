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
