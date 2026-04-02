import client from './client'
import type { AssignRolePayload, BindingRead, CheckAccessRequest, CheckAccessResult, NamespaceAccessEntry, PaginatedList, PolicyRule, RoleRead, UserPermissionSummary } from '../types/rbac'

export const rbacApi = {
  listClusterRoles: (includeSystem = false, limit = 500, cursor?: string): Promise<PaginatedList<RoleRead>> =>
    client.get('/rbac/cluster-roles', { params: { include_system: includeSystem, limit, ...(cursor ? { continue: cursor } : {}) } }).then((r) => r.data),

  createClusterRole: (name: string, rules: PolicyRule[]): Promise<RoleRead> =>
    client.post('/rbac/cluster-roles', { name, rules }).then((r) => r.data),

  updateClusterRole: (name: string, rules: PolicyRule[]): Promise<RoleRead> =>
    client.patch(`/rbac/cluster-roles/${name}`, { rules }).then((r) => r.data),

  deleteClusterRole: (name: string): Promise<void> =>
    client.delete(`/rbac/cluster-roles/${name}`).then(),

  listRoles: (namespace: string, limit = 500, cursor?: string): Promise<PaginatedList<RoleRead>> =>
    client.get(`/rbac/roles/${namespace}`, { params: { limit, ...(cursor ? { continue: cursor } : {}) } }).then((r) => r.data),

  createRole: (namespace: string, name: string, rules: PolicyRule[]): Promise<RoleRead> =>
    client.post('/rbac/roles', { namespace, name, rules }).then((r) => r.data),

  updateRole: (namespace: string, name: string, rules: PolicyRule[]): Promise<RoleRead> =>
    client.put(`/rbac/roles/${namespace}/${name}`, { rules }).then((r) => r.data),

  deleteRole: (namespace: string, name: string): Promise<void> =>
    client.delete(`/rbac/roles/${namespace}/${name}`).then(),

  listClusterBindings: (): Promise<BindingRead[]> =>
    client.get('/rbac/bindings/cluster').then((r) => r.data),

  listNamespaceBindings: (namespace: string): Promise<BindingRead[]> =>
    client.get(`/rbac/bindings/namespace/${namespace}`).then((r) => r.data),

  getUserPermissions: (username: string): Promise<UserPermissionSummary> =>
    client.get(`/rbac/users/${username}/permissions`).then((r) => r.data),

  assignRole: (username: string, payload: AssignRolePayload, userKind = 'User', saNamespace?: string): Promise<void> =>
    client
      .post(`/rbac/users/${username}/roles`, payload, { params: { user_kind: userKind, sa_namespace: saNamespace } })
      .then(),

  revokeRole: (username: string, roleName: string, namespace?: string): Promise<void> =>
    client
      .delete(`/rbac/users/${username}/roles/${roleName}`, { params: { namespace } })
      .then(),

  listNamespaces: (): Promise<string[]> =>
    client.get('/rbac/namespaces').then((r) => r.data),

  getNamespaceAccess: (namespace: string): Promise<NamespaceAccessEntry[]> =>
    client.get(`/rbac/namespace/${namespace}/access`).then((r) => r.data),

  checkAccess: (req: CheckAccessRequest): Promise<CheckAccessResult> =>
    client.post('/rbac/check-access', req).then((r) => r.data),
}
