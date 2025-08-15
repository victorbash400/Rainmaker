import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '@/store/authStore'
import { apiPost } from '@/lib/api'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function Login() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    setError('')

    try {
      const response = await apiPost<{
        access_token: string
        token_type: string
        expires_in: number
      }>('/api/v1/auth/login', data)

      // For demo purposes, create a mock user
      const mockUser = {
        id: 1,
        email: data.email,
        name: 'Demo User',
        role: 'admin',
      }

      login(mockUser, response.access_token)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.message || 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="bg-white/20 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-white/40">
        <h2 className="text-2xl font-light text-center text-slate-800 mb-8">Welcome back</h2>

        <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
          {error && (
            <div className="rounded-lg bg-red-500/20 backdrop-blur-sm border-l-4 border-red-600 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
              Email address
            </label>
            <input
              {...register('email')}
              type="email"
              autoComplete="email"
              className="w-full px-4 py-3 rounded-xl border border-slate-300/50 bg-white/30 backdrop-blur-sm focus:outline-none focus:border-slate-500 focus:bg-white/40 transition-all duration-200 text-slate-800 placeholder-slate-500"
              placeholder="Enter your email"
            />
            {errors.email && (
              <p className="mt-2 text-sm text-red-700">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
              Password
            </label>
            <input
              {...register('password')}
              type="password"
              autoComplete="current-password"
              className="w-full px-4 py-3 rounded-xl border border-slate-300/50 bg-white/30 backdrop-blur-sm focus:outline-none focus:border-slate-500 focus:bg-white/40 transition-all duration-200 text-slate-800 placeholder-slate-500"
              placeholder="Enter your password"
            />
            {errors.password && (
              <p className="mt-2 text-sm text-red-700">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-slate-800/80 hover:bg-slate-900/80 backdrop-blur-sm text-white font-medium py-3 px-4 rounded-xl transition-all duration-200 border border-slate-600/50 hover:border-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="mt-8 text-center">
          <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3 border border-slate-300/50">
            <p className="text-sm text-slate-700 font-medium mb-1">Demo credentials:</p>
            <p className="text-sm text-slate-600 font-mono">admin@rainmaker.com / password</p>
          </div>
        </div>
      </div>
    </div>
  )
}