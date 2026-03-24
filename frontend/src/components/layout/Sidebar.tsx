import { NavLink } from 'react-router-dom'
import { Users, Shield, FileCode2, Server } from 'lucide-react'

const links = [
  { to: '/users', icon: Users, label: 'Users' },
  { to: '/rbac', icon: Shield, label: 'RBAC' },
  { to: '/kubeconfig', icon: FileCode2, label: 'Kubeconfig' },
  { to: '/clusters', icon: Server, label: 'Clusters' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-slate-900 border-r border-slate-800 flex flex-col">
      <div className="px-5 py-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-brand-500 flex items-center justify-center">
            <span className="text-white text-xs font-bold">CV</span>
          </div>
          <span className="font-semibold text-slate-100 text-sm">ClusterVision</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-600 text-white'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-500">{__APP_VERSION__}</p>
      </div>
    </aside>
  )
}
