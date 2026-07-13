import { useState } from 'react'
import toast from 'react-hot-toast'
import { Copy, Check, Terminal, FormInput } from 'lucide-react'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Button from '../ui/Button'
import { useAddCluster } from '../../hooks/useCluster'
import { clusterApi } from '../../api/cluster'

interface Props {
  onClose: () => void
}

type Tab = 'manual' | 'command'

export default function AddClusterModal({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>('command')

  // Manual tab
  const [name, setName] = useState('')
  const [apiUrl, setApiUrl] = useState('')
  const [caData, setCaData] = useState('')
  const [token, setToken] = useState('')

  // Command tab
  const [cmdName, setCmdName] = useState('')
  const [script, setScript] = useState<string | null>(null)
  const [loadingScript, setLoadingScript] = useState(false)
  const [copied, setCopied] = useState(false)

  const add = useAddCluster(onClose)

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name || !apiUrl || !caData || !token) return
    add.mutate({ name, api_url: apiUrl, ca_data: caData, token })
  }

  const handleGenerateScript = async () => {
    if (!cmdName.trim()) return
    setLoadingScript(true)
    try {
      const s = await clusterApi.bootstrapScript(cmdName.trim())
      setScript(s)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate script')
    } finally {
      setLoadingScript(false)
    }
  }

  const handleCopy = () => {
    if (!script) return
    navigator.clipboard.writeText(script)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Modal open onClose={onClose} title="Add cluster" closeOnBackdrop={false}>
      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-800/60 rounded-lg mb-4">
        <button
          onClick={() => setTab('command')}
          className={`flex-1 flex items-center justify-center gap-2 text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
            tab === 'command'
              ? 'bg-surface-700 text-surface-100'
              : 'text-surface-300 hover:text-surface-100'
          }`}
        >
          <Terminal size={13} /> Via command
        </button>
        <button
          onClick={() => setTab('manual')}
          className={`flex-1 flex items-center justify-center gap-2 text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
            tab === 'manual'
              ? 'bg-surface-700 text-surface-100'
              : 'text-surface-300 hover:text-surface-100'
          }`}
        >
          <FormInput size={13} /> Manual
        </button>
      </div>

      {tab === 'command' && (
        <div className="space-y-3">
          <p className="text-xs text-surface-300">
            Run the generated script on the remote cluster. It creates a ServiceAccount with
            the required permissions and registers the cluster automatically.
          </p>
          <div className="flex gap-2">
            <Input
              className="flex-1"
              placeholder="prod-cluster"
              value={cmdName}
              onChange={(e) => setCmdName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerateScript()}
            />
            <Button
              size="sm"
              onClick={handleGenerateScript}
              loading={loadingScript}
              disabled={!cmdName.trim()}
            >
              Generate
            </Button>
          </div>

          {script && (
            <div className="relative">
              <pre className="bg-surface-950 border border-surface-600 rounded-md p-3 text-xs font-mono text-surface-200 overflow-auto max-h-64 whitespace-pre">
                {script}
              </pre>
              <button
                onClick={handleCopy}
                className="absolute top-2 right-2 p-1.5 rounded bg-surface-800 hover:bg-surface-700 text-surface-300 hover:text-surface-100 transition-colors"
                title="Copy to clipboard"
              >
                {copied ? <Check size={13} className="text-green-400" /> : <Copy size={13} />}
              </button>
            </div>
          )}

          {script && (
            <p className="text-xs text-surface-400">
              After running the script, the cluster will appear automatically in the Clusters page.
            </p>
          )}

          <div className="flex justify-end pt-1">
            <Button variant="secondary" onClick={onClose}>Close</Button>
          </div>
        </div>
      )}

      {tab === 'manual' && (
        <form onSubmit={handleManualSubmit} className="space-y-3">
          <Input
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="prod-cluster"
            required
          />
          <Input
            label="API Server URL"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="https://api.prod-cluster.example.com:6443"
            required
          />
          <div className="space-y-1">
            <label className="block text-xs font-medium text-surface-300">
              CA Certificate <span className="text-surface-500">(base64)</span>
            </label>
            <textarea
              className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-xs font-mono text-surface-100 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
              rows={3}
              value={caData}
              onChange={(e) => setCaData(e.target.value)}
              placeholder="LS0tLS1CRUdJTi..."
              required
            />
            <p className="text-xs text-surface-500">
              kubectl config view --raw -o jsonpath=&#39;&#123;.clusters[0].cluster.certificate-authority-data&#125;&#39;
            </p>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-surface-300">ServiceAccount Token</label>
            <textarea
              className="w-full bg-surface-800 border border-surface-600 rounded-md px-3 py-2 text-xs font-mono text-surface-100 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
              rows={3}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="eyJhbGciOiJSUzI1..."
              required
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" className="flex-1" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              loading={add.isPending}
              disabled={!name || !apiUrl || !caData || !token}
            >
              Add
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}
