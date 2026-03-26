import { useState } from 'react'
import { CheckCircle, XCircle, ShieldQuestion } from 'lucide-react'
import Button from '../ui/Button'
import Select from '../ui/Select'
import { useCheckAccess, useNamespaces } from '../../hooks/useRbac'
import type { CheckAccessResult } from '../../types/rbac'

const COMMON_VERBS = ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete', 'deletecollection']

const COMMON_RESOURCES = [
  'pods', 'deployments', 'services', 'configmaps', 'secrets',
  'serviceaccounts', 'roles', 'rolebindings', 'clusterroles', 'clusterrolebindings',
  'namespaces', 'nodes', 'persistentvolumes', 'persistentvolumeclaims',
]

export default function AccessSimulatorPanel() {
  const { data: namespaces = [] } = useNamespaces()
  const checkAccess = useCheckAccess()

  const [user, setUser] = useState('')
  const [verb, setVerb] = useState('get')
  const [resource, setResource] = useState('pods')
  const [customResource, setCustomResource] = useState('')
  const [namespace, setNamespace] = useState('')
  const [apiGroup, setApiGroup] = useState('')
  const [result, setResult] = useState<CheckAccessResult | null>(null)

  const effectiveResource = customResource.trim() || resource

  const handleCheck = () => {
    if (!user.trim() || !effectiveResource) return
    checkAccess.mutate(
      {
        user: user.trim(),
        verb,
        resource: effectiveResource,
        namespace: namespace || undefined,
        api_group: apiGroup || undefined,
      },
      { onSuccess: (data) => setResult(data) }
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-surface-900 border border-surface-600 rounded-xl p-6 space-y-4">
        {/* User */}
        <div className="space-y-1">
          <label className="block text-xs font-medium text-surface-300">User</label>
          <input
            value={user}
            onChange={(e) => { setUser(e.target.value); setResult(null) }}
            placeholder="alice, system:serviceaccount:default:mysa..."
            className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-sm font-mono text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          {/* Verb */}
          <Select
            label="Verb"
            value={verb}
            onChange={(e) => { setVerb(e.target.value); setResult(null) }}
            options={COMMON_VERBS.map((v) => ({ value: v, label: v }))}
          />

          {/* Namespace */}
          <Select
            label="Namespace (optional)"
            value={namespace}
            onChange={(e) => { setNamespace(e.target.value); setResult(null) }}
            options={[{ value: '', label: 'Cluster-wide' }, ...namespaces.map((n) => ({ value: n, label: n }))]}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          {/* Resource preset */}
          <Select
            label="Resource"
            value={customResource ? '__custom__' : resource}
            onChange={(e) => {
              if (e.target.value === '__custom__') return
              setResource(e.target.value)
              setCustomResource('')
              setResult(null)
            }}
            options={[
              ...COMMON_RESOURCES.map((r) => ({ value: r, label: r })),
              { value: '__custom__', label: '— custom —' },
            ]}
          />

          {/* Custom resource */}
          <div className="space-y-1">
            <label className="block text-xs font-medium text-surface-300">Custom resource</label>
            <input
              value={customResource}
              onChange={(e) => { setCustomResource(e.target.value); setResult(null) }}
              placeholder="e.g. pods/log"
              className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-sm font-mono text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* API group */}
        <div className="space-y-1">
          <label className="block text-xs font-medium text-surface-300">API Group <span className="text-surface-500">(empty = core)</span></label>
          <input
            value={apiGroup}
            onChange={(e) => { setApiGroup(e.target.value); setResult(null) }}
            placeholder="apps, rbac.authorization.k8s.io..."
            className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-sm font-mono text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <Button
          onClick={handleCheck}
          loading={checkAccess.isPending}
          disabled={!user.trim() || !effectiveResource}
          className="w-full justify-center"
        >
          Check access
        </Button>
      </div>

      {/* Result */}
      {result && (
        <div className={`flex items-start gap-4 p-5 rounded-xl border ${
          result.allowed
            ? 'bg-emerald-950/30 border-emerald-700/40'
            : 'bg-red-950/30 border-red-700/40'
        }`}>
          {result.allowed
            ? <CheckCircle size={28} className="text-emerald-400 shrink-0 mt-0.5" />
            : <XCircle size={28} className="text-red-400 shrink-0 mt-0.5" />
          }
          <div>
            <p className={`text-base font-semibold ${result.allowed ? 'text-emerald-300' : 'text-red-300'}`}>
              {result.allowed ? 'Allowed' : 'Denied'}
            </p>
            <p className="text-xs text-surface-400 mt-1 font-mono">
              {user} <span className="text-surface-500">can{result.allowed ? '' : 'not'}</span>{' '}
              <span className="text-brand-300">{verb}</span>{' '}
              <span className="text-surface-200">{effectiveResource}</span>
              {namespace && <> in <span className="text-surface-200">{namespace}</span></>}
            </p>
            {result.reason && (
              <p className="text-xs text-surface-500 mt-2 italic">{result.reason}</p>
            )}
          </div>
        </div>
      )}

      {!result && !checkAccess.isPending && (
        <div className="flex items-center gap-3 text-surface-500 text-sm">
          <ShieldQuestion size={18} />
          <span>Fill in the form and click "Check access" to simulate a permission check.</span>
        </div>
      )}
    </div>
  )
}
