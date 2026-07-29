import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Badge from '../ui/Badge'
import { useJitPolicies, useSetJitPolicy, useDeleteJitPolicy } from '../../hooks/useAccessRequests'

interface Props {
  onClose: () => void
}

export default function JitPolicyModal({ onClose }: Props) {
  const { data: policies = [], isLoading } = useJitPolicies()
  const setPolicy = useSetJitPolicy()
  const deletePolicy = useDeleteJitPolicy()

  const [roleKind, setRoleKind] = useState<'ClusterRole' | 'Role'>('ClusterRole')
  const [roleName, setRoleName] = useState('')
  const [eligible, setEligible] = useState('true')
  const [maxTtl, setMaxTtl] = useState('')

  const canSubmit = roleName.trim().length > 0

  const handleSubmit = () => {
    if (!canSubmit) return
    setPolicy.mutate(
      {
        roleKind,
        roleName: roleName.trim(),
        payload: {
          eligible: eligible === 'true',
          max_ttl_minutes: maxTtl.trim() ? Number(maxTtl) : null,
        },
      },
      { onSuccess: () => { setRoleName(''); setMaxTtl(''); setEligible('true') } },
    )
  }

  return (
    <Modal open onClose={onClose} title="JIT role policies" size="lg">
      <div className="space-y-5">
        <p className="text-xs text-surface-500">
          Roles with no override below are eligible for JIT with the default TTL cap (24h). Add an override to
          block a role from self-service entirely, or tighten how long it can be requested for.
        </p>

        {isLoading ? (
          <div className="text-sm text-surface-400 text-center py-6">Loading...</div>
        ) : policies.length === 0 ? (
          <div className="text-sm text-surface-400 text-center py-6">No overrides yet — every role uses the default.</div>
        ) : (
          <div className="rounded-lg border border-surface-600 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface-800 text-surface-400 text-xs uppercase tracking-wide">
                  <th className="px-3 py-2 text-left">Kind</th>
                  <th className="px-3 py-2 text-left">Role</th>
                  <th className="px-3 py-2 text-left">Eligible</th>
                  <th className="px-3 py-2 text-left">Max TTL</th>
                  <th className="px-3 py-2 text-right">-</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {policies.map((p) => (
                  <tr key={`${p.role_kind}/${p.role_name}`} className="hover:bg-surface-800/50 transition-colors">
                    <td className="px-3 py-2 text-surface-300 text-xs">{p.role_kind}</td>
                    <td className="px-3 py-2 font-mono text-surface-200">{p.role_name}</td>
                    <td className="px-3 py-2">
                      <Badge variant={p.eligible ? 'success' : 'danger'}>{p.eligible ? 'eligible' : 'blocked'}</Badge>
                    </td>
                    <td className="px-3 py-2 text-surface-300 text-xs">
                      {p.max_ttl_minutes != null ? `${p.max_ttl_minutes} min` : 'default (24h)'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => deletePolicy.mutate({ roleKind: p.role_kind, roleName: p.role_name })}
                        className="text-surface-400 hover:text-red-400 transition-colors"
                        title="Remove override"
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
          <p className="text-xs font-medium text-surface-300">Add / update override</p>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Role kind"
              value={roleKind}
              onChange={(e) => setRoleKind(e.target.value as 'ClusterRole' | 'Role')}
              options={[
                { value: 'ClusterRole', label: 'ClusterRole' },
                { value: 'Role', label: 'Role' },
              ]}
            />
            <Input label="Role name" placeholder="cluster-admin" value={roleName} onChange={(e) => setRoleName(e.target.value)} />
            <Select
              label="Eligible for JIT"
              value={eligible}
              onChange={(e) => setEligible(e.target.value)}
              options={[
                { value: 'true', label: 'Yes' },
                { value: 'false', label: 'No — block entirely' },
              ]}
            />
            <Input
              label="Max TTL (minutes)"
              type="number"
              placeholder="default (1440)"
              value={maxTtl}
              onChange={(e) => setMaxTtl(e.target.value)}
              disabled={eligible === 'false'}
            />
          </div>
          <Button size="sm" loading={setPolicy.isPending} disabled={!canSubmit} onClick={handleSubmit}>
            Save override
          </Button>
        </div>

        <div className="flex justify-end pt-2">
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
      </div>
    </Modal>
  )
}
