import client from './client'

export interface DriftEvent {
  kind: 'external_modification' | 'label_stripped' | 'orphaned'
  binding_name: string
  namespace: string | null
  detail: string
  detected_at: string
}

export const driftApi = {
  list: (limit = 50): Promise<{ events: DriftEvent[]; total: number }> =>
    client.get('/drift/events', { params: { limit } }).then((r) => r.data),

  scan: (): Promise<{ new_events: DriftEvent[]; count: number }> =>
    client.post('/drift/scan').then((r) => r.data),

  clear: (): Promise<void> =>
    client.delete('/drift/events').then(() => undefined),
}
