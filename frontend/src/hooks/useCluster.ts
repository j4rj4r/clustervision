import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { clusterApi, type AddClusterPayload } from '../api/cluster'
import { useClusterStore } from '../store/clusterStore'

export const useClusterInfo = () =>
  useQuery({
    queryKey: ['cluster-info', useClusterStore.getState().activeCluster],
    queryFn: clusterApi.info,
    staleTime: 60_000,
    retry: false,
  })

export const useClusters = () =>
  useQuery({
    queryKey: ['clusters'],
    queryFn: clusterApi.list,
    staleTime: 30_000,
  })

export const useAddCluster = (onSuccess?: () => void) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: AddClusterPayload) => clusterApi.add(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clusters'] })
      toast.success('Cluster added')
      onSuccess?.()
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export const useRemoveCluster = () => {
  const qc = useQueryClient()
  const { activeCluster, setActiveCluster } = useClusterStore()
  return useMutation({
    mutationFn: (name: string) => clusterApi.remove(name),
    onSuccess: (_data, name) => {
      qc.invalidateQueries({ queryKey: ['clusters'] })
      if (activeCluster === name) setActiveCluster('local')
      toast.success('Cluster removed')
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
