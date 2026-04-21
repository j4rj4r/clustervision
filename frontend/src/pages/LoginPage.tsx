import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogIn } from 'lucide-react'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authApi.login(username, password)
      setAuth({ username: data.username, role: data.role }, data.access_token)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : ''
      if (msg === 'Invalid credentials') {
        setError('Incorrect username or password.')
      } else if (!username || !password) {
        setError('Please fill in all fields.')
      } else {
        setError('Sign in failed — please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-9 h-9 rounded-xl bg-brand-600/20 ring-1 ring-brand-500/40 flex items-center justify-center">
            <span className="text-brand-400 text-xs font-bold tracking-tight">CV</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-surface-100 tracking-tight">ClusterVision</p>
            <p className="text-xs text-surface-500">Kubernetes RBAC management</p>
          </div>
        </div>

        <div className="bg-surface-900 border border-surface-700/60 rounded-xl p-6 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <h1 className="text-base font-semibold text-surface-100 mb-5">Sign in</h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />

            {error && (
              <p className="text-xs text-red-400 bg-red-950/30 border border-red-800/40 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full" loading={loading}>
              <LogIn size={14} /> Sign in
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
