import client from './client'
import type { RoleName } from '../store/authStore'
import type { LinkedUser } from './auth'

export interface CvUser {
  username: string
  roles: Record<string, RoleName>
  source: 'local' | 'ldap'
  last_login_at?: string
  linked_managed_user: LinkedUser | null
}

export const adminApi = {
  listUsers: (): Promise<CvUser[]> =>
    client.get('/auth/users').then((r) => r.data),

  createUser: (username: string, password: string): Promise<{ username: string }> =>
    client.post('/auth/users', { username, password }).then((r) => r.data),

  deleteUser: (username: string): Promise<void> =>
    client.delete(`/auth/users/${username}`).then(() => undefined),

  resetPassword: (username: string, password: string): Promise<void> =>
    client.post(`/auth/users/${username}/password`, { username, password }).then(() => undefined),

  setLink: (username: string, name: string, namespace: string): Promise<LinkedUser> =>
    client.put(`/auth/users/${username}/link`, { name, namespace }).then((r) => r.data),

  clearLink: (username: string): Promise<void> =>
    client.delete(`/auth/users/${username}/link`).then(() => undefined),
}
