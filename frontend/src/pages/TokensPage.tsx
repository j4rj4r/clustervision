import { useState } from 'react'
import { RefreshCw, Trash2, RotateCcw } from 'lucide-react'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import { useQueryClient } from '@tanstack/react-query'
import {
  useTokenHistory,
  useDeleteHistoryEntry,
  useClearHistory,
  useSaTokens,
  useRevokeSaToken,
  useRotateSaToken,
} from '../hooks/useTokens'
import type { SaTokenInfo, TokenHistoryEntry } from '../types/token'

type Tab = 'history' | 'sa-tokens'

export default function TokensPage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('history')
  const [clearConfirm, setClearConfirm] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<SaTokenInfo | null>(null)
  const [rotateTarget, setRotateTarget] = useState<SaTokenInfo | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<TokenHistoryEntry | null>(null)

  const { data: history = [], isLoading: loadingHistory } = useTokenHistory()
  const { data: saTokens = [], isLoading: loadingSA } = useSaTokens()

  const deleteEntry = useDeleteHistoryEntry()
  const clearHistory = useClearHistory()
  const revokeSA = useRevokeSaToken()
  const rotateSA = useRotateSaToken()

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['token-history'] })
    qc.invalidateQueries({ queryKey: ['sa-tokens'] })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Tokens</h1>
          <p className="text-sm text-surface-400 mt-0.5">Kubeconfig generation history and service account tokens</p>
        </div>
        <Button variant="ghost" size="sm" onClick={refresh}>
          <RefreshCw size={13} />
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-surface-600">
        {([
          { key: 'history', label: 'Generation History' },
          { key: 'sa-tokens', label: 'SA Tokens' },
        ] as { key: Tab; label: string }[]).map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === key
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-surface-400 hover:text-surface-200 hover:border-surface-500'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* History tab */}
      {tab === 'history' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Button
              variant="danger"
              size="sm"
              disabled={history.length === 0}
              onClick={() => setClearConfirm(true)}
            >
              <Trash2 size={13} /> Clear all
            </Button>
          </div>
          {loadingHistory ? (
            <div className="text-sm text-surface-400 text-center py-8">Loading...</div>
          ) : history.length === 0 ? (
            <div className="text-sm text-surface-400 text-center py-12">No generation history yet.</div>
          ) : (
            <div className="rounded-lg border border-surface-600 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-surface-800 text-surface-400 text-xs uppercase tracking-wide">
                    <th className="px-4 py-3 text-left">User</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-left">Namespace</th>
                    <th className="px-4 py-3 text-left">Generated at</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700">
                  {history.map((entry) => (
                    <tr key={entry.id} className="hover:bg-surface-800/50 transition-colors">
                      <td className="px-4 py-3 font-mono text-surface-200">{entry.user}</td>
                      <td className="px-4 py-3">
                        <Badge variant={entry.user_type === 'certificate' ? 'info' : 'default'}>
                          {entry.user_type}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 font-mono text-surface-300">{entry.namespace}</td>
                      <td className="px-4 py-3 text-surface-400 text-xs">
                        {new Date(entry.generated_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setDeleteTarget(entry)}
                          className="text-surface-400 hover:text-red-400 transition-colors"
                          title="Delete entry"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* SA Tokens tab */}
      {tab === 'sa-tokens' && (
        <div className="space-y-3">
          {loadingSA ? (
            <div className="text-sm text-surface-400 text-center py-8">Loading...</div>
          ) : saTokens.length === 0 ? (
            <div className="text-sm text-surface-400 text-center py-12">No managed SA tokens found.</div>
          ) : (
            <div className="rounded-lg border border-surface-600 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-surface-800 text-surface-400 text-xs uppercase tracking-wide">
                    <th className="px-4 py-3 text-left">Secret</th>
                    <th className="px-4 py-3 text-left">Service Account</th>
                    <th className="px-4 py-3 text-left">Namespace</th>
                    <th className="px-4 py-3 text-left">Created</th>
                    <th className="px-4 py-3 text-left">Token</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700">
                  {saTokens.map((t) => (
                    <tr key={`${t.namespace}/${t.secret_name}`} className="hover:bg-surface-800/50 transition-colors">
                      <td className="px-4 py-3 font-mono text-surface-200">{t.secret_name}</td>
                      <td className="px-4 py-3 font-mono text-surface-300">{t.sa_name}</td>
                      <td className="px-4 py-3 font-mono text-surface-300">{t.namespace}</td>
                      <td className="px-4 py-3 text-surface-400 text-xs">
                        {t.created_at ? new Date(t.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={t.token_present ? 'success' : 'danger'}>
                          {t.token_present ? 'present' : 'missing'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-3">
                          <button
                            onClick={() => setRotateTarget(t)}
                            className="text-surface-400 hover:text-brand-400 transition-colors"
                            title="Rotate token"
                          >
                            <RotateCcw size={14} />
                          </button>
                          <button
                            onClick={() => setRevokeTarget(t)}
                            className="text-surface-400 hover:text-red-400 transition-colors"
                            title="Revoke token"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Confirm clear history */}
      <Modal open={clearConfirm} onClose={() => setClearConfirm(false)} title="Clear history" size="sm">
        <p className="text-sm text-surface-300 mb-6">
          Delete all {history.length} generation history entries? This cannot be undone.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => setClearConfirm(false)}>Cancel</Button>
          <Button
            variant="danger"
            className="flex-1"
            loading={clearHistory.isPending}
            onClick={() => clearHistory.mutate(undefined, { onSuccess: () => setClearConfirm(false) })}
          >
            Clear all
          </Button>
        </div>
      </Modal>

      {/* Confirm delete single entry */}
      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete entry" size="sm">
        <p className="text-sm text-surface-300 mb-6">
          Remove this history entry for{' '}
          <span className="font-mono text-white">{deleteTarget?.user}</span>?
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            className="flex-1"
            loading={deleteEntry.isPending}
            onClick={() =>
              deleteEntry.mutate(deleteTarget!.id, { onSuccess: () => setDeleteTarget(null) })
            }
          >
            Delete
          </Button>
        </div>
      </Modal>

      {/* Confirm revoke SA token */}
      <Modal open={!!revokeTarget} onClose={() => setRevokeTarget(null)} title="Revoke SA token" size="sm">
        <p className="text-sm text-surface-300 mb-6">
          Delete secret{' '}
          <span className="font-mono text-white">{revokeTarget?.secret_name}</span>?{' '}
          All kubeconfigs using this token will stop working immediately.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => setRevokeTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            className="flex-1"
            loading={revokeSA.isPending}
            onClick={() =>
              revokeSA.mutate(
                { secretName: revokeTarget!.secret_name, namespace: revokeTarget!.namespace },
                { onSuccess: () => setRevokeTarget(null) },
              )
            }
          >
            Revoke
          </Button>
        </div>
      </Modal>

      {/* Confirm rotate SA token */}
      <Modal open={!!rotateTarget} onClose={() => setRotateTarget(null)} title="Rotate SA token" size="sm">
        <p className="text-sm text-surface-300 mb-6">
          Rotate token for{' '}
          <span className="font-mono text-white">{rotateTarget?.secret_name}</span>?{' '}
          The old token will be invalidated and a new one created. Kubeconfigs will need to be regenerated.
        </p>
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => setRotateTarget(null)}>Cancel</Button>
          <Button
            variant="primary"
            className="flex-1"
            loading={rotateSA.isPending}
            onClick={() =>
              rotateSA.mutate(
                {
                  secretName: rotateTarget!.secret_name,
                  saName: rotateTarget!.sa_name,
                  namespace: rotateTarget!.namespace,
                },
                { onSuccess: () => setRotateTarget(null) },
              )
            }
          >
            Rotate
          </Button>
        </div>
      </Modal>
    </div>
  )
}
