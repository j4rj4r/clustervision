import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { tokensApi } from '../api/tokens'

export function useTokenHistory() {
  return useQuery({
    queryKey: ['token-history'],
    queryFn: tokensApi.listHistory,
    staleTime: 30_000,
  })
}

export function useDeleteHistoryEntry() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => tokensApi.deleteHistoryEntry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['token-history'] }),
  })
}

export function useClearHistory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: tokensApi.clearHistory,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['token-history'] }),
  })
}

export function useSaTokens() {
  return useQuery({
    queryKey: ['sa-tokens'],
    queryFn: tokensApi.listSaTokens,
    staleTime: 30_000,
  })
}

export function useRevokeSaToken() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ secretName, namespace }: { secretName: string; namespace: string }) =>
      tokensApi.revokeSaToken(secretName, namespace),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-tokens'] }),
  })
}

export function useRotateSaToken() {
  const qc = useQueryClient()
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sa-tokens'] }),
  })
}
