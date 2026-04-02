import { Fragment, useState } from 'react'
import { ChevronDown, ChevronRight, Copy, Pencil, Trash2, ChevronsUpDown, ArrowUp, ArrowDown, ShieldOff, Plus } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Pagination from '../ui/Pagination'
import type { RoleRead } from '../../types/rbac'

const PAGE_SIZE = 25

interface Props {
  roles: RoleRead[]
  title: string
  onEdit?: (role: RoleRead) => void
  onCopy?: (role: RoleRead) => void
  onDelete?: (role: RoleRead) => void
  onCreateClick?: () => void
}

type SortCol = 'name' | 'rules' | 'status'
type SortDir = 'asc' | 'desc'

function SortIcon({ col, sortCol, sortDir }: { col: SortCol; sortCol: SortCol; sortDir: SortDir }) {
  if (col !== sortCol) return <ChevronsUpDown size={12} className="opacity-30 ml-1 inline" />
  return sortDir === 'asc'
    ? <ArrowUp size={12} className="ml-1 inline text-brand-400" />
    : <ArrowDown size={12} className="ml-1 inline text-brand-400" />
}

export default function RoleList({ roles, title, onEdit, onCopy, onDelete, onCreateClick }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [sortCol, setSortCol] = useState<SortCol>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [page, setPage] = useState(0)

  const toggleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortCol(col); setSortDir('asc') }
    setPage(0)
  }

  const sorted = [...roles].sort((a, b) => {
    let cmp = 0
    if (sortCol === 'name') cmp = a.name.localeCompare(b.name)
    else if (sortCol === 'rules') cmp = (a.rules?.length ?? 0) - (b.rules?.length ?? 0)
    else if (sortCol === 'status') cmp = Number(a.is_system) - Number(b.is_system)
    return sortDir === 'asc' ? cmp : -cmp
  })

  const paginated = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  if (roles.length === 0) return (
    <div className="text-center py-14 space-y-4">
      <ShieldOff size={32} className="mx-auto text-surface-600" />
      <div>
        <p className="text-sm font-medium text-surface-400">No roles in {title || 'this namespace'}</p>
        <p className="text-xs text-surface-500 mt-1">Create a role to start assigning permissions.</p>
      </div>
      {onCreateClick && (
        <Button size="sm" onClick={onCreateClick}>
          <Plus size={13} /> Create role
        </Button>
      )}
    </div>
  )

  const toggle = (name: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  const thClass = 'px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider cursor-pointer select-none hover:text-surface-200 transition-colors'

  return (
    <div>
      {title && <h3 className="text-xs font-semibold text-surface-400 uppercase tracking-widest mb-3 px-1">{title}</h3>}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-600 bg-surface-900/50">
            <th className="w-10 px-4 py-3" />
            <th className={thClass} onClick={() => toggleSort('name')}>
              Name <SortIcon col="name" sortCol={sortCol} sortDir={sortDir} />
            </th>
            <th className={thClass} onClick={() => toggleSort('rules')}>
              Rules <SortIcon col="rules" sortCol={sortCol} sortDir={sortDir} />
            </th>
            <th className={thClass} onClick={() => toggleSort('status')}>
              Status <SortIcon col="status" sortCol={sortCol} sortDir={sortDir} />
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-surface-400 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-700">
          {paginated.map((role) => (
            <Fragment key={role.name}>
              <tr
                className="hover:bg-surface-700/40 transition-colors cursor-pointer"
                onClick={() => toggle(role.name)}
              >
                <td className="px-4 py-3 w-10">
                  <span className="p-1 rounded text-surface-400">
                    {expanded.has(role.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-surface-100">{role.name}</td>
                <td className="px-4 py-3 text-surface-400 text-xs">{role.rules?.length ?? 0}</td>
                <td className="px-4 py-3">
                  {role.is_system
                    ? <Badge variant="warning" dot>system</Badge>
                    : <Badge variant="success" dot>custom</Badge>
                  }
                </td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-2">
                    {onCopy && (
                      <button
                        aria-label="Copy role"
                        onClick={() => onCopy(role)}
                        className="p-1 text-surface-500 hover:text-surface-200 transition-colors"
                      >
                        <Copy size={13} />
                      </button>
                    )}
                    {!role.is_system && onEdit && (
                      <button
                        aria-label="Edit role"
                        onClick={() => onEdit(role)}
                        className="p-1 text-surface-500 hover:text-surface-200 transition-colors"
                      >
                        <Pencil size={13} />
                      </button>
                    )}
                    {!role.is_system && onDelete && (
                      <button
                        aria-label="Delete role"
                        onClick={() => onDelete(role)}
                        className="p-1 text-surface-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
              {expanded.has(role.name) && (
                <tr key={`${role.name}-rules`}>
                  <td colSpan={5} className="bg-surface-950/60 px-12 py-4 border-b border-surface-600">
                    <div className="space-y-2">
                      {role.rules?.map((rule, i) => (
                        <div key={i} className="flex flex-wrap gap-1.5 text-xs">
                          <span className="text-surface-500">groups:</span>
                          {rule.api_groups.map((g) => <Badge key={g} variant="default">{g || 'core'}</Badge>)}
                          <span className="text-surface-500 ml-2">resources:</span>
                          {rule.resources.map((r) => <Badge key={r} variant="info">{r}</Badge>)}
                          <span className="text-surface-500 ml-2">verbs:</span>
                          {rule.verbs.map((v) => <Badge key={v} variant="success">{v}</Badge>)}
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      <Pagination page={page} pageSize={PAGE_SIZE} total={sorted.length} onChange={setPage} />
    </div>
  )
}
