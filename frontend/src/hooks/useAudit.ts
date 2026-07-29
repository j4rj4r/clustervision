import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { auditApi } from '../api/audit'
import type { AuditLogQuery } from '../types/audit'

export const useAuditLog = (query: AuditLogQuery, enabled = true) =>
  useQuery({
    queryKey: ['audit-log', query],
    queryFn: () => auditApi.list(query),
    placeholderData: keepPreviousData,
    staleTime: 15_000,
    enabled,
  })
