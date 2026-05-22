import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAppDispatch } from '../../hooks/useRedux'
import { setCredentials, setToken, setError } from '../../store/slices/authSlice'
import { authService } from '../../services/auth'

declare global {
    interface Window { google: any }
}

const f = "'Geist', 'Inter', system-ui, sans-serif"
const serif = "'Source Serif 4', Georgia, serif"
const mono = "'Geist Mono', monospace"

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [loginError, setLoginError] = useState<string | null>(null)
    const [focused, setFocused] = useState<string | null>(null)
    const navigate = useNavigate()
    const dispatch = useAppDispatch()

    const handleGoogleLogin = useCallback(async (response: any) => {
        setIsLoading(true)
        setLoginError(null)
        try {
            const result = await authService.loginWithGoogle(response.credential)
            localStorage.setItem('token', result.access_token)
            if (result.refresh_token) localStorage.setItem('refresh_token', result.refresh_token)
            dispatch(setToken(result.access_token))
            const user = await authService.getCurrentUser()
            dispatch(setCredentials({ user, token: result.access_token }))
            navigate('/dashboard')
        } catch {
            setLoginError('Google authentication failed. Please try again.')
        } finally {
            setIsLoading(false)
        }
    }, [dispatch, navigate])

    useEffect(() => {
        const init = () => {
            if (window.google?.accounts?.id && document.getElementById('googleSync')) {
                try {
                    window.google.accounts.id.initialize({
                        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
                        callback: handleGoogleLogin,
                    })
                    window.google.accounts.id.renderButton(
                        document.getElementById('googleSync'),
                        { theme: 'outline', size: 'large', width: '320' }
                    )
                    return true
                } catch { return false }
            }
            return false
        }
        if (!init()) {
            const id = setInterval(() => { if (init()) clearInterval(id) }, 100)
            const tid = setTimeout(() => clearInterval(id), 10000)
            return () => { clearInterval(id); clearTimeout(tid) }
        }
    }, [handleGoogleLogin])

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setLoginError(null)
        try {
            const response = await authService.login({ email, password })
            localStorage.setItem('token', response.access_token)
            if (response.refresh_token) localStorage.setItem('refresh_token', response.refresh_token)
            dispatch(setToken(response.access_token))
            const user = await authService.getCurrentUser()
            dispatch(setCredentials({ user, token: response.access_token }))
            navigate('/dashboard')
        } catch (err: any) {
            const msg = err.response?.data?.detail || 'Invalid email or password.'
            setLoginError(msg)
            dispatch(setError(msg))
        } finally {
            setIsLoading(false)
        }
    }

    const inputStyle = (name: string): React.CSSProperties => ({
        width: '100%',
        padding: '10px 12px',
        fontFamily: f,
        fontSize: 14,
        color: 'var(--ink-900)',
        background: 'var(--surface)',
        border: `1px solid ${focused === name ? 'var(--accent)' : 'var(--border)'}`,
        outline: 'none',
        boxSizing: 'border-box',
        transition: 'border-color 0.15s',
    })

    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--bg)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '40px 16px',
            fontFamily: f,
        }}>
            {/* Wordmark — above the card */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }}>
                <div style={{
                    width: 32, height: 32,
                    border: '1.5px solid var(--accent)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                }}>
                    <span style={{ color: 'var(--accent)', fontFamily: serif, fontSize: 15, fontWeight: 600 }}>E</span>
                </div>
                <div>
                    <div style={{ fontFamily: mono, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-800)', lineHeight: 1.2 }}>
                        ECOWAS Summit
                    </div>
                    <div style={{ fontFamily: mono, fontSize: 9, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-400)' }}>
                        TWG Platform
                    </div>
                </div>
            </div>

            {/* Card */}
            <div style={{
                width: '100%',
                maxWidth: 400,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
                padding: '36px 36px 28px',
            }}>
                {/* Heading */}
                <h1 style={{
                    fontFamily: serif,
                    fontSize: 26,
                    fontWeight: 600,
                    color: 'var(--ink-900)',
                    letterSpacing: '-0.01em',
                    lineHeight: 1.2,
                    marginBottom: 6,
                }}>
                    Sign in to your account
                </h1>
                <p style={{ fontFamily: f, fontSize: 13, color: 'var(--ink-500)', marginBottom: 28, lineHeight: 1.5 }}>
                    Use your official ECOWAS credentials.
                </p>

                {/* Error */}
                {loginError && (
                    <div style={{
                        padding: '9px 12px',
                        background: 'rgba(185,28,28,0.06)',
                        border: '1px solid rgba(185,28,28,0.18)',
                        marginBottom: 20,
                        fontFamily: f,
                        fontSize: 13,
                        color: 'var(--terra)',
                        lineHeight: 1.5,
                    }}>
                        {loginError}
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleLogin}>
                    <div style={{ marginBottom: 14 }}>
                        <label style={{ display: 'block', fontFamily: mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 5 }}>
                            Email Address
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            onFocus={() => setFocused('email')}
                            onBlur={() => setFocused(null)}
                            placeholder="name@ecowas.int"
                            required
                            style={inputStyle('email')}
                        />
                    </div>

                    <div style={{ marginBottom: 6 }}>
                        <label style={{ display: 'block', fontFamily: mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-500)', marginBottom: 5 }}>
                            Password
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            onFocus={() => setFocused('password')}
                            onBlur={() => setFocused(null)}
                            placeholder="••••••••"
                            required
                            style={inputStyle('password')}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 22 }}>
                        <Link
                            to="/forgot-password"
                            style={{ fontFamily: f, fontSize: 12, color: 'var(--ink-400)', textDecoration: 'none', transition: 'color 0.15s' }}
                            onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')}
                            onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-400)')}
                        >
                            Forgot password?
                        </Link>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        style={{
                            width: '100%',
                            padding: '10px 16px',
                            background: isLoading ? 'var(--ink-300)' : 'var(--accent)',
                            color: 'white',
                            border: 'none',
                            cursor: isLoading ? 'not-allowed' : 'pointer',
                            fontFamily: f,
                            fontSize: 14,
                            fontWeight: 500,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 8,
                            transition: 'opacity 0.15s',
                            marginBottom: 20,
                        }}
                        onMouseEnter={e => { if (!isLoading) e.currentTarget.style.opacity = '0.88' }}
                        onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
                    >
                        {isLoading ? (
                            <>
                                <div style={{ width: 13, height: 13, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                                Signing in…
                            </>
                        ) : 'Log in'}
                    </button>

                    {/* OR divider */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                        <span style={{ fontFamily: mono, fontSize: 9, color: 'var(--ink-400)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>or</span>
                        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
                    </div>

                    <div id="googleSync" style={{ display: 'flex', justifyContent: 'center' }} />
                </form>
            </div>

            {/* Footer */}
            <div style={{ marginTop: 28, textAlign: 'center' }}>
                <p style={{ fontFamily: mono, fontSize: 9, color: 'var(--ink-400)', letterSpacing: '0.06em', textTransform: 'uppercase', lineHeight: 2 }}>
                    ECOWAS Summit © 2026 · Authorized Personnel Only
                </p>
            </div>

            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
                input::placeholder { color: var(--ink-300); font-family: ${f}; }
            `}</style>
        </div>
    )
}
