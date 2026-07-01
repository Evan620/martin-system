import ConflictDashboard from '../../components/admin/ConflictDashboard';
import GlobalStateDashboard from '../../components/admin/GlobalStateDashboard';
import SupervisorActionsCard from '../../components/admin/SupervisorActionsCard';

/**
 * Admin Control Tower Page
 * 
 * A standalone page for the Secretariat to manage:
 * - Weekly Packet preparation
 * - Conflict detection and resolution
 * - Force reconciliation
 * - Auto-negotiation between agents
 */
export default function ControlTower() {
    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 flex items-center justify-center" style={{ borderRadius: 'var(--radius-ctl)', background: 'color-mix(in srgb, var(--terra) 12%, transparent)' }}>
                    <span className="material-symbols-outlined text-2xl" style={{ color: 'var(--terra)' }}>radar</span>
                </div>
                <div>
                    <h1 className="text-2xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>Control Tower</h1>
                    <p className="text-sm" style={{ color: 'var(--ink-500)' }}>Synthesis & Conflict Resolution Center</p>
                </div>
            </div>

            {/* Global State Dashboard */}
            <GlobalStateDashboard />

            {/* Supervisor Autonomous Actions */}
            <SupervisorActionsCard />

            {/* Conflict Dashboard Component */}
            <ConflictDashboard />
        </div>
    );
}
