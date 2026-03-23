import { useQuery } from '@tanstack/react-query'
import { clusterApi } from '../api/cluster'

export const useClusterInfo = () =>
  useQuery({
    queryKey: ['cluster-info'],
    queryFn: clusterApi.info,
    staleTime: 60_000,
    retry: false,
  })
