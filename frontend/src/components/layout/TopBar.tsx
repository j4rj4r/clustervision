import { Server } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useClusterInfo, useClusters } from '../../hooks/useCluster'
import { useClusterStore } from '../../store/clusterStore'

const routeLabels: Record<string, string> = {
  '/users':      'Users',
  '/rbac':       'Permissions',
  '/kubeconfig': 'Kubeconfig',
  '/tokens':     'History',
  '/clusters':   'Clusters',
}

export default function TopBar() {
  const { pathname } = useLocation()
  const { data, isError, isLoading } = useClusterInfo()
  const { data: clusters = [] } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()

  const pageLabel = routeLabels[pathname] ?? 'ClusterVision'

  return (
    <header className="h-13 bg-surface-900/80 backdrop-blur-sm border-b border-surface-700/40 shadow-[0_1px_0_rgba(0,0,0,0.2)] flex items-center px-6 gap-4">
      <span className="text-sm font-semibold text-surface-100 tracking-tight">{pageLabel}</span>

      <div className="flex-1" />

      <div className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border transition-all ${
        isError
          ? 'bg-red-950/20 border-red-800/40 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]'
          : 'bg-surface-800/60 border-surface-600/60 hover:border-surface-500/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]'
      }`}>
        <Server size={12} className="text-surface-400 shrink-0" />

        {clusters.length > 1 ? (
          <select
            aria-label="Active cluster"
            value={activeCluster}
            onChange={(e) => setActiveCluster(e.target.value)}
            className="bg-transparent text-xs text-surface-300 font-mono cursor-pointer focus:outline-none"
          >
            {clusters.map((c) => (
              <option key={c.name} value={c.name} className="bg-surface-800">{c.name}</option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-surface-300 font-mono">{activeCluster}</span>
        )}

        <span className="w-px h-3 bg-surface-700 mx-0.5" />

        {isLoading ? (
          <span className="text-xs text-surface-500">—</span>
        ) : isError ? (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
            <span className="text-xs text-red-400">Unreachable</span>
          </>
        ) : (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 animate-pulse" />
            <span className="text-xs text-emerald-400">Connected</span>
            {data?.git_version && (
              <span className="text-xs text-surface-500 font-mono">{data.git_version}</span>
            )}
          </>
        )}
      </div>
    </header>
  )
}
