import { NavLink } from 'react-router-dom'
import { Users, Shield, FileCode2, Server, Key } from 'lucide-react'

const links = [
  { to: '/users',      icon: Users,    label: 'Users',      desc: 'Manage cluster users'     },
  { to: '/rbac',       icon: Shield,   label: 'Permissions', desc: 'Roles & bindings'         },
  { to: '/kubeconfig', icon: FileCode2, label: 'Kubeconfig', desc: 'Generate access config'   },
  { to: '/tokens',     icon: Key,      label: 'History',    desc: 'Kubeconfig generations'   },
  { to: '/clusters',   icon: Server,   label: 'Clusters',   desc: 'Connected clusters'        },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-surface-900 border-r border-surface-600 flex flex-col">
      <div className="px-5 py-4 border-b border-surface-700/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-brand-600/20 ring-1 ring-brand-500/40 flex items-center justify-center">
            <span className="text-brand-400 text-[10px] font-bold tracking-tight">CV</span>
          </div>
          <span className="font-semibold text-surface-100 text-sm tracking-tight">ClusterVision</span>
        </div>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {links.map(({ to, icon: Icon, label, desc }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md transition-all ${
                isActive
                  ? 'bg-brand-600/10 text-brand-300 ring-1 ring-brand-500/20'
                  : 'text-surface-400 hover:text-surface-100 hover:bg-surface-800'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={17} className="shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight">{label}</p>
                  <p className={`text-xs leading-tight truncate ${isActive ? 'text-brand-400/60' : 'text-surface-600'}`}>{desc}</p>
                </div>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-3 border-t border-surface-600">
        <p className="text-xs text-surface-400">{__APP_VERSION__}</p>
      </div>
    </aside>
  )
}
