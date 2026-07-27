import { useState } from 'react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Select from '../ui/Select'
import { useUsers } from '../../hooks/useUsers'
import { useClusterRoles, useRoles, useNamespaces } from '../../hooks/useRbac'
import { useCreateAccessRequest } from '../../hooks/useAccessRequests'

interface Props {
  onClose: () => void
}

const TTL_PRESETS = [
  { value: 30, label: '30 minutes' },
  { value: 60, label: '1 hour' },
  { value: 120, label: '2 hours' },
  { value: 240, label: '4 hours' },
  { value: 480, label: '8 hours' },
  { value: 1440, label: '24 hours' },
]

// SA names are only unique per namespace — key options on both, same fix as
// the kubeconfig user picker.
const userKey = (u: { name: string; namespace?: string }) => `${u.namespace ?? ''}/${u.name}`

export default function RequestAccessModal({ onClose }: Props) {
  const { data: usersData } = useUsers()
  const users = usersData?.users ?? []
  const { data: namespaces = [] } = useNamespaces()
  const { data: clusterRoles = [] } = useClusterRoles()

  const [targetKey, setTargetKey] = useState('')
  const [scope, setScope] = useState<'cluster' | 'namespace'>('cluster')
  const [namespace, setNamespace] = useState('')
  const [roleValue, setRoleValue] = useState('')
  const [ttlMinutes, setTtlMinutes] = useState(60)
  const [reason, setReason] = useState('')

  const { data: nsRoles = [] } = useRoles(scope === 'namespace' ? namespace : '')
  const create = useCreateAccessRequest(onClose)

  const target = users.find((u) => userKey(u) === targetKey)

  const roleOptions =
    scope === 'namespace' && namespace
      ? [
          ...nsRoles.map((r) => ({ value: `Role::${r.name}`, label: `${r.name} (Role)` })),
          ...clusterRoles.map((r) => ({ value: `ClusterRole::${r.name}`, label: `${r.name} (ClusterRole — this namespace only)` })),
        ]
      : clusterRoles.map((r) => ({ value: `ClusterRole::${r.name}`, label: r.name }))

  const canSubmit = !!target && !!roleValue && !!reason.trim() && (scope === 'cluster' || !!namespace)

  const handleSubmit = () => {
    if (!canSubmit || !target) return
    const [roleKind, roleName] = roleValue.split('::') as ['Role' | 'ClusterRole', string]
    create.mutate({
      target_username: target.name,
      user_kind: target.user_type === 'service_account' ? 'ServiceAccount' : 'User',
      sa_namespace: target.user_type === 'service_account' ? target.namespace : undefined,
      role_name: roleName,
      role_kind: roleKind,
      namespace: scope === 'namespace' ? namespace : undefined,
      ttl_minutes: ttlMinutes,
      reason: reason.trim(),
    })
  }

  return (
    <Modal open onClose={onClose} title="Request temporary access" size="md" closeOnBackdrop={false}>
      <div className="space-y-4">
        <Select
          label="Target user"
          value={targetKey}
          onChange={(e) => setTargetKey(e.target.value)}
          options={[
            { value: '', label: 'Select a user...' },
            ...users.map((u) => ({
              value: userKey(u),
              label: u.user_type === 'certificate' ? `${u.name} (X.509)` : `${u.name} (SA · ${u.namespace || 'default'})`,
            })),
          ]}
        />

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setScope('cluster')}
            className={`p-2.5 rounded-lg border text-left text-xs transition-colors ${scope === 'cluster' ? 'border-brand-500 bg-brand-500/10 text-brand-300' : 'border-surface-600 text-surface-400 hover:border-surface-500'}`}
          >
            <p className="font-medium">Cluster-wide</p>
            <p className="text-surface-500 mt-0.5">Access to all namespaces</p>
          </button>
          <button
            type="button"
            onClick={() => setScope('namespace')}
            className={`p-2.5 rounded-lg border text-left text-xs transition-colors ${scope === 'namespace' ? 'border-brand-500 bg-brand-500/10 text-brand-300' : 'border-surface-600 text-surface-400 hover:border-surface-500'}`}
          >
            <p className="font-medium">Namespace-scoped</p>
            <p className="text-surface-500 mt-0.5">Only on one namespace</p>
          </button>
        </div>

        {scope === 'namespace' && (
          <Select
            label="Namespace"
            value={namespace}
            onChange={(e) => { setNamespace(e.target.value); setRoleValue('') }}
            options={[{ value: '', label: 'Select...' }, ...namespaces.map((n) => ({ value: n, label: n }))]}
          />
        )}

        <Select
          label="Role"
          value={roleValue}
          onChange={(e) => setRoleValue(e.target.value)}
          options={[{ value: '', label: 'Select...' }, ...roleOptions]}
        />

        <Select
          label="Duration"
          value={String(ttlMinutes)}
          onChange={(e) => setTtlMinutes(Number(e.target.value))}
          options={TTL_PRESETS.map((p) => ({ value: String(p.value), label: p.label }))}
        />

        <div className="space-y-1">
          <label className="block text-xs font-medium text-surface-300">Reason</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Why do you need this access?"
            className="w-full bg-surface-900 border border-surface-600 rounded-md px-3 py-2 text-sm text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
          />
        </div>

        <p className="text-xs text-surface-500">
          An admin must approve this request before access is granted. It expires automatically after the
          selected duration — no manual cleanup needed.
        </p>

        <div className="flex gap-3 pt-2">
          <Button variant="secondary" className="flex-1" onClick={onClose}>Cancel</Button>
          <Button className="flex-1" loading={create.isPending} disabled={!canSubmit} onClick={handleSubmit}>
            Submit request
          </Button>
        </div>
      </div>
    </Modal>
  )
}
