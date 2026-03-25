import { useState } from 'react'
import { LogIn } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import Badge from '../ui/Badge'
import { useImportUser, useUnmanagedServiceAccounts } from '../../hooks/useUsers'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ImportUserModal({ open, onClose }: Props) {
  const [userType, setUserType] = useState<'certificate' | 'service_account'>('service_account')
  const [name, setName] = useState('')
  const [namespace, setNamespace] = useState('default')
  const [groups, setGroups] = useState('')
  const [selectedSA, setSelectedSA] = useState<{ name: string; namespace: string } | null>(null)

  const { data: unmanagedSAs = [] } = useUnmanagedServiceAccounts()
  const importUser = useImportUser(onClose)

  const handleClose = () => {
    setName(''); setNamespace('default'); setGroups(''); setSelectedSA(null)
    onClose()
  }

  const handleSelectSA = (sa: { name: string; namespace: string }) => {
    setSelectedSA(sa)
    setName(sa.name)
    setNamespace(sa.namespace)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    importUser.mutate({
      name,
      user_type: userType,
      namespace,
      groups: groups.split(',').map((g) => g.trim()).filter(Boolean),
    })
  }

  return (
    <Modal open={open} onClose={handleClose} title="Import existing user" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Select
          label="Type"
          value={userType}
          onChange={(e) => { setUserType(e.target.value as typeof userType); setSelectedSA(null); setName('') }}
          options={[
            { value: 'service_account', label: 'ServiceAccount' },
            { value: 'certificate', label: 'Certificate (X.509)' },
          ]}
        />

        {userType === 'service_account' && unmanagedSAs.length > 0 && (
          <div className="space-y-1">
            <label className="block text-xs font-medium text-surface-300">
              Unmanaged ServiceAccounts ({unmanagedSAs.length})
            </label>
            <div className="max-h-48 overflow-y-auto space-y-1 border border-surface-600 rounded-md p-2 bg-surface-950">
              {unmanagedSAs.map((sa) => (
                <button
                  key={`${sa.namespace}/${sa.name}`}
                  type="button"
                  onClick={() => handleSelectSA(sa)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded text-sm text-left transition-colors ${
                    selectedSA?.name === sa.name && selectedSA?.namespace === sa.namespace
                      ? 'bg-brand-600 text-white'
                      : 'hover:bg-surface-700 text-surface-200'
                  }`}
                >
                  <span className="font-mono">{sa.name}</span>
                  <Badge variant="default">{sa.namespace}</Badge>
                </button>
              ))}
            </div>
          </div>
        )}

        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="rapvoy"
          required
        />

        {userType === 'service_account' && (
          <Input
            label="Namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            placeholder="rapvoy-dev"
          />
        )}

        {userType === 'certificate' && (
          <Input
            label="Groups (comma-separated)"
            value={groups}
            onChange={(e) => setGroups(e.target.value)}
            placeholder="developers, devops"
          />
        )}

        <p className="text-xs text-surface-400">
          Import registers the user in ClusterVision without modifying existing Kubernetes resources.
        </p>

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose} className="flex-1">
            Cancel
          </Button>
          <Button type="submit" loading={importUser.isPending} disabled={!name} className="flex-1">
            <LogIn size={14} /> Import
          </Button>
        </div>
      </form>
    </Modal>
  )
}
