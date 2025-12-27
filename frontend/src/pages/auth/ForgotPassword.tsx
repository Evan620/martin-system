import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Input } from '../../components/ui'

export default function ForgotPassword() {
    const [email, setEmail] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)

        // Simulate API call
        setTimeout(() => {
            setIsLoading(false)
            setIsSubmitted(true)
        }, 1500)
    }

    if (isSubmitted) {
        return (
            <div className="flex h-screen bg-[#020617] text-white items-center justify-center p-8">
                <div className="w-full max-w-md space-y-8 text-center">
                    <div className="flex justify-center">
                        <div className="w-16 h-16 bg-green-600/20 rounded-full flex items-center justify-center">
                            <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold">Check Your Email</h2>
                        <p className="text-slate-400">
                            We've sent password reset instructions to <span className="text-white font-medium">{email}</span>
                        </p>
                    </div>

                    <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-4 text-sm text-slate-300">
                        <p>Didn't receive the email? Check your spam folder or</p>
                        <button
                            onClick={() => setIsSubmitted(false)}
                            className="text-blue-400 hover:text-blue-300 font-medium mt-1"
                        >
                            try another email address
                        </button>
                    </div>

                    <Link
                        to="/login"
                        className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Login
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="flex h-screen bg-[#020617] text-white">
            {/* Left side - Visuals */}
            <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-blue-950 via-slate-900 to-slate-950">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-500/20 via-transparent to-transparent"></div>

                {/* Abstract visualization */}
                <div className="absolute inset-0 flex items-center justify-center opacity-30">
                    <svg className="w-full h-full p-20" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <radialGradient id="grad3" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                                <stop offset="0%" style={{ stopColor: '#3b82f6', stopOpacity: 0.6 }} />
                                <stop offset="100%" style={{ stopColor: '#1d4ed8', stopOpacity: 0 }} />
                            </radialGradient>
                        </defs>
                        <circle cx="100" cy="100" r="80" fill="url(#grad3)" />
                        <path d="M100 40 L100 160" stroke="#3b82f6" strokeWidth="0.5" />
                        <path d="M40 100 L160 100" stroke="#3b82f6" strokeWidth="0.5" />
                        <circle cx="100" cy="100" r="50" stroke="#3b82f6" strokeWidth="0.3" fill="none" opacity="0.5" />
                    </svg>
                </div>

                <div className="relative z-10 flex flex-col justify-end p-16 space-y-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                            <span className="font-bold text-lg">E</span>
                        </div>
                        <span className="text-xl font-display font-semibold">ECOWAS SUMMIT TWG</span>
                    </div>
                    <h1 className="text-5xl font-display font-bold leading-tight">
                        Secure Account Recovery
                    </h1>
                    <p className="text-blue-200 text-lg max-w-lg">
                        We'll help you regain access to your account securely. Enter your email to receive reset instructions.
                    </p>
                    <div className="flex gap-2">
                        <div className="w-2 h-2 bg-slate-700 rounded-full"></div>
                        <div className="w-2 h-2 bg-slate-700 rounded-full"></div>
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Right side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-[#020617]">
                <div className="w-full max-w-md space-y-8">
                    <div className="flex justify-end">
                        <div className="flex items-center gap-2 px-3 py-1 bg-slate-800/50 border border-slate-700 rounded-full text-xs text-slate-400">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            PASSWORD RESET
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold">Forgot Password?</h2>
                        <p className="text-slate-400">No worries! Enter your email and we'll send you reset instructions.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <Input
                            label="Official Email"
                            type="email"
                            placeholder="name@ecowas.int"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:ring-blue-500"
                        />

                        <Button
                            type="submit"
                            isLoading={isLoading}
                            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2"
                        >
                            Send Reset Instructions
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </Button>
                    </form>

                    <div className="text-center">
                        <Link
                            to="/login"
                            className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Login
                        </Link>
                    </div>

                    <div className="pt-8 border-t border-slate-800 text-center">
                        <p className="text-xs text-slate-500">
                            ECOWAS Summit © 2024. Authorized Personnel Only.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
