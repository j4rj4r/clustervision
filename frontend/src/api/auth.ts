import axios from 'axios'
import client, { formatApiError } from './client'
import type { RoleName } from '../store/authStore'

export interface LinkedUser {
  name: string
  namespace: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  roles: Record<string, RoleName>
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

  // Uses the regular (Bearer-authenticated) client, not authClient — this
  // needs the access token, unlike login/refresh/logout which run on the cookie.
  myLink: (): Promise<LinkedUser | null> =>
    client.get('/auth/me/link').then((r) => r.data),
}
