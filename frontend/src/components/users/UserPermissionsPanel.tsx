import { useState, useMemo } from 'react'
import { Plus, X } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Select from '../ui/Select'
import { useUserPermissions, useAssignRole, useRevokeRole, useClusterRoles, useRoles, useNamespaces } from '../../hooks/useRbac'

interface Props {
  username: string
  userType: string
}

export default function UserPermissionsPanel({ username, userType }: Props) {
  const { data: perms, isLoading } = useUserPermissions(username)
  const { data: clusterRoles = [] } = useClusterRoles()
  const { data: namespaces = [] } = useNamespaces()
  const assignRole = useAssignRole(username)
  const revokeRole = useRevokeRole(username)

  const [showAssign, setShowAssign] = useState(false)
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedNs, setSelectedNs] = useState('')
  const [scope, setScope] = useState<'cluster' | 'namespace'>('cluster')

  const { data: nsRoles = [] } = useRoles(scope === 'namespace' ? selectedNs : '')

  const roleOptions = useMemo(() => {
    if (scope === 'namespace' && selectedNs) {
      return [
        ...nsRoles.map((r) => ({ value: `Role::${r.name}`, label: `${r.name} (Role)` })),
        ...clusterRoles.map((r) => ({ value: `ClusterRole::${r.name}`, label: `${r.name} (ClusterRole)` })),
      ]
    }
    return clusterRoles.map((r) => ({ value: `ClusterRole::${r.name}`, label: r.name }))
  }, [scope, selectedNs, nsRoles, clusterRoles])

  const handleAssign = () => {
    if (!selectedRole) return
    const [kind, name] = selectedRole.split('::') as ['Role' | 'ClusterRole', string]
    assignRole.mutate({
      payload: {
        role_name: name,
        role_kind: kind,
        namespace: scope === 'namespace' ? selectedNs : undefined,
      },
      userKind: userType === 'service_account' ? 'ServiceAccount' : 'User',
    }, { onSuccess: () => { setShowAssign(false); setSelectedRole('') } })
  }

  if (isLoading) return <p className="text-xs text-surface-400 py-3">Loading permissions...</p>

  const allBindings = [...(perms?.cluster_bindings ?? []), ...(perms?.namespace_bindings ?? [])]

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-surface-300 uppercase tracking-wider">Permissions</p>
        <Button size="sm" variant="ghost" onClick={() => setShowAssign(!showAssign)}>
          <Plus size={12} /> Assign role
        </Button>
      </div>

      {showAssign && (
        <div className="flex items-end gap-2 p-3 bg-surface-800 rounded-lg">
          <Select
            label="Scope"
            value={scope}
            onChange={(e) => { setScope(e.target.value as 'cluster' | 'namespace'); setSelectedRole(''); setSelectedNs('') }}
            options={[{ value: 'cluster', label: 'Cluster-wide' }, { value: 'namespace', label: 'Namespace' }]}
          />
          {scope === 'namespace' && (
            <Select
              label="Namespace"
              value={selectedNs}
              onChange={(e) => { setSelectedNs(e.target.value); setSelectedRole('') }}
              options={[{ value: '', label: 'Select...' }, ...namespaces.map((ns) => ({ value: ns, label: ns }))]}
            />
          )}
          <Select
            label="Role"
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            options={[{ value: '', label: 'Select...' }, ...roleOptions]}
          />
          <Button size="sm" onClick={handleAssign} loading={assignRole.isPending} disabled={!selectedRole}>
            Add
          </Button>
        </div>
      )}

      {allBindings.length === 0 ? (
        <p className="text-xs text-surface-500 py-1">No roles assigned</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {allBindings.map((b) => (
            <div key={b.name} className="flex items-center gap-1.5 bg-surface-800 border border-surface-600 rounded-md px-2 py-1">
              <span className="text-xs font-mono text-surface-200">{b.role_ref}</span>
              {b.namespace && <Badge variant="default">{b.namespace}</Badge>}
              <button
                onClick={() => revokeRole.mutate({ roleName: b.role_ref, namespace: b.namespace ?? undefined })}
                className="text-surface-500 hover:text-red-400 transition-colors ml-0.5"
              >
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
