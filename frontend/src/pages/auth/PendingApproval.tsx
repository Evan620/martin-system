import { Link } from 'react-router-dom'
import { Card, Button } from '../../components/ui'

export default function PendingApproval() {
    return (
        <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--bg)' }}>
            <div className="w-full max-w-md animate-blur-slide">
                <Card className="p-8 text-center space-y-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)' }}>
                    <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto" style={{ background: 'var(--accent-soft)' }}>
                        <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: 'var(--accent)' }}>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>

                    <div className="space-y-2">
                        <h1 className="text-2xl font-bold" style={{ color: 'var(--ink-900)' }}>Application Pending</h1>
                        <p style={{ color: 'var(--ink-600)' }}>
                            Your account has been successfully created and is currently awaiting administrator approval.
                        </p>
                    </div>

                    <div className="p-4 text-sm text-left" style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-ctl)', color: 'var(--ink-700)' }}>
                        <p className="font-semibold mb-1" style={{ color: 'var(--ink-900)' }}>What happens next?</p>
                        <ul className="list-disc list-inside space-y-1">
                            <li>An administrator will review your request.</li>
                            <li>They will assign your organizational role.</li>
                            <li>You will receive access once the review is complete.</li>
                        </ul>
                    </div>

                    <div className="pt-4">
                        <Link to="/login">
                            <Button className="clickable-scale w-full" variant="outline">
                                Back to Login
                            </Button>
                        </Link>
                    </div>
                </Card>

                <p className="mt-8 text-center text-xs" style={{ color: 'var(--ink-400)' }}>
                    WAIIS © 2026. Authorized Personnel Only.
                </p>
            </div>
        </div>
    )
}
