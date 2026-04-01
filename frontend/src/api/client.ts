import axios from 'axios'
import { useClusterStore } from '../store/clusterStore'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const cluster = useClusterStore.getState().activeCluster
  if (cluster && cluster !== 'local') {
    config.params = { ...config.params, cluster }
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail ?? err.message ?? 'Unknown error'
    return Promise.reject(new Error(message))
  },
)

export default client
