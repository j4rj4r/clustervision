import client from './client'
import type { SaTokenInfo, TokenHistoryEntry } from '../types/token'

export const tokensApi = {
  listHistory: (): Promise<TokenHistoryEntry[]> =>
    client.get('/tokens/history').then((r) => r.data),

  deleteHistoryEntry: (id: string): Promise<void> =>
    client.delete(`/tokens/history/${id}`).then(() => undefined),

  clearHistory: (): Promise<void> =>
    client.delete('/tokens/history').then(() => undefined),

  listSaTokens: (): Promise<SaTokenInfo[]> =>
    client.get('/tokens/sa-tokens').then((r) => r.data),

  revokeSaToken: (secretName: string, namespace: string): Promise<void> =>
    client.delete(`/tokens/sa-tokens/${secretName}`, { params: { namespace } }).then(() => undefined),

  rotateSaToken: (secretName: string, saName: string, namespace: string): Promise<void> =>
    client
      .post(`/tokens/sa-tokens/${secretName}/rotate`, { sa_name: saName, namespace })
      .then(() => undefined),
}
