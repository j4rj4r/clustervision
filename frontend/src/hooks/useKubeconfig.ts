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
    onSuccess: (yaml, vars) => {
      const blob = new Blob([yaml], { type: 'application/x-yaml' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${vars.username}-kubeconfig.yaml`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Kubeconfig downloaded')
    },
    onError: (err: Error) => toast.error(err.message),
  })
