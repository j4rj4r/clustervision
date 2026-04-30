import { useState } from 'react'
import { Plus, RefreshCw } from 'lucide-react'
import Button from '../components/ui/Button'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
import Tooltip from '../components/ui/Tooltip'
import RoleList from '../components/rbac/RoleList'
import RoleEditorModal from '../components/rbac/RoleEditorModal'
import NamespaceAccessPanel from '../components/rbac/NamespaceAccessPanel'
import AccessSimulatorPanel from '../components/rbac/AccessSimulatorPanel'
import DriftPanel from '../components/rbac/DriftPanel'
import { useAuthStore } from '../store/authStore'
import { useQuery } from '@tanstack/react-query'
import { driftApi } from '../api/drift'
import {
  useClusterRoles, useRoles, useNamespaces,
  useCreateClusterRole, useUpdateClusterRole, useDeleteClusterRole,
  useCreateRole, useUpdateRole, useDeleteRole,
} from '../hooks/useRbac'
import { useQueryClient } from '@tanstack/react-query'
import type { PolicyRule, RoleRead } from '../types/rbac'

type Tab = 'roles' | 'clusterroles' | 'access' | 'simulator' | 'drift'

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

  const isAdmin = useAuthStore((s) => s.isAdmin())
  const { data: driftData } = useQuery({
    queryKey: ['drift-events'],
    queryFn: () => driftApi.list(),
    refetchInterval: 30_000,
    enabled: isAdmin,
  })
  const driftCount = driftData?.total ?? 0

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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Permissions</h1>
          <p className="text-sm text-surface-400 mt-0.5">Manage roles and access rules across your cluster</p>
        </div>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-xs text-surface-300 cursor-pointer">
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

      {/* Tabs */}
      <div className="flex border-b border-surface-600">
        {([
          { key: 'roles', label: 'Namespace roles', tip: 'Roles that apply within a specific namespace only' },
          { key: 'clusterroles', label: 'Cluster-wide roles', tip: 'Roles that apply across all namespaces in the cluster' },
          { key: 'access', label: 'Who has access', tip: undefined },
          { key: 'simulator', label: 'Test permissions', tip: undefined },
          ...(isAdmin ? [{ key: 'drift' as Tab, label: 'Drift detection', tip: undefined, badge: driftCount }] : []),
        ] as { key: Tab; label: string; tip?: string; badge?: number }[]).map(({ key, label, tip, badge }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px flex items-center gap-1.5 ${
              tab === key
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-surface-400 hover:text-surface-200 hover:border-surface-500'
            }`}
          >
            {tip ? <Tooltip content={tip}><span>{label}</span></Tooltip> : label}
            {!!badge && (
              <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-semibold">
                {badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Roles tab */}
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
          {loadingR ? (
            <div className="text-sm text-surface-400 text-center py-8">Loading...</div>
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
              onCopy={(role) => setModal({ open: true, isCluster: false, copyFrom: role })}
              onDelete={(role) => setDeleteTarget({ role, isCluster: false })}
              onCreateClick={() => setModal({ open: true, isCluster: false, role: undefined })}
            />
          )}
        </div>
      )}

      {/* ClusterRoles tab */}
      {tab === 'clusterroles' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setModal({ open: true, isCluster: true, role: undefined })}>
              <Plus size={13} /> Create ClusterRole
            </Button>
          </div>
          {loadingCR ? (
            <div className="text-sm text-surface-400 text-center py-8">Loading...</div>
          ) : errorCR ? (
            <div className="text-center py-8 space-y-2">
              <p className="text-sm text-red-400">Failed to load ClusterRoles.</p>
              <button onClick={() => refetchCR()} className="text-xs text-brand-400 hover:underline">Retry</button>
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
      )}

      {/* Namespace Access tab */}
      {tab === 'access' && <NamespaceAccessPanel />}

      {/* Access Simulator tab */}
      {tab === 'simulator' && <AccessSimulatorPanel />}

      {/* Drift detection tab */}
      {tab === 'drift' && <DriftPanel />}

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

      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Confirm deletion"
        size="sm"
      >
        <p className="text-sm text-surface-300 mb-6">
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
