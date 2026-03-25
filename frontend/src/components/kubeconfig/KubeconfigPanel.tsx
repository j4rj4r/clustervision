import { useState, useEffect } from 'react'
import { Download } from 'lucide-react'
import Button from '../ui/Button'
import Select from '../ui/Select'
import { useUsers } from '../../hooks/useUsers'
import { useNamespaces } from '../../hooks/useRbac'
import { useGenerateKubeconfig } from '../../hooks/useKubeconfig'
interface Props {
  preselectedName?: string
  preselectedNamespace?: string
}

export default function KubeconfigPanel({ preselectedName, preselectedNamespace }: Props) {
  const { data: usersData, isError: usersError } = useUsers()
  const { data: namespaces = [] } = useNamespaces()
  const generate = useGenerateKubeconfig()

  const users = usersData?.users ?? []

  const [selectedUsername, setSelectedUsername] = useState(preselectedName ?? '')
  const [namespace, setNamespace] = useState(preselectedNamespace ?? 'default')
  const [privateKey, setPrivateKey] = useState('')

  const selectedUser = users.find((u) => u.name === selectedUsername)

  // Auto-update namespace when the selected user changes
  useEffect(() => {
    if (selectedUser?.namespace) {
      setNamespace(selectedUser.namespace)
    }
  }, [selectedUser?.name])

  const handleGenerate = () => {
    if (!selectedUser) return
    generate.mutate({
      username: selectedUser.name,
      user_type: selectedUser.user_type,
      namespace,
      private_key_pem: selectedUser.user_type === 'certificate' ? privateKey : undefined,
    })
  }

  if (usersError) return (
    <div className="text-center py-8 space-y-2">
      <p className="text-sm text-red-400">Failed to load users.</p>
    </div>
  )

  return (
    <div className="space-y-4 max-w-lg">
      <Select
        label="User"
        value={selectedUsername}
        onChange={(e) => setSelectedUsername(e.target.value)}
        options={[
          { value: '', label: 'Select a user...' },
          ...users.map((u) => ({ value: u.name, label: `${u.name} (${u.user_type === 'certificate' ? 'X.509' : 'SA'})` })),
        ]}
      />

      <Select
        label="Default namespace"
        value={namespace}
        onChange={(e) => setNamespace(e.target.value)}
        options={[{ value: 'default', label: 'default' }, ...namespaces.filter((n) => n !== 'default').map((n) => ({ value: n, label: n }))]}
      />

      {selectedUser?.user_type === 'certificate' && (
        <div className="space-y-1">
          <label className="block text-xs font-medium text-surface-300">
            Private Key PEM
          </label>
          <textarea
            value={privateKey}
            onChange={(e) => setPrivateKey(e.target.value)}
            placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
            rows={6}
            className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-xs text-surface-200 font-mono placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
          />
          <p className="text-xs text-surface-400">
            Paste the private key saved at user creation time.
          </p>
        </div>
      )}

      <Button
        onClick={handleGenerate}
        loading={generate.isPending}
        disabled={!selectedUsername || (selectedUser?.user_type === 'certificate' && !privateKey)}
        className="w-full"
      >
        <Download size={14} /> Generate & Download
      </Button>
    </div>
  )
}
