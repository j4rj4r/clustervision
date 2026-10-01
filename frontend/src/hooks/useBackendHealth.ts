import { useQuery } from '@tanstack/react-query'
import client from '../api/client'

// Deliberately NOT scoped by activeCluster (unlike useClusterInfo) — this is
// "is the ClusterVision backend itself reachable", independent of whether
// the currently selected K8s cluster happens to be up. /auth/me is a pure
// JWT decode with no DB/K8s calls, so it can't fail because of a broken
// cluster — only because the backend truly can't be reached.
export const useBackendHealth = () =>
  useQuery({
    queryKey: ['backend-health'],
    queryFn: () => client.get('/auth/me').then(() => true as const),
    staleTime: 60_000,
    retry: false,
  })
