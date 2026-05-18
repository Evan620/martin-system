import React from 'react';
import { Project, ProjectStatus } from '../../types/pipeline';
import {
    LightBulbIcon,
    ClockIcon,
    MagnifyingGlassIcon,
    CheckBadgeIcon,
    StarIcon,
    CurrencyDollarIcon,
    TrophyIcon,
    XCircleIcon,
    ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface Props {
    project: Project;
}

const PHASE1 = [
    { key: ProjectStatus.DRAFT, label: 'Draft', icon: LightBulbIcon },
    { key: ProjectStatus.PIPELINE, label: 'Pipeline', icon: ClockIcon },
    { key: ProjectStatus.UNDER_REVIEW, label: 'Under Review', icon: MagnifyingGlassIcon },
    { key: ProjectStatus.SUMMIT_READY, label: 'Summit Ready', icon: CheckBadgeIcon },
];

const PHASE2 = [
    { key: ProjectStatus.DEAL_ROOM_FEATURED, label: 'Deal Room Featured', icon: StarIcon },
    { key: ProjectStatus.IN_NEGOTIATION, label: 'In Negotiation', icon: CurrencyDollarIcon },
    { key: ProjectStatus.COMMITTED, label: 'Committed', icon: TrophyIcon },
];

const ALL_STAGES = [...PHASE1, ...PHASE2];

export const ProjectLifecycleTimeline: React.FC<Props> = ({ project }) => {
    const currentStatus = project.status;
    const isDeclined = currentStatus === ProjectStatus.DECLINED;
    const isRevision = currentStatus === ProjectStatus.NEEDS_REVISION;

    let activeIndex = ALL_STAGES.findIndex(s => s.key === currentStatus);
    if (activeIndex === -1) {
        if (isDeclined || isRevision) activeIndex = ALL_STAGES.findIndex(s => s.key === ProjectStatus.UNDER_REVIEW);
        else activeIndex = 0;
    }

    const renderStage = (stage: typeof ALL_STAGES[0], index: number, isFirst: boolean) => {
        const isCompleted = index < activeIndex;
        const isActive = index === activeIndex;
        const Icon = stage.icon;

        let statusColor = 'bg-gray-200 text-gray-400';
        if (isCompleted) statusColor = 'bg-green-500 text-white';
        else if (isActive) {
            if (isDeclined) statusColor = 'bg-red-500 text-white';
            else if (isRevision) statusColor = 'bg-amber-500 text-white';
            else statusColor = 'bg-blue-600 text-white';
        }

        return (
            <div key={stage.key} className="relative flex flex-col items-center flex-1 group">
                {!isFirst && (
                    <div className={`absolute top-5 right-[50%] w-full h-[2px] -translate-y-1/2 ${index <= activeIndex ? 'bg-green-500' : 'bg-gray-200'}`} />
                )}
                <div className={`relative z-10 flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${statusColor} shadow-sm border-2 border-white`}>
                    {isActive && isDeclined ? <XCircleIcon className="w-6 h-6" /> :
                     isActive && isRevision ? <ExclamationTriangleIcon className="w-6 h-6" /> :
                     <Icon className="w-5 h-5" />}
                </div>
                <div className="mt-3 text-center">
                    <p className={`text-xs font-semibold ${isActive ? 'text-gray-900' : 'text-gray-500'}`}>
                        {stage.label}
                    </p>
                    {isActive && (
                        <span className="text-[10px] text-gray-400 font-medium">
                            {isDeclined ? 'Declined' : isRevision ? 'Needs Revision' : 'Current Stage'}
                        </span>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="w-full py-6 overflow-x-auto">
            <div className="px-4 min-w-[800px]">
                <div className="mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-blue-500 ml-2">
                        Phase 1 — Project Development
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    {PHASE1.map((stage, i) => renderStage(stage, i, i === 0))}
                </div>
                <div className="flex items-center gap-3 my-3 px-2">
                    <div className="flex-1 border-t border-dashed border-orange-300" />
                    <span className="text-[10px] text-orange-500 font-semibold whitespace-nowrap">Secretariat selects for summit</span>
                    <div className="flex-1 border-t border-dashed border-orange-300" />
                </div>
                <div className="mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-purple-500 ml-2">
                        Phase 2 — Deal Making
                    </span>
                </div>
                <div className="flex items-center justify-between">
                    {PHASE2.map((stage, i) => renderStage(stage, PHASE1.length + i, i === 0))}
                </div>
            </div>
        </div>
    );
};
