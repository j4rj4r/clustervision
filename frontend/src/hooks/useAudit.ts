import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { auditApi } from '../api/audit'
import { downloadBlob } from '../lib/downloadBlob'
import type { AuditLogExportQuery, AuditLogQuery } from '../types/audit'

export const useAuditLog = (query: AuditLogQuery, enabled = true) =>
  useQuery({
    queryKey: ['audit-log', query],
    queryFn: () => auditApi.list(query),
    placeholderData: keepPreviousData,
    staleTime: 15_000,
    enabled,
  })

export const useExportAuditLog = () =>
  useMutation({
    mutationFn: (query: AuditLogExportQuery) => auditApi.export(query),
    onSuccess: (blob) => downloadBlob(blob, 'clustervision-audit-log.csv'),
    onError: (err: Error) => toast.error(err.message),
  })
