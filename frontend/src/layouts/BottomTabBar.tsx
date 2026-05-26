import { useNavigate, useLocation } from 'react-router-dom';

interface BottomTabBarProps {
    onMoreClick: () => void;
}

const TABS = [
    { id: 'dashboard', label: 'Home', icon: 'dashboard', path: '/dashboard' },
    { id: 'pipeline', label: 'Pipeline', icon: 'work_outline', path: '/deal-pipeline' },
    { id: 'schedule', label: 'Schedule', icon: 'calendar_month', path: '/schedule' },
    { id: 'actions', label: 'Actions', icon: 'task_alt', path: '/actions' },
    { id: 'more', label: 'More', icon: 'menu', path: null },
] as const;

export default function BottomTabBar({ onMoreClick }: BottomTabBarProps) {
    const navigate = useNavigate();
    const location = useLocation();

    const isActive = (path: string | null, id: string) => {
        if (id === 'more') return false;
        if (!path) return false;
        if (path === '/dashboard') return location.pathname === '/dashboard' || location.pathname === '/';
        if (path === '/deal-pipeline') return location.pathname.startsWith('/deal-pipeline') && !location.pathname.startsWith('/deal-pipeline/buyers');
        return location.pathname.startsWith(path);
    };

    return (
        <nav
            className="bottom-tab-bar fixed bottom-0 left-0 right-0 z-30"
            style={{
                height: 64,
                background: 'var(--surface)',
                borderTop: '1px solid var(--border)',
                paddingBottom: 'env(safe-area-inset-bottom, 0)',
                fontFamily: "'Geist', 'Inter', system-ui, sans-serif",
            }}
        >
            {TABS.map(tab => {
                const on = isActive(tab.path, tab.id);
                const onClick = tab.id === 'more' ? onMoreClick : () => tab.path && navigate(tab.path);
                return (
                    <button
                        key={tab.id}
                        onClick={onClick}
                        style={{
                            flex: 1,
                            display: 'flex', flexDirection: 'column',
                            alignItems: 'center', justifyContent: 'center', gap: 3,
                            background: 'transparent', border: 'none', cursor: 'pointer',
                            color: on ? 'var(--accent)' : 'var(--ink-500)',
                            paddingTop: 8, paddingBottom: 6,
                            fontFamily: 'inherit',
                        }}
                    >
                        <span
                            className="material-symbols-outlined"
                            style={{
                                fontSize: 22,
                                fontVariationSettings: on ? '"FILL" 1, "wght" 500' : '"FILL" 0, "wght" 300',
                            }}
                        >
                            {tab.icon}
                        </span>
                        <span style={{ fontSize: 10, fontWeight: on ? 500 : 400, letterSpacing: '0.02em' }}>
                            {tab.label}
                        </span>
                    </button>
                );
            })}
        </nav>
    );
}
