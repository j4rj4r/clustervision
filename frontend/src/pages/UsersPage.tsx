import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, RefreshCw, FileInput } from 'lucide-react'
import Button from '../components/ui/Button'
import UserList from '../components/users/UserList'
import CreateUserWizard from '../components/users/CreateUserWizard'
import DeleteUserModal from '../components/users/DeleteUserModal'
import ImportUserModal from '../components/users/ImportUserModal'
import { useUsers } from '../hooks/useUsers'
import { useQueryClient } from '@tanstack/react-query'
import { useClusterStore } from '../store/clusterStore'
import { rbacApi } from '../api/rbac'
import type { User } from '../types/user'

export default function UsersPage() {
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useUsers()
  const qc = useQueryClient()
  const cluster = useClusterStore((s) => s.activeCluster)

  // Prefetch permissions for all users as soon as the list loads
  useEffect(() => {
    if (!data?.users) return
    data.users.forEach((user) => {
      qc.prefetchQuery({
        queryKey: ['user-permissions', cluster, user.name],
        queryFn: () => rbacApi.getUserPermissions(user.name),
        staleTime: 120_000,
      })
    })
  }, [data?.users, cluster])
  const [createOpen, setCreateOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [toDelete, setToDelete] = useState<User | null>(null)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Users</h1>
          <p className="text-sm text-surface-400 mt-0.5">
            {data ? `${data.total} user${data.total !== 1 ? 's' : ''}` : 'Loading...'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['users'] })}>
            <RefreshCw size={13} />
          </Button>
          <Button variant="secondary" onClick={() => setImportOpen(true)}>
            <FileInput size={14} /> Import
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={14} /> Create
          </Button>
        </div>
      </div>

      <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-surface-400">Loading users...</div>
        ) : isError ? (
          <div className="py-16 text-center space-y-3">
            <p className="text-sm text-red-400">Failed to load users.</p>
            <button onClick={() => refetch()} className="text-xs text-brand-400 hover:underline">Retry</button>
          </div>
        ) : (
          <UserList
            users={data?.users ?? []}
            onDelete={setToDelete}
            onCreateClick={() => setCreateOpen(true)}
            onKubeconfig={(user) => {
              const params = new URLSearchParams({ user: user.name })
              // Always include the namespace — SA names alone are ambiguous
              if (user.namespace) params.set('namespace', user.namespace)
              navigate(`/kubeconfig?${params.toString()}`)
            }}
          />
        )}
      </div>

      <CreateUserWizard open={createOpen} onClose={() => setCreateOpen(false)} />
      <ImportUserModal open={importOpen} onClose={() => setImportOpen(false)} />
      <DeleteUserModal user={toDelete} onClose={() => setToDelete(null)} />
    </div>
  )
}
