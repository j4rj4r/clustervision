import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, KeyRound, ShieldCheck, ShieldOff, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { adminApi, type CvUser } from '../api/admin'
import { useAuthStore } from '../store/authStore'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import Badge from '../components/ui/Badge'

// ── Create user modal ──────────────────────────────────────────────────────

function CreateUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'viewer' | 'admin'>('viewer')
  const [usernameError, setUsernameError] = useState('')

  const create = useMutation({
    mutationFn: () => adminApi.createUser(username, password, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      toast.success(`User "${username}" created`)
      onClose()
      setUsername(''); setPassword(''); setRole('viewer'); setUsernameError('')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const handleSubmit = () => {
    if (!username) { setUsernameError('Required'); return }
    if (!/^[a-z0-9][a-z0-9_\-\.]*$/.test(username)) {
      setUsernameError('Lowercase letters, numbers, dashes, dots, underscores only')
      return
    }
    if (!password) return
    create.mutate()
  }

  return (
    <Modal open={open} onClose={onClose} title="Create user" size="sm">
      <div className="space-y-4">
        <Input
          label="Username"
          value={username}
          onChange={(e) => { setUsername(e.target.value); setUsernameError('') }}
          error={usernameError}
          autoFocus
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div>
          <label className="block text-xs font-medium text-surface-300 mb-2">Role</label>
          <div className="grid grid-cols-2 gap-2">
            {(['viewer', 'admin'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setRole(r)}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  role === r ? 'border-brand-500 bg-brand-500/10' : 'border-surface-600 hover:border-surface-500'
                }`}
              >
                <p className="text-sm font-medium text-surface-100 capitalize">{r}</p>
                <p className="text-xs text-surface-400 mt-0.5">
                  {r === 'admin' ? 'Full read & write access' : 'Read-only access'}
                </p>
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-3 pt-1">
          <Button variant="secondary" size="sm" className="flex-1" onClick={onClose}>Cancel</Button>
          <Button
            size="sm"
            className="flex-1"
            loading={create.isPending}
            disabled={!username || !password}
            onClick={handleSubmit}
          >
            Create
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Reset password modal ───────────────────────────────────────────────────

function ResetPasswordModal({ user, onClose }: { user: CvUser | null; onClose: () => void }) {
  const qc = useQueryClient()
  const [password, setPassword] = useState('')

  const reset = useMutation({
    mutationFn: () => adminApi.resetPassword(user!.username, password),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      toast.success('Password updated')
      onClose()
      setPassword('')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Modal open={!!user} onClose={onClose} title="Reset password" size="sm">
      <div className="space-y-4">
        <p className="text-sm text-surface-400">
          Set a new password for <span className="font-mono text-surface-100">{user?.username}</span>.
        </p>
        <Input
          label="New password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" className="flex-1" onClick={onClose}>Cancel</Button>
          <Button
            size="sm"
            className="flex-1"
            loading={reset.isPending}
            disabled={!password}
            onClick={() => reset.mutate()}
          >
            Update
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function AdminPage() {
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [createOpen, setCreateOpen] = useState(false)
  const [resetTarget, setResetTarget] = useState<CvUser | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CvUser | null>(null)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['cv-users'],
    queryFn: adminApi.listUsers,
  })

  const toggleRole = useMutation({
    mutationFn: (user: CvUser) =>
      adminApi.changeRole(user.username, user.role === 'admin' ? 'viewer' : 'admin'),
    onSuccess: (_, user) => {
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      toast.success(`Role updated for "${user.username}"`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteUser = useMutation({
    mutationFn: (username: string) => adminApi.deleteUser(username),
    onSuccess: (_, username) => {
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      toast.success(`User "${username}" deleted`)
      setDeleteTarget(null)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Settings</h1>
          <p className="text-sm text-surface-400 mt-0.5">ClusterVision access management</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['cv-users'] })}>
            <RefreshCw size={13} />
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus size={13} /> Create user
          </Button>
        </div>
      </div>

      <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-sm text-surface-400">Loading…</div>
        ) : users.length === 0 ? (
          <div className="py-12 text-center text-sm text-surface-500">No users yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-600 bg-surface-900/60">
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400">Username</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400">Role</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-surface-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {users.map((user) => {
                const isSelf = user.username === currentUser?.username
                return (
                  <tr key={user.username} className="hover:bg-surface-700/40 transition-colors">
                    <td className="px-4 py-3 font-mono text-surface-100 font-medium">
                      {user.username}
                      {isSelf && <span className="ml-2 text-xs text-surface-500">(you)</span>}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={user.role === 'admin' ? 'info' : 'default'} dot>
                        {user.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={isSelf}
                          title={user.role === 'admin' ? 'Demote to viewer' : 'Promote to admin'}
                          onClick={() => toggleRole.mutate(user)}
                        >
                          {user.role === 'admin'
                            ? <><ShieldOff size={12} /> Viewer</>
                            : <><ShieldCheck size={12} /> Admin</>}
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setResetTarget(user)}
                        >
                          <KeyRound size={12} /> Password
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          aria-label="Delete user"
                          disabled={isSelf}
                          className="text-red-400 hover:text-red-300 hover:bg-red-950/30"
                          onClick={() => setDeleteTarget(user)}
                        >
                          <Trash2 size={13} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <CreateUserModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <ResetPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} />

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete user" size="sm">
        <p className="text-sm text-surface-300 mb-6">
          Delete <span className="font-mono text-surface-100">{deleteTarget?.username}</span>?
          They will immediately lose access to ClusterVision.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" className="flex-1" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
            className="flex-1"
            loading={deleteUser.isPending}
            onClick={() => deleteTarget && deleteUser.mutate(deleteTarget.username)}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  )
}
