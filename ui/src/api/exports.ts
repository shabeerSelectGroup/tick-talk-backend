import { api, unwrap } from '@/api/client'
import type { ApiResponse } from '@/types'
import type { ExportJob, ExportType } from '@/types/reports'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export async function listExportJobs(eventId: number): Promise<ExportJob[]> {
  return unwrap<ExportJob[]>(await api.get(`/admin/events/${eventId}/reports/exports`))
}

export async function createExportJob(eventId: number, exportType: ExportType): Promise<ExportJob> {
  return unwrap<ExportJob>(
    await api.post(`/admin/events/${eventId}/reports/exports`, { export_type: exportType })
  )
}

export async function getExportJob(eventId: number, jobId: number): Promise<ExportJob> {
  return unwrap<ExportJob>(await api.get(`/admin/events/${eventId}/reports/exports/${jobId}`))
}

export function downloadExportUrl(eventId: number, jobId: number): string {
  return `${baseURL}/admin/events/${eventId}/reports/exports/${jobId}/download`
}

/** Download file with admin auth header (blob). */
export async function downloadExportFile(eventId: number, job: ExportJob): Promise<void> {
  const url = downloadExportUrl(eventId, job.id)
  const token = api.defaults.headers.common.Authorization as string | undefined
  const res = await fetch(url, {
    credentials: 'include',
    headers: token ? { Authorization: token } : {},
  })
  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as ApiResponse<null> | null
    throw new Error(err?.error?.message ?? 'Download failed')
  }
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = job.file_name ?? `export-${job.id}`
  a.click()
  URL.revokeObjectURL(a.href)
}
