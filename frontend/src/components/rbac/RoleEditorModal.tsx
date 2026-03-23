import { useState } from 'react'
import { Plus, Trash2, X } from 'lucide-react'
import Button from '../ui/Button'
import type { PolicyRule, RoleRead } from '../../types/rbac'

const ALL_VERBS = ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete', 'deletecollection']

interface Props {
  role?: RoleRead
  namespace?: string
  isCluster: boolean
  onSave: (name: string, rules: PolicyRule[], namespace?: string) => void
  onClose: () => void
  loading?: boolean
}

function emptyRule(): PolicyRule {
  return { api_groups: [''], resources: [], verbs: [] }
}

function RuleRow({
  rule,
  onChange,
  onRemove,
}: {
  rule: PolicyRule
  onChange: (r: PolicyRule) => void
  onRemove: () => void
}) {
  const toggleVerb = (v: string) => {
    const next = rule.verbs.includes(v) ? rule.verbs.filter((x) => x !== v) : [...rule.verbs, v]
    onChange({ ...rule, verbs: next })
  }

  return (
    <div className="border border-slate-700 rounded-lg p-3 space-y-2 bg-slate-900">
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-slate-500 mb-1">API Groups <span className="text-slate-600">(virgule, vide = core)</span></label>
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-brand-500"
            value={rule.api_groups.join(', ')}
            onChange={(e) => onChange({ ...rule, api_groups: e.target.value.split(',').map((s) => s.trim()) })}
            placeholder='apps, rbac.authorization.k8s.io'
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-slate-500 mb-1">Resources <span className="text-slate-600">(virgule)</span></label>
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-brand-500"
            value={rule.resources.join(', ')}
            onChange={(e) => onChange({ ...rule, resources: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
            placeholder='pods, deployments'
          />
        </div>
        <button onClick={onRemove} className="self-end text-slate-600 hover:text-red-400 transition-colors pb-1">
          <Trash2 size={14} />
        </button>
      </div>
      <div>
        <label className="block text-xs text-slate-500 mb-1">Verbs</label>
        <div className="flex flex-wrap gap-1">
          {ALL_VERBS.map((v) => (
            <button
              key={v}
              onClick={() => toggleVerb(v)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                rule.verbs.includes(v)
                  ? 'bg-brand-500/20 text-brand-300 border border-brand-500/40'
                  : 'bg-slate-800 text-slate-500 border border-slate-700 hover:border-slate-500'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function RoleEditorModal({ role, namespace: defaultNs, isCluster, onSave, onClose, loading }: Props) {
  const isEdit = !!role
  const [name, setName] = useState(role?.name ?? '')
  const [namespace, setNamespace] = useState(role?.namespace ?? defaultNs ?? 'default')
  const [rules, setRules] = useState<PolicyRule[]>(role?.rules?.length ? role.rules : [emptyRule()])

  const updateRule = (i: number, r: PolicyRule) => setRules((prev) => prev.map((x, idx) => (idx === i ? r : x)))
  const removeRule = (i: number) => setRules((prev) => prev.filter((_, idx) => idx !== i))

  const handleSave = () => {
    if (!name.trim()) return
    onSave(name.trim(), rules, isCluster ? undefined : namespace)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-100">
            {isEdit ? 'Modifier' : 'Créer'} {isCluster ? 'ClusterRole' : 'Role'}
          </h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300"><X size={16} /></button>
        </div>

        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs text-slate-400 mb-1">Nom</label>
              <input
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-50"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isEdit}
                placeholder='mon-role'
              />
            </div>
            {!isCluster && (
              <div className="w-40">
                <label className="block text-xs text-slate-400 mb-1">Namespace</label>
                <input
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-50"
                  value={namespace}
                  onChange={(e) => setNamespace(e.target.value)}
                  disabled={isEdit}
                />
              </div>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs text-slate-400">Règles</label>
              <button
                onClick={() => setRules((prev) => [...prev, emptyRule()])}
                className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300"
              >
                <Plus size={12} /> Ajouter une règle
              </button>
            </div>
            {rules.map((rule, i) => (
              <RuleRow key={i} rule={rule} onChange={(r) => updateRule(i, r)} onRemove={() => removeRule(i)} />
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-800">
          <Button variant="ghost" size="sm" onClick={onClose}>Annuler</Button>
          <Button size="sm" onClick={handleSave} loading={loading} disabled={!name.trim() || rules.length === 0}>
            {isEdit ? 'Enregistrer' : 'Créer'}
          </Button>
        </div>
      </div>
    </div>
  )
}
