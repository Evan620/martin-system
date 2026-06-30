import React from 'react';

const ComingSoonOverlay: React.FC = () => {
    return (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-white/60 backdrop-blur-[2px] rounded-xl overflow-hidden pointer-events-none">
            <div className="bg-[var(--surface)] px-8 py-4 rounded-2xl border border-[var(--border)] transform -rotate-12 animate-pulse">
                <span className="text-4xl font-black tracking-tighter text-[var(--ink-900)] drop-shadow-sm">
                    COMING SOON
                </span>
            </div>
        </div>
    );
};

export default ComingSoonOverlay;
