import { Server } from 'lucide-react'
import { useClusterInfo, useClusters } from '../../hooks/useCluster'
import { useClusterStore } from '../../store/clusterStore'

export default function TopBar() {
  const { data, isError, isLoading } = useClusterInfo()
  const { data: clusters = [] } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()

  return (
    <header className="h-12 bg-slate-900 border-b border-slate-800 flex items-center px-6">
      <div className="flex-1" />

      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors ${
        isError
          ? 'bg-red-950/30 border-red-800/50'
          : 'bg-slate-800 border-slate-700 hover:border-slate-600'
      }`}>
        <Server size={13} className={isError ? 'text-red-400' : 'text-brand-400'} />

        {clusters.length > 1 ? (
          <select
            aria-label="Active cluster"
            value={activeCluster}
            onChange={(e) => setActiveCluster(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-mono cursor-pointer focus:outline-none"
          >
            {clusters.map((c) => (
              <option key={c.name} value={c.name} className="bg-slate-800">{c.name}</option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-slate-200 font-mono">{activeCluster}</span>
        )}

        <span className="w-px h-3 bg-slate-700 mx-0.5" />

        {isLoading ? (
          <span className="text-xs text-slate-500">...</span>
        ) : isError ? (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
            <span className="text-xs text-red-400">Unreachable</span>
          </>
        ) : (
          <>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span className="text-xs text-emerald-400">Connected</span>
            {data?.git_version && (
              <span className="text-xs text-slate-500 font-mono">{data.git_version}</span>
            )}
          </>
        )}
      </div>
    </header>
  )
}
