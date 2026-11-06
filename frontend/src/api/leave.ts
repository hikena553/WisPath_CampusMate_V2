import request from '@/utils/request'
import type { LeaveRequestOut, LeaveRequestCreate } from '@/types'

export function getMyLeaves() {
  return request.get<LeaveRequestOut[]>('/leave/my')
}

export function createLeave(data: LeaveRequestCreate) {
  return request.post<LeaveRequestOut>('/leave/create', data)
}

export function deleteLeave(id: number) {
  return request.delete(`/leave/${id}`)
}

export function getPendingLeaves(studentId?: number) {
  return request.get<LeaveRequestOut[]>('/leave/pending', { params: { student_id: studentId } })
}

export function reviewLeave(id: number, action: 'approve' | 'reject', reject_reason?: string) {
  return request.post(`/leave/${id}/review`, { action, reject_reason })
}

export function getAllLeaves(status?: string, studentId?: number) {
  const params: Record<string, unknown> = {}
  if (status) params.status = status
  if (studentId != null) params.student_id = studentId
  return request.get<LeaveRequestOut[]>('/leave/all', { params })
}

export function analyzeLeave(id: number) {
  return request.get<{ suggestion: string; reason: string }>(`/leave/${id}/analyze`)
}

export interface LeaveStatsItem {
  key: string
  label: string
  total: number
  approved: number
  rejected: number
  pending: number
}

export interface LeaveStats {
  total: number
  approved: number
  rejected: number
  pending: number
  by_type: LeaveStatsItem[]
  by_class: LeaveStatsItem[]
}

export function getLeaveStats() {
  return request.get<LeaveStats>('/leave/stats')
}
