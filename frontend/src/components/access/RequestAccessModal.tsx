import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Input from '../ui/Input'
import Select from '../ui/Select'
import { accessRequestsApi } from '../../api/accessRequests'
import { useClusterRoles, useNamespaces } from '../../hooks/useRbac'

interface Props {
  open: boolean
  onClose: () => void
}

export default function RequestAccessModal({ open, onClose }: Props) {
  const qc = useQueryClient()
  const [roleName, setRoleName] = useState('')
  const [roleKind] = useState('ClusterRole')
  const [scope, setScope] = useState<'cluster' | 'namespace'>('namespace')
  const [namespace, setNamespace] = useState('')
  const [justification, setJustification] = useState('')

  const { data: clusterRoles = [] } = useClusterRoles()
  const { data: namespaces = [] } = useNamespaces()

  const submit = useMutation({
    mutationFn: () => accessRequestsApi.create({
      role_name: roleName,
      role_kind: roleKind,
      namespace: scope === 'namespace' ? namespace : null,
      justification,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['access-requests'] })
      toast.success('Access request submitted')
      handleClose()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const handleClose = () => {
    setRoleName(''); setScope('namespace'); setNamespace(''); setJustification('')
    onClose()
  }

  const roleOptions = clusterRoles.map((r) => ({ value: r.name, label: r.name }))

  return (
    <Modal open={open} onClose={handleClose} title="Request access" size="sm">
      <div className="space-y-4">
        <p className="text-xs text-surface-400">
          Your request will be sent to an admin for review. You'll see the outcome in your profile.
        </p>

        <Select
          label="Role"
          value={roleName}
          onChange={(e) => setRoleName(e.target.value)}
          options={[{ value: '', label: 'Select a role…' }, ...roleOptions]}
        />

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => setScope('namespace')}
            className={`p-2.5 rounded-lg border text-left text-xs transition-colors ${scope === 'namespace' ? 'border-brand-500 bg-brand-500/10 text-brand-300' : 'border-surface-600 text-surface-400 hover:border-surface-500'}`}
          >
            <p className="font-medium">Namespace</p>
            <p className="text-surface-500 mt-0.5">Specific namespace only</p>
          </button>
          <button
            onClick={() => setScope('cluster')}
            className={`p-2.5 rounded-lg border text-left text-xs transition-colors ${scope === 'cluster' ? 'border-brand-500 bg-brand-500/10 text-brand-300' : 'border-surface-600 text-surface-400 hover:border-surface-500'}`}
          >
            <p className="font-medium">Cluster-wide</p>
            <p className="text-surface-500 mt-0.5">All namespaces</p>
          </button>
        </div>

        {scope === 'namespace' && (
          <Select
            label="Namespace"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            options={[{ value: '', label: 'Select…' }, ...namespaces.map((n) => ({ value: n, label: n }))]}
          />
        )}

        <Input
          label="Justification"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Why do you need this access?"
          hint="Required — helps the admin make the right decision"
        />

        <div className="flex gap-3 pt-1">
          <Button variant="secondary" size="sm" className="flex-1" onClick={handleClose}>Cancel</Button>
          <Button
            size="sm"
            className="flex-1"
            loading={submit.isPending}
            disabled={!roleName || !justification || (scope === 'namespace' && !namespace)}
            onClick={() => submit.mutate()}
          >
            Submit request
          </Button>
        </div>
      </div>
    </Modal>
  )
}
