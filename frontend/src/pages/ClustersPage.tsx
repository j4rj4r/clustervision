import { useState } from 'react'
import { Plus, Server, Trash2, TriangleAlert } from 'lucide-react'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import AddClusterModal from '../components/clusters/AddClusterModal'
import { useClusters, useRemoveCluster } from '../hooks/useCluster'
import { useClusterStore } from '../store/clusterStore'

export default function ClustersPage() {
  const { data: clusters = [], isLoading } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()
  const remove = useRemoveCluster()
  const [addOpen, setAddOpen] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<string | null>(null)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Clusters</h1>
          <p className="text-sm text-surface-400 mt-0.5">Manage connected clusters</p>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <Plus size={14} /> Add
        </Button>
      </div>

      <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-surface-400">Loading...</div>
        ) : clusters.length === 0 ? (
          <div className="py-16 text-center text-sm text-surface-400">No clusters</div>
        ) : (
          <div className="divide-y divide-surface-700">
            {clusters.map((c) => (
              <div
                key={c.name}
                className={`flex items-center gap-4 px-4 py-3 transition-colors cursor-pointer hover:bg-surface-700/40 ${
                  activeCluster === c.name ? 'bg-brand-600/10 border-l-2 border-brand-500' : ''
                }`}
                onClick={() => setActiveCluster(c.name)}
              >
                <Server size={16} className={activeCluster === c.name ? 'text-brand-400' : 'text-surface-400'} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-surface-100">{c.name}</span>
                    {c.is_local && <Badge variant="success">local</Badge>}
                    {activeCluster === c.name && <Badge variant="info">active</Badge>}
                  </div>
                  {!c.is_local && (
                    <p className="text-xs text-surface-400 truncate mt-0.5">{c.api_url}</p>
                  )}
                </div>
                {!c.is_local && (
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label="Remove cluster"
                    onClick={(e) => { e.stopPropagation(); setRemoveTarget(c.name) }}
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

      <Modal open={!!removeTarget} onClose={() => setRemoveTarget(null)} title="Remove cluster" size="sm">
        <div className="space-y-5">
          <div className="flex gap-3 p-3 rounded-lg bg-red-950/40 border border-red-500/20">
            <TriangleAlert size={16} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-sm text-surface-200">
              Remove <span className="font-mono font-semibold text-surface-100">{removeTarget}</span> from
              ClusterVision? The cluster itself is untouched, but its stored connection credentials are deleted.
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setRemoveTarget(null)} className="flex-1">Cancel</Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() => remove.mutate(removeTarget!, { onSuccess: () => setRemoveTarget(null) })}
              className="flex-1"
            >
              <Trash2 size={14} /> Remove
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
