import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/auth'

export default function RequireAuth() {
  const { user, setAuth } = useAuthStore()
  const [checking, setChecking] = useState(!user)

  useEffect(() => {
    if (user) return
    authApi
      .refresh()
      .then((data) =>
        setAuth({ username: data.username, role: data.role }, data.access_token)
      )
      .catch(() => {
        // No valid refresh cookie — will redirect to /login
      })
      .finally(() => setChecking(false))
  }, [])

  if (checking) {
    return (
      <div className="min-h-screen bg-surface-950 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
