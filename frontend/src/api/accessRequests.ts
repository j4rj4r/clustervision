import client from './client'
import type { AccessRequest, AccessRequestCreatePayload } from '../types/accessRequest'

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
}
