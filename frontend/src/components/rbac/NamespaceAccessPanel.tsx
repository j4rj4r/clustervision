import { useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import Badge from '../ui/Badge'
import Select from '../ui/Select'
import { useNamespaceAccess, useNamespaces } from '../../hooks/useRbac'
import { useQueryClient } from '@tanstack/react-query'
import { useClusterStore } from '../../store/clusterStore'
import type { NamespaceAccessEntry } from '../../types/rbac'

const KIND_VARIANT: Record<string, 'info' | 'default' | 'warning'> = {
  User: 'info',
  ServiceAccount: 'default',
  Group: 'warning',
}

const SCOPE_VARIANT: Record<string, 'success' | 'warning'> = {
  namespace: 'success',
  cluster: 'warning',
}

export default function NamespaceAccessPanel() {
  const qc = useQueryClient()
  const cluster = useClusterStore((s) => s.activeCluster)
  const { data: namespaces = [] } = useNamespaces()
  const [namespace, setNamespace] = useState('default')
  const [search, setSearch] = useState('')
  const [kindFilter, setKindFilter] = useState('')

  const { data: entries = [], isLoading, isError, refetch } = useNamespaceAccess(namespace)

  const filtered = entries.filter((e) => {
    const matchSearch = !search || e.subject.toLowerCase().includes(search.toLowerCase())
    const matchKind = !kindFilter || e.subject_kind === kindFilter
    return matchSearch && matchKind
  })

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-end gap-3 flex-wrap">
        <Select
          label="Namespace"
          value={namespace}
          onChange={(e) => setNamespace(e.target.value)}
          options={namespaces.map((n) => ({ value: n, label: n }))}
        />
        <Select
          label="Kind"
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value)}
          options={[
            { value: '', label: 'All kinds' },
            { value: 'User', label: 'User' },
            { value: 'ServiceAccount', label: 'ServiceAccount' },
            { value: 'Group', label: 'Group' },
          ]}
        />
        <div className="flex-1 min-w-48 space-y-1">
          <label className="block text-xs font-medium text-surface-300">Search</label>
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by subject name..."
              className="w-full bg-surface-900 border border-surface-600 rounded-md pl-8 pr-3 py-2 text-sm text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>
        <button
          onClick={() => { qc.invalidateQueries({ queryKey: ['namespace-access', cluster, namespace] }); refetch() }}
          className="pb-0.5 text-surface-400 hover:text-surface-200 transition-colors"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Table */}
      <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-sm text-surface-400">Loading...</div>
        ) : isError ? (
          <div className="py-16 text-center space-y-2">
            <p className="text-sm text-red-400">Failed to load access data.</p>
            <button onClick={() => refetch()} className="text-xs text-brand-400 hover:underline">Retry</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-sm text-surface-500">No entries found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-600 bg-surface-900/60">
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Subject</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Kind</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Role Kind</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Scope</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">Binding</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {filtered.map((e, i) => (
                <tr key={i} className="hover:bg-surface-700/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-surface-100 text-xs">
                    {e.subject}
                    {e.subject_namespace && (
                      <span className="text-surface-500 ml-1">({e.subject_namespace})</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={KIND_VARIANT[e.subject_kind] ?? 'default'}>{e.subject_kind}</Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-surface-200 text-xs">{e.role}</td>
                  <td className="px-4 py-3">
                    <Badge variant={e.role_kind === 'ClusterRole' ? 'warning' : 'info'}>{e.role_kind}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={SCOPE_VARIANT[e.scope]} dot>{e.scope}</Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-surface-500 text-xs">{e.binding}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-surface-500">
        Showing {filtered.length} of {entries.length} entries — includes RoleBindings in <span className="font-mono">{namespace}</span> and all ClusterRoleBindings.
      </p>
    </div>
  )
}
