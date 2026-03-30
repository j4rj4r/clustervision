import { Outlet } from 'react-router-dom'
import { ServerCrash } from 'lucide-react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { useClusterInfo } from '../../hooks/useCluster'

export default function Layout() {
  const { isError, isPending } = useClusterInfo()

  if (isPending) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface-950 text-surface-400 text-sm">
        Connecting...
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface-950">
        <div className="flex flex-col items-center gap-4 text-center px-6">
          <ServerCrash size={48} className="text-red-500 opacity-80" />
          <h1 className="text-lg font-semibold text-surface-100">Backend unreachable</h1>
          <p className="text-sm text-surface-400 max-w-sm">
            ClusterVision cannot connect to the API server. Make sure the backend is running and reachable.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 px-4 py-2 text-xs rounded-md bg-surface-800 hover:bg-surface-700 text-surface-200 border border-surface-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-surface-950 text-surface-200 overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
