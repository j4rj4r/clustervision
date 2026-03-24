import { ChevronDown, ChevronRight, Copy, Pencil, Shield, Trash2 } from 'lucide-react'
import { useState } from 'react'
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
    <div className="text-center py-8 text-slate-600 text-sm">{title} — no roles</div>
  )

  const toggle = (name: string) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })

  return (
    <div>
      {title && <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">{title}</h3>}
      <div className="bg-slate-900 border border-slate-800 rounded-lg divide-y divide-slate-800">
        {roles.map((role) => (
          <div key={role.name}>
            <div className="flex items-center gap-2 px-4 py-3 hover:bg-slate-800/50 transition-colors">
              <button
                aria-label={expanded.has(role.name) ? 'Collapse' : 'Expand'}
                aria-expanded={expanded.has(role.name)}
                onClick={() => toggle(role.name)}
                className="flex items-center gap-3 flex-1 min-w-0 text-left group"
              >
                <span className="p-1 rounded text-slate-500 group-hover:text-slate-300 group-hover:bg-slate-700/50 transition-colors shrink-0">
                  {expanded.has(role.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
                <Shield size={14} className="text-brand-400 shrink-0" />
                <span className="font-mono text-sm text-slate-200 flex-1 truncate">{role.name}</span>
                {role.is_system && <Badge>system</Badge>}
                <span className="text-xs text-slate-500 shrink-0">{role.rules?.length ?? 0} rules</span>
              </button>
              <div className="flex items-center gap-2 shrink-0">
                {onCopy && (
                  <button
                    aria-label="Copy role"
                    onClick={() => onCopy(role)}
                    className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
                  >
                    <Copy size={13} />
                  </button>
                )}
                {!role.is_system && onEdit && (
                  <button
                    aria-label="Edit role"
                    onClick={() => onEdit(role)}
                    className="p-1 text-slate-600 hover:text-slate-300 transition-colors"
                  >
                    <Pencil size={13} />
                  </button>
                )}
                {!role.is_system && onDelete && (
                  <button
                    aria-label="Delete role"
                    onClick={() => onDelete(role)}
                    className="p-1 text-slate-600 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            </div>

            {expanded.has(role.name) && (
              <div className="px-4 pb-4 bg-slate-950/50">
                <div className="divide-y divide-slate-800">
                  {role.rules?.map((rule, i) => (
                    <div key={i} className="py-2 text-xs font-mono">
                      <div className="flex flex-wrap gap-1">
                        <span className="text-slate-500">groups:</span>
                        {rule.api_groups.map((g) => <Badge key={g} variant="default">{g || 'core'}</Badge>)}
                        <span className="text-slate-500 ml-2">resources:</span>
                        {rule.resources.map((r) => <Badge key={r} variant="info">{r}</Badge>)}
                        <span className="text-slate-500 ml-2">verbs:</span>
                        {rule.verbs.map((v) => <Badge key={v} variant="success">{v}</Badge>)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
