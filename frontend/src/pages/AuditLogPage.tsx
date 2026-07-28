import { useState } from 'react'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import { useAuditLog } from '../hooks/useAudit'
import type { AuditLogEntry } from '../types/audit'

const PAGE_SIZE = 25

function statusVariant(status: number): 'success' | 'warning' | 'danger' {
  if (status < 300) return 'success'
  if (status < 500) return 'warning'
  return 'danger'
}

function methodVariant(method: string): 'info' | 'danger' | 'default' {
  if (method === 'DELETE') return 'danger'
  if (method === 'POST' || method === 'PUT' || method === 'PATCH') return 'info'
  return 'default'
}

export default function AuditLogPage() {
  const qc = useQueryClient()
  const [actor, setActor] = useState('')
  const [pathContains, setPathContains] = useState('')
  const [offset, setOffset] = useState(0)
  const [payloadTarget, setPayloadTarget] = useState<AuditLogEntry | null>(null)

  const { data, isLoading } = useAuditLog({
    limit: PAGE_SIZE,
    offset,
    actor: actor || undefined,
    path_contains: pathContains || undefined,
  })
  const items = data?.items ?? []
  const total = data?.total ?? 0

  const resetAndFilter = (fn: () => void) => {
    setOffset(0)
    fn()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Audit Log</h1>
          <p className="text-sm text-surface-400 mt-0.5">
            Every mutating request against RBAC, users, tokens, clusters and Vault config — successful or not.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['audit-log'] })}>
          <RefreshCw size={13} />
        </Button>
      </div>

      <div className="flex gap-3">
        <div className="w-56">
          <Input
            placeholder="Filter by actor..."
            value={actor}
            onChange={(e) => resetAndFilter(() => setActor(e.target.value))}
          />
        </div>
        <div className="w-72">
          <Input
            placeholder="Filter by path (contains)..."
            value={pathContains}
            onChange={(e) => resetAndFilter(() => setPathContains(e.target.value))}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm text-surface-400 text-center py-8">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-surface-400 text-center py-12">No matching audit entries.</div>
      ) : (
        <div className="rounded-lg border border-surface-600 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surface-800 text-surface-400 text-xs uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Time</th>
                <th className="px-4 py-3 text-left">Actor</th>
                <th className="px-4 py-3 text-left">Method</th>
                <th className="px-4 py-3 text-left">Path</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-right">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {items.map((entry) => (
                <tr key={entry.id} className="hover:bg-surface-800/50 transition-colors">
                  <td className="px-4 py-3 text-surface-400 text-xs whitespace-nowrap">
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    {entry.actor ? (
                      <span className="font-mono text-surface-200">
                        {entry.actor}
                        {entry.actor_role && <span className="text-surface-500"> ({entry.actor_role})</span>}
                      </span>
                    ) : (
                      <span className="text-surface-500 italic">unknown</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={methodVariant(entry.method)}>{entry.method}</Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-surface-300 text-xs">{entry.path}</td>
                  <td className="px-4 py-3">
                    <Badge variant={statusVariant(entry.status_code)}>{entry.status_code}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {entry.payload ? (
                      <button
                        onClick={() => setPayloadTarget(entry)}
                        className="text-brand-400 hover:text-brand-300 text-xs transition-colors"
                      >
                        View
                      </button>
                    ) : (
                      <span className="text-surface-600 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > 0 && (
        <div className="flex items-center justify-between text-sm text-surface-400">
          <span>
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              <ChevronLeft size={13} /> Prev
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next <ChevronRight size={13} />
            </Button>
          </div>
        </div>
      )}

      <Modal open={!!payloadTarget} onClose={() => setPayloadTarget(null)} title="Request payload" size="lg">
        <pre className="bg-surface-900 border border-surface-600 rounded-md p-4 text-xs text-surface-200 overflow-auto max-h-96">
          {JSON.stringify(payloadTarget?.payload, null, 2)}
        </pre>
      </Modal>
    </div>
  )
}
