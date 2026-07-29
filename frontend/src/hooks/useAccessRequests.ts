import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { accessRequestsApi } from '../api/accessRequests'
import { useClusterStore } from '../store/clusterStore'
import type { AccessRequestCreatePayload, JitRolePolicySetPayload } from '../types/accessRequest'

const useCluster = () => useClusterStore((s) => s.activeCluster)

export const useAccessRequests = () => {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['access-requests', cluster],
    queryFn: accessRequestsApi.list,
    staleTime: 15_000,
    // Pending/active grants change state on their own (approval, expiry) —
    // poll gently so the queue and countdowns don't go stale while the page
    // is open, without hammering the API.
    refetchInterval: 30_000,
  })
}

export const useCreateAccessRequest = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (payload: AccessRequestCreatePayload) => accessRequestsApi.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['access-requests', cluster] })
      toast.success('Access request submitted')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useApproveAccessRequest = () => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (id: string) => accessRequestsApi.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['access-requests', cluster] })
      toast.success('Access granted')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDenyAccessRequest = () => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (id: string) => accessRequestsApi.deny(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['access-requests', cluster] })
      toast.success('Request denied')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useRevokeAccessRequest = () => {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (id: string) => accessRequestsApi.revoke(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['access-requests', cluster] })
      toast.success('Access revoked')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useJitPolicies = () =>
  useQuery({
    queryKey: ['jit-policies'],
    queryFn: accessRequestsApi.listPolicies,
    staleTime: 15_000,
  })

export const useSetJitPolicy = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ roleKind, roleName, payload }: { roleKind: string; roleName: string; payload: JitRolePolicySetPayload }) =>
      accessRequestsApi.setPolicy(roleKind, roleName, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jit-policies'] })
      toast.success('Policy saved')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useDeleteJitPolicy = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ roleKind, roleName }: { roleKind: string; roleName: string }) =>
      accessRequestsApi.deletePolicy(roleKind, roleName),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jit-policies'] })
      toast.success('Policy override removed')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
