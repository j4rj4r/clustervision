import { Activity, ChevronDown, Server } from 'lucide-react'
import { useClusterInfo, useClusters } from '../../hooks/useCluster'
import { useClusterStore } from '../../store/clusterStore'

export default function TopBar() {
  const { data, isError } = useClusterInfo()
  const { data: clusters = [] } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()

  return (
    <header className="h-12 bg-slate-900 border-b border-slate-800 flex items-center px-6 gap-4">
      <div className="flex items-center gap-2 text-sm">
        <Activity
          size={14}
          className={isError ? 'text-red-500' : 'text-emerald-500'}
        />
        <span className={`font-medium ${isError ? 'text-red-400' : 'text-emerald-400'}`}>
          {isError ? 'Cluster unreachable' : 'Connected'}
        </span>
        {data && (
          <span className="text-slate-500 text-xs ml-1">· {data.git_version}</span>
        )}
      </div>

      <div className="flex-1" />

      {clusters.length > 1 && (
        <div className="relative">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg cursor-pointer hover:border-slate-600 transition-colors group">
            <Server size={13} className="text-brand-400" />
            <select
              value={activeCluster}
              onChange={(e) => setActiveCluster(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-mono cursor-pointer focus:outline-none appearance-none pr-4"
            >
              {clusters.map((c) => (
                <option key={c.name} value={c.name} className="bg-slate-800">
                  {c.name}
                </option>
              ))}
            </select>
            <ChevronDown size={12} className="text-slate-500 pointer-events-none absolute right-2" />
          </div>
        </div>
      )}
    </header>
  )
}
