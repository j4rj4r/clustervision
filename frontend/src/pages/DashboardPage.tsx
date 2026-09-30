import { Link } from 'react-router-dom'
import { Users, Shield, Server, Clock, ScrollText, Plus, ArrowRight, FileCode2 } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import { INSTANCE_SCOPE, useAuthStore } from '../store/authStore'
import { useClusterStore } from '../store/clusterStore'
import { useUsers } from '../hooks/useUsers'
import { useClusterRoles } from '../hooks/useRbac'
import { useClusters } from '../hooks/useCluster'
import { useAccessRequests } from '../hooks/useAccessRequests'
import { useAuditLog } from '../hooks/useAudit'
import { useMyLink } from '../hooks/useLink'

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
  const instanceRole = useAuthStore((s) => s.roleFor(INSTANCE_SCOPE))
  const isInstanceAdmin = instanceRole === 'admin'
  // Admins and approvers both see everyone's pending requests (both can act
  // on them) — everyone else sees only their own.
  const isPrivileged = isInstanceAdmin || instanceRole === 'approver'
  const username = useAuthStore((s) => s.user?.username)
  const activeCluster = useClusterStore((s) => s.activeCluster)
  const canWrite = useAuthStore((s) => s.canWrite(activeCluster))
  const { data: myLink } = useMyLink()

  const { data: usersData, isLoading: loadingUsers } = useUsers()
  const { data: clusterRoles, isLoading: loadingRoles } = useClusterRoles(false, true)
  const { data: clusters, isLoading: loadingClusters } = useClusters()
  const { data: accessRequests = [], isLoading: loadingRequests } = useAccessRequests()
  const { data: auditPage, isLoading: loadingAudit } = useAuditLog({ limit: 6, offset: 0 }, isInstanceAdmin)

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
          label={isPrivileged ? 'Pending access requests' : 'Your pending requests'}
          value={loadingRequests ? '—' : (isPrivileged ? pending.length : myPending.length)}
          to="/access-requests"
        />
        <StatTile icon={Server} label="Connected clusters" value={loadingClusters ? '—' : clusters?.length ?? 0} to="/clusters" />
        <StatTile icon={Shield} label="ClusterRoles" value={loadingRoles ? '—' : clusterRoles?.length ?? 0} to="/rbac" />
      </div>

      <div className="flex flex-wrap gap-2">
        {canWrite && (
          <Link to="/users">
            <Button size="sm" variant="secondary"><Plus size={13} /> Create user</Button>
          </Link>
        )}
        <Link to="/access-requests">
          <Button size="sm" variant="secondary"><Plus size={13} /> Request access</Button>
        </Link>
        {myLink && (
          <Link to={`/kubeconfig?user=${encodeURIComponent(myLink.name)}&namespace=${encodeURIComponent(myLink.namespace)}`}>
            <Button size="sm" variant="secondary"><FileCode2 size={13} /> My kubeconfig</Button>
          </Link>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending access requests */}
        <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700/60">
            <h2 className="text-sm font-semibold text-surface-100">
              {isPrivileged ? 'Pending access requests' : 'Your pending requests'}
            </h2>
            <Link to="/access-requests" className="text-xs text-brand-400 hover:underline flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {loadingRequests ? (
            <div className="py-10 text-center text-sm text-surface-400">Loading...</div>
          ) : (isPrivileged ? pending : myPending).length === 0 ? (
            <div className="py-10 text-center text-sm text-surface-400">Nothing pending.</div>
          ) : (
            <ul className="divide-y divide-surface-700">
              {(isPrivileged ? pending : myPending).slice(0, 6).map((r) => (
                <li key={r.id} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-surface-200 font-mono truncate">{r.target_username}</p>
                    <p className="text-xs text-surface-500 truncate">
                      {r.role_name} · {r.ttl_minutes} min {isPrivileged ? `· requested by ${r.requester}` : ''}
                    </p>
                  </div>
                  <Badge variant="warning" dot>pending</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recent audit activity — instance admin only */}
        {isInstanceAdmin && (
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
