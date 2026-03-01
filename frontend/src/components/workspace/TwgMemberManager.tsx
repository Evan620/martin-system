import { useState, useEffect } from 'react';
import { twgs } from '../../services/api';

interface TwgMember {
    id: string;
    full_name: string;
    email: string;
    role: string;
    organization: string | null;
    is_active: boolean;
    is_political_lead: boolean;
    is_technical_lead: boolean;
}

interface TwgMemberManagerProps {
    twgId: string;
    twgName?: string;
    canEdit?: boolean;
}

/**
 * Parse bulk text input into member entries.
 * Supports formats:
 *   - email@example.com (one per line or comma-separated)
 *   - Full Name <email@example.com>
 *   - Full Name, email@example.com
 */
function parseBulkInput(text: string): { email: string; full_name: string }[] {
    const entries: { email: string; full_name: string }[] = [];
    const seen = new Set<string>();

    // Split by newlines and commas (but not commas inside "Name, email" pairs)
    const lines = text.split(/\n/).map(l => l.trim()).filter(Boolean);

    for (const line of lines) {
        // Format: Name <email>
        const angleBracket = line.match(/^(.+?)\s*<([^>]+@[^>]+)>\s*$/);
        if (angleBracket) {
            const email = angleBracket[2].trim().toLowerCase();
            if (!seen.has(email)) {
                seen.add(email);
                entries.push({ email, full_name: angleBracket[1].trim() });
            }
            continue;
        }

        // Format: Name, email  (name has no @, email has @)
        const commaParts = line.split(',').map(p => p.trim());
        if (commaParts.length === 2 && commaParts[1].includes('@') && !commaParts[0].includes('@')) {
            const email = commaParts[1].toLowerCase();
            if (!seen.has(email)) {
                seen.add(email);
                entries.push({ email, full_name: commaParts[0] });
            }
            continue;
        }

        // Format: plain emails (comma-separated on one line)
        const emailCandidates = line.split(/[,;]/).map(p => p.trim()).filter(Boolean);
        for (const candidate of emailCandidates) {
            if (candidate.includes('@')) {
                const email = candidate.toLowerCase();
                if (!seen.has(email)) {
                    seen.add(email);
                    entries.push({ email, full_name: '' });
                }
            }
        }
    }

    return entries;
}

