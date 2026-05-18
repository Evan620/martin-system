import React from 'react';
import { Project, ProjectStatus } from '../../types/pipeline';
import {
    ClipboardDocumentListIcon,
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

const STAGES = [
    { key: ProjectStatus.DRAFT, label: 'Draft', icon: ClipboardDocumentListIcon },
    { key: ProjectStatus.PIPELINE, label: 'Pipeline', icon: ClockIcon },
    { key: ProjectStatus.UNDER_REVIEW, label: 'Under Review', icon: MagnifyingGlassIcon },
    { key: ProjectStatus.SUMMIT_READY, label: 'Summit Ready', icon: CheckBadgeIcon },
    { key: ProjectStatus.DEAL_ROOM_FEATURED, label: 'Featured', icon: StarIcon },
    { key: ProjectStatus.IN_NEGOTIATION, label: 'Negotiation', icon: CurrencyDollarIcon },
    { key: ProjectStatus.COMMITTED, label: 'Committed', icon: TrophyIcon }
];

export const ProjectLifecycleTimeline: React.FC<Props> = ({ project }) => {
    const currentStatus = project.status;

    // Determine if we are in a "negative" state (Declined/Needs Revision)
    const isDeclined = currentStatus === ProjectStatus.DECLINED;
    const isRevision = currentStatus === ProjectStatus.NEEDS_REVISION;

    // Map current status to an index in our linear timeline
    // If declined/revision, we map them to UNDER_REVIEW but show different UI
    let activeIndex = STAGES.findIndex(s => s.key === currentStatus);

    if (activeIndex === -1) {
        if (isDeclined || isRevision) {
            activeIndex = STAGES.findIndex(s => s.key === ProjectStatus.UNDER_REVIEW);
        } else if (currentStatus === ProjectStatus.IMPLEMENTED) {
            activeIndex = STAGES.length - 1; // Show as fully complete
        } else {
            // Fallback for legacy or other states
            activeIndex = 0;
        }
    }

    return (
        <div className="w-full py-6 overflow-x-auto">
            <div className="flex items-center justify-between min-w-[800px] px-4">
                {STAGES.map((stage, index) => {
                    const isCompleted = index < activeIndex;
                    const isActive = index === activeIndex;
                    const Icon = stage.icon;

                    let statusColor = 'bg-gray-200 text-gray-400';

                    if (isCompleted) {
                        statusColor = 'bg-green-500 text-white';
                    } else if (isActive) {
                        if (isDeclined) statusColor = 'bg-red-500 text-white';
                        else if (isRevision) statusColor = 'bg-amber-500 text-white';
                        else statusColor = 'bg-blue-600 text-white';
                    }

                    return (
                        <div key={stage.key} className="relative flex flex-col items-center flex-1 group">
                            {/* Connector Line */}
                            {index !== 0 && (
                                <div
                                    className={`absolute top-5 right-[50%] w-full h-[2px] -translate-y-1/2 ${index <= activeIndex ? 'bg-green-500' : 'bg-gray-200'
                                        } ${isActive && !isCompleted ? 'bg-gray-200' : ''}`}
                                // Fix line logic: Line fills if NEXT step is reached 
                                // Actually, strictly: line behind filled if this step reached.
                                />
                            )}

                            {/* Icon Bubble */}
                            <div
                                className={`relative z-10 flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${statusColor} shadow-sm border-2 border-white`}
                            >
                                {isActive && isDeclined ? (
                                    <XCircleIcon className="w-6 h-6" />
                                ) : isActive && isRevision ? (
                                    <ExclamationTriangleIcon className="w-6 h-6" />
                                ) : (
                                    <Icon className="w-5 h-5" />
                                )}
                            </div>

                            {/* Label */}
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
                })}
            </div>
        </div>
    );
};
