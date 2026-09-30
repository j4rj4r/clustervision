import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { permissionsApi } from '../api/permissions'
import type { RoleName } from '../store/authStore'

export const useScopes = () =>
  useQuery({
    queryKey: ['permission-scopes'],
    queryFn: permissionsApi.listScopes,
    staleTime: 30_000,
  })

export const useUserRoles = (username: string | null) =>
  useQuery({
    queryKey: ['user-roles', username],
    queryFn: () => permissionsApi.listUserRoles(username!),
    enabled: !!username,
  })

export const useSetUserRole = (username: string | null) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ scope, role }: { scope: string; role: RoleName }) =>
      permissionsApi.setUserRole(username!, scope, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-roles', username] })
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      toast.success('Role saved')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteUserRole = (username: string | null) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scope: string) => permissionsApi.deleteUserRole(username!, scope),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-roles', username] })
      qc.invalidateQueries({ queryKey: ['cv-users'] })
      toast.success('Role removed')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
