import client from './client'

export interface VaultStatus {
  enabled: boolean
  addr?: string
  mount?: string
  base_path?: string
  namespace?: string
  healthy?: boolean
  error?: string | null
}

export interface VaultConfig {
  addr: string
  token: string
  mount: string
  base_path: string
  namespace: string
}

export const vaultApi = {
  status: (): Promise<VaultStatus> =>
    client.get('/admin/vault/status').then((r) => r.data),

  configure: (config: VaultConfig): Promise<VaultStatus> =>
    client.put('/admin/vault/config', config).then((r) => r.data),

  disable: (): Promise<void> =>
    client.delete('/admin/vault/config').then(() => undefined),
}
