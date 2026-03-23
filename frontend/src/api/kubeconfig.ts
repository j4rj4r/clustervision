import client from './client'
import type { UserType } from '../types/user'

interface KubeconfigRequest {
  username: string
  user_type: UserType
  namespace: string
  private_key_pem?: string
}

export const kubeconfigApi = {
  generate: async (payload: KubeconfigRequest): Promise<string> => {
    const res = await client.post('/kubeconfig/generate', payload, {
      responseType: 'text',
    })
    return res.data as string
  },
}
