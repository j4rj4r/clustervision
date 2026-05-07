import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, Clipboard, Download, FileCode2, RefreshCw, Upload, Vault } from 'lucide-react'
import Select from '../ui/Select'
import { useUsers } from '../../hooks/useUsers'
import { useNamespaces } from '../../hooks/useRbac'
import { useGenerateKubeconfig, downloadKubeconfig } from '../../hooks/useKubeconfig'
import { vaultApi } from '../../api/vault'

interface Props {
  preselectedName?: string
  preselectedNamespace?: string
}

export default function KubeconfigPanel({ preselectedName, preselectedNamespace }: Props) {
  const { data: usersData, isError: usersError } = useUsers()
  const { data: namespaces = [] } = useNamespaces()
  const { data: vaultStatus } = useQuery({ queryKey: ['vault-status'], queryFn: vaultApi.status })
  const generate = useGenerateKubeconfig()

  const vaultEnabled = vaultStatus?.enabled && vaultStatus.healthy

  const users = usersData?.users ?? []

  const [selectedUsername, setSelectedUsername] = useState(preselectedName ?? '')
  const [namespace, setNamespace] = useState(preselectedNamespace ?? '')
  const [privateKey, setPrivateKey] = useState('')
  const [copied, setCopied] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handlePemUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      const match = text.match(/(-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC )?PRIVATE KEY-----)/)
      setPrivateKey(match ? match[1].trim() : text.trim())
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const selectedUser = users.find((u) => u.name === selectedUsername)
  const isCert = selectedUser?.user_type === 'certificate'
  const canGenerate = !!selectedUser && (!isCert || !!privateKey.trim() || !!vaultEnabled)

  // Auto-update namespace when user changes
  useEffect(() => {
    if (selectedUser?.namespace) setNamespace(selectedUser.namespace)
    generate.reset()
    setPrivateKey('')
  }, [selectedUsername])

  const handleGenerate = () => {
    if (!canGenerate) return
    generate.mutate({
      username: selectedUser!.name,
      user_type: selectedUser!.user_type,
      namespace,
      private_key_pem: isCert ? privateKey : undefined,
    })
  }

  // Auto-generate for SA users and cert users when Vault is active (no key input needed)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!canGenerate || (isCert && !vaultEnabled)) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(handleGenerate, 1500)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [selectedUsername, namespace, users, vaultEnabled])

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
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <label className="block text-xs font-medium text-surface-300">Private Key PEM</label>
                {vaultEnabled && <span className="flex items-center gap-1 text-xs text-brand-400"><Vault size={11} /> from Vault</span>}
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
              >
                <Upload size={11} /> Upload .pem
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pem,.key,.txt"
              className="hidden"
              onChange={handlePemUpload}
            />
            <textarea
              value={privateKey}
              onChange={(e) => setPrivateKey(e.target.value)}
              placeholder={vaultEnabled ? '(optional — key will be fetched from Vault)' : '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----'}
              rows={vaultEnabled ? 3 : 6}
              className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-xs text-surface-200 font-mono placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
            />
            <p className="text-xs text-surface-400">
              {vaultEnabled
                ? 'Key fetched from Vault automatically. Paste or upload to override.'
                : 'Upload the credentials.pem downloaded at user creation, or paste the key directly.'}
            </p>
          </div>
        )}

        {isCert && (
          <button
            onClick={handleGenerate}
            disabled={!canGenerate || generate.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
          >
            <RefreshCw size={13} className={generate.isPending ? 'animate-spin' : ''} />
            {generate.isPending ? 'Generating…' : 'Generate kubeconfig'}
          </button>
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
                {!selectedUser ? 'Select a user to preview' : isCert && !vaultEnabled ? 'Paste your private key to generate' : 'Loading...'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
