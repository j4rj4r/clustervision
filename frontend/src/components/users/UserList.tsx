import { useState } from 'react'
import { Shield, Trash2, FileCode2, ChevronDown, ChevronRight } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import UserPermissionsPanel from './UserPermissionsPanel'
import type { User } from '../../types/user'

interface Props {
  users: User[]
  onDelete: (user: User) => void
  onKubeconfig: (user: User) => void
}

export default function UserList({ users, onDelete, onKubeconfig }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  if (users.length === 0) {
    return (
      <div className="text-center py-16 text-surface-400">
        <Shield size={36} className="mx-auto mb-3 opacity-30" />
        <p className="text-sm">No users yet. Create one to get started.</p>
      </div>
    )
  }

  const toggle = (name: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-surface-600 bg-surface-900/60">
          <th className="w-10 px-4 py-3" />
          <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Name</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Type</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Groups</th>
          <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Created</th>
          <th className="px-4 py-3 text-right text-xs font-medium text-surface-400 uppercase tracking-wider">Actions</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-surface-700">
        {users.map((user) => (
          <>
            <tr key={user.name} className="hover:bg-surface-700/40 transition-colors">
              <td className="px-4 py-3 w-10">
                <button
                  aria-label={expanded.has(user.name) ? 'Collapse' : 'Expand'}
                  aria-expanded={expanded.has(user.name)}
                  onClick={() => toggle(user.name)}
                  className="p-1 rounded text-surface-400 hover:text-surface-200 hover:bg-surface-600/50 transition-colors"
                >
                  {expanded.has(user.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
              </td>
              <td className="px-4 py-3 font-mono text-surface-100 font-medium">{user.name}</td>
              <td className="px-4 py-3">
                <Badge variant={user.user_type === 'certificate' ? 'info' : 'default'} dot>
                  {user.user_type === 'certificate' ? 'X.509' : 'ServiceAccount'}
                </Badge>
              </td>
              <td className="px-4 py-3 text-surface-400 text-xs">
                {user.groups?.length > 0 ? user.groups.join(', ') : <span className="text-surface-500">—</span>}
              </td>
              <td className="px-4 py-3 text-surface-400 text-xs">
                {new Date(user.created_at).toLocaleDateString()}
                {user.cert_expiry && (
                  <span className="text-surface-500 ml-1">· exp. {new Date(user.cert_expiry).toLocaleDateString()}</span>
                )}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center justify-end gap-2">
                  <Button size="sm" variant="secondary" onClick={() => onKubeconfig(user)}>
                    <FileCode2 size={12} /> Kubeconfig
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label="Delete user"
                    onClick={() => onDelete(user)}
                    className="text-red-400 hover:text-red-300 hover:bg-red-950/30"
                  >
                    <Trash2 size={13} />
                  </Button>
                </div>
              </td>
            </tr>
            {expanded.has(user.name) && (
              <tr key={`${user.name}-panel`}>
                <td colSpan={6} className="bg-surface-950/60 px-12 py-4 border-b border-surface-600">
                  <UserPermissionsPanel username={user.name} userType={user.user_type} />
                </td>
              </tr>
            )}
          </>
        ))}
      </tbody>
    </table>
  )
}
