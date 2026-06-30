import { describe, it, expect } from 'vitest';
import {
    eventLocalToUTCISO,
    eventInputToUTCISO,
    toEventInputValue,
    formatMeetingTime,
    formatMeetingDate,
} from './dates';

// The bug this guards against: meetings entered as an EAT wall-clock were being
// stored using the creator's BROWSER timezone, so a "3:00 PM" meeting created
// from a UTC machine got saved as 15:00Z and displayed as 6:00 PM EAT.
describe('eventLocalToUTCISO (EAT wall-clock -> stored UTC)', () => {
    it('stores 3:00 PM EAT as 12:00Z', () => {
        expect(eventLocalToUTCISO('2026-07-01', '15:00')).toBe('2026-07-01T12:00:00.000Z');
    });

    it('stores 5:00 PM EAT as 14:00Z', () => {
        expect(eventLocalToUTCISO('2026-07-02', '17:00')).toBe('2026-07-02T14:00:00.000Z');
    });

    it('round-trips: an entered EAT time displays back as the same EAT time', () => {
        const stored = eventLocalToUTCISO('2026-07-01', '15:00');
        expect(formatMeetingTime(stored)).toBe('03:00 PM EAT');
        expect(formatMeetingDate(stored)).toBe('Jul 1, 2026');
    });

    it('is independent of the host browser timezone (fixed +03:00 offset)', () => {
        // Same inputs must always produce the same UTC instant regardless of TZ env.
        expect(eventLocalToUTCISO('2026-12-25', '09:30')).toBe('2026-12-25T06:30:00.000Z');
    });
});

// The edit form (MeetingDetail) pre-fills a datetime-local from stored UTC and
// saves it back. This must round-trip without drift, or editing a meeting's
// title would silently shift its time.
describe('edit-form helpers (toEventInputValue <-> eventInputToUTCISO)', () => {
    it('pre-fills a stored UTC instant as the EAT datetime-local', () => {
        expect(toEventInputValue('2026-07-01T12:00:00Z')).toBe('2026-07-01T15:00');
    });

    it('saves the EAT datetime-local back to the correct UTC instant', () => {
        expect(eventInputToUTCISO('2026-07-01T15:00')).toBe('2026-07-01T12:00:00.000Z');
    });

    it('round-trips without drift (open-edit -> save keeps the same instant)', () => {
        const stored = '2026-07-01T12:00:00Z';
        expect(eventInputToUTCISO(toEventInputValue(stored))).toBe('2026-07-01T12:00:00.000Z');
        // and it still displays as the same EAT time
        expect(formatMeetingTime(stored)).toBe('03:00 PM EAT');
    });
});
