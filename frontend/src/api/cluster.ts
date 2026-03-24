import client from './client'

export interface ClusterInfo {
  git_version: string
  platform: string
  go_version: string
}

export interface ClusterEntry {
  name: string
  api_url: string
  is_local: boolean
}

export interface AddClusterPayload {
  name: string
  api_url: string
  ca_data: string
  token: string
}

export const clusterApi = {
  info: (): Promise<ClusterInfo> =>
    client.get('/cluster/info').then((r) => r.data),

  list: (): Promise<ClusterEntry[]> =>
    client.get('/cluster/clusters').then((r) => r.data),

  add: (payload: AddClusterPayload): Promise<ClusterEntry> =>
    client.post('/cluster/clusters', payload).then((r) => r.data),

  remove: (name: string): Promise<void> =>
    client.delete(`/cluster/clusters/${name}`).then(() => undefined),

  bootstrapScript: (name: string): Promise<string> =>
    client.get(`/cluster/bootstrap-script`, { params: { name }, responseType: 'text' }).then((r) => r.data),
}
