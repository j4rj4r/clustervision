import { useState } from 'react'
import { Plus, Check, X, RotateCcw, ShieldCheck, RefreshCw, Settings2 } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import RequestAccessModal from '../components/access/RequestAccessModal'
import JitPolicyModal from '../components/access/JitPolicyModal'
import { useAuthStore } from '../store/authStore'
import {
  useAccessRequests,
  useApproveAccessRequest,
  useDenyAccessRequest,
  useRevokeAccessRequest,
} from '../hooks/useAccessRequests'
import type { AccessRequest, AccessRequestStatus } from '../types/accessRequest'

const STATUS_VARIANT: Record<AccessRequestStatus, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  pending: 'warning',
  approved: 'success',
  denied: 'danger',
  revoked: 'danger',
  expired: 'default',
}

function scopeLabel(r: AccessRequest) {
  return r.namespace ? `${r.role_name} · ${r.namespace}` : `${r.role_name} · cluster-wide`
}

function formatDate(iso?: string) {
  return iso ? new Date(iso).toLocaleString() : '—'
}

export default function AccessRequestsPage() {
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const username = useAuthStore((s) => s.user?.username)
  const { data: requests = [], isLoading, refetch } = useAccessRequests()

  const [requestOpen, setRequestOpen] = useState(false)
  const [policiesOpen, setPoliciesOpen] = useState(false)
  const [confirm, setConfirm] = useState<{ action: 'approve' | 'revoke'; request: AccessRequest } | null>(null)

  const approve = useApproveAccessRequest()
  const deny = useDenyAccessRequest()
  const revoke = useRevokeAccessRequest()

  const handleConfirm = () => {
    if (!confirm) return
    const mutation = confirm.action === 'approve' ? approve : revoke
    mutation.mutate(confirm.request.id, { onSuccess: () => setConfirm(null) })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Access Requests</h1>
          <p className="text-sm text-surface-400 mt-0.5">
            {isAdmin
              ? 'Review requests for temporary, time-boxed role grants.'
              : 'Request temporary access — an admin must approve before anything is granted.'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCw size={13} />
          </Button>
          {isAdmin && (
            <Button variant="secondary" size="sm" onClick={() => setPoliciesOpen(true)}>
              <Settings2 size={13} /> Policies
            </Button>
          )}
          <Button size="sm" onClick={() => setRequestOpen(true)}>
            <Plus size={13} /> Request access
          </Button>
        </div>
      </div>

      <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-surface-400">Loading...</div>
        ) : requests.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <ShieldCheck size={32} className="mx-auto text-surface-600" />
            <p className="text-sm text-surface-400">No access requests yet.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-800 text-surface-400 text-xs uppercase tracking-wide">
                {isAdmin && <th className="px-4 py-3 text-left">Requester</th>}
                <th className="px-4 py-3 text-left">Target</th>
                <th className="px-4 py-3 text-left">Role</th>
                <th className="px-4 py-3 text-left">Reason</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Expires</th>
                {isAdmin && <th className="px-4 py-3 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {requests.map((r) => {
                const isOwnRequest = r.requester === username
                return (
                  <tr key={r.id} className="hover:bg-surface-800/50 transition-colors align-top">
                    {isAdmin && <td className="px-4 py-3 font-mono text-surface-200">{r.requester}</td>}
                    <td className="px-4 py-3 font-mono text-surface-200">
                      {r.target_username}
                      <span className="text-surface-500 ml-1">({r.user_kind === 'ServiceAccount' ? 'SA' : 'User'})</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-surface-300 text-xs">{scopeLabel(r)}</td>
                    <td className="px-4 py-3 text-surface-300 text-xs max-w-56 truncate" title={r.reason}>{r.reason}</td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT[r.status]} dot>{r.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-surface-400 text-xs">
                      {r.status === 'approved' ? formatDate(r.expires_at) : r.status === 'pending' ? `${r.ttl_minutes} min requested` : '—'}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-3">
                          {r.status === 'pending' && (
                            <>
                              <button
                                onClick={() => setConfirm({ action: 'approve', request: r })}
                                disabled={isOwnRequest}
                                title={isOwnRequest ? 'Cannot approve your own request' : 'Approve'}
                                className="text-surface-400 hover:text-emerald-400 disabled:opacity-30 disabled:hover:text-surface-400 transition-colors"
                              >
                                <Check size={14} />
                              </button>
                              <button
                                onClick={() => deny.mutate(r.id)}
                                title="Deny"
                                className="text-surface-400 hover:text-red-400 transition-colors"
                              >
                                <X size={14} />
                              </button>
                            </>
                          )}
                          {r.status === 'approved' && (
                            <button
                              onClick={() => setConfirm({ action: 'revoke', request: r })}
                              title="Revoke now"
                              className="text-surface-400 hover:text-red-400 transition-colors"
                            >
                              <RotateCcw size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {requestOpen && <RequestAccessModal onClose={() => setRequestOpen(false)} />}
      {policiesOpen && <JitPolicyModal onClose={() => setPoliciesOpen(false)} />}

      <Modal
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={confirm?.action === 'approve' ? 'Approve access request' : 'Revoke access'}
        size="sm"
      >
        {confirm && (
          <div className="space-y-5">
            <p className="text-sm text-surface-300">
              {confirm.action === 'approve' ? (
                <>
                  Grant <span className="font-mono text-white">{confirm.request.target_username}</span> the role{' '}
                  <span className="font-mono text-white">{confirm.request.role_name}</span> for{' '}
                  <span className="text-white">{confirm.request.ttl_minutes} minutes</span>? It will be revoked
                  automatically when it expires.
                </>
              ) : (
                <>
                  Revoke <span className="font-mono text-white">{confirm.request.target_username}</span>'s access to{' '}
                  <span className="font-mono text-white">{confirm.request.role_name}</span> immediately, instead of
                  waiting for it to expire naturally?
                </>
              )}
            </p>
            <div className="flex gap-3">
              <Button variant="secondary" className="flex-1" onClick={() => setConfirm(null)}>Cancel</Button>
              <Button
                variant={confirm.action === 'revoke' ? 'danger' : 'primary'}
                className="flex-1"
                loading={approve.isPending || revoke.isPending}
                onClick={handleConfirm}
              >
                {confirm.action === 'approve' ? 'Approve' : 'Revoke'}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
