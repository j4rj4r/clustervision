import { useState } from 'react'
import { Plus, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
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
  const [clusterRolesOpen, setClusterRolesOpen] = useState(false)

  const [modal, setModal] = useState<{
    open: boolean
    isCluster: boolean
    role?: RoleRead
  }>({ open: false, isCluster: true })

  const [deleteTarget, setDeleteTarget] = useState<{ role: RoleRead; isCluster: boolean } | null>(null)

  const { data: clusterRoles = [], isLoading: loadingCR, isError: errorCR, refetch: refetchCR } = useClusterRoles(showSystem, clusterRolesOpen)
  const { data: roles = [], isLoading: loadingR, isError: errorR, refetch: refetchR } = useRoles(namespace)
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

  const confirmDelete = () => {
    if (!deleteTarget) return
    if (deleteTarget.isCluster) {
      deleteCR.mutate(deleteTarget.role.name)
    } else {
      deleteR.mutate({ namespace: deleteTarget.role.namespace ?? namespace, name: deleteTarget.role.name })
    }
    setDeleteTarget(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">RBAC</h1>
          <p className="text-sm text-slate-500 mt-0.5">ClusterRoles and namespace Roles</p>
        </div>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={showSystem}
              onChange={(e) => setShowSystem(e.target.checked)}
              className="accent-brand-500"
            />
            System roles
          </label>
          <Button variant="ghost" size="sm" onClick={() => {
            qc.invalidateQueries({ queryKey: ['cluster-roles'] })
            qc.invalidateQueries({ queryKey: ['roles'] })
          }}>
            <RefreshCw size={13} />
          </Button>
        </div>
      </div>

      {/* Roles (main section) */}
      <div className="space-y-3">
        <div className="flex items-end gap-3 justify-between">
          <Select
            label="Namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            options={namespaces.map((n) => ({ value: n, label: n }))}
          />
          <Button size="sm" onClick={() => setModal({ open: true, isCluster: false, role: undefined })}>
            <Plus size={13} /> Create Role
          </Button>
        </div>
        {loadingR ? (
          <div className="text-sm text-slate-500 text-center py-8">Loading...</div>
        ) : errorR ? (
          <div className="text-center py-8 space-y-2">
            <p className="text-sm text-red-400">Failed to load Roles.</p>
            <button onClick={() => refetchR()} className="text-xs text-brand-400 hover:underline">Retry</button>
          </div>
        ) : (
          <RoleList
            roles={roles}
            title={`Roles — ${namespace}`}
            onEdit={(role) => setModal({ open: true, isCluster: false, role })}
            onDelete={(role) => setDeleteTarget({ role, isCluster: false })}
          />
        )}
      </div>

      {/* ClusterRoles (collapsible, secondary) */}
      <div className="border border-slate-800 rounded-lg overflow-hidden">
        <button
          onClick={() => setClusterRolesOpen((o) => !o)}
          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-800/50 transition-colors text-left group"
        >
          <span className="p-1 rounded text-slate-500 group-hover:text-slate-300 group-hover:bg-slate-700/50 transition-colors shrink-0">
            {clusterRolesOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
          <span className="text-sm font-medium text-slate-400 group-hover:text-slate-200 transition-colors flex-1">
            ClusterRoles
          </span>
          {clusterRolesOpen && (
            <Button
              size="sm"
              onClick={(e) => { e.stopPropagation(); setModal({ open: true, isCluster: true, role: undefined }) }}
            >
              <Plus size={13} /> Create ClusterRole
            </Button>
          )}
        </button>

        {clusterRolesOpen && (
          <div className="border-t border-slate-800 p-4">
            {loadingCR ? (
              <div className="text-sm text-slate-500 text-center py-6">Loading...</div>
            ) : errorCR ? (
              <div className="text-center py-6 space-y-2">
                <p className="text-sm text-red-400">Failed to load ClusterRoles.</p>
                <button onClick={() => refetchCR()} className="text-xs text-brand-400 hover:underline">Retry</button>
              </div>
            ) : (
              <RoleList
                roles={clusterRoles}
                title=""
                onEdit={(role) => setModal({ open: true, isCluster: true, role })}
                onDelete={(role) => setDeleteTarget({ role, isCluster: true })}
              />
            )}
          </div>
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

      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Confirm deletion"
        size="sm"
      >
        <p className="text-sm text-slate-300 mb-6">
          Delete {deleteTarget?.isCluster ? 'ClusterRole' : 'Role'}{' '}
          <span className="font-mono text-white">{deleteTarget?.role.name}</span>?
          This action is irreversible and may affect all bound users.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            className="flex-1"
            loading={deleteCR.isPending || deleteR.isPending}
            onClick={confirmDelete}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  )
}
