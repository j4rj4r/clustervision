import client from './client'

export interface CvUser {
  username: string
  role: 'admin' | 'viewer'
}

export const adminApi = {
  listUsers: (): Promise<CvUser[]> =>
    client.get('/auth/users').then((r) => r.data),

  createUser: (username: string, password: string, role: string): Promise<CvUser> =>
    client.post('/auth/users', { username, password, role }).then((r) => r.data),

  deleteUser: (username: string): Promise<void> =>
    client.delete(`/auth/users/${username}`).then(() => undefined),

  changeRole: (username: string, role: string): Promise<void> =>
    client.patch(`/auth/users/${username}/role`, { role }).then(() => undefined),

  resetPassword: (username: string, password: string): Promise<void> =>
    client.post(`/auth/users/${username}/password`, { username, password }).then(() => undefined),
}
