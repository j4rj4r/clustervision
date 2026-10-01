import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { ServerCrash } from 'lucide-react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import { useBackendHealth } from '../../hooks/useBackendHealth'
import type { ApiError } from '../../api/client'

export default function Layout() {
  const { isError, isPending, error } = useBackendHealth()
  // No response at all (status undefined) means our own backend is
  // genuinely unreachable — a real response with an error status would mean
  // the backend answered but rejected the request for some other reason.
  // Either way this check is deliberately independent of the active
  // cluster (see useBackendHealth) — gating the whole app shell, including
  // TopBar, on a per-cluster query used to cause an infinite mount/unmount
  // loop whenever the selected cluster was unreachable: TopBar renders only
  // when this resolves, but TopBar itself also queries cluster info, and a
  // query with no cached success data refetches on every mount, flipping
  // this back to pending and unmounting TopBar again, forever.
  const backendUnreachable = isError && (error as ApiError | null)?.status === undefined

  if (isPending) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface-950 text-surface-400 text-sm">
        Connecting...
      </div>
    )
  }

  if (backendUnreachable) {
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
          <Suspense fallback={<div className="text-sm text-surface-400">Loading...</div>}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  )
}