const TwgMemberManager = ({ twgId, twgName, canEdit = true }: TwgMemberManagerProps) => {
    const [members, setMembers] = useState<TwgMember[]>([]);
    const [loading, setLoading] = useState(true);
    const [addEmail, setAddEmail] = useState('');
    const [addName, setAddName] = useState('');
    const [adding, setAdding] = useState(false);
    const [removingId, setRemovingId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Bulk mode state
    const [bulkMode, setBulkMode] = useState(false);
    const [bulkText, setBulkText] = useState('');
    const [bulkResult, setBulkResult] = useState<any>(null);

    const parsedBulk = bulkMode ? parseBulkInput(bulkText) : [];

    const loadMembers = async () => {
        try {
            setLoading(true);
            const response = await twgs.listMembers(twgId);
            setMembers(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load members');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (twgId) loadMembers();
    }, [twgId]);

    const handleAddMember = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!addEmail.trim()) return;

        setAdding(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await twgs.addMember(twgId, addEmail.trim(), addName.trim());
            setSuccess(response.data.message);
            setAddEmail('');
            setAddName('');
            await loadMembers();
            setTimeout(() => setSuccess(null), 4000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add member');
            setTimeout(() => setError(null), 5000);
        } finally {
            setAdding(false);
        }
    };

    const handleBulkAdd = async () => {
        if (parsedBulk.length === 0) return;

        setAdding(true);
        setError(null);
        setSuccess(null);
        setBulkResult(null);

        try {
            const response = await twgs.bulkAddMembers(twgId, parsedBulk);
            const data = response.data;
            setSuccess(data.message);
            setBulkResult(data);
            setBulkText('');
            await loadMembers();
            setTimeout(() => { setSuccess(null); setBulkResult(null); }, 8000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add members');
            setTimeout(() => setError(null), 5000);
        } finally {
            setAdding(false);
        }
    };

    const handleRemoveMember = async (userId: string, name: string) => {
        if (!confirm(`Remove ${name} from this TWG?`)) return;

        setRemovingId(userId);
        setError(null);
        setSuccess(null);

        try {
            const response = await twgs.removeMember(twgId, userId);
            setSuccess(response.data.message);
            await loadMembers();
            setTimeout(() => setSuccess(null), 4000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to remove member');
            setTimeout(() => setError(null), 5000);
        } finally {
            setRemovingId(null);
        }
    };

    const getRoleBadge = (member: TwgMember) => {
        if (member.is_political_lead) return { label: 'Political Lead', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' };
        if (member.is_technical_lead) return { label: 'Technical Lead', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' };
        if (member.role === 'TWG_FACILITATOR') return { label: 'Facilitator', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' };
        if (member.role === 'ADMIN' || member.role === 'SECRETARIAT_LEAD') return { label: member.role.replace('_', ' '), color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' };
        return { label: 'Member', color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400' };
    };

    return (
        <div className="space-y-6">
            {/* Add Member Form - only for editors */}
            {canEdit && (
                <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-black text-slate-900 dark:text-white flex items-center gap-2">
                            <span className="material-symbols-outlined text-blue-600 text-[20px]">
                                {bulkMode ? 'group_add' : 'person_add'}
                            </span>
                            {bulkMode ? 'Bulk Add Members' : 'Add Member'}
                        </h3>
                        <button
                            onClick={() => { setBulkMode(!bulkMode); setBulkResult(null); }}
                            className="text-xs font-bold text-blue-600 hover:text-blue-500 transition-colors flex items-center gap-1"
                        >
                            <span className="material-symbols-outlined text-[16px]">
                                {bulkMode ? 'person_add' : 'group_add'}
                            </span>
                            {bulkMode ? 'Single Add' : 'Bulk Add'}
                        </button>
                    </div>

                    {bulkMode ? (
                        /* Bulk Add Mode */
                        <div className="space-y-3">
                            <textarea
                                value={bulkText}
                                onChange={(e) => setBulkText(e.target.value)}
                                placeholder={`Paste emails here (one per line). Supported formats:\n\njohn@example.com\nJane Doe <jane@example.com>\nJohn Smith, john@example.com`}
                                disabled={adding}
                                rows={6}
                                className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700 dark:text-slate-200 placeholder:text-slate-400 resize-none"
                            />
                            <div className="flex items-center justify-between">
                                <div className="text-xs text-slate-500">
                                    {parsedBulk.length > 0 ? (
                                        <span className="font-bold text-blue-600">
                                            {parsedBulk.length} member{parsedBulk.length !== 1 ? 's' : ''} detected
                                            {parsedBulk.filter(p => !p.full_name).length > 0 && (
                                                <span className="text-amber-500 ml-1">
                                                    ({parsedBulk.filter(p => !p.full_name).length} without names)
                                                </span>
                                            )}
                                        </span>
                                    ) : bulkText.trim() ? (
                                        <span className="text-amber-500">No valid emails detected</span>
                                    ) : null}
                                </div>
                                <button
                                    onClick={handleBulkAdd}
                                    disabled={adding || parsedBulk.length === 0}
                                    className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-blue-600/20"
                                >
                                    {adding ? (
                                        <>
                                            <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                                            Adding...
                                        </>
                                    ) : (
                                        <>
                                            <span className="material-symbols-outlined text-[18px]">group_add</span>
                                            Add {parsedBulk.length} Member{parsedBulk.length !== 1 ? 's' : ''}
                                        </>
                                    )}
                                </button>
                            </div>

                            {/* Bulk Result Summary */}
                            {bulkResult && (
                                <div className="mt-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 text-xs space-y-1">
                                    {bulkResult.summary.added > 0 && (
                                        <div className="flex items-center gap-1 text-green-600 dark:text-green-400 font-bold">
                                            <span className="material-symbols-outlined text-[14px]">check_circle</span>
                                            {bulkResult.summary.added} added
                                            {bulkResult.summary.new_accounts > 0 && ` (${bulkResult.summary.new_accounts} new accounts)`}
                                        </div>
                                    )}
                                    {bulkResult.summary.skipped > 0 && (
                                        <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-bold">
                                            <span className="material-symbols-outlined text-[14px]">info</span>
                                            {bulkResult.summary.skipped} skipped (already members)
                                        </div>
                                    )}
                                    {bulkResult.summary.errors > 0 && (
                                        <div className="flex items-center gap-1 text-red-600 dark:text-red-400 font-bold">
                                            <span className="material-symbols-outlined text-[14px]">error</span>
                                            {bulkResult.summary.errors} failed
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ) : (
                        /* Single Add Mode */
                        <>
                            <form onSubmit={handleAddMember} className="flex gap-3 flex-wrap">
                                <input
                                    type="text"
                                    value={addName}
                                    onChange={(e) => setAddName(e.target.value)}
                                    placeholder="Full name"
                                    disabled={adding}
                                    className="w-48 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700 dark:text-slate-200 placeholder:text-slate-400"
                                />
                                <input
                                    type="email"
                                    value={addEmail}
                                    onChange={(e) => setAddEmail(e.target.value)}
                                    placeholder="Email address"
                                    disabled={adding}
                                    className="flex-1 min-w-[200px] px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700 dark:text-slate-200 placeholder:text-slate-400"
                                />
                                <button
                                    type="submit"
                                    disabled={adding || !addEmail.trim()}
                                    className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold text-sm hover:bg-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-blue-600/20"
                                >
                                    {adding ? (
                                        <>
                                            <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                                            Adding...
                                        </>
                                    ) : (
                                        <>
                                            <span className="material-symbols-outlined text-[18px]">add</span>
                                            Add
                                        </>
                                    )}
                                </button>
                            </form>
                            <p className="text-[11px] text-slate-400 mt-2">
                                If the user isn't registered yet, provide their full name and a new account will be created automatically.
                            </p>
                        </>
                    )}
                </div>
            )}

            {/* Feedback Messages */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm font-bold flex items-center gap-2 border border-red-200 dark:border-red-800">
                    <span className="material-symbols-outlined text-[18px]">error</span>
                    {error}
                </div>
            )}
            {success && (
                <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-sm font-bold flex items-center gap-2 border border-green-200 dark:border-green-800">
                    <span className="material-symbols-outlined text-[18px]">check_circle</span>
                    {success}
                </div>
            )}

            {/* Members List */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
                    <h3 className="text-sm font-black text-slate-900 dark:text-white flex items-center gap-2">
                        <span className="material-symbols-outlined text-blue-600 text-[20px]">group</span>
                        {twgName ? `${twgName} Members` : 'TWG Members'}
                    </h3>
                    <span className="text-xs font-bold text-slate-400 bg-slate-100 dark:bg-slate-700 px-3 py-1 rounded-full">
                        {members.length} member{members.length !== 1 ? 's' : ''}
                    </span>
                </div>

                {loading ? (
                    <div className="p-12 text-center">
                        <span className="material-symbols-outlined animate-spin text-blue-500 text-3xl">progress_activity</span>
                        <p className="text-sm text-slate-500 mt-2 font-medium">Loading members...</p>
                    </div>
                ) : members.length === 0 ? (
                    <div className="p-12 text-center">
                        <span className="material-symbols-outlined text-slate-300 dark:text-slate-600 text-5xl">group_off</span>
                        <p className="text-sm text-slate-500 mt-3 font-medium">No members yet</p>
                        <p className="text-xs text-slate-400 mt-1">Add members using the form above</p>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-100 dark:divide-slate-700">
                        {members.map((member) => {
                            const badge = getRoleBadge(member);
                            const isLead = member.is_political_lead || member.is_technical_lead;
                            return (
                                <div
                                    key={member.id}
                                    className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
                                >
                                    {/* Avatar */}
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm shrink-0
                                        ${isLead
                                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 ring-2 ring-blue-500/30'
                                            : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                                        }`}
                                    >
                                        {member.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                                {member.full_name}
                                            </span>
                                            <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider ${badge.color}`}>
                                                {badge.label}
                                            </span>
                                            {!member.is_active && (
                                                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-red-100 text-red-600">
                                                    Inactive
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3 mt-0.5">
                                            <span className="text-xs text-slate-500 truncate">{member.email}</span>
                                            {member.organization && (
                                                <>
                                                    <span className="text-slate-300 dark:text-slate-600">•</span>
                                                    <span className="text-xs text-slate-400 truncate">{member.organization}</span>
                                                </>
                                            )}
                                        </div>
                                    </div>

                                    {/* Remove Button - hidden for leads and read-only viewers */}
                                    {canEdit && !isLead && (
                                        <button
                                            onClick={() => handleRemoveMember(member.id, member.full_name)}
                                            disabled={removingId === member.id}
                                            className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all opacity-0 group-hover:opacity-100 disabled:opacity-50"
                                            title={`Remove ${member.full_name}`}
                                        >
                                            {removingId === member.id ? (
                                                <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                                            ) : (
                                                <span className="material-symbols-outlined text-[18px]">person_remove</span>
                                            )}
                                        </button>
                                    )}
                                    {canEdit && isLead && (
                                        <span className="material-symbols-outlined text-[18px] text-slate-300 dark:text-slate-600" title="Leads cannot be removed here">
                                            lock
                                        </span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default TwgMemberManager;
