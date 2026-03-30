import { useState, useEffect } from 'react'
import { AlertTriangle, Check, CheckCircle, Clipboard, Download, FileCode2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import { useCreateUser } from '../../hooks/useUsers'
import { useNamespaces, useClusterRoles } from '../../hooks/useRbac'
import { useGenerateKubeconfig, downloadKubeconfig } from '../../hooks/useKubeconfig'
import { rbacApi } from '../../api/rbac'
import type { UserWithCredentials } from '../../types/user'

interface Props {
  open: boolean
  onClose: () => void
}

type Step = 1 | 2 | 3

const PRESETS = [
  { id: 'none',     label: 'No permissions', desc: 'Assign later manually',           role: null },
  { id: 'readonly', label: 'Read-only',       desc: 'Can view but not modify',         role: 'view' },
  { id: 'developer',label: 'Developer',       desc: 'Can create, update resources',    role: 'edit' },
  { id: 'admin',    label: 'Admin',           desc: 'Full access on selected scopes',  role: 'admin' },
]

function StepIndicator({ current }: { current: Step }) {
  const steps = [
    { n: 1, label: 'Identity' },
    { n: 2, label: 'Permissions' },
    { n: 3, label: 'Done' },
  ]
  return (
    <div className="flex items-center gap-0 mb-6">
      {steps.map((s, i) => (
        <div key={s.n} className="flex items-center">
          <div className={`flex items-center gap-1.5 ${current === s.n ? 'text-brand-400' : current > s.n ? 'text-emerald-400' : 'text-surface-500'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border ${
              current > s.n ? 'border-emerald-500 bg-emerald-500/20' :
              current === s.n ? 'border-brand-500 bg-brand-500/20' :
              'border-surface-600 bg-surface-800'
            }`}>
              {current > s.n ? <Check size={12} /> : s.n}
            </div>
            <span className="text-xs font-medium">{s.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`h-px w-8 mx-2 ${current > s.n ? 'bg-emerald-500/40' : 'bg-surface-600'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

export default function CreateUserWizard({ open, onClose }: Props) {
  const [step, setStep] = useState<Step>(1)

  // Step 1
  const [name, setName] = useState('')
  const [nameError, setNameError] = useState('')
  const [userType, setUserType] = useState<'certificate' | 'service_account'>('service_account')
  const [saNamespace, setSaNamespace] = useState('default')
  const [groups, setGroups] = useState('')

  // Step 2
  const [preset, setPreset] = useState('readonly')
  const [scope, setScope] = useState<'cluster' | 'namespace'>('namespace')
  const [selectedNs, setSelectedNs] = useState<Set<string>>(new Set())
  const [assigning, setAssigning] = useState(false)

  // Step 3
  const [credentials, setCredentials] = useState<UserWithCredentials | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [copied, setCopied] = useState(false)

  const { data: namespaces = [] } = useNamespaces()
  const generateKubeconfig = useGenerateKubeconfig()

  const createUser = useCreateUser(async (data) => {
    setCredentials(data)

    // Assign roles if a preset is selected
    const selectedPreset = PRESETS.find((p) => p.id === preset)
    if (selectedPreset?.role) {
      setAssigning(true)
      try {
        const userKind = userType === 'service_account' ? 'ServiceAccount' : 'User'
        const saNs = userType === 'service_account' ? saNamespace : undefined

        if (scope === 'cluster') {
          await rbacApi.assignRole(data.name, { role_name: selectedPreset.role, role_kind: 'ClusterRole' }, userKind, saNs)
        } else {
          await Promise.all(
            [...selectedNs].map((ns) =>
              rbacApi.assignRole(data.name, { role_name: selectedPreset.role!, role_kind: 'ClusterRole', namespace: ns }, userKind, saNs)
            )
          )
        }
      } catch {
        toast.error('User created but role assignment failed')
      } finally {
        setAssigning(false)
      }
    }

    // Auto-generate kubeconfig
    generateKubeconfig.mutate({
      username: data.name,
      user_type: data.user_type,
      namespace: userType === 'service_account' ? saNamespace : '',
      private_key_pem: data.private_key_pem ?? undefined,
    })

    setStep(3)
  })

  const handleClose = () => {
    setStep(1)
    setName(''); setNameError(''); setUserType('service_account')
    setSaNamespace('default'); setGroups('')
    setPreset('readonly'); setScope('namespace'); setSelectedNs(new Set())
    setCredentials(null); setConfirmed(false); setCopied(false)
    generateKubeconfig.reset()
    onClose()
  }

  const validateStep1 = () => {
    if (!name) { setNameError('Required'); return false }
    if (!/^[a-z0-9][a-z0-9\-\.]*$/.test(name)) {
      setNameError('Lowercase letters, numbers, dashes and dots only')
      return false
    }
    setNameError('')
    return true
  }

  const handleStep1Next = () => {
    if (validateStep1()) setStep(2)
  }

  const handleCreate = () => {
    createUser.mutate({
      name,
      user_type: userType,
      groups: groups.split(',').map((g) => g.trim()).filter(Boolean),
      namespace: userType === 'service_account' ? saNamespace : undefined,
    })
  }

  const toggleNs = (ns: string) =>
    setSelectedNs((prev) => {
      const next = new Set(prev)
      next.has(ns) ? next.delete(ns) : next.add(ns)
      return next
    })

  const handleCopyKey = async () => {
    if (!credentials?.private_key_pem) return
    await navigator.clipboard.writeText(credentials.private_key_pem)
    toast.success('Private key copied')
  }

  const handleCopyKubeconfig = () => {
    if (!generateKubeconfig.data) return
    navigator.clipboard.writeText(generateKubeconfig.data)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadCredentials = () => {
    if (!credentials) return
    const content = [
      `# ClusterVision credentials for ${credentials.name}`,
      `# Generated: ${new Date().toISOString()}`,
      `# WARNING: Store these securely. The private key will NOT be shown again.`,
      '', '# Certificate:', credentials.certificate_pem ?? '',
      '', '# Private Key:', credentials.private_key_pem ?? '',
    ].join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${credentials.name}-credentials.pem`; a.click()
    URL.revokeObjectURL(url)
  }

  const isCert = userType === 'certificate'
  const canClose = step !== 3 || !isCert || confirmed

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={canClose ? handleClose : undefined} />
      <div className="relative bg-surface-800 border border-surface-600 rounded-xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-600">
          <h2 className="text-base font-semibold text-surface-100">Add user</h2>
          {canClose && (
            <button onClick={handleClose} className="text-surface-400 hover:text-surface-200 transition-colors">
              <X size={18} />
            </button>
          )}
        </div>

        <div className="px-6 py-5">
          <StepIndicator current={step} />

          {/* ── Step 1: Identity ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setUserType('service_account')}
                  className={`p-3 rounded-lg border text-left transition-colors ${userType === 'service_account' ? 'border-brand-500 bg-brand-500/10' : 'border-surface-600 hover:border-surface-500'}`}
                >
                  <p className="text-sm font-medium text-surface-100">ServiceAccount</p>
                  <p className="text-xs text-surface-400 mt-0.5">For apps, CI/CD pipelines</p>
                </button>
                <button
                  onClick={() => setUserType('certificate')}
                  className={`p-3 rounded-lg border text-left transition-colors ${isCert ? 'border-brand-500 bg-brand-500/10' : 'border-surface-600 hover:border-surface-500'}`}
                >
                  <p className="text-sm font-medium text-surface-100">Certificate (X.509)</p>
                  <p className="text-xs text-surface-400 mt-0.5">For human users</p>
                </button>
              </div>

              <Input
                label="Username"
                value={name}
                onChange={(e) => { setName(e.target.value); setNameError('') }}
                placeholder={isCert ? 'alice' : 'sa-ci-myapp'}
                error={nameError}
                hint="Lowercase, alphanumeric, dash or dot"
              />

              {userType === 'service_account' && (
                <Select
                  label="Namespace"
                  value={saNamespace}
                  onChange={(e) => setSaNamespace(e.target.value)}
                  options={namespaces.length ? namespaces.map((n) => ({ value: n, label: n })) : [{ value: 'default', label: 'default' }]}
                />
              )}

              {isCert && (
                <Input
                  label="Groups (optional, comma-separated)"
                  value={groups}
                  onChange={(e) => setGroups(e.target.value)}
                  placeholder="developers, devops"
                  hint="Maps to /O= in the certificate subject"
                />
              )}

              <div className="flex gap-3 pt-2">
                <Button variant="secondary" onClick={handleClose} className="flex-1">Cancel</Button>
                <Button onClick={handleStep1Next} className="flex-1">Next →</Button>
              </div>
            </div>
          )}

          {/* ── Step 2: Permissions ── */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-surface-300 mb-2">Permission level</label>
                <div className="grid grid-cols-2 gap-2">
                  {PRESETS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setPreset(p.id)}
                      className={`p-3 rounded-lg border text-left transition-colors ${preset === p.id ? 'border-brand-500 bg-brand-500/10' : 'border-surface-600 hover:border-surface-500'}`}
                    >
                      <p className="text-sm font-medium text-surface-100">{p.label}</p>
                      <p className="text-xs text-surface-400 mt-0.5">{p.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {preset !== 'none' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setScope('namespace')}
                      className={`p-2.5 rounded-lg border text-left text-xs transition-colors ${scope === 'namespace' ? 'border-brand-500 bg-brand-500/10 text-brand-300' : 'border-surface-600 text-surface-400 hover:border-surface-500'}`}
                    >
                      <p className="font-medium">Namespace-scoped</p>
                      <p className="text-surface-500 mt-0.5">Only on selected namespaces</p>
                    </button>
                    <button
                      onClick={() => setScope('cluster')}
                      className={`p-2.5 rounded-lg border text-left text-xs transition-colors ${scope === 'cluster' ? 'border-brand-500 bg-brand-500/10 text-brand-300' : 'border-surface-600 text-surface-400 hover:border-surface-500'}`}
                    >
                      <p className="font-medium">Cluster-wide</p>
                      <p className="text-surface-500 mt-0.5">Access to all namespaces</p>
                    </button>
                  </div>

                  {scope === 'namespace' && (
                    <div>
                      <label className="block text-xs font-medium text-surface-300 mb-2">Namespaces</label>
                      <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
                        {namespaces.map((ns) => (
                          <label key={ns} className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-700 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selectedNs.has(ns)}
                              onChange={() => toggleNs(ns)}
                              className="accent-brand-500"
                            />
                            <span className="text-sm font-mono text-surface-200">{ns}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button variant="secondary" onClick={() => setStep(1)} className="flex-1">← Back</Button>
                <Button
                  onClick={handleCreate}
                  loading={createUser.isPending || assigning}
                  disabled={preset !== 'none' && scope === 'namespace' && selectedNs.size === 0}
                  className="flex-1"
                >
                  Create user
                </Button>
              </div>
            </div>
          )}

          {/* ── Step 3: Done ── */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle size={18} />
                <span className="text-sm font-medium">User <span className="font-mono">{name}</span> created</span>
              </div>

              {/* Cert credentials */}
              {isCert && credentials?.private_key_pem && (
                <div className="space-y-3">
                  <div className="flex items-start gap-3 p-3 bg-amber-900/20 border border-amber-500/30 rounded-lg">
                    <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-amber-300">
                      <span className="font-semibold">One-time display.</span> The private key is not stored — save it now.
                    </p>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-medium text-surface-300">Private Key</label>
                      <button onClick={handleCopyKey} className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
                        <Clipboard size={11} /> Copy
                      </button>
                    </div>
                    <pre className="bg-surface-950 border border-surface-600 rounded-md p-3 text-xs text-surface-200 max-h-28 overflow-y-auto font-mono">
                      {credentials.private_key_pem}
                    </pre>
                  </div>
                  <Button variant="secondary" onClick={handleDownloadCredentials} className="w-full">
                    <Download size={13} /> Download credentials.pem
                  </Button>
                </div>
              )}

              {/* Kubeconfig */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-surface-300">Kubeconfig</label>
                  {generateKubeconfig.data && (
                    <div className="flex gap-3">
                      <button onClick={handleCopyKubeconfig} className="text-xs text-surface-400 hover:text-surface-200 flex items-center gap-1">
                        {copied ? <Check size={11} className="text-emerald-400" /> : <Clipboard size={11} />}
                        {copied ? 'Copied!' : 'Copy'}
                      </button>
                      <button
                        onClick={() => downloadKubeconfig(generateKubeconfig.data!, name)}
                        className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
                      >
                        <Download size={11} /> Download
                      </button>
                    </div>
                  )}
                </div>
                <div className="bg-surface-950 border border-surface-700 rounded-lg overflow-hidden">
                  {generateKubeconfig.isPending ? (
                    <div className="flex items-center justify-center py-6 text-xs text-surface-500">Generating kubeconfig...</div>
                  ) : generateKubeconfig.data ? (
                    <pre className="px-4 py-3 text-xs text-surface-300 font-mono overflow-auto max-h-48">
                      {generateKubeconfig.data}
                    </pre>
                  ) : (
                    <div className="flex items-center justify-center gap-2 py-6 text-surface-600">
                      <FileCode2 size={18} className="opacity-40" />
                      <span className="text-xs">Kubeconfig unavailable</span>
                    </div>
                  )}
                </div>
              </div>

              {isCert && (
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                    className="mt-0.5 accent-brand-500"
                  />
                  <span className="text-sm text-surface-200">I have saved my private key. I understand it cannot be recovered.</span>
                </label>
              )}

              <Button className="w-full" disabled={isCert && !confirmed} onClick={handleClose}>
                Done
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  )
}
