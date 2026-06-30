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
                <div className="text-center p-8 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 max-w-md">
                    <span className="material-symbols-outlined text-4xl text-slate-300 mb-4 block">event_busy</span>
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-2">Monitor Offline</h2>
                    <p className="text-slate-500 text-sm mb-6">{error}</p>
                    <button
                        onClick={() => navigate('/schedule')}
                        className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-sm font-medium transition-colors clickable-scale"
                    >
                        View Schedule
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col items-center justify-center">
            <div className="size-12 rounded-full border-4 border-teal-600 border-t-transparent animate-spin mb-4"></div>
            <p className="text-slate-500 font-medium">Entering Live Monitor...</p>
        </div>
    );
}
