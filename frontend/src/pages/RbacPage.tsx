import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import RoleList from '../components/rbac/RoleList'
import { useClusterRoles, useRoles, useNamespaces } from '../hooks/useRbac'
import { useQueryClient } from '@tanstack/react-query'

export default function RbacPage() {
  const qc = useQueryClient()
  const [namespace, setNamespace] = useState('default')
  const [showSystem, setShowSystem] = useState(false)
  const [showClusterRoles, setShowClusterRoles] = useState(false)

  const { data: clusterRoles = [], isLoading: loadingCR } = useClusterRoles(showSystem)
  const { data: roles = [], isLoading: loadingR } = useRoles(namespace)
  const { data: namespaces = [] } = useNamespaces()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">RBAC</h1>
          <p className="text-sm text-slate-500 mt-0.5">Cluster roles and namespace roles</p>
        </div>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showClusterRoles}
              onChange={(e) => setShowClusterRoles(e.target.checked)}
              className="accent-brand-500"
            />
            ClusterRoles
          </label>
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showSystem}
              onChange={(e) => setShowSystem(e.target.checked)}
              className="accent-brand-500"
            />
            Roles système
          </label>
          <Button variant="ghost" size="sm" onClick={() => {
            qc.invalidateQueries({ queryKey: ['cluster-roles'] })
            qc.invalidateQueries({ queryKey: ['roles'] })
          }}>
            <RefreshCw size={13} />
          </Button>
        </div>
      </div>

      {showClusterRoles && (loadingCR ? (
        <div className="text-sm text-slate-500 text-center py-8">Loading roles...</div>
      ) : (
        <RoleList roles={clusterRoles} title="ClusterRoles" />
      ))}

      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Select
            label="Namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            options={namespaces.map((n) => ({ value: n, label: n }))}
          />
        </div>
        {loadingR ? (
          <div className="text-sm text-slate-500">Loading...</div>
        ) : (
          <RoleList roles={roles} title={`Roles in ${namespace}`} />
        )}
      </div>
    </div>
  )
}
