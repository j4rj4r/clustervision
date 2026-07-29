import { Link } from 'react-router-dom'
import { Users, Shield, Server, Clock, ScrollText, Plus, ArrowRight } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import { useAuthStore } from '../store/authStore'
import { useUsers } from '../hooks/useUsers'
import { useClusterRoles } from '../hooks/useRbac'
import { useClusters } from '../hooks/useCluster'
import { useAccessRequests } from '../hooks/useAccessRequests'
import { useAuditLog } from '../hooks/useAudit'

function StatTile({
  icon: Icon,
  label,
  value,
  to,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>
  label: string
  value: number | string
  to: string
}) {
  return (
    <Link
      to={to}
      className="bg-surface-900 border border-surface-600 rounded-xl p-4 flex items-center gap-3 hover:border-surface-500 transition-colors"
    >
      <div className="w-9 h-9 rounded-lg bg-brand-600/10 ring-1 ring-brand-500/20 flex items-center justify-center shrink-0">
        <Icon size={16} className="text-brand-400" />
      </div>
      <div className="min-w-0">
        <p className="text-xl font-semibold text-surface-100 leading-tight">{value}</p>
        <p className="text-xs text-surface-400 truncate">{label}</p>
      </div>
    </Link>
  )
}

function methodVariant(method: string): 'info' | 'danger' | 'default' {
  if (method === 'DELETE') return 'danger'
  if (method === 'POST' || method === 'PUT' || method === 'PATCH') return 'info'
  return 'default'
}

export default function DashboardPage() {
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const username = useAuthStore((s) => s.user?.username)

  const { data: usersData, isLoading: loadingUsers } = useUsers()
  const { data: clusterRoles, isLoading: loadingRoles } = useClusterRoles(false, true)
  const { data: clusters, isLoading: loadingClusters } = useClusters()
  const { data: accessRequests = [], isLoading: loadingRequests } = useAccessRequests()
  const { data: auditPage, isLoading: loadingAudit } = useAuditLog({ limit: 6, offset: 0 }, isAdmin)

  const pending = accessRequests.filter((r) => r.status === 'pending')
  const myPending = pending.filter((r) => r.requester === username)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-surface-100">Dashboard</h1>
        <p className="text-sm text-surface-400 mt-0.5">Overview of your ClusterVision instance.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile icon={Users} label="Managed users" value={loadingUsers ? '—' : usersData?.total ?? 0} to="/users" />
        <StatTile
          icon={Clock}
          label={isAdmin ? 'Pending access requests' : 'Your pending requests'}
          value={loadingRequests ? '—' : (isAdmin ? pending.length : myPending.length)}
          to="/access-requests"
        />
        <StatTile icon={Server} label="Connected clusters" value={loadingClusters ? '—' : clusters?.length ?? 0} to="/clusters" />
        <StatTile icon={Shield} label="ClusterRoles" value={loadingRoles ? '—' : clusterRoles?.length ?? 0} to="/rbac" />
      </div>

      <div className="flex flex-wrap gap-2">
        <Link to="/users">
          <Button size="sm" variant="secondary"><Plus size={13} /> Create user</Button>
        </Link>
        <Link to="/access-requests">
          <Button size="sm" variant="secondary"><Plus size={13} /> Request access</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending access requests */}
        <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/60">
            <h2 className="text-sm font-semibold text-surface-100">
              {isAdmin ? 'Pending access requests' : 'Your pending requests'}
            </h2>
            <Link to="/access-requests" className="text-xs text-brand-400 hover:underline flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {loadingRequests ? (
            <div className="py-10 text-center text-sm text-surface-400">Loading...</div>
          ) : (isAdmin ? pending : myPending).length === 0 ? (
            <div className="py-10 text-center text-sm text-surface-400">Nothing pending.</div>
          ) : (
            <ul className="divide-y divide-surface-700">
              {(isAdmin ? pending : myPending).slice(0, 6).map((r) => (
                <li key={r.id} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-surface-200 font-mono truncate">{r.target_username}</p>
                    <p className="text-xs text-surface-500 truncate">
                      {r.role_name} · {r.ttl_minutes} min {isAdmin ? `· requested by ${r.requester}` : ''}
                    </p>
                  </div>
                  <Badge variant="warning" dot>pending</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recent audit activity — admin only */}
        {isAdmin && (
          <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/60">
              <h2 className="text-sm font-semibold text-surface-100 flex items-center gap-1.5">
                <ScrollText size={14} /> Recent activity
              </h2>
              <Link to="/audit-log" className="text-xs text-brand-400 hover:underline flex items-center gap-1">
                View all <ArrowRight size={12} />
              </Link>
            </div>
            {loadingAudit ? (
              <div className="py-10 text-center text-sm text-surface-400">Loading...</div>
            ) : (auditPage?.items ?? []).length === 0 ? (
              <div className="py-10 text-center text-sm text-surface-400">No activity recorded yet.</div>
            ) : (
              <ul className="divide-y divide-surface-700">
                {auditPage!.items.map((e) => (
                  <li key={e.id} className="px-4 py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex items-center gap-2">
                      <Badge variant={methodVariant(e.method)}>{e.method}</Badge>
                      <p className="text-xs text-surface-300 font-mono truncate">{e.path}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-surface-500 font-mono">{e.actor ?? 'unknown'}</span>
                      <span className="text-xs text-surface-600">{new Date(e.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
