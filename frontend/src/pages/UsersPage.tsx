import { useState } from 'react'
import { Plus, RefreshCw, FileInput } from 'lucide-react'
import Button from '../components/ui/Button'
import UserList from '../components/users/UserList'
import CreateUserModal from '../components/users/CreateUserModal'
import DeleteUserModal from '../components/users/DeleteUserModal'
import ImportUserModal from '../components/users/ImportUserModal'
import { useUsers } from '../hooks/useUsers'
import { useQueryClient } from '@tanstack/react-query'
import type { User } from '../types/user'

export default function UsersPage() {
  const { data, isLoading, isError, refetch } = useUsers()
  const qc = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [toDelete, setToDelete] = useState<User | null>(null)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Users</h1>
          <p className="text-sm text-slate-500 mt-0.5">
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

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-slate-500">Loading users...</div>
        ) : isError ? (
          <div className="py-16 text-center space-y-3">
            <p className="text-sm text-red-400">Failed to load users.</p>
            <button onClick={() => refetch()} className="text-xs text-brand-400 hover:underline">Retry</button>
          </div>
        ) : (
          <UserList
            users={data?.users ?? []}
            onDelete={setToDelete}
            onKubeconfig={(user) => {
              const ns = user.namespace && user.namespace !== 'default' ? `&namespace=${user.namespace}` : ''
              window.location.href = `/kubeconfig?user=${user.name}${ns}`
            }}
          />
        )}
      </div>

      <CreateUserModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <ImportUserModal open={importOpen} onClose={() => setImportOpen(false)} />
      <DeleteUserModal user={toDelete} onClose={() => setToDelete(null)} />
    </div>
  )
}
