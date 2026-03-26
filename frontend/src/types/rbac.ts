export interface PolicyRule {
  api_groups: string[]
  resources: string[]
  verbs: string[]
  resource_names?: string[]
}

export interface RoleRead {
  name: string
  namespace?: string
  rules: PolicyRule[]
  is_system: boolean
}

export type SubjectKind = 'User' | 'Group' | 'ServiceAccount'

export interface Subject {
  kind: SubjectKind
  name: string
  namespace?: string
}

export interface BindingRead {
  name: string
  namespace?: string
  role_ref: string
  role_kind: string
  subjects: Subject[]
}

export interface UserPermissionSummary {
  username: string
  cluster_bindings: BindingRead[]
  namespace_bindings: BindingRead[]
}

export interface AssignRolePayload {
  role_name: string
  role_kind: 'ClusterRole' | 'Role'
  namespace?: string
}

export interface NamespaceAccessEntry {
  subject: string
  subject_kind: 'User' | 'Group' | 'ServiceAccount'
  subject_namespace?: string
  role: string
  role_kind: 'Role' | 'ClusterRole'
  binding: string
  scope: 'namespace' | 'cluster'
}

export interface CheckAccessRequest {
  user: string
  verb: string
  resource: string
  namespace?: string
  api_group?: string
}

export interface CheckAccessResult {
  allowed: boolean
  denied: boolean
  reason: string
}
