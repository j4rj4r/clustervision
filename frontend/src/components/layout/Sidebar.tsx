import { NavLink } from 'react-router-dom'
import { Users, Shield, FileCode2, Server, Key, Settings, Clock, ScrollText, LayoutDashboard } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useAccessRequests } from '../../hooks/useAccessRequests'

const links = [
  { to: '/dashboard',        icon: LayoutDashboard, label: 'Dashboard', desc: 'Overview'                 },
  { to: '/users',            icon: Users,     label: 'Users',           desc: 'Manage cluster users'    },
  { to: '/rbac',             icon: Shield,    label: 'Permissions',     desc: 'Roles & bindings'        },
  { to: '/access-requests',  icon: Clock,     label: 'Access Requests', desc: 'Time-boxed role grants'  },
  { to: '/kubeconfig',       icon: FileCode2, label: 'Kubeconfig',      desc: 'Generate access config'  },
  { to: '/tokens',           icon: Key,       label: 'History',         desc: 'Kubeconfig generations'  },
  { to: '/clusters',         icon: Server,    label: 'Clusters',        desc: 'Connected clusters'      },
]

export default function Sidebar() {
  const isAdmin = useAuthStore((s) => s.isAdmin())
  // Same cached query the Access Requests page uses — admins see everyone's
  // pending count (needs their action), others see their own (in progress).
  const { data: accessRequests = [] } = useAccessRequests()
  const pendingCount = accessRequests.filter((r) => r.status === 'pending').length

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
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-tight">{label}</p>
                  <p className={`text-xs leading-tight truncate ${isActive ? 'text-brand-400/60' : 'text-surface-600'}`}>{desc}</p>
                </div>
                {to === '/access-requests' && pendingCount > 0 && (
                  <span className="shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-semibold flex items-center justify-center">
                    {pendingCount}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Settings & Audit log — admin only */}
      {isAdmin && (
        <div className="px-2 pb-2 border-t border-surface-700/60 pt-2 space-y-0.5">
          <NavLink
            to="/settings"
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
                <Settings size={17} className="shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight">Settings</p>
                  <p className={`text-xs leading-tight truncate ${isActive ? 'text-brand-400/60' : 'text-surface-600'}`}>Access management</p>
                </div>
              </>
            )}
          </NavLink>
          <NavLink
            to="/audit-log"
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
                <ScrollText size={17} className="shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium leading-tight">Audit Log</p>
                  <p className={`text-xs leading-tight truncate ${isActive ? 'text-brand-400/60' : 'text-surface-600'}`}>Who did what</p>
                </div>
              </>
            )}
          </NavLink>
        </div>
      )}

      <div className="px-5 py-3 border-t border-surface-600">
        <p className="text-xs text-surface-400">{__APP_VERSION__}</p>
      </div>
    </aside>
  )
}
