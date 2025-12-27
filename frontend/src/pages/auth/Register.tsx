import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Button, Input } from '../../components/ui'
import { useAppDispatch } from '../../hooks/useRedux'
import { setCredentials, setToken } from '../../store/slices/authSlice'
import { authService } from '../../services/auth'
import { UserRole } from '../../types/auth'

declare global {
    interface Window {
        google: any;
    }
}

export default function Register() {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        organization: '',
        role: 'twg_member'
    })
    const [errors, setErrors] = useState<Record<string, string>>({})
    const [isLoading, setIsLoading] = useState(false)
    const navigate = useNavigate()
    const dispatch = useAppDispatch()

    useEffect(() => {
        // Initialize Google Login
        if (window.google) {
            window.google.accounts.id.initialize({
                client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
                callback: handleGoogleLogin,
            });
            window.google.accounts.id.renderButton(
                document.getElementById("googleSync"),
                { theme: "dark", size: "large", width: "250" }
            );
        }
    }, []);

    const handleGoogleLogin = async (response: any) => {
        setIsLoading(true);
        try {
            const result = await authService.loginWithGoogle(response.credential);

            localStorage.setItem('token', result.access_token);
            dispatch(setToken(result.access_token));

            const user = await authService.getCurrentUser();

            if (user) {
                if (!user.is_active) {
                    navigate('/pending-approval');
                } else {
                    dispatch(setCredentials({
                        user: user,
                        token: result.access_token
                    }));
                    navigate('/dashboard');
                }
            }
        } catch (err: any) {
            console.error('Google login failed', err);
            if (err.response?.status === 403) {
                navigate('/pending-approval');
            } else {
                setErrors(prev => ({ ...prev, general: 'Google authentication failed. Please try again.' }));
            }
        } finally {
            setIsLoading(false);
        }
    };

    const validateForm = () => {
        const newErrors: Record<string, string> = {}

        if (!formData.name.trim()) {
            newErrors.name = 'Full name is required'
        }

        if (!formData.email.trim()) {
            newErrors.email = 'Email is required'
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            newErrors.email = 'Invalid email format'
        }

        if (!formData.password) {
            newErrors.password = 'Password is required'
        } else if (formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters'
        } else {
            // Validate password strength to match backend requirements
            const hasUpperCase = /[A-Z]/.test(formData.password)
            const hasLowerCase = /[a-z]/.test(formData.password)
            const hasDigit = /[0-9]/.test(formData.password)
            const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(formData.password)

            if (!hasUpperCase) {
                newErrors.password = 'Password must contain at least one uppercase letter'
            } else if (!hasLowerCase) {
                newErrors.password = 'Password must contain at least one lowercase letter'
            } else if (!hasDigit) {
                newErrors.password = 'Password must contain at least one digit'
            } else if (!hasSpecialChar) {
                newErrors.password = 'Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)'
            }
        }

        if (formData.password !== formData.confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match'
        }

        if (!formData.organization.trim()) {
            newErrors.organization = 'Organization is required'
        }

        setErrors(newErrors)
        return Object.keys(newErrors).length === 0
    }

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!validateForm()) {
            return
        }

        setIsLoading(true)

        try {
            // Call backend registration
            const response = await authService.register({
                full_name: formData.name,
                email: formData.email,
                password: formData.password,
                organization: formData.organization,
                role: formData.role as UserRole
            });

            // Registration successful!
            // Assuming the backend logs us in automatically (UserWithToken response)
            // If backend returns tokens, we can auto-login
            if (response.access_token) {
                localStorage.setItem('token', response.access_token);

                // Construct user object or fetch it. The backend /register returns UserWithToken
                // which includes the user object.
                if (response.user) {
                    if (!response.user.is_active) {
                        navigate('/pending-approval');
                    } else {
                        dispatch(setCredentials({
                            user: response.user,
                            token: response.access_token
                        }));
                        navigate('/dashboard');
                    }
                } else {
                    navigate('/login');
                }
            } else {
                // If manual verification needed
                navigate('/login');
            }
        } catch (err: any) {
            console.error('Registration error:', err);
            console.error('Error response:', err.response?.data);
            const errorMessage = err.response?.data?.detail || err.response?.data?.message || 'Registration failed. Please try again.';
            setErrors(prev => ({ ...prev, general: errorMessage }));
        } finally {
            setIsLoading(false);
        }
    }

    const handleChange = (field: string, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }))
        // Clear error when user starts typing
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }))
        }
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
                            <radialGradient id="grad2" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
                                <stop offset="0%" style={{ stopColor: '#3b82f6', stopOpacity: 0.6 }} />
                                <stop offset="100%" style={{ stopColor: '#1d4ed8', stopOpacity: 0 }} />
                            </radialGradient>
                        </defs>
                        <circle cx="100" cy="100" r="80" fill="url(#grad2)" />
                        <circle cx="100" cy="100" r="80" stroke="#3b82f6" strokeWidth="0.5" fill="none" />
                        <circle cx="100" cy="100" r="60" stroke="#3b82f6" strokeWidth="0.3" fill="none" opacity="0.5" />
                        <circle cx="100" cy="100" r="40" stroke="#3b82f6" strokeWidth="0.3" fill="none" opacity="0.3" />
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
                        Join the Future of Regional Collaboration
                    </h1>
                    <p className="text-blue-200 text-lg max-w-lg">
                        Create your account to access cutting-edge AI-powered tools for strategic planning and data analysis.
                    </p>
                    <div className="flex gap-2">
                        <div className="w-2 h-2 bg-slate-700 rounded-full"></div>
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <div className="w-2 h-2 bg-slate-700 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Right side - Form */}
            <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-[#020617] overflow-y-auto">
                <div className="w-full max-w-md space-y-8 py-8">
                    <div className="flex justify-end">
                        <div className="flex items-center gap-2 px-3 py-1 bg-slate-800/50 border border-slate-700 rounded-full text-xs text-slate-400">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                            </svg>
                            NEW ACCOUNT
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h2 className="text-3xl font-display font-bold">Create Account</h2>
                        <p className="text-slate-400">Register to access the TWG workspace and collaboration tools.</p>
                    </div>

                    <form onSubmit={handleRegister} className="space-y-5">
                        {errors.general && (
                            <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
                                <p className="text-red-400 text-sm">{errors.general}</p>
                            </div>
                        )}
                        <div className="space-y-4">
                            <Input
                                label="Full Name"
                                type="text"
                                placeholder="John Doe"
                                value={formData.name}
                                onChange={(e) => handleChange('name', e.target.value)}
                                required
                                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:ring-blue-500"
                            />
                            {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name}</p>}

                            <Input
                                label="Official Email"
                                type="email"
                                placeholder="name@ecowas.int"
                                value={formData.email}
                                onChange={(e) => handleChange('email', e.target.value)}
                                required
                                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:ring-blue-500"
                            />
                            {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email}</p>}

                            <Input
                                label="Organization"
                                type="text"
                                placeholder="ECOWAS Commission"
                                value={formData.organization}
                                onChange={(e) => handleChange('organization', e.target.value)}
                                required
                                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:ring-blue-500"
                            />
                            {errors.organization && <p className="text-red-400 text-xs mt-1">{errors.organization}</p>}

                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Role</label>
                                <select
                                    value={formData.role}
                                    onChange={(e) => handleChange('role', e.target.value)}
                                    className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    <option value="twg_member">TWG Member</option>
                                    <option value="twg_facilitator">TWG Facilitator</option>
                                    <option value="secretariat_lead">Secretariat Lead</option>
                                    <option value="admin">Administrator</option>
                                </select>
                            </div>

                            <Input
                                label="Password"
                                type="password"
                                placeholder="••••••••"
                                value={formData.password}
                                onChange={(e) => handleChange('password', e.target.value)}
                                required
                                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:ring-blue-500"
                            />
                            {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password}</p>}

                            <Input
                                label="Confirm Password"
                                type="password"
                                placeholder="••••••••"
                                value={formData.confirmPassword}
                                onChange={(e) => handleChange('confirmPassword', e.target.value)}
                                required
                                className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-600 focus:ring-blue-500"
                            />
                            {errors.confirmPassword && <p className="text-red-400 text-xs mt-1">{errors.confirmPassword}</p>}
                        </div>

                        <Button
                            type="submit"
                            isLoading={isLoading}
                            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2"
                        >
                            Create Account
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </Button>

                        <div className="relative flex items-center gap-4">
                            <div className="flex-1 h-px bg-slate-800"></div>
                            <span className="text-xs text-slate-500 font-medium">OR</span>
                            <div className="flex-1 h-px bg-slate-800"></div>
                        </div>

                        <div id="googleSync" className="w-full flex justify-center"></div>
                    </form>

                    <div className="text-center">
                        <p className="text-sm text-slate-400">
                            Already have an account?{' '}
                            <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">
                                Log In
                            </Link>
                        </p>
                    </div>

                    <div className="pt-6 border-t border-slate-800 text-center">
                        <p className="text-xs text-slate-500">
                            ECOWAS Summit © 2024. Authorized Personnel Only.
                        </p>
                        <p className="text-xs text-slate-600 mt-1">
                            By creating an account, you agree to our Terms of Service and Privacy Policy.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
