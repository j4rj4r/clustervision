import { useQuery } from '@tanstack/react-query'
import { User, ShieldCheck, Key, AlertTriangle, FileCode2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'

interface Binding {
  name: string
  namespace: string | null
  role_ref: string
  role_kind: string
}

interface CertInfo {
  cert_expiry: string | null
  created_at: string
  imported: boolean
  groups: string[]
}

interface ProfileData {
  username: string
  role: 'admin' | 'viewer'
  cert_info: CertInfo | null
  cluster_bindings: Binding[]
  namespace_bindings: Binding[]
}

function ExpiryInfo({ expiry }: { expiry: string }) {
  const days = Math.floor((new Date(expiry).getTime() - Date.now()) / 86_400_000)
  const variant = days < 0 ? 'danger' : days < 30 ? 'danger' : days < 90 ? 'warning' : 'success'
  const label = days < 0 ? 'Expired' : `${days}d remaining`
  return <Badge variant={variant}>{label}</Badge>
}

export default function ProfilePage() {
  const navigate = useNavigate()
  const currentUser = useAuthStore((s) => s.user)
  const isAdmin = useAuthStore((s) => s.isAdmin())

  const { data, isLoading } = useQuery<ProfileData>({
    queryKey: ['profile-me'],
    queryFn: () => client.get('/profile/me').then((r) => r.data),
  })

  const allBindings = [...(data?.cluster_bindings ?? []), ...(data?.namespace_bindings ?? [])]

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-semibold text-surface-100">My profile</h1>
        <p className="text-sm text-surface-400 mt-0.5">Your identity and permissions in the cluster</p>
      </div>

      {/* Identity card */}
      <div className="bg-surface-900 border border-surface-600 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
            <User size={20} className="text-brand-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-surface-100 font-mono">{currentUser?.username}</p>
            <Badge variant={currentUser?.role === 'admin' ? 'info' : 'default'} dot>
              {currentUser?.role}
            </Badge>
          </div>
        </div>

        {/* Certificate info */}
        {data?.cert_info && (
          <div className="border-t border-surface-700 pt-4 space-y-2">
            <p className="text-xs font-medium text-surface-400 uppercase tracking-wide">Certificate (X.509)</p>
            <div className="flex flex-wrap gap-4 text-xs text-surface-300">
              <span>Created {new Date(data.cert_info.created_at).toLocaleDateString()}</span>
              {data.cert_info.cert_expiry && (
                <span className="flex items-center gap-1.5">
                  Expires <ExpiryInfo expiry={data.cert_info.cert_expiry} />
                </span>
              )}
              {data.cert_info.imported && (
                <Badge variant="warning">Imported — no managed CSR</Badge>
              )}
            </div>
            {data.cert_info.groups.length > 0 && (
              <p className="text-xs text-surface-400">Groups: <span className="font-mono text-surface-200">{data.cert_info.groups.join(', ')}</span></p>
            )}
            {data.cert_info.cert_expiry && Math.floor((new Date(data.cert_info.cert_expiry).getTime() - Date.now()) / 86_400_000) < 30 && (
              <div className="flex items-start gap-2 p-2.5 bg-amber-900/20 border border-amber-500/30 rounded-lg mt-2">
                <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
                <p className="text-xs text-amber-300">Your certificate is expiring soon. Ask an admin to renew it.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* K8s Permissions */}
      <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-surface-700 flex items-center gap-2">
          <ShieldCheck size={15} className="text-brand-400" />
          <p className="text-sm font-medium text-surface-200">Cluster permissions</p>
        </div>

        {isLoading ? (
          <div className="py-10 text-center text-sm text-surface-400">Loading...</div>
        ) : allBindings.length === 0 ? (
          <div className="py-10 text-center space-y-1">
            <Key size={24} className="mx-auto text-surface-600 opacity-40" />
            <p className="text-sm text-surface-400">No roles assigned yet</p>
            <p className="text-xs text-surface-500">Ask an admin to grant you access</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700 bg-surface-900/60">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-surface-400">Role</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-surface-400">Scope</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-surface-400">Binding</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {allBindings.map((b) => (
                <tr key={b.name} className="hover:bg-surface-800/40">
                  <td className="px-4 py-2.5 font-mono text-surface-100 text-xs">{b.role_ref}</td>
                  <td className="px-4 py-2.5">
                    {b.namespace
                      ? <Badge variant="default">{b.namespace}</Badge>
                      : <Badge variant="info">Cluster-wide</Badge>
                    }
                  </td>
                  <td className="px-4 py-2.5 font-mono text-surface-500 text-xs truncate max-w-[180px]">{b.name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Quick actions */}
      <div className="flex gap-3">
        <Button variant="secondary" onClick={() => navigate('/kubeconfig')}>
          <FileCode2 size={14} /> Generate kubeconfig
        </Button>
        {!isAdmin && (
          <Button variant="ghost" onClick={() => navigate('/access-requests/new')}>
            Request more access
          </Button>
        )}
      </div>
    </div>
  )
}
