import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { rbacApi } from '../api/rbac'
import type { AssignRolePayload } from '../types/rbac'

export const useClusterRoles = (includeSystem = false) =>
  useQuery({
    queryKey: ['cluster-roles', includeSystem],
    queryFn: () => rbacApi.listClusterRoles(includeSystem),
  })

export const useRoles = (namespace: string) =>
  useQuery({
    queryKey: ['roles', namespace],
    queryFn: () => rbacApi.listRoles(namespace),
    enabled: !!namespace,
  })

export const useUserPermissions = (username: string) =>
  useQuery({
    queryKey: ['user-permissions', username],
    queryFn: () => rbacApi.getUserPermissions(username),
    enabled: !!username,
  })

export const useNamespaces = () =>
  useQuery({ queryKey: ['namespaces'], queryFn: rbacApi.listNamespaces })

export const useAssignRole = (username: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ payload, userKind }: { payload: AssignRolePayload; userKind?: string }) =>
      rbacApi.assignRole(username, payload, userKind),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-permissions', username] })
      toast.success('Role assigned')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useRevokeRole = (username: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ roleName, namespace }: { roleName: string; namespace?: string }) =>
      rbacApi.revokeRole(username, roleName, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-permissions', username] })
      toast.success('Role revoked')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
