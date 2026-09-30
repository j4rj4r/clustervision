import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Select from '../ui/Select'
import Badge from '../ui/Badge'
import { useScopes, useUserRoles, useSetUserRole, useDeleteUserRole } from '../../hooks/usePermissions'
import type { RoleName } from '../../store/authStore'
import { INSTANCE_SCOPE } from '../../store/authStore'

const ROLE_OPTIONS: { value: RoleName; label: string }[] = [
  { value: 'viewer', label: 'Viewer — read-only' },
  { value: 'operator', label: 'Operator — manage users, RBAC, kubeconfig, tokens' },
  { value: 'approver', label: 'Approver — approve/deny JIT requests (instance only)' },
  { value: 'admin', label: 'Admin — full control' },
]

const ROLE_BADGE: Record<RoleName, 'info' | 'success' | 'warning' | 'default'> = {
  viewer: 'default',
  operator: 'success',
  approver: 'warning',
  admin: 'info',
}

function scopeLabel(scope: string) {
  if (scope === INSTANCE_SCOPE) return 'Instance settings'
  return scope
}

interface Props {
  username: string
  onClose: () => void
}

export default function RoleAssignmentsModal({ username, onClose }: Props) {
  const { data: scopes = [] } = useScopes()
  const { data: roles = [], isLoading } = useUserRoles(username)
  const setRole = useSetUserRole(username)
  const deleteRole = useDeleteUserRole(username)

  const assignedScopes = new Set(roles.map((r) => r.scope))
  const availableScopes = scopes.filter((s) => !assignedScopes.has(s))

  const [scope, setScope] = useState('')
  const [role, setRole_] = useState<RoleName>('viewer')

  const effectiveScope = scope || availableScopes[0] || ''
  const canSubmit = effectiveScope.length > 0

  const handleSubmit = () => {
    if (!canSubmit) return
    setRole.mutate({ scope: effectiveScope, role }, { onSuccess: () => setScope('') })
  }

  return (
    <Modal open onClose={onClose} title={`Roles for ${username}`} size="lg">
      <div className="space-y-5">
        <p className="text-xs text-surface-500">
          No role on a scope means no access to it at all — including reads. Instance settings
          (login accounts, cluster registry, Vault config, audit log, JIT policy) requires{' '}
          <span className="font-mono">admin</span> on{' '}
          <span className="font-mono">{scopeLabel(INSTANCE_SCOPE)}</span>.
        </p>

        {isLoading ? (
          <div className="text-sm text-surface-400 text-center py-6">Loading...</div>
        ) : roles.length === 0 ? (
          <div className="text-sm text-surface-400 text-center py-6">No access — assign a role below.</div>
        ) : (
          <div className="rounded-lg border border-surface-600 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-800 text-surface-400 text-xs uppercase tracking-wide">
                  <th className="px-3 py-2 text-left">Scope</th>
                  <th className="px-3 py-2 text-left">Role</th>
                  <th className="px-3 py-2 text-right">-</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {roles.map((r) => (
                  <tr key={r.scope} className="hover:bg-surface-800/50 transition-colors">
                    <td className="px-3 py-2 font-mono text-surface-200">{scopeLabel(r.scope)}</td>
                    <td className="px-3 py-2">
                      <Badge variant={ROLE_BADGE[r.role]}>{r.role}</Badge>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => deleteRole.mutate(r.scope)}
                        className="p-1.5 rounded-md bg-surface-800 border border-surface-600 text-surface-300 hover:bg-red-950/40 hover:border-red-500/50 hover:text-red-400 transition-colors"
                        title="Remove role"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="border-t border-surface-700 pt-4 space-y-3">
          <p className="text-xs font-medium text-surface-300">Add / update role</p>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Scope"
              value={effectiveScope}
              onChange={(e) => setScope(e.target.value)}
              options={scopes.map((s) => ({ value: s, label: scopeLabel(s) }))}
              disabled={scopes.length === 0}
            />
            <Select
              label="Role"
              value={role}
              onChange={(e) => setRole_(e.target.value as RoleName)}
              options={ROLE_OPTIONS}
            />
          </div>
          <Button size="sm" loading={setRole.isPending} disabled={!canSubmit} onClick={handleSubmit}>
            Save role
          </Button>
        </div>

        <div className="flex justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
      </div>
    </Modal>
  )
}
