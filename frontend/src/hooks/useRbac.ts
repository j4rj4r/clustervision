import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { rbacApi } from '../api/rbac'
import type { AssignRolePayload, PolicyRule } from '../types/rbac'

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

export const useCreateClusterRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, rules }: { name: string; rules: PolicyRule[] }) =>
      rbacApi.createClusterRole(name, rules),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cluster-roles'] })
      toast.success('ClusterRole créé')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useUpdateClusterRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, rules }: { name: string; rules: PolicyRule[] }) =>
      rbacApi.updateClusterRole(name, rules),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cluster-roles'] })
      toast.success('ClusterRole mis à jour')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteClusterRole = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => rbacApi.deleteClusterRole(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cluster-roles'] })
      toast.success('ClusterRole supprimé')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useCreateRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ namespace, name, rules }: { namespace: string; name: string; rules: PolicyRule[] }) =>
      rbacApi.createRole(namespace, name, rules),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['roles', vars.namespace] })
      toast.success('Role créé')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useUpdateRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ namespace, name, rules }: { namespace: string; name: string; rules: PolicyRule[] }) =>
      rbacApi.updateRole(namespace, name, rules),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['roles', vars.namespace] })
      toast.success('Role mis à jour')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteRole = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ namespace, name }: { namespace: string; name: string }) =>
      rbacApi.deleteRole(namespace, name),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['roles', vars.namespace] })
      toast.success('Role supprimé')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

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
