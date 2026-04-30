import client from './client'

export interface AccessRequest {
  id: string
  requester: string
  role_name: string
  role_kind: string
  namespace: string | null
  justification: string
  status: 'pending' | 'approved' | 'denied'
  created_at: string
  resolved_at: string | null
  resolved_by: string | null
  denial_reason: string | null
}

export interface CreateRequestPayload {
  role_name: string
  role_kind: string
  namespace?: string | null
  justification: string
}

export const accessRequestsApi = {
  list: (status?: string): Promise<AccessRequest[]> =>
    client.get('/access-requests', { params: status ? { status } : {} }).then((r) => r.data),

  create: (payload: CreateRequestPayload): Promise<AccessRequest> =>
    client.post('/access-requests', payload).then((r) => r.data),

  approve: (id: string): Promise<AccessRequest> =>
    client.post(`/access-requests/${id}/approve`).then((r) => r.data),

  deny: (id: string, reason: string): Promise<AccessRequest> =>
    client.post(`/access-requests/${id}/deny`, { reason }).then((r) => r.data),

  cancel: (id: string): Promise<void> =>
    client.delete(`/access-requests/${id}`).then(() => undefined),
}
