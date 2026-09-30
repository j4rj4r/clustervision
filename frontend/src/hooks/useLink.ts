import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { adminApi } from '../api/admin'
import { authApi } from '../api/auth'

export const useMyLink = () =>
  useQuery({
    queryKey: ['my-link'],
    queryFn: authApi.myLink,
    staleTime: 30_000,
  })

export const useSetLink = (username: string | null) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, namespace }: { name: string; namespace: string }) =>
      adminApi.setLink(username!, name, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      qc.invalidateQueries({ queryKey: ['my-link'] })
      toast.success('Identity linked')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useClearLink = (username: string | null) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => adminApi.clearLink(username!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      qc.invalidateQueries({ queryKey: ['my-link'] })
      toast.success('Identity unlinked')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
