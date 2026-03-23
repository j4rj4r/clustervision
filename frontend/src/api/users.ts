import client from './client'
import type { CreateUserPayload, User, UserList, UserWithCredentials } from '../types/user'

export interface ImportUserPayload {
  name: string
  user_type: UserType
  namespace: string
  groups: string[]
}

export const usersApi = {
  list: (): Promise<UserList> => client.get('/users').then((r) => r.data),

  listUnmanagedServiceAccounts: (): Promise<{ name: string; namespace: string }[]> =>
    client.get('/users/unmanaged-serviceaccounts').then((r) => r.data),

  import: (payload: ImportUserPayload): Promise<User> =>
    client.post('/users/import', payload).then((r) => r.data),

  get: (username: string): Promise<User> =>
    client.get(`/users/${username}`).then((r) => r.data),

  create: (payload: CreateUserPayload): Promise<UserWithCredentials> =>
    client.post('/users', payload).then((r) => r.data),

  delete: (username: string, userType: string, namespace = 'default'): Promise<void> =>
    client
      .delete(`/users/${username}`, { params: { user_type: userType, namespace } })
      .then(() => undefined),
}
