import { useState } from 'react'
import { ChevronDown, ChevronRight, Copy, Pencil, Trash2 } from 'lucide-react'
import Badge from '../ui/Badge'
import type { RoleRead } from '../../types/rbac'

interface Props {
  roles: RoleRead[]
  title: string
  onEdit?: (role: RoleRead) => void
  onCopy?: (role: RoleRead) => void
  onDelete?: (role: RoleRead) => void
}

export default function RoleList({ roles, title, onEdit, onCopy, onDelete }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  if (roles.length === 0) return (
    <div className="text-center py-8 text-surface-500 text-sm">{title ? `${title} — ` : ''}No roles</div>
  )

  const toggle = (name: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  return (
    <div>
      {title && <h3 className="text-xs font-semibold text-surface-400 uppercase tracking-widest mb-3 px-1">{title}</h3>}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-600 bg-surface-900/50">
            <th className="w-10 px-4 py-3" />
            <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Name</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Rules</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Status</th>
            <th className="px-4 py-3 text-right text-xs font-medium text-surface-400 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-700">
          {roles.map((role) => (
            <>
              <tr key={role.name} className="hover:bg-surface-700/40 transition-colors">
                <td className="px-4 py-3 w-10">
                  <button
                    aria-label={expanded.has(role.name) ? 'Collapse' : 'Expand'}
                    aria-expanded={expanded.has(role.name)}
                    onClick={() => toggle(role.name)}
                    className="p-1 rounded text-surface-400 hover:text-surface-200 hover:bg-surface-600/50 transition-colors"
                  >
                    {expanded.has(role.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </button>
                </td>
                <td className="px-4 py-3 font-mono text-surface-100">{role.name}</td>
                <td className="px-4 py-3 text-surface-400 text-xs">{role.rules?.length ?? 0}</td>
                <td className="px-4 py-3">
                  {role.is_system
                    ? <Badge variant="warning" dot>system</Badge>
                    : <Badge variant="success" dot>custom</Badge>
                  }
                </td>
                <td className="px-4 py-3">
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
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
