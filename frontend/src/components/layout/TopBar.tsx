import { Activity } from 'lucide-react'
import { useClusterInfo } from '../../hooks/useCluster'

export default function TopBar() {
  const { data, isError } = useClusterInfo()

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
    </header>
  )
}
