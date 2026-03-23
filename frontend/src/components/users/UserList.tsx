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
  const [expanded, setExpanded] = useState<string | null>(null)

  if (users.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Shield size={36} className="mx-auto mb-3 opacity-30" />
        <p className="text-sm">No users yet. Create one to get started.</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-slate-800">
      {users.map((user) => (
        <div key={user.name}>
          <div className="flex items-center gap-4 px-4 py-3 hover:bg-slate-800/50 transition-colors">
            <button
              onClick={() => setExpanded(expanded === user.name ? null : user.name)}
              className="text-slate-500 hover:text-slate-300"
            >
              {expanded === user.name ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-medium text-slate-100">{user.name}</span>
                <Badge variant={user.user_type === 'certificate' ? 'info' : 'default'}>
                  {user.user_type === 'certificate' ? 'X.509' : 'ServiceAccount'}
                </Badge>
                {user.groups?.length > 0 && (
                  <span className="text-xs text-slate-500">{user.groups.join(', ')}</span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Created {new Date(user.created_at).toLocaleDateString()}
                {user.namespace !== 'default' && ` · ns: ${user.namespace}`}
                {user.cert_expiry && ` · expires ${new Date(user.cert_expiry).toLocaleDateString()}`}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={() => onKubeconfig(user)}>
                <FileCode2 size={13} /> Kubeconfig
              </Button>
              <Button size="sm" variant="ghost" onClick={() => onDelete(user)} className="text-red-400 hover:text-red-300 hover:bg-red-900/20">
                <Trash2 size={13} />
              </Button>
            </div>
          </div>

          {expanded === user.name && (
            <div className="px-12 pb-4 bg-slate-900/50">
              <UserPermissionsPanel username={user.name} userType={user.user_type} />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
