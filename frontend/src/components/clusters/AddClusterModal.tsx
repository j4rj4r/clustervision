import { useState } from 'react'
import Modal from '../ui/Modal'
import Input from '../ui/Input'
import Button from '../ui/Button'
import { useAddCluster } from '../../hooks/useCluster'

interface Props {
  onClose: () => void
}

export default function AddClusterModal({ onClose }: Props) {
  const [name, setName] = useState('')
  const [apiUrl, setApiUrl] = useState('')
  const [caData, setCaData] = useState('')
  const [token, setToken] = useState('')

  const add = useAddCluster(onClose)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name || !apiUrl || !caData || !token) return
    add.mutate({ name, api_url: apiUrl, ca_data: caData, token })
  }

  return (
    <Modal open onClose={onClose} title="Add cluster">
      <form onSubmit={handleSubmit} className="space-y-3">
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
          <label className="block text-xs font-medium text-slate-400">
            CA Certificate <span className="text-slate-600">(base64 du PEM)</span>
          </label>
          <textarea
            className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
            rows={3}
            value={caData}
            onChange={(e) => setCaData(e.target.value)}
            placeholder="LS0tLS1CRUdJTi..."
            required
          />
          <p className="text-xs text-slate-600">
            kubectl config view --raw -o jsonpath='{'{.clusters[0].cluster.certificate-authority-data}'}'
          </p>
        </div>
        <div className="space-y-1">
          <label className="block text-xs font-medium text-slate-400">ServiceAccount Token</label>
          <textarea
            className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
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
    </Modal>
  )
}
