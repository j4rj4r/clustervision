import { useState } from 'react'
import { Fragment } from 'react'
import { Shield, Trash2, FileCode2, ChevronDown, ChevronRight, ChevronsUpDown, ArrowUp, ArrowDown, Plus, RefreshCw } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Pagination from '../ui/Pagination'
import Tooltip from '../ui/Tooltip'
import UserPermissionsPanel from './UserPermissionsPanel'
import RenewCertModal from './RenewCertModal'
import type { User } from '../../types/user'

const PAGE_SIZE = 20

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
  const [page, setPage] = useState(0)
  const [renewTarget, setRenewTarget] = useState<string | null>(null)

  const toggleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortCol(col); setSortDir('asc') }
    setPage(0)
  }

  const sorted = [...users].sort((a, b) => {
    let cmp = 0
    if (sortCol === 'name') cmp = a.name.localeCompare(b.name)
    else if (sortCol === 'type') cmp = a.user_type.localeCompare(b.user_type)
    else if (sortCol === 'created_at') cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    return sortDir === 'asc' ? cmp : -cmp
  })

  const paginated = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

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

  const thClass = 'px-4 py-3 text-left text-xs font-medium text-surface-400 tracking-normal cursor-pointer select-none hover:text-surface-200 transition-colors'

  return (
    <>
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
          <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 tracking-normal">Groups</th>
          <th className={thClass} onClick={() => toggleSort('created_at')}>
            Created <SortIcon col="created_at" sortCol={sortCol} sortDir={sortDir} />
          </th>
          <th className="px-4 py-3 text-right text-xs font-medium text-surface-400 tracking-normal">Actions</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-surface-700">
        {paginated.map((user) => (
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
                <Tooltip content={
                  user.user_type === 'certificate'
                    ? 'Certificate user (X.509) — authenticates with a private key and signed certificate, typically for human users'
                    : 'ServiceAccount — a Kubernetes identity for applications and automated processes'
                }>
                  <Badge variant={user.user_type === 'certificate' ? 'info' : 'default'} dot>
                    {user.user_type === 'certificate' ? 'X.509' : 'ServiceAccount'}
                  </Badge>
                </Tooltip>
              </td>
              <td className="px-4 py-3 text-surface-400 text-xs">
                {user.groups?.length > 0 ? user.groups.join(', ') : <span className="text-surface-500">—</span>}
              </td>
              <td className="px-4 py-3 text-surface-400 text-xs tabular-nums">
                <div>{new Date(user.created_at).toLocaleDateString()}</div>
                {user.cert_expiry && (
                  <div className="mt-1"><ExpiryBadge expiry={user.cert_expiry} /></div>
                )}
              </td>
              <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                <div className="flex items-center justify-end gap-2">
                  {user.user_type === 'certificate' && !user.imported && (
                    <Button
                      size="sm"
                      variant="secondary"
                      title="Renew certificate"
                      onClick={() => setRenewTarget(user.name)}
                      className={
                        user.cert_expiry && Math.floor((new Date(user.cert_expiry).getTime() - Date.now()) / 86_400_000) < 30
                          ? 'text-amber-400 border-amber-500/40 hover:border-amber-400'
                          : ''
                      }
                    >
                      <RefreshCw size={12} /> Renew
                    </Button>
                  )}
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
    <Pagination page={page} pageSize={PAGE_SIZE} total={sorted.length} onChange={setPage} />
    <RenewCertModal username={renewTarget} onClose={() => setRenewTarget(null)} />
    </>
  )
}
