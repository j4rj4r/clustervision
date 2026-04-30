import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Lock, CheckCircle, XCircle, ChevronDown, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { vaultAdminApi, type VaultConfig } from '../../api/vaultAdmin'
import Button from '../ui/Button'
import Input from '../ui/Input'

export default function VaultConfigSection() {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(false)
  const [form, setForm] = useState<VaultConfig>({
    addr: '',
    token: '',
    mount: 'secret',
    base_path: 'clustervision/users',
    namespace: '',
  })

  const { data: status } = useQuery({
    queryKey: ['vault-status'],
    queryFn: vaultAdminApi.status,
    refetchInterval: 60_000,
  })

  const configure = useMutation({
    mutationFn: (config: VaultConfig) => vaultAdminApi.configure(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vault-status'] })
      toast.success('Vault configured successfully')
      setExpanded(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const disable = useMutation({
    mutationFn: vaultAdminApi.disable,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vault-status'] })
      toast.success('Vault integration disabled')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const field = (key: keyof VaultConfig) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value })),
  })

  return (
    <div className="bg-surface-900 border border-surface-600 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-surface-800/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Lock size={16} className="text-brand-400" />
          <div>
            <p className="text-sm font-medium text-surface-100">Vault integration</p>
            <p className="text-xs text-surface-400 mt-0.5">
              Store private keys in HashiCorp Vault instead of displaying them once
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {status?.enabled ? (
            <span className="flex items-center gap-1.5 text-xs">
              {status.healthy
                ? <><CheckCircle size={12} className="text-emerald-400" /><span className="text-emerald-400">Connected</span></>
                : <><XCircle size={12} className="text-red-400" /><span className="text-red-400">Unhealthy</span></>
              }
            </span>
          ) : (
            <span className="text-xs text-surface-500">Disabled</span>
          )}
          {expanded ? <ChevronDown size={15} className="text-surface-400" /> : <ChevronRight size={15} className="text-surface-400" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-surface-700 px-5 py-5 space-y-4">
          {status?.enabled && (
            <div className="flex items-center justify-between p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-lg">
              <div className="text-xs text-emerald-300">
                <p className="font-medium">Vault active</p>
                <p className="text-emerald-400/70 mt-0.5">{status.addr} — mount: {status.mount}</p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="text-red-400 hover:text-red-300"
                loading={disable.isPending}
                onClick={() => disable.mutate()}
              >
                Disable
              </Button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <Input label="Vault address" placeholder="https://vault.example.com" {...field('addr')} />
            <Input label="Token" type="password" placeholder="hvs.xxxxxx" {...field('token')} />
            <Input label="KV mount" placeholder="secret" {...field('mount')} />
            <Input label="Base path" placeholder="clustervision/users" {...field('base_path')} />
            <Input label="Vault namespace" placeholder="(Enterprise only)" {...field('namespace')} />
          </div>

          <p className="text-xs text-surface-500">
            When enabled, private keys are stored at <code className="font-mono bg-surface-700 px-1 rounded">{`{mount}/data/{base_path}/{username}`}</code> and never returned in the API response.
          </p>

          <div className="flex gap-3">
            <Button variant="secondary" size="sm" onClick={() => setExpanded(false)}>Cancel</Button>
            <Button
              size="sm"
              loading={configure.isPending}
              disabled={!form.addr || !form.token}
              onClick={() => configure.mutate(form)}
            >
              Save & test connection
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
