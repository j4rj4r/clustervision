import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { kubeconfigApi } from '../api/kubeconfig'
import type { UserType } from '../types/user'

interface GenerateOptions {
  username: string
  user_type: UserType
  namespace: string
  private_key_pem?: string
}

export const useGenerateKubeconfig = () =>
  useMutation({
    mutationFn: (opts: GenerateOptions) => kubeconfigApi.generate(opts),
    onError: (err: Error) => toast.error(err.message),
  })

export function downloadKubeconfig(yaml: string, username: string) {
  const blob = new Blob([yaml], { type: 'application/x-yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${username}-kubeconfig.yaml`
  a.click()
  URL.revokeObjectURL(url)
}
