import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Input } from '../../components/ui'
import { authService } from '../../services/auth'

export default function ForgotPassword() {
    const [email, setEmail] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setError('')

        try {
            await authService.forgotPassword(email)
            setIsSubmitted(true)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to send reset email. Please try again.')
        } finally {
            setIsLoading(false)
        }
    }

    if (isSubmitted) {
        return (
            <div className="flex h-screen items-center justify-center p-8" style={{ background: 'var(--bg)', color: 'var(--ink-900)' }}>
                <div className="w-full max-w-md space-y-8 text-center animate-blur-slide">
                    <div className="flex justify-center">
                        <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'var(--accent-soft)' }}>
                            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: 'var(--accent)' }}>
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>Check Your Email</h2>
                        <p style={{ color: 'var(--ink-500)' }}>
                            We've sent password reset instructions to <span className="font-medium" style={{ color: 'var(--ink-900)' }}>{email}</span>
                        </p>
                    </div>

                    <div className="p-4 text-sm" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-card)', color: 'var(--ink-600)' }}>
                        <p>Didn't receive the email? Check your spam folder or</p>
                        <button
                            onClick={() => setIsSubmitted(false)}
                            className="font-medium mt-1"
                            style={{ color: 'var(--accent)' }}
                        >
                            try another email address
                        </button>
                    </div>

                    <Link
                        to="/login"
                        className="inline-flex items-center gap-2 transition-colors"
                        style={{ color: 'var(--ink-500)' }}
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
        <div className="flex h-screen" style={{ background: 'var(--bg)', color: 'var(--ink-900)' }}>
            {/* Left side - Visuals */}
            <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden" style={{ background: 'var(--accent)' }}>
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent"></div>

                {/* Abstract visualization */}
                <div className="absolute inset-0 flex items-center justify-center opacity-30">
                    <svg className="w-full h-full p-20" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <radialGradient id="grad3" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                                <stop offset="0%" style={{ stopColor: '#ffffff', stopOpacity: 0.6 }} />
                                <stop offset="100%" style={{ stopColor: '#ffffff', stopOpacity: 0 }} />
                            </radialGradient>
                        </defs>
                        <circle cx="100" cy="100" r="80" fill="url(#grad3)" />
                        <path d="M100 40 L100 160" stroke="#ffffff" strokeWidth="0.5" />
                        <path d="M40 100 L160 100" stroke="#ffffff" strokeWidth="0.5" />
                        <circle cx="100" cy="100" r="50" stroke="#ffffff" strokeWidth="0.3" fill="none" opacity="0.5" />
                    </svg>
                </div>

                <div className="relative z-10 flex flex-col justify-end p-16 space-y-6" style={{ color: 'var(--accent-ink)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.14)', border: '1px solid rgba(255,255,255,0.18)' }}>
                            <span className="font-bold text-lg">W</span>
                        </div>
                        <span className="text-xl font-display font-semibold">WAIIS TWG</span>
                    </div>
                    <h1 className="text-5xl font-display font-bold leading-tight">
                        Secure Account Recovery
                    </h1>
                    <p className="text-lg max-w-lg" style={{ color: 'rgba(255,255,255,0.82)' }}>
                        We'll help you regain access to your account securely. Enter your email to receive reset instructions.
                    </p>
                    <div className="flex gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.4)' }}></div>
                        <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.4)' }}></div>
                        <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.9)' }}></div>
                    </div>
                </div>
            </div>

            {/* Right side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8" style={{ background: 'var(--surface)' }}>
                <div className="w-full max-w-md space-y-8 animate-blur-slide">
                    <div className="flex justify-end">
                        <div className="qp-eyebrow flex items-center gap-2 px-3 py-1 rounded-full" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            PASSWORD RESET
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold" style={{ color: 'var(--ink-900)' }}>Forgot Password?</h2>
                        <p style={{ color: 'var(--ink-500)' }}>No worries! Enter your email and we'll send you reset instructions.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <Input
                            label="Official Email"
                            type="email"
                            placeholder="name@ecowas.int"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />

                        {error && (
                            <div className="px-4 py-3 text-sm" style={{ background: 'var(--surface-2)', border: '1px solid color-mix(in srgb, var(--terra) 35%, var(--border))', color: 'var(--terra)', borderRadius: 'var(--radius-ctl)' }}>
                                {error}
                            </div>
                        )}

                        <Button
                            type="submit"
                            isLoading={isLoading}
                            className="clickable-scale w-full py-3 font-semibold flex items-center justify-center gap-2"
                            style={{ background: 'var(--accent)', color: 'var(--accent-ink)', borderRadius: 'var(--radius-ctl)' }}
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
                            className="inline-flex items-center gap-2 text-slate-500 hover:text-primary transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Login
                        </Link>
                    </div>

                    <div className="pt-8 border-t border-slate-100 text-center">
                        <p className="text-xs text-slate-400">
                            WAIIS © 2026. Authorized Personnel Only.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
