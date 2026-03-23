import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { usersApi } from '../api/users'
import type { CreateUserPayload } from '../types/user'

export const useUsers = () =>
  useQuery({ queryKey: ['users'], queryFn: usersApi.list })

export const useUser = (username: string) =>
  useQuery({ queryKey: ['users', username], queryFn: () => usersApi.get(username) })

export const useCreateUser = (onSuccess?: (data: Awaited<ReturnType<typeof usersApi.create>>) => void) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateUserPayload) => usersApi.create(payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      onSuccess?.(data)
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteUser = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ username, userType, namespace }: { username: string; userType: string; namespace?: string }) =>
      usersApi.delete(username, userType, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      toast.success('User deleted')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
