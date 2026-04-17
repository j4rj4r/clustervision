import { NavLink } from 'react-router-dom'
import { Users, Shield, FileCode2, Server, Key } from 'lucide-react'

const links = [
  { to: '/users',      icon: Users,     label: 'Users'      },
  { to: '/rbac',       icon: Shield,    label: 'Permissions' },
  { to: '/kubeconfig', icon: FileCode2,  label: 'Kubeconfig'  },
  { to: '/tokens',     icon: Key,       label: 'History'    },
  { to: '/clusters',   icon: Server,    label: 'Clusters'   },
]

export default function Sidebar() {
  return (
    <aside className="w-52 bg-surface-900 border-r border-surface-700/50 flex flex-col">
      <div className="px-4 py-4 border-b border-surface-700/40">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-brand-600/15 ring-1 ring-brand-500/30 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] flex items-center justify-center">
            <span className="text-brand-400 text-[10px] font-bold tracking-tight">CV</span>
          </div>
          <span className="font-semibold text-surface-100 text-sm tracking-tight">ClusterVision</span>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-all ${
                isActive
                  ? 'bg-brand-600/12 text-brand-300 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]'
                  : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/70'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} className={`shrink-0 ${isActive ? 'text-brand-400' : ''}`} />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-surface-700/40">
        <p className="text-[11px] text-surface-500 tabular-nums">{__APP_VERSION__}</p>
      </div>
    </aside>
  )
}
