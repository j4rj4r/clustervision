import { useState } from 'react'
import { Plus, Server, Trash2 } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import AddClusterModal from '../components/clusters/AddClusterModal'
import { useClusters, useRemoveCluster } from '../hooks/useCluster'
import { useClusterStore } from '../store/clusterStore'

export default function ClustersPage() {
  const { data: clusters = [], isLoading } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()
  const remove = useRemoveCluster()
  const [addOpen, setAddOpen] = useState(false)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Clusters</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage connected clusters</p>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <Plus size={14} /> Add
        </Button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-slate-500">Loading...</div>
        ) : clusters.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-500">No clusters</div>
        ) : (
          <div className="divide-y divide-slate-800">
            {clusters.map((c) => (
              <div
                key={c.name}
                className={`flex items-center gap-4 px-4 py-3 transition-colors cursor-pointer hover:bg-slate-800/50 ${
                  activeCluster === c.name ? 'bg-brand-600/10 border-l-2 border-brand-500' : ''
                }`}
                onClick={() => setActiveCluster(c.name)}
              >
                <Server size={16} className={activeCluster === c.name ? 'text-brand-400' : 'text-slate-500'} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-slate-100">{c.name}</span>
                    {c.is_local && <Badge variant="success">local</Badge>}
                    {activeCluster === c.name && <Badge variant="info">active</Badge>}
                  </div>
                  {!c.is_local && (
                    <p className="text-xs text-slate-500 truncate mt-0.5">{c.api_url}</p>
                  )}
                </div>
                {!c.is_local && (
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label="Remove cluster"
                    onClick={(e) => { e.stopPropagation(); remove.mutate(c.name) }}
                    className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
                  >
                    <Trash2 size={13} />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {addOpen && <AddClusterModal onClose={() => setAddOpen(false)} />}
    </div>
  )
}
