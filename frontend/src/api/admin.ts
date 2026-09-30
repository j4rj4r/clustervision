import client from './client'
import type { RoleName } from '../store/authStore'

export interface CvUser {
  username: string
  roles: Record<string, RoleName>
  source: 'local' | 'ldap'
  last_login_at?: string
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
}
