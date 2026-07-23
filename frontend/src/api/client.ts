import axios, { AxiosError } from 'axios'
import { useClusterStore } from '../store/clusterStore'
import { useAuthStore } from '../store/authStore'
import { queryClient } from '../lib/queryClient'

export interface ApiError extends Error {
  status?: number
}

// FastAPI puts a string in `detail` for business errors, but an array of
// {loc, msg} objects for 422 validation errors — stringify both readably.
export function formatApiError(err: AxiosError<{ detail?: unknown }>): ApiError {
  const detail = err.response?.data?.detail
  let message: string
  if (typeof detail === 'string') {
    message = detail
  } else if (Array.isArray(detail)) {
    message = detail
      .map((d) => {
        if (d && typeof d === 'object' && 'msg' in d) {
          const loc = Array.isArray((d as { loc?: unknown[] }).loc)
            ? (d as { loc: unknown[] }).loc.slice(1).join('.')
            : ''
          return loc ? `${loc}: ${(d as { msg: string }).msg}` : (d as { msg: string }).msg
        }
        return String(d)
      })
      .join(' — ')
  } else {
    message = err.message || 'Request failed'
  }
  const error = new Error(message) as ApiError
  error.status = err.response?.status
  return error
}

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

client.interceptors.request.use((config) => {
  const cluster = useClusterStore.getState().activeCluster
  if (cluster && cluster !== 'local') {
    config.params = { ...config.params, cluster }
  }
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let pendingQueue: Array<(token: string | null) => void> = []

const drainQueue = (token: string | null) => {
  pendingQueue.forEach((cb) => cb(token))
  pendingQueue = []
}

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push((token) => {
            if (!token) return reject(err)
            original.headers.Authorization = `Bearer ${token}`
            resolve(client(original))
          })
        })
      }

      isRefreshing = true
      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
        useAuthStore.getState().setAccessToken(data.access_token)
        drainQueue(data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return client(original)
      } catch {
        drainQueue(null)
        useAuthStore.getState().clearAuth()
        // Session data must not survive into the next login
        queryClient.clear()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(formatApiError(err))
  },
)

export default client
