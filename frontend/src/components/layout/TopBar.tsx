import { Server, LogOut } from 'lucide-react'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useClusterInfo, useClusters } from '../../hooks/useCluster'
import { useClusterStore } from '../../store/clusterStore'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/auth'
import Modal from '../ui/Modal'
import Button from '../ui/Button'

const routeLabels: Record<string, string> = {
  '/users':      'Users',
  '/rbac':       'Permissions',
  '/kubeconfig': 'Kubeconfig',
  '/tokens':     'History',
  '/clusters':   'Clusters',
}

export default function TopBar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { data, isError, isLoading } = useClusterInfo()
  const { data: clusters = [] } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()
  const { user, clearAuth } = useAuthStore()
  const [confirmLogout, setConfirmLogout] = useState(false)

  const pageLabel = routeLabels[pathname] ?? 'ClusterVision'

  const handleLogout = async () => {
    await authApi.logout().catch(() => undefined)
    clearAuth()
    navigate('/login', { replace: true })
  }

  return (
    <header className="h-14 bg-surface-900 border-b border-surface-600 flex items-center px-6 gap-4">
      <span className="text-sm font-semibold text-surface-100">{pageLabel}</span>

      <div className="flex-1" />

      {/* Cluster pill */}
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
        isError
          ? 'bg-red-950/30 border-red-800/50'
          : 'bg-surface-800 border-surface-500 hover:border-brand-500/60'
      }`}>
        <Server size={13} className="text-surface-300 shrink-0" />

        {clusters.length > 1 ? (
          <select
            aria-label="Active cluster"
            value={activeCluster}
            onChange={(e) => setActiveCluster(e.target.value)}
            className="bg-transparent text-xs text-surface-200 font-mono cursor-pointer focus:outline-none"
          >
            {clusters.map((c) => (
              <option key={c.name} value={c.name} className="bg-surface-800">{c.name}</option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-surface-200 font-mono">{activeCluster}</span>
        )}

        <span className="w-px h-3 bg-surface-600 mx-0.5" />

        {isLoading ? (
          <span className="text-xs text-surface-400">...</span>
        ) : isError ? (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
            <span className="text-xs text-red-300">Unreachable</span>
          </>
        ) : (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
            <span className="text-xs text-emerald-300">Connected</span>
            {data?.git_version && (
              <span className="text-xs text-surface-400 font-mono">{data.git_version}</span>
            )}
          </>
        )}
      </div>

      {/* User badge + logout */}
      {user && (
        <>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface-800 border border-surface-600">
              <span className="text-xs text-surface-300 font-mono">{user.username}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                user.role === 'admin'
                  ? 'bg-brand-600/20 text-brand-400'
                  : 'bg-surface-700 text-surface-400'
              }`}>
                {user.role}
              </span>
            </div>
            <button
              onClick={() => setConfirmLogout(true)}
              title="Sign out"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-surface-400 hover:text-surface-200 hover:bg-surface-800 border border-transparent hover:border-surface-600 transition-all text-xs"
            >
              <LogOut size={14} />
              <span>Sign out</span>
            </button>
          </div>

          <Modal open={confirmLogout} onClose={() => setConfirmLogout(false)} title="Sign out" size="sm">
            <p className="text-sm text-surface-300 mb-6">
              Sign out of <span className="font-mono text-surface-100">{user.username}</span>?
            </p>
            <div className="flex gap-3">
              <Button variant="secondary" size="sm" className="flex-1" onClick={() => setConfirmLogout(false)}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" className="flex-1" onClick={handleLogout}>
                <LogOut size={13} /> Sign out
              </Button>
            </div>
          </Modal>
        </>
      )}
    </header>
  )
}
