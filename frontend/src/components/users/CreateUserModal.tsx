import { useState } from 'react'
import { AlertTriangle, Copy, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import { useCreateUser } from '../../hooks/useUsers'
import type { UserWithCredentials } from '../../types/user'

interface Props {
  open: boolean
  onClose: () => void
}

export default function CreateUserModal({ open, onClose }: Props) {
  const [name, setName] = useState('')
  const [userType, setUserType] = useState<'certificate' | 'service_account'>('certificate')
  const [groups, setGroups] = useState('')
  const [namespace, setNamespace] = useState('default')
  const [nameError, setNameError] = useState('')

  // One-time credentials state
  const [credentials, setCredentials] = useState<UserWithCredentials | null>(null)
  const [confirmed, setConfirmed] = useState(false)

  const createUser = useCreateUser((data) => {
    if (data.private_key_pem) {
      setCredentials(data)
    } else {
      toast.success(`User ${data.name} created`)
      handleClose()
    }
  })

  const validate = () => {
    if (!name) { setNameError('Required'); return false }
    if (!/^[a-z0-9][a-z0-9\-\.]*$/.test(name)) {
      setNameError('Lowercase letters, numbers, dashes and dots only')
      return false
    }
    setNameError('')
    return true
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    createUser.mutate({
      name,
      user_type: userType,
      groups: groups.split(',').map((g) => g.trim()).filter(Boolean),
      namespace,
    })
  }

  const handleClose = () => {
    setName(''); setGroups(''); setNamespace('default'); setNameError('')
    setCredentials(null); setConfirmed(false)
    onClose()
  }

  const downloadCredentials = () => {
    if (!credentials) return
    const content = [
      `# ClusterVision credentials for ${credentials.name}`,
      `# Generated: ${new Date().toISOString()}`,
      `# WARNING: Store these securely. The private key will NOT be shown again.`,
      '',
      '# Certificate:',
      credentials.certificate_pem ?? '',
      '',
      '# Private Key:',
      credentials.private_key_pem ?? '',
    ].join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${credentials.name}-credentials.pem`
    a.click()
    URL.revokeObjectURL(url)
  }

  const copyKey = async () => {
    if (!credentials?.private_key_pem) return
    await navigator.clipboard.writeText(credentials.private_key_pem)
    toast.success('Private key copied')
  }

  // Show credentials screen after creation
  if (credentials) {
    return (
      <Modal open={open} onClose={() => {}} title="Save your credentials" size="xl">
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-amber-900/20 border border-amber-500/30 rounded-lg">
            <AlertTriangle size={18} className="text-amber-400 mt-0.5 shrink-0" />
            <div className="text-sm text-amber-300">
              <p className="font-semibold mb-1">One-time display — save now</p>
              <p className="text-amber-400/80">The private key is not stored by ClusterVision. If you lose it, you must delete and recreate the user.</p>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-slate-400">Private Key</label>
              <button onClick={copyKey} className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300">
                <Copy size={12} /> Copy
              </button>
            </div>
            <pre className="bg-slate-950 border border-slate-700 rounded-md p-3 text-xs text-slate-300 overflow-x-auto max-h-36 overflow-y-auto font-mono">
              {credentials.private_key_pem}
            </pre>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-2">Certificate</label>
            <pre className="bg-slate-950 border border-slate-700 rounded-md p-3 text-xs text-slate-300 overflow-x-auto max-h-24 overflow-y-auto font-mono">
              {credentials.certificate_pem}
            </pre>
          </div>

          <Button variant="secondary" onClick={downloadCredentials} className="w-full">
            <Download size={14} /> Download credentials.pem
          </Button>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="mt-0.5 accent-brand-500"
            />
            <span className="text-sm text-slate-300">
              I have saved my private key. I understand it cannot be recovered.
            </span>
          </label>

          <Button
            className="w-full"
            disabled={!confirmed}
            onClick={handleClose}
          >
            Done
          </Button>
        </div>
      </Modal>
    )
  }

  return (
    <Modal open={open} onClose={handleClose} title="Create user">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Username"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="alice"
          error={nameError}
          hint="Lowercase, alphanumeric, dash or dot"
        />

        <Select
          label="User type"
          value={userType}
          onChange={(e) => setUserType(e.target.value as typeof userType)}
          options={[
            { value: 'certificate', label: 'Certificate (X.509)' },
            { value: 'service_account', label: 'ServiceAccount' },
          ]}
        />

        {userType === 'certificate' && (
          <Input
            label="Groups (comma-separated)"
            value={groups}
            onChange={(e) => setGroups(e.target.value)}
            placeholder="developers, devops"
            hint="Maps to /O= in the certificate subject"
          />
        )}

        {userType === 'service_account' && (
          <Input
            label="Namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            placeholder="default"
          />
        )}

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose} className="flex-1">
            Cancel
          </Button>
          <Button type="submit" loading={createUser.isPending} className="flex-1">
            Create
          </Button>
        </div>
      </form>
    </Modal>
  )
}
