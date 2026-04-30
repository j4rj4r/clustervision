import { useState } from 'react'
import { AlertTriangle, Clipboard, Download, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { useRenewCertificate } from '../../hooks/useUsers'
import type { UserWithCredentials } from '../../types/user'

interface Props {
  username: string | null
  onClose: () => void
}

export default function RenewCertModal({ username, onClose }: Props) {
  const [credentials, setCredentials] = useState<UserWithCredentials | null>(null)
  const [confirmed, setConfirmed] = useState(false)

  const renew = useRenewCertificate((data) => setCredentials(data))

  const handleClose = () => {
    setCredentials(null)
    setConfirmed(false)
    onClose()
  }

  const handleCopy = async () => {
    if (!credentials?.private_key_pem) return
    await navigator.clipboard.writeText(credentials.private_key_pem)
    toast.success('Private key copied')
  }

  const handleDownload = () => {
    if (!credentials) return
    const content = [
      `# ClusterVision credentials for ${credentials.name}`,
      `# Renewed: ${new Date().toISOString()}`,
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

  const canClose = !credentials || confirmed

  return (
    <Modal
      open={!!username}
      onClose={canClose ? handleClose : () => {}}
      title="Renew certificate"
      size="md"
    >
      {!credentials ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-amber-900/20 border border-amber-500/30 rounded-lg">
            <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
            <div className="text-xs text-amber-300 space-y-1">
              <p className="font-semibold">A new key pair will be generated.</p>
              <p>The old certificate remains valid until its original expiry date. Distribute the new kubeconfig after renewal.</p>
            </div>
          </div>
          <p className="text-sm text-surface-400">
            Renew certificate for <span className="font-mono text-surface-100">{username}</span>?
          </p>
          <div className="flex gap-3">
            <Button variant="secondary" size="sm" className="flex-1" onClick={handleClose}>Cancel</Button>
            <Button
              size="sm"
              className="flex-1"
              loading={renew.isPending}
              onClick={() => username && renew.mutate(username)}
            >
              <RefreshCw size={13} /> Renew
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-amber-900/20 border border-amber-500/30 rounded-lg">
            <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-300">
              <span className="font-semibold">One-time display.</span> The private key is not stored — save it now.
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-surface-300">Private Key</label>
              <button onClick={handleCopy} className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
                <Clipboard size={11} /> Copy
              </button>
            </div>
            <pre className="bg-surface-950 border border-surface-600 rounded-md p-3 text-xs text-surface-200 max-h-28 overflow-y-auto font-mono">
              {credentials.private_key_pem}
            </pre>
          </div>

          <Button variant="secondary" onClick={handleDownload} className="w-full">
            <Download size={13} /> Download credentials.pem
          </Button>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="mt-0.5 accent-brand-500"
            />
            <span className="text-sm text-surface-200">I have saved my private key. I understand it cannot be recovered.</span>
          </label>

          <Button className="w-full" disabled={!confirmed} onClick={handleClose}>
            Done
          </Button>
        </div>
      )}
    </Modal>
  )
}
