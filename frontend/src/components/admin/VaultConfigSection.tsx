import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck, ShieldOff, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { vaultApi, type VaultConfig } from '../../api/vault'
import Button from '../ui/Button'
import Input from '../ui/Input'

const DEFAULT_CONFIG: VaultConfig = {
  addr: '',
  token: '',
  mount: 'secret',
  base_path: 'clustervision/users',
  namespace: '',
}

export default function VaultConfigSection() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<VaultConfig>(DEFAULT_CONFIG)

  const { data: status, isLoading } = useQuery({
    queryKey: ['vault-status'],
    queryFn: vaultApi.status,
  })

  const configure = useMutation({
    mutationFn: vaultApi.configure,
    onSuccess: (data) => {
      qc.setQueryData(['vault-status'], data)
      if (data.healthy) {
        toast.success('Vault connected and healthy')
      } else {
        toast.error(data.error ?? 'Vault health check failed — verify address and token')
      }
      setEditing(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const disable = useMutation({
    mutationFn: vaultApi.disable,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vault-status'] })
      toast.success('Vault integration disabled')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const handleEdit = () => {
    setForm({
      addr: status?.addr ?? '',
      token: '',
      mount: status?.mount ?? 'secret',
      base_path: status?.base_path ?? 'clustervision/users',
      namespace: status?.namespace ?? '',
    })
    setEditing(true)
  }

  const field = (key: keyof VaultConfig) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value })),
  })

  if (isLoading) return <div className="py-4 text-sm text-surface-500"><Loader2 size={14} className="animate-spin inline mr-2" />Loading…</div>

  return (
    <div className="bg-surface-900 border border-surface-600 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-surface-200">HashiCorp Vault</span>
          {status?.enabled ? (
            <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${status.healthy ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'}`}>
              <ShieldCheck size={11} />
              {status.healthy ? 'Connected' : 'Unreachable'}
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-surface-700 text-surface-400">
              <ShieldOff size={11} />
              Disabled
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {status?.enabled && !editing && (
            <Button size="sm" variant="ghost" className="text-red-400 hover:text-red-300" loading={disable.isPending} onClick={() => disable.mutate()}>
              Disable
            </Button>
          )}
          {!editing && (
            <Button size="sm" variant="secondary" onClick={handleEdit}>
              {status?.enabled ? 'Edit' : 'Configure'}
            </Button>
          )}
        </div>
      </div>

      {status?.enabled && !editing && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
            <span className="text-surface-500">Address</span><span className="text-surface-300 font-mono">{status.addr}</span>
            <span className="text-surface-500">Mount</span><span className="text-surface-300 font-mono">{status.mount}</span>
            <span className="text-surface-500">Base path</span><span className="text-surface-300 font-mono">{status.base_path}</span>
            {status.namespace && <><span className="text-surface-500">Namespace</span><span className="text-surface-300 font-mono">{status.namespace}</span></>}
          </div>
          {status.error && (
            <p className="text-xs text-red-400 bg-red-950/30 border border-red-500/20 rounded-lg px-3 py-2 font-mono break-all">
              {status.error}
            </p>
          )}
        </div>
      )}

      {editing && (
        <div className="space-y-3">
          <p className="text-xs text-surface-400">
            When enabled, certificate private keys are written to Vault KV v2 and <strong className="text-surface-300">not returned inline</strong>.
          </p>
          <Input label="Vault address" placeholder="https://vault.example.com" {...field('addr')} />
          <Input label="Token" type="password" placeholder="hvs.XXXX" {...field('token')} hint="Leave blank to keep existing token" />
          <div className="grid grid-cols-2 gap-3">
            <Input label="KV mount" placeholder="secret" {...field('mount')} />
            <Input label="Base path" placeholder="clustervision/users" {...field('base_path')} />
          </div>
          <Input label="Vault namespace (Enterprise only)" placeholder="admin/team" {...field('namespace')} />
          <div className="flex gap-3 pt-1">
            <Button variant="secondary" size="sm" className="flex-1" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" className="flex-1" loading={configure.isPending} disabled={!form.addr} onClick={() => configure.mutate(form)}>
              Save &amp; test connection
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
