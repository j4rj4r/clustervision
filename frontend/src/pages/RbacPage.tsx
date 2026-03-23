import { useState } from 'react'
import { Plus, RefreshCw } from 'lucide-react'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import RoleList from '../components/rbac/RoleList'
import RoleEditorModal from '../components/rbac/RoleEditorModal'
import {
  useClusterRoles, useRoles, useNamespaces,
  useCreateClusterRole, useUpdateClusterRole, useDeleteClusterRole,
  useCreateRole, useUpdateRole, useDeleteRole,
} from '../hooks/useRbac'
import { useQueryClient } from '@tanstack/react-query'
import type { PolicyRule, RoleRead } from '../types/rbac'

export default function RbacPage() {
  const qc = useQueryClient()
  const [namespace, setNamespace] = useState('default')
  const [showSystem, setShowSystem] = useState(false)
  const [showClusterRoles, setShowClusterRoles] = useState(false)

  const [modal, setModal] = useState<{
    open: boolean
    isCluster: boolean
    role?: RoleRead
  }>({ open: false, isCluster: true })

  const { data: clusterRoles = [], isLoading: loadingCR } = useClusterRoles(showSystem)
  const { data: roles = [], isLoading: loadingR } = useRoles(namespace)
  const { data: namespaces = [] } = useNamespaces()

  const closeModal = () => setModal({ open: false, isCluster: true })

  const createCR = useCreateClusterRole(closeModal)
  const updateCR = useUpdateClusterRole(closeModal)
  const deleteCR = useDeleteClusterRole()
  const createR = useCreateRole(closeModal)
  const updateR = useUpdateRole(closeModal)
  const deleteR = useDeleteRole()

  const handleSave = (name: string, rules: PolicyRule[], ns?: string) => {
    if (modal.isCluster) {
      modal.role
        ? updateCR.mutate({ name, rules })
        : createCR.mutate({ name, rules })
    } else {
      modal.role
        ? updateR.mutate({ namespace: ns ?? namespace, name, rules })
        : createR.mutate({ namespace: ns ?? namespace, name, rules })
    }
  }

  const isSaving =
    createCR.isPending || updateCR.isPending || createR.isPending || updateR.isPending

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

      {showClusterRoles && (
        <div className="space-y-2">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setModal({ open: true, isCluster: true, role: undefined })}>
              <Plus size={13} /> Créer ClusterRole
            </Button>
          </div>
          {loadingCR ? (
            <div className="text-sm text-slate-500 text-center py-8">Loading roles...</div>
          ) : (
            <RoleList
              roles={clusterRoles}
              title="ClusterRoles"
              onEdit={(role) => setModal({ open: true, isCluster: true, role })}
              onDelete={(role) => deleteCR.mutate(role.name)}
            />
          )}
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-center gap-3 justify-between">
          <Select
            label="Namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            options={namespaces.map((n) => ({ value: n, label: n }))}
          />
          <Button size="sm" onClick={() => setModal({ open: true, isCluster: false, role: undefined })}>
            <Plus size={13} /> Créer Role
          </Button>
        </div>
        {loadingR ? (
          <div className="text-sm text-slate-500">Loading...</div>
        ) : (
          <RoleList
            roles={roles}
            title={`Roles in ${namespace}`}
            onEdit={(role) => setModal({ open: true, isCluster: false, role })}
            onDelete={(role) => deleteR.mutate({ namespace: role.namespace ?? namespace, name: role.name })}
          />
        )}
      </div>

      {modal.open && (
        <RoleEditorModal
          role={modal.role}
          namespace={namespace}
          isCluster={modal.isCluster}
          onSave={handleSave}
          onClose={closeModal}
          loading={isSaving}
        />
      )}
    </div>
  )
}
