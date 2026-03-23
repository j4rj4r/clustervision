import { useSearchParams } from 'react-router-dom'
import { FileCode2 } from 'lucide-react'
import KubeconfigPanel from '../components/kubeconfig/KubeconfigPanel'

export default function KubeconfigPage() {
  const [searchParams] = useSearchParams()
  const preselectedName = searchParams.get('user') ?? undefined
  const preselectedNamespace = searchParams.get('namespace') ?? undefined

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Kubeconfig</h1>
        <p className="text-sm text-slate-500 mt-0.5">Generate a kubeconfig file for any user</p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-lg bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
            <FileCode2 size={18} className="text-brand-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-200">Generate kubeconfig</p>
            <p className="text-xs text-slate-500">
              For certificate users, you must provide your private key (not stored by ClusterVision).
            </p>
          </div>
        </div>

        <KubeconfigPanel preselectedName={preselectedName} preselectedNamespace={preselectedNamespace} />
      </div>
    </div>
  )
}
