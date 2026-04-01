import { useState } from 'react'
import { Fragment } from 'react'
import { Shield, Trash2, FileCode2, ChevronDown, ChevronRight, ChevronsUpDown, ArrowUp, ArrowDown, Plus } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import UserPermissionsPanel from './UserPermissionsPanel'
import type { User } from '../../types/user'

interface Props {
  users: User[]
  onDelete: (user: User) => void
  onKubeconfig: (user: User) => void
  onCreateClick?: () => void
}

function ExpiryBadge({ expiry }: { expiry: string }) {
  const days = Math.floor((new Date(expiry).getTime() - Date.now()) / 86_400_000)
  if (days < 0) return <Badge variant="danger">Expired</Badge>
  if (days < 30) return <Badge variant="danger">{days}d left</Badge>
  if (days < 90) return <Badge variant="warning">{days}d left</Badge>
  return <Badge variant="success">{days}d left</Badge>
}

type SortCol = 'name' | 'type' | 'created_at'
type SortDir = 'asc' | 'desc'

function SortIcon({ col, sortCol, sortDir }: { col: SortCol; sortCol: SortCol; sortDir: SortDir }) {
  if (col !== sortCol) return <ChevronsUpDown size={12} className="opacity-30 ml-1 inline" />
  return sortDir === 'asc'
    ? <ArrowUp size={12} className="ml-1 inline text-brand-400" />
    : <ArrowDown size={12} className="ml-1 inline text-brand-400" />
}

export default function UserList({ users, onDelete, onKubeconfig, onCreateClick }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [sortCol, setSortCol] = useState<SortCol>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const toggleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortCol(col); setSortDir('asc') }
  }

  const sorted = [...users].sort((a, b) => {
    let cmp = 0
    if (sortCol === 'name') cmp = a.name.localeCompare(b.name)
    else if (sortCol === 'type') cmp = a.user_type.localeCompare(b.user_type)
    else if (sortCol === 'created_at') cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    return sortDir === 'asc' ? cmp : -cmp
  })

  if (users.length === 0) {
    return (
      <div className="text-center py-16 text-surface-400 space-y-4">
        <Shield size={36} className="mx-auto opacity-30" />
        <div>
          <p className="text-sm font-medium text-surface-300">No users yet</p>
          <p className="text-xs text-surface-500 mt-1">Create a ServiceAccount or certificate user to get started.</p>
        </div>
        {onCreateClick && (
          <Button size="sm" onClick={onCreateClick}>
            <Plus size={13} /> Create user
          </Button>
        )}
      </div>
    )
  }

  const toggle = (name: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  const thClass = 'px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider cursor-pointer select-none hover:text-surface-200 transition-colors'

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-surface-600 bg-surface-900/60">
          <th className="w-10 px-4 py-3" />
          <th className={thClass} onClick={() => toggleSort('name')}>
            Name <SortIcon col="name" sortCol={sortCol} sortDir={sortDir} />
          </th>
          <th className={thClass} onClick={() => toggleSort('type')}>
            Type <SortIcon col="type" sortCol={sortCol} sortDir={sortDir} />
          </th>
          <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Groups</th>
          <th className={thClass} onClick={() => toggleSort('created_at')}>
            Created <SortIcon col="created_at" sortCol={sortCol} sortDir={sortDir} />
          </th>
          <th className="px-4 py-3 text-right text-xs font-medium text-surface-400 uppercase tracking-wider">Actions</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-surface-700">
        {sorted.map((user) => (
          <Fragment key={user.name}>
            <tr
              className="hover:bg-surface-700/40 transition-colors cursor-pointer"
              onClick={() => toggle(user.name)}
            >
              <td className="px-4 py-3 w-10">
                <span className="p-1 rounded text-surface-400">
                  {expanded.has(user.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
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
                <div>{new Date(user.created_at).toLocaleDateString()}</div>
                {user.cert_expiry && (
                  <div className="mt-1"><ExpiryBadge expiry={user.cert_expiry} /></div>
                )}
              </td>
              <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
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
                  <UserPermissionsPanel username={user.name} userType={user.user_type} userNamespace={user.namespace} />
                </td>
              </tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
  )
}
