import client from './client'
import type { UserType } from '../types/user'

interface KubeconfigRequest {
  username: string
  user_type: UserType
  namespace: string
  /** Namespace the SA lives in — disambiguates same-named SAs across
   *  namespaces (`namespace` is only the kubeconfig's default context) */
  sa_namespace?: string
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
