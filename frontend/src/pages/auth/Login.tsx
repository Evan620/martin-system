import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Button, Input } from '../../components/ui'
import { useAppDispatch } from '../../hooks/useRedux'
import { setCredentials, setToken, setError } from '../../store/slices/authSlice'
import { authService } from '../../services/auth'

declare global {
    interface Window {
        google: any;
    }
}

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [loginError, setLoginError] = useState<string | null>(null)
    const navigate = useNavigate()
    const dispatch = useAppDispatch()

    const handleGoogleLogin = useCallback(async (response: any) => {
        setIsLoading(true);
        setLoginError(null);
        try {
            const result = await authService.loginWithGoogle(response.credential);

            localStorage.setItem('token', result.access_token);
            if (result.refresh_token) {
                localStorage.setItem('refresh_token', result.refresh_token)
            }
            dispatch(setToken(result.access_token));

            const user = await authService.getCurrentUser();
            dispatch(setCredentials({
                user: user,
                token: result.access_token
            }));

            navigate('/dashboard');
        } catch (err: any) {
            console.error('Google login failed', err);
            // Admin approval disabled - show error instead
            setLoginError('Google authentication failed. Please try again.');
        } finally {
            setIsLoading(false);
        }
    }, [dispatch, navigate]);

    useEffect(() => {
        // Function to attempt initialization
        const initializeGoogle = () => {
            if (window.google?.accounts?.id && document.getElementById("googleSync")) {
                try {
                    window.google.accounts.id.initialize({
                        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
                        callback: handleGoogleLogin,
                    });

                    window.google.accounts.id.renderButton(
                        document.getElementById("googleSync"),
                        { theme: "dark", size: "large", width: "250" }
                    );
                    return true;
                } catch (error) {
                    console.error("[ERROR] Google Sign-In Initialization Error:", error);
                    return false;
                }
            }
            return false;
        };

        // Check immediately
        if (!initializeGoogle()) {
            // Set up polling interval
            const intervalId = setInterval(() => {
                if (initializeGoogle()) {
                    clearInterval(intervalId);
                }
            }, 100);

            // Safety timeout after 10 seconds
            const timeoutId = setTimeout(() => {
                clearInterval(intervalId);
            }, 10000);

            return () => {
                clearInterval(intervalId);
                clearTimeout(timeoutId);
            };
        }
    }, [handleGoogleLogin]);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setLoginError(null)

        try {
            // Call backend login
            const response = await authService.login({ email, password })

            // Expected response: { access_token, refresh_token, token_type }
            // We need to fetch the user profile next, or if the backend returns it with login
            // Assuming we need to fetch user profile separately or backend returns it.
            // Let's check auth.py: login returns only tokens.
            // So we need to fetch /auth/me after login.

            // Store tokens — access token for requests, refresh token for silent renewal
            localStorage.setItem('token', response.access_token)
            if (response.refresh_token) {
                localStorage.setItem('refresh_token', response.refresh_token)
            }

            // Dispatch token to store so api interceptor can use it for subsequent calls
            dispatch(setToken(response.access_token))

            // Fetch current user
            const user = await authService.getCurrentUser()

            dispatch(setCredentials({
                user: user,
                token: response.access_token
            }))

            navigate('/dashboard')
        } catch (err: any) {
            console.error('Login failed', err)
            // Admin approval disabled - show error message directly
            const errorMessage = err.response?.data?.detail || 'Invalid email or password. Please try again.'
            setLoginError(errorMessage)
            dispatch(setError(errorMessage))
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="flex h-screen bg-slate-50 text-slate-900">
            {/* Left side - Visuals */}
            <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-primary">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent"></div>

                {/* Abstract Globe/Network visualization placeholder */}
                <div className="absolute inset-0 flex items-center justify-center opacity-40">
                    <svg className="w-full h-full p-20" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <radialGradient id="grad1" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                                <stop offset="0%" style={{ stopColor: '#ffffff', stopOpacity: 0.5 }} />
                                <stop offset="100%" style={{ stopColor: '#ffffff', stopOpacity: 0 }} />
                            </radialGradient>
                        </defs>
                        <circle cx="100" cy="100" r="80" fill="url(#grad1)" />
                        <circle cx="100" cy="100" r="80" stroke="#ffffff" strokeWidth="0.5" fill="none" />
                        <path d="M20 100 Q 100 20 180 100" stroke="#ffffff" strokeWidth="0.2" fill="none" />
                        <path d="M20 100 Q 100 180 180 100" stroke="#ffffff" strokeWidth="0.2" fill="none" />
                        <path d="M100 20 Q 20 100 100 180" stroke="#ffffff" strokeWidth="0.2" fill="none" />
                        <path d="M100 20 Q 180 100 100 180" stroke="#ffffff" strokeWidth="0.2" fill="none" />
                    </svg>
                </div>

                <div className="relative z-10 flex flex-col justify-end p-16 space-y-6 text-white">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white/10 backdrop-blur-sm rounded-lg flex items-center justify-center border border-white/20">
                            <span className="font-bold text-lg">E</span>
                        </div>
                        <span className="text-xl font-display font-semibold">ECOWAS SUMMIT TWG</span>
                    </div>
                    <h1 className="text-5xl font-display font-bold leading-tight">
                        Empowering Regional Cooperation through AI-Driven Insights
                    </h1>
                    <p className="text-blue-100 text-lg max-w-lg">
                        Welcome to the Technical Working Group Support System. Securely access real-time data analysis and strategic planning tools.
                    </p>
                    <div className="flex gap-2">
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                        <div className="w-2 h-2 bg-white/50 rounded-full"></div>
                        <div className="w-2 h-2 bg-white/50 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Right side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white">
                <div className="w-full max-w-md space-y-8">
                    <div className="flex justify-end">
                        <div className="flex items-center gap-2 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full text-xs text-slate-500 font-medium">
                            <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 00-2 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                            SECURE ACCESS
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold text-slate-900">Log In</h2>
                        <p className="text-slate-500">Enter your official credentials to access the TWG workspace.</p>
                    </div>

                    {loginError && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                            {loginError}
                        </div>
                    )}

                    <form onSubmit={handleLogin} className="space-y-6">
                        <div className="space-y-4">
                            <Input
                                label="Official Email"
                                type="email"
                                placeholder="name@ecowas.int"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:ring-primary focus:border-primary"
                            />
                            <div className="space-y-1">
                                <Input
                                    label="Password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:ring-primary focus:border-primary"
                                />
                                <div className="flex justify-end">
                                    <Link to="/forgot-password" className="text-sm text-slate-500 hover:text-primary transition-colors">
                                        Forgot Password?
                                    </Link>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <Button
                                type="submit"
                                isLoading={isLoading}
                                className="w-full py-3 bg-primary hover:bg-blue-800 text-white font-semibold rounded-lg shadow-lg shadow-blue-900/10 flex items-center justify-center gap-2"
                            >
                                Access Dashboard
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                </svg>
                            </Button>

                            <div className="relative flex items-center gap-4">
                                <div className="flex-1 h-px bg-slate-200"></div>
                                <span className="text-xs text-slate-500 font-medium">OR</span>
                                <div className="flex-1 h-px bg-slate-200"></div>
                            </div>

                            <div id="googleSync" className="w-full flex justify-center"></div>
                        </div>
                    </form>

                    <div className="pt-8 border-t border-slate-100 text-center">
                        <p className="text-xs text-slate-400">
                            ECOWAS Summit © 2026. Authorized Personnel Only.
                        </p>
                        <p className="text-xs text-slate-400 mt-1">
                            By logging in, you agree to our Terms of Service and Privacy Policy.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
