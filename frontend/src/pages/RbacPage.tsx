import { useState } from 'react'
import { Plus, RefreshCw, AlertCircle } from 'lucide-react'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
import RoleList from '../components/rbac/RoleList'
import RoleEditorModal from '../components/rbac/RoleEditorModal'
import NamespaceAccessPanel from '../components/rbac/NamespaceAccessPanel'
import AccessSimulatorPanel from '../components/rbac/AccessSimulatorPanel'
import { SkeletonTable } from '../components/ui/Skeleton'
import {
  useClusterRoles, useRoles, useNamespaces,
  useCreateClusterRole, useUpdateClusterRole, useDeleteClusterRole,
  useCreateRole, useUpdateRole, useDeleteRole,
} from '../hooks/useRbac'
import { useQueryClient } from '@tanstack/react-query'
import type { PolicyRule, RoleRead } from '../types/rbac'

type Tab = 'roles' | 'clusterroles' | 'access' | 'simulator'

const TABS: { key: Tab; label: string }[] = [
  { key: 'roles',       label: 'Roles'           },
  { key: 'clusterroles', label: 'Cluster Roles'  },
  { key: 'access',      label: 'Who has access'  },
  { key: 'simulator',   label: 'Test permissions' },
]

export default function RbacPage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('roles')
  const [namespace, setNamespace] = useState('default')
  const [showSystem, setShowSystem] = useState(false)

  const [modal, setModal] = useState<{
    open: boolean
    isCluster: boolean
    role?: RoleRead
    copyFrom?: RoleRead
  }>({ open: false, isCluster: false })

  const [deleteTarget, setDeleteTarget] = useState<{ role: RoleRead; isCluster: boolean } | null>(null)

  const { data: clusterRoles = [], isLoading: loadingCR, isError: errorCR, refetch: refetchCR } = useClusterRoles(showSystem, tab === 'clusterroles')
  const { data: roles = [], isLoading: loadingR, isError: errorR, refetch: refetchR } = useRoles(namespace)
  const { data: namespaces = [] } = useNamespaces()

  const closeModal = () => setModal({ open: false, isCluster: false, role: undefined, copyFrom: undefined })

  const createCR = useCreateClusterRole(closeModal)
  const updateCR = useUpdateClusterRole(closeModal)
  const deleteCR = useDeleteClusterRole()
  const createR = useCreateRole(closeModal)
  const updateR = useUpdateRole(closeModal)
  const deleteR = useDeleteRole()

  const handleSave = (name: string, rules: PolicyRule[], ns?: string) => {
    if (modal.isCluster) {
      modal.role ? updateCR.mutate({ name, rules }) : createCR.mutate({ name, rules })
    } else {
      modal.role
        ? updateR.mutate({ namespace: ns ?? namespace, name, rules })
        : createR.mutate({ namespace: ns ?? namespace, name, rules })
    }
  }

  const isSaving = createCR.isPending || updateCR.isPending || createR.isPending || updateR.isPending

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
    <div className="space-y-5 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-surface-100 tracking-tight">Permissions</h1>
          <p className="text-xs text-surface-500 mt-0.5">Roles and cluster-wide bindings</p>
        </div>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-xs text-surface-400 cursor-pointer select-none">
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

      {/* Pill tabs */}
      <div className="flex items-center gap-1 bg-surface-800/60 border border-surface-700/50 rounded-lg p-1 w-fit shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-3.5 py-1.5 text-xs font-medium rounded-md transition-all ${
              tab === key
                ? 'bg-brand-600/20 text-brand-300 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]'
                : 'text-surface-400 hover:text-surface-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'roles' && (
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
          <div className="bg-surface-900 border border-surface-700/60 rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
            {loadingR ? (
              <SkeletonTable rows={5} cols={4} />
            ) : errorR ? (
              <div className="text-center py-12 space-y-2">
                <AlertCircle size={24} className="mx-auto text-red-400/50" />
                <p className="text-sm text-red-400">Failed to load Roles.</p>
                <button onClick={() => refetchR()} className="text-xs text-brand-400 hover:text-brand-300 transition-colors">Retry</button>
              </div>
            ) : (
              <RoleList
                roles={roles}
                title={`Roles — ${namespace}`}
                onEdit={(role) => setModal({ open: true, isCluster: false, role })}
                onCopy={(role) => setModal({ open: true, isCluster: false, copyFrom: role })}
                onDelete={(role) => setDeleteTarget({ role, isCluster: false })}
                onCreateClick={() => setModal({ open: true, isCluster: false, role: undefined })}
              />
            )}
          </div>
        </div>
      )}

      {tab === 'clusterroles' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setModal({ open: true, isCluster: true, role: undefined })}>
              <Plus size={13} /> Create ClusterRole
            </Button>
          </div>
          <div className="bg-surface-900 border border-surface-700/60 rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
            {loadingCR ? (
              <SkeletonTable rows={5} cols={4} />
            ) : errorCR ? (
              <div className="text-center py-12 space-y-2">
                <AlertCircle size={24} className="mx-auto text-red-400/50" />
                <p className="text-sm text-red-400">Failed to load ClusterRoles.</p>
                <button onClick={() => refetchCR()} className="text-xs text-brand-400 hover:text-brand-300 transition-colors">Retry</button>
              </div>
            ) : (
              <RoleList
                roles={clusterRoles}
                title="ClusterRoles"
                onEdit={(role) => setModal({ open: true, isCluster: true, role })}
                onCopy={(role) => setModal({ open: true, isCluster: true, copyFrom: role })}
                onDelete={(role) => setDeleteTarget({ role, isCluster: true })}
                onCreateClick={() => setModal({ open: true, isCluster: true, role: undefined })}
              />
            )}
          </div>
        </div>
      )}

      {tab === 'access' && <NamespaceAccessPanel />}
      {tab === 'simulator' && <AccessSimulatorPanel />}

      {modal.open && (
        <RoleEditorModal
          role={modal.role}
          copyFrom={modal.copyFrom}
          namespace={namespace}
          namespaces={namespaces}
          isCluster={modal.isCluster}
          onSave={handleSave}
          onClose={closeModal}
          loading={isSaving}
        />
      )}

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Confirm deletion" size="sm">
        <p className="text-sm text-surface-300 mb-6">
          Delete {deleteTarget?.isCluster ? 'ClusterRole' : 'Role'}{' '}
          <span className="font-mono text-surface-100">{deleteTarget?.role.name}</span>?{' '}
          This action is irreversible and may affect all bound users.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" className="flex-1" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
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
