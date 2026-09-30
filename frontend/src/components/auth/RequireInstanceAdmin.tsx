import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

// The backend rejects these calls regardless — this just avoids a
// non-admin briefly seeing the page shell before the API calls 403.
export default function RequireInstanceAdmin() {
  const isInstanceAdmin = useAuthStore((s) => s.isInstanceAdmin())
  if (!isInstanceAdmin) return <Navigate to="/" replace />
  return <Outlet />
}
