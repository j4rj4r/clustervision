import { ChevronDown, ChevronRight, Shield } from 'lucide-react'
import { useState } from 'react'
import Badge from '../ui/Badge'
import type { RoleRead } from '../../types/rbac'

interface Props {
  roles: RoleRead[]
  title: string
}

export default function RoleList({ roles, title }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (roles.length === 0) return null

  return (
    <div>
      <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">{title}</h3>
      <div className="bg-slate-900 border border-slate-800 rounded-lg divide-y divide-slate-800">
        {roles.map((role) => (
          <div key={role.name}>
            <button
              onClick={() => setExpanded(expanded === role.name ? null : role.name)}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-800/50 text-left transition-colors"
            >
              {expanded === role.name ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
              <Shield size={14} className="text-brand-400" />
              <span className="font-mono text-sm text-slate-200 flex-1">{role.name}</span>
              {role.is_system && <Badge>system</Badge>}
              <span className="text-xs text-slate-500">{role.rules?.length ?? 0} rules</span>
            </button>

            {expanded === role.name && (
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
