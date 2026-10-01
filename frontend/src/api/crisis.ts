import request from '@/utils/request'
import type { CrisisAlert } from '@/types'

export interface CrisisConfig {
  keywords: string[]
  notify_counselor: boolean
  default_keywords: string[]
}

export function getAlerts(resolved?: boolean) {
  const params = resolved !== undefined ? { resolved } : {}
  return request.get<CrisisAlert[]>('/crisis/alerts', { params })
}

export function getCrisisConfig() {
  return request.get<CrisisConfig>('/crisis/config')
}

export function updateCrisisConfig(data: { keywords: string[]; notify_counselor: boolean }) {
  return request.put<{ message: string; keywords: string[]; notify_counselor: boolean }>('/crisis/config', data)
}

export function getStudentAlerts(studentId: number) {
  return request.get<CrisisAlert[]>(`/crisis/students/${studentId}/alerts`)
}

export function resolveAlert(id: number, resolved = true) {
  return request.post(`/crisis/${id}/resolve`, { resolved })
}

export function interveneAlert(id: number, data: {
  intervention_type: string
  intervention_note?: string
  follow_up_date?: string
  resolved?: boolean
}) {
  return request.post(`/crisis/${id}/intervene`, data)
}
