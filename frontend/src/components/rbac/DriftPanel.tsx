import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw, Trash2, Wifi } from 'lucide-react'
import toast from 'react-hot-toast'
import { driftApi, type DriftEvent } from '../../api/drift'
import { useAuthStore } from '../../store/authStore'
import Badge from '../ui/Badge'
import Button from '../ui/Button'

const KIND_LABELS: Record<DriftEvent['kind'], { label: string; variant: 'danger' | 'warning' }> = {
  external_modification: { label: 'Modified externally', variant: 'danger' },
  label_stripped:        { label: 'Label removed',       variant: 'warning' },
  orphaned:              { label: 'Orphaned binding',    variant: 'warning' },
}

export default function DriftPanel() {
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['drift-events'],
    queryFn: () => driftApi.list(),
    refetchInterval: 30_000,
    enabled: isAdmin,
  })

  const scan = useMutation({
    mutationFn: driftApi.scan,
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['drift-events'] })
      if (res.count === 0) toast.success('No new drift detected')
      else toast.error(`${res.count} new drift event(s) detected`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const clear = useMutation({
    mutationFn: driftApi.clear,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['drift-events'] })
      toast.success('Drift events cleared')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (!isAdmin) return null

  const events = data?.events ?? []

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wifi size={14} className={events.length > 0 ? 'text-red-400' : 'text-emerald-400'} />
          <p className="text-sm font-medium text-surface-200">
            RBAC drift detection
          </p>
          {events.length > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-xs font-semibold">
              {events.length}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {events.length > 0 && (
            <Button size="sm" variant="ghost" loading={clear.isPending} onClick={() => clear.mutate()}>
              <Trash2 size={12} /> Clear
            </Button>
          )}
          <Button size="sm" variant="ghost" loading={scan.isPending} onClick={() => scan.mutate()}>
            <RefreshCw size={12} /> Scan now
          </Button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-xs text-surface-400 py-4 text-center">Loading...</p>
      ) : events.length === 0 ? (
        <div className="flex items-center gap-2.5 p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
          <p className="text-xs text-emerald-300">No drift detected — all managed bindings look healthy.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((evt, i) => {
            const meta = KIND_LABELS[evt.kind]
            return (
              <div key={i} className="flex items-start gap-3 p-3 bg-surface-800 border border-surface-600 rounded-lg">
                <AlertTriangle size={14} className={meta.variant === 'danger' ? 'text-red-400 mt-0.5 shrink-0' : 'text-amber-400 mt-0.5 shrink-0'} />
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-surface-100">{evt.binding_name}</span>
                    {evt.namespace && <Badge variant="default">{evt.namespace}</Badge>}
                    <Badge variant={meta.variant}>{meta.label}</Badge>
                  </div>
                  <p className="text-xs text-surface-400">{evt.detail}</p>
                  <p className="text-xs text-surface-600">{new Date(evt.detected_at).toLocaleString()}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
