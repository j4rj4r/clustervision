import client from './client'
import type { AssignRolePayload, BindingRead, RoleRead, UserPermissionSummary } from '../types/rbac'

export const rbacApi = {
  listClusterRoles: (includeSystem = false): Promise<RoleRead[]> =>
    client.get('/rbac/cluster-roles', { params: { include_system: includeSystem } }).then((r) => r.data),

  listRoles: (namespace: string): Promise<RoleRead[]> =>
    client.get(`/rbac/roles/${namespace}`).then((r) => r.data),

  listClusterBindings: (): Promise<BindingRead[]> =>
    client.get('/rbac/bindings/cluster').then((r) => r.data),

  listNamespaceBindings: (namespace: string): Promise<BindingRead[]> =>
    client.get(`/rbac/bindings/namespace/${namespace}`).then((r) => r.data),

  getUserPermissions: (username: string): Promise<UserPermissionSummary> =>
    client.get(`/rbac/users/${username}/permissions`).then((r) => r.data),

  assignRole: (username: string, payload: AssignRolePayload, userKind = 'User'): Promise<void> =>
    client
      .post(`/rbac/users/${username}/assign`, payload, { params: { user_kind: userKind } })
      .then(() => undefined),

  revokeRole: (username: string, roleName: string, namespace?: string): Promise<void> =>
    client
      .delete(`/rbac/users/${username}/revoke`, { params: { role_name: roleName, namespace } })
      .then(() => undefined),

  listNamespaces: (): Promise<string[]> =>
    client.get('/rbac/namespaces').then((r) => r.data),
}
