import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { tokensApi } from '../api/tokens'
import { useClusterStore } from '../store/clusterStore'

// Token history lives in a ConfigMap inside the cluster and SA tokens are
// cluster resources — the axios interceptor sends ?cluster= with every call,
// so cached data is only valid for the cluster it was fetched from.
const useCluster = () => useClusterStore((s) => s.activeCluster)

export function useTokenHistory() {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['token-history', cluster],
    queryFn: tokensApi.listHistory,
    staleTime: 30_000,
  })
}

export function useDeleteHistoryEntry() {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: (id: string) => tokensApi.deleteHistoryEntry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['token-history', cluster] }),
    onError: (err: Error) => toast.error(err.message),
  })
}

export function useClearHistory() {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: tokensApi.clearHistory,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['token-history', cluster] }),
    onError: (err: Error) => toast.error(err.message),
  })
}

export function useSaTokens() {
  const cluster = useCluster()
  return useQuery({
    queryKey: ['sa-tokens', cluster],
    queryFn: tokensApi.listSaTokens,
    staleTime: 30_000,
  })
}

export function useRevokeSaToken() {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({ secretName, namespace }: { secretName: string; namespace: string }) =>
      tokensApi.revokeSaToken(secretName, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sa-tokens', cluster] })
      toast.success('Token revoked')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export function useRotateSaToken() {
  const qc = useQueryClient()
  const cluster = useCluster()
  return useMutation({
    mutationFn: ({
      secretName,
      saName,
      namespace,
    }: {
      secretName: string
      saName: string
      namespace: string
    }) => tokensApi.rotateSaToken(secretName, saName, namespace),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sa-tokens', cluster] })
      toast.success('Token rotated')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
