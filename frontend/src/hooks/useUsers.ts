import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { usersApi, type ImportUserPayload } from '../api/users'
import { useClusterStore } from '../store/clusterStore'
import type { CreateUserPayload, DeleteUserPayload } from '../types/user'

const useCluster = () => useClusterStore((s) => s.activeCluster)

export const useUsers = () => {
  const cluster = useCluster()
  return useQuery({ queryKey: ['users', cluster], queryFn: usersApi.list })
}

export const useCreateUser = (onSuccess?: (data: Awaited<ReturnType<typeof usersApi.create>>) => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (payload: CreateUserPayload) => usersApi.create(payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['users', cluster] })
      onSuccess?.(data)
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useUnmanagedServiceAccounts = () => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['unmanaged-sa', cluster],
    queryFn: usersApi.listUnmanagedServiceAccounts,
  })
}

export const useImportUser = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (payload: ImportUserPayload) => usersApi.import(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', cluster] })
      qc.invalidateQueries({ queryKey: ['unmanaged-sa', cluster] })
      toast.success('User imported')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteUser = () => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ username, userType, namespace }: DeleteUserPayload) =>
      usersApi.delete(username, userType, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users', cluster] })
      toast.success('User deleted')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
