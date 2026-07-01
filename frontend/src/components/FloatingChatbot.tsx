import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

export default function FloatingChatbot() {
    const [isOpen, setIsOpen] = useState(false)
    const navigate = useNavigate()
    const location = useLocation()

    // Don't show on the assistant page itself
    if (location.pathname === '/assistant') {
        return null
    }

    const handleClick = () => {
        navigate('/assistant')
    }

    return (
        <>
            {/* Floating Button */}
            <button
                onClick={handleClick}
                onMouseEnter={() => setIsOpen(true)}
                onMouseLeave={() => setIsOpen(false)}
                className="fixed bottom-8 right-8 w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 hover:scale-110 z-50 group"
                style={{ background: 'var(--accent)', color: 'var(--accent-ink)', boxShadow: '0 12px 32px color-mix(in srgb, var(--accent) 40%, transparent)' }}
                aria-label="Open Secretariat Martin"
            >
                <svg
                    className="w-8 h-8 transition-transform group-hover:rotate-12"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                >
                    <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                    <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
                </svg>

                {/* Pulse animation */}
                <span className="absolute inset-0 rounded-full animate-ping opacity-20" style={{ background: 'var(--accent)' }}></span>

                {/* Notification badge */}
                <span className="absolute -top-1 -right-1 w-5 h-5 text-[10px] font-black rounded-full flex items-center justify-center shadow-lg" style={{ background: 'var(--terra)', color: 'var(--accent-ink)' }}>
                    3
                </span>
            </button>

            {/* Tooltip */}
            <div
                className={`fixed bottom-8 right-28 px-4 py-2 shadow-2xl transition-all duration-300 z-50 ${isOpen ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4 pointer-events-none'
                    }`}
                style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-900)' }}
            >
                <div className="flex items-center gap-2">
                    <svg className="w-4 h-4" style={{ color: 'var(--accent)' }} fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" />
                    </svg>
                    <div>
                        <p className="text-sm font-bold" style={{ color: 'var(--ink-900)' }}>Secretariat Martin</p>
                        <p className="text-[10px]" style={{ color: 'var(--ink-500)' }}>AI-powered support</p>
                    </div>
                </div>
                {/* Arrow */}
                <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full">
                    <div className="w-0 h-0 border-t-8 border-t-transparent border-b-8 border-b-transparent border-l-8" style={{ borderLeftColor: 'var(--surface)' }}></div>
                </div>
            </div>
        </>
    )
}
