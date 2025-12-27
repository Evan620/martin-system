import { Link } from 'react-router-dom'
import { Card, Button } from '../../components/ui'

export default function PendingApproval() {
    return (
        <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6">
            <div className="w-full max-w-md">
                <Card className="border-slate-800 bg-slate-900/50 p-8 text-center space-y-6">
                    <div className="w-20 h-20 bg-blue-600/10 rounded-full flex items-center justify-center mx-auto">
                        <svg className="w-10 h-10 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>

                    <div className="space-y-2">
                        <h1 className="text-2xl font-bold text-white">Application Pending</h1>
                        <p className="text-slate-400">
                            Your account has been successfully created and is currently awaiting administrator approval.
                        </p>
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-lg text-sm text-slate-300 text-left">
                        <p className="font-semibold mb-1 text-white">What happens next?</p>
                        <ul className="list-disc list-inside space-y-1">
                            <li>An administrator will review your request.</li>
                            <li>They will assign your organizational role.</li>
                            <li>You will receive access once the review is complete.</li>
                        </ul>
                    </div>

                    <div className="pt-4">
                        <Link to="/login">
                            <Button className="w-full" variant="outline">
                                Back to Login
                            </Button>
                        </Link>
                    </div>
                </Card>

                <p className="mt-8 text-center text-xs text-slate-600">
                    ECOWAS Summit © 2024. Authorized Personnel Only.
                </p>
            </div>
        </div>
    )
}
