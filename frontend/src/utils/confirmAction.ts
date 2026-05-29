import api from '../services/api';

/**
 * A confirm-then-execute envelope emitted by Martin's write tools.
 * The agent returns this JSON when an action needs explicit user confirmation
 * before it touches the database (e.g. advance_project_stage, create_action_item).
 */
export type ConfirmCard = {
    status: 'confirmation_required';
    type?: string;
    action_id: string;
    action_type: string;
    summary: string;
    payload: Record<string, any>;
    irreversible?: boolean;
    confirm_endpoint: string;
};

/**
 * Detect whether a message body is a confirmation_required envelope.
 * Returns the parsed card or null if the content is ordinary prose.
 */
export function tryParseConfirm(content: string): ConfirmCard | null {
    const trimmed = (content || '').trim();
    if (!trimmed.startsWith('{')) return null;
    try {
        const j = JSON.parse(trimmed);
        if (j && j.status === 'confirmation_required' && j.action_id && j.confirm_endpoint) {
            return j as ConfirmCard;
        }
    } catch {
        /* not JSON */
    }
    return null;
}

/**
 * POST the user's confirm/cancel decision to /agents/execute and return a short
 * human-readable result string.
 *
 * The backend emits confirm_endpoint as "/api/v1/agents/execute" (an
 * origin-relative path), but the Vite dev proxy strips the "/api" prefix, so
 * calling it directly yields a 404. We resolve against the api service base URL
 * so the request lands on the FastAPI router cleanly in both dev and prod.
 */
export async function executeConfirm(card: ConfirmCard, confirmed: boolean): Promise<string> {
    const base = (api.defaults.baseURL || '').replace(/\/$/, '');
    const path = card.confirm_endpoint.replace(/^\/api\/v1/, '').replace(/^\//, '');
    const url = `${base}/${path}`;
    const token = localStorage.getItem('token');
    const resp = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ action_id: card.action_id, confirmed, edits: {} }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) return `Action failed: ${data.detail || resp.statusText}`;
    if (data.cancelled) return 'Cancelled.';
    if (data.success === true || data.status === 'ok') return data.message || 'Done.';
    return JSON.stringify(data);
}
