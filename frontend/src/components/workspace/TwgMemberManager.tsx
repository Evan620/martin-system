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

const TwgMemberManager = ({ twgId, twgName, canEdit = true }: TwgMemberManagerProps) => {
    const [members, setMembers] = useState<TwgMember[]>([]);
    const [loading, setLoading] = useState(true);
    const [addEmail, setAddEmail] = useState('');
    const [addName, setAddName] = useState('');
    const [adding, setAdding] = useState(false);
    const [removingId, setRemovingId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

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
                    <h3 className="text-sm font-black text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                        <span className="material-symbols-outlined text-blue-600 text-[20px]">person_add</span>
                        Add Member
                    </h3>
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
