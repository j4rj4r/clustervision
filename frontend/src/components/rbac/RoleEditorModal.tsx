import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Select from '../ui/Select'
import type { PolicyRule, RoleRead } from '../../types/rbac'

const ALL_VERBS = ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete', 'deletecollection']

interface Props {
  role?: RoleRead
  copyFrom?: RoleRead
  namespace?: string
  namespaces?: string[]
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
    <div className="border border-surface-600 rounded-lg p-3 space-y-2 bg-surface-900">
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-surface-400 mb-1">API Groups <span className="text-surface-500">(comma, empty = core)</span></label>
          <input
            className="w-full bg-surface-800 border border-surface-600 rounded px-2 py-1 text-xs font-mono text-surface-100 focus:outline-none focus:border-brand-500"
            value={rule.api_groups.join(', ')}
            onChange={(e) => onChange({ ...rule, api_groups: e.target.value.split(',').map((s) => s.trim()) })}
            placeholder='apps, rbac.authorization.k8s.io'
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-surface-400 mb-1">Resources <span className="text-surface-500">(comma-separated)</span></label>
          <input
            className="w-full bg-surface-800 border border-surface-600 rounded px-2 py-1 text-xs font-mono text-surface-100 focus:outline-none focus:border-brand-500"
            value={rule.resources.join(', ')}
            onChange={(e) => onChange({ ...rule, resources: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
            placeholder='pods, deployments'
          />
        </div>
        <button aria-label="Remove rule" onClick={onRemove} className="self-end text-surface-500 hover:text-red-400 transition-colors pb-1">
          <Trash2 size={14} />
        </button>
      </div>
      <div>
        <label className="block text-xs text-surface-400 mb-1">Verbs</label>
        <div className="flex flex-wrap gap-1">
          {ALL_VERBS.map((v) => (
            <button
              key={v}
              onClick={() => toggleVerb(v)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                rule.verbs.includes(v)
                  ? 'bg-brand-500/20 text-brand-300 border border-brand-500/40'
                  : 'bg-surface-800 text-surface-400 border border-surface-600 hover:border-surface-400'
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

export default function RoleEditorModal({ role, copyFrom, namespace: defaultNs, namespaces = [], isCluster, onSave, onClose, loading }: Props) {
  const isEdit = !!role
  const isCopy = !!copyFrom
  const [name, setName] = useState(role?.name ?? (isCopy ? `copy-of-${copyFrom!.name}` : ''))
  const [namespace, setNamespace] = useState(role?.namespace ?? copyFrom?.namespace ?? defaultNs ?? 'default')
  const [rules, setRules] = useState<PolicyRule[]>(
    role?.rules?.length ? role.rules : copyFrom?.rules?.length ? copyFrom.rules : [emptyRule()]
  )

  const updateRule = (i: number, r: PolicyRule) => setRules((prev) => prev.map((x, idx) => (idx === i ? r : x)))
  const removeRule = (i: number) => setRules((prev) => prev.filter((_, idx) => idx !== i))

  const handleSave = () => {
    if (!name.trim()) return
    onSave(name.trim(), rules, isCluster ? undefined : namespace)
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`${isEdit ? 'Edit' : isCopy ? 'Copy' : 'Create'} ${isCluster ? 'ClusterRole' : 'Role'}`}
      size="lg"
      closeOnBackdrop={false}
    >
      <div className="space-y-4">
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-xs text-surface-300 mb-1">Name</label>
            <input
              className="w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm font-mono text-surface-100 focus:outline-none focus:border-brand-500 disabled:opacity-50"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isEdit && !isCopy}
              placeholder='my-role'
            />
          </div>
          {!isCluster && (
            <div className="w-40">
              <Select
                label="Namespace"
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                disabled={isEdit && !isCopy}
                options={namespaces.map((n) => ({ value: n, label: n }))}
              />
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs text-surface-300">Rules</label>
            <button
              onClick={() => setRules((prev) => [...prev, emptyRule()])}
              className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300"
            >
              <Plus size={12} /> Add rule
            </button>
          </div>
          {rules.map((rule, i) => (
            <RuleRow key={i} rule={rule} onChange={(r) => updateRule(i, r)} onRemove={() => removeRule(i)} />
          ))}
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={handleSave} loading={loading} disabled={!name.trim() || rules.length === 0}>
            {isEdit ? 'Save' : 'Create'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
