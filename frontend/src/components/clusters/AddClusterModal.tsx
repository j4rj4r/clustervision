import { useState } from 'react'
import { X } from 'lucide-react'
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

  const handleSubmit = () => {
    if (!name || !apiUrl || !caData || !token) return
    add.mutate({ name, api_url: apiUrl, ca_data: caData, token })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-100">Ajouter un cluster</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300"><X size={16} /></button>
        </div>

        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Nom</label>
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-brand-500"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="prod-cluster"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">API Server URL</label>
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-brand-500"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="https://api.prod-cluster.example.com:6443"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              CA Certificate <span className="text-slate-600">(base64 du PEM)</span>
            </label>
            <textarea
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-brand-500 resize-none"
              rows={3}
              value={caData}
              onChange={(e) => setCaData(e.target.value)}
              placeholder="LS0tLS1CRUdJTi..."
            />
            <p className="text-xs text-slate-600 mt-0.5">
              kubectl config view --raw -o jsonpath='&#123;.clusters[0].cluster.certificate-authority-data&#125;'
            </p>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">ServiceAccount Token</label>
            <textarea
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-brand-500 resize-none"
              rows={3}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="eyJhbGciOiJSUzI1..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-800">
          <Button variant="ghost" size="sm" onClick={onClose}>Annuler</Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            loading={add.isPending}
            disabled={!name || !apiUrl || !caData || !token}
          >
            Ajouter
          </Button>
        </div>
      </div>
    </div>
  )
}
