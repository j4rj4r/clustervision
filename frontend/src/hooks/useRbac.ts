import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { rbacApi } from '../api/rbac'
import { useClusterStore } from '../store/clusterStore'
import type { AssignRolePayload, CheckAccessRequest, PolicyRule } from '../types/rbac'

const useCluster = () => useClusterStore((s) => s.activeCluster)

export const useClusterRoles = (includeSystem = false, enabled = true) => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['cluster-roles', cluster, includeSystem],
    queryFn: () => rbacApi.listClusterRoles(includeSystem),
    staleTime: 60_000,
    enabled,
  })
}

export const useRoles = (namespace: string) => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['roles', cluster, namespace],
    queryFn: () => rbacApi.listRoles(namespace),
    staleTime: 60_000,
    enabled: !!namespace,
  })
}

export const useUserPermissions = (username: string) => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['user-permissions', cluster, username],
    queryFn: () => rbacApi.getUserPermissions(username),
    staleTime: 30_000,
    enabled: !!username,
  })
}

export const useNamespaces = () => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['namespaces', cluster],
    queryFn: rbacApi.listNamespaces,
    staleTime: 120_000,
  })
}

export const useNamespaceAccess = (namespace: string) => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['namespace-access', cluster, namespace],
    queryFn: () => rbacApi.getNamespaceAccess(namespace),
    staleTime: 30_000,
    enabled: !!namespace,
  })
}

export const useCheckAccess = () =>
  useMutation({ mutationFn: (req: CheckAccessRequest) => rbacApi.checkAccess(req) })

export const useCreateClusterRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ name, rules }: { name: string; rules: PolicyRule[] }) =>
      rbacApi.createClusterRole(name, rules),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cluster-roles', cluster] })
      toast.success('ClusterRole created')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useUpdateClusterRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ name, rules }: { name: string; rules: PolicyRule[] }) =>
      rbacApi.updateClusterRole(name, rules),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cluster-roles', cluster] })
      toast.success('ClusterRole updated')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteClusterRole = () => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (name: string) => rbacApi.deleteClusterRole(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cluster-roles', cluster] })
      toast.success('ClusterRole deleted')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useCreateRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ namespace, name, rules }: { namespace: string; name: string; rules: PolicyRule[] }) =>
      rbacApi.createRole(namespace, name, rules),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['roles', cluster, vars.namespace] })
      toast.success('Role created')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useUpdateRole = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ namespace, name, rules }: { namespace: string; name: string; rules: PolicyRule[] }) =>
      rbacApi.updateRole(namespace, name, rules),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['roles', cluster, vars.namespace] })
      toast.success('Role updated')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteRole = () => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ namespace, name }: { namespace: string; name: string }) =>
      rbacApi.deleteRole(namespace, name),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['roles', cluster, vars.namespace] })
      toast.success('Role deleted')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useAssignRole = (username: string) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ payload, userKind }: { payload: AssignRolePayload; userKind?: string }) =>
      rbacApi.assignRole(username, payload, userKind),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-permissions', cluster, username] })
      toast.success('Role assigned')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useRevokeRole = (username: string) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ roleName, namespace }: { roleName: string; namespace?: string }) =>
      rbacApi.revokeRole(username, roleName, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user-permissions', cluster, username] })
      toast.success('Role revoked')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
