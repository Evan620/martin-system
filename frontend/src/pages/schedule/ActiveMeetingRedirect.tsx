import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { meetings } from '../../services/api';

export default function ActiveMeetingRedirect() {
    const navigate = useNavigate();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const findActive = async () => {
            try {
                const res = await meetings.getActive();
                if (res.data?.id) {
                    navigate(`/meetings/${res.data.id}/live`);
                } else {
                    setError("No active meeting found at the moment.");
                }
            } catch (err) {
                setError("No meetings are currently in progress.");
            }
        };

        findActive();
    }, [navigate]);

    if (error) {
        return (
            <div className="h-full flex items-center justify-center">
                <div className="text-center p-8 max-w-md" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                    <span className="material-symbols-outlined text-4xl mb-4 block" style={{ color: 'var(--ink-300)' }}>event_busy</span>
                    <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--ink-900)' }}>Monitor Offline</h2>
                    <p className="text-sm mb-6" style={{ color: 'var(--ink-500)' }}>{error}</p>
                    <button
                        onClick={() => navigate('/schedule')}
                        className="px-4 py-2 text-sm font-medium qp-transition clickable-scale"
                        style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
                    >
                        View Schedule
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col items-center justify-center">
            <div className="size-12 rounded-full border-4 border-t-transparent animate-spin mb-4" style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}></div>
            <p className="font-medium" style={{ color: 'var(--ink-500)' }}>Entering Live Monitor...</p>
        </div>
    );
}
