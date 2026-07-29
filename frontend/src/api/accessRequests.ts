import client from './client'
import type {
  AccessRequest,
  AccessRequestCreatePayload,
  AccessRequestExportQuery,
  JitRolePolicy,
  JitRolePolicySetPayload,
} from '../types/accessRequest'

export const accessRequestsApi = {
  list: (): Promise<AccessRequest[]> =>
    client.get('/access-requests').then((r) => r.data),

  create: (payload: AccessRequestCreatePayload): Promise<AccessRequest> =>
    client.post('/access-requests', payload).then((r) => r.data),

  approve: (id: string): Promise<AccessRequest> =>
    client.post(`/access-requests/${id}/approve`).then((r) => r.data),

  deny: (id: string): Promise<AccessRequest> =>
    client.post(`/access-requests/${id}/deny`).then((r) => r.data),

  revoke: (id: string): Promise<AccessRequest> =>
    client.post(`/access-requests/${id}/revoke`).then((r) => r.data),

  listPolicies: (): Promise<JitRolePolicy[]> =>
    client.get('/access-requests/policies').then((r) => r.data),

  setPolicy: (roleKind: string, roleName: string, payload: JitRolePolicySetPayload): Promise<JitRolePolicy> =>
    client.put(`/access-requests/policies/${roleKind}/${roleName}`, payload).then((r) => r.data),

  deletePolicy: (roleKind: string, roleName: string): Promise<void> =>
    client.delete(`/access-requests/policies/${roleKind}/${roleName}`).then(() => undefined),

  export: (query: AccessRequestExportQuery): Promise<Blob> =>
    client.get('/access-requests/export', { params: query, responseType: 'blob' }).then((r) => r.data),
}
