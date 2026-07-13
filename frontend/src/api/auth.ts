import axios from 'axios'
import { formatApiError } from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
  role: 'admin' | 'viewer'
  username: string
}

// Dedicated client for auth — no token injection, always sends cookies
const authClient = axios.create({ baseURL: '/api/v1', withCredentials: true })

authClient.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(formatApiError(err)),
)

export const authApi = {
  login: (username: string, password: string): Promise<LoginResponse> =>
    authClient.post('/auth/login', { username, password }).then((r) => r.data),

  refresh: (): Promise<LoginResponse> =>
    authClient.post('/auth/refresh').then((r) => r.data),

  logout: (): Promise<void> =>
    authClient.post('/auth/logout').then(() => undefined),

  me: (): Promise<LoginResponse> =>
    authClient.get('/auth/me').then((r) => r.data),
}
