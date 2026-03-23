import client from './client'

export interface ClusterInfo {
  git_version: string
  platform: string
  go_version: string
}

export const clusterApi = {
  info: (): Promise<ClusterInfo> => client.get('/cluster/info').then((r) => r.data),
}
