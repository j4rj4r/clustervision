import client from './client'
import type { RoleName } from '../store/authStore'

export interface ScopeRole {
  scope: string
  role: RoleName
}

export const permissionsApi = {
  listScopes: (): Promise<string[]> =>
    client.get('/permissions/scopes').then((r) => r.data),

  listUserRoles: (username: string): Promise<ScopeRole[]> =>
    client.get(`/permissions/users/${username}`).then((r) => r.data),

  setUserRole: (username: string, scope: string, role: RoleName): Promise<ScopeRole> =>
    client.put(`/permissions/users/${username}/${scope}`, { role }).then((r) => r.data),

  deleteUserRole: (username: string, scope: string): Promise<void> =>
    client.delete(`/permissions/users/${username}/${scope}`).then(() => undefined),
}
