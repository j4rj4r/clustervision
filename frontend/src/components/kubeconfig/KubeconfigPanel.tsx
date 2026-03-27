import { useState, useEffect, useRef } from 'react'
import { Check, Clipboard, Download, FileCode2 } from 'lucide-react'
import Select from '../ui/Select'
import { useUsers } from '../../hooks/useUsers'
import { useNamespaces } from '../../hooks/useRbac'
import { useGenerateKubeconfig, downloadKubeconfig } from '../../hooks/useKubeconfig'

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
  const [namespace, setNamespace] = useState(preselectedNamespace ?? '')
  const [privateKey, setPrivateKey] = useState('')
  const [copied, setCopied] = useState(false)

  const selectedUser = users.find((u) => u.name === selectedUsername)
  const isCert = selectedUser?.user_type === 'certificate'
  const canGenerate = !!selectedUser && (!isCert || !!privateKey.trim())

  // Auto-update namespace when user changes
  useEffect(() => {
    if (selectedUser?.namespace) setNamespace(selectedUser.namespace)
    generate.reset()
    setPrivateKey('')
  }, [selectedUsername])

  // Debounced auto-generate
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!canGenerate) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      generate.mutate({
        username: selectedUser!.name,
        user_type: selectedUser!.user_type,
        namespace,
        private_key_pem: isCert ? privateKey : undefined,
      })
    }, 500)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [selectedUsername, namespace, privateKey])

  const handleCopy = () => {
    if (!generate.data) return
    navigator.clipboard.writeText(generate.data)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    if (!generate.data || !selectedUser) return
    downloadKubeconfig(generate.data, selectedUser.name)
  }

  if (usersError) return (
    <div className="text-center py-8">
      <p className="text-sm text-red-400">Failed to load users.</p>
    </div>
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Form */}
      <div className="space-y-4">
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
          options={[{ value: '', label: '— none —' }, ...namespaces.map((n) => ({ value: n, label: n }))]}
        />

        {isCert && (
          <div className="space-y-1">
            <label className="block text-xs font-medium text-surface-300">Private Key PEM</label>
            <textarea
              value={privateKey}
              onChange={(e) => setPrivateKey(e.target.value)}
              placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
              rows={6}
              className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-xs text-surface-200 font-mono placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
            />
            <p className="text-xs text-surface-400">Paste the private key saved at user creation time.</p>
          </div>
        )}
      </div>

      {/* Live preview */}
      <div className="flex flex-col min-h-48">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-surface-300">Preview</span>
          {generate.data && (
            <div className="flex gap-3">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 text-xs text-surface-400 hover:text-surface-200 transition-colors"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Clipboard size={13} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 transition-colors"
              >
                <Download size={13} /> Download
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 bg-surface-950 border border-surface-700 rounded-lg overflow-hidden">
          {generate.isPending ? (
            <div className="h-full flex items-center justify-center text-xs text-surface-500">Generating...</div>
          ) : generate.data ? (
            <pre className="h-full px-4 py-3 text-xs text-surface-300 font-mono overflow-auto">
              {generate.data}
            </pre>
          ) : (
            <div className="h-full flex flex-col items-center justify-center gap-2 text-surface-600">
              <FileCode2 size={28} className="opacity-40" />
              <p className="text-xs">
                {!selectedUser ? 'Select a user to preview' : isCert ? 'Paste your private key to preview' : 'Loading...'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
