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

export function getPendingLeaves() {
  return request.get<LeaveRequestOut[]>('/leave/pending')
}

export function reviewLeave(id: number, action: 'approve' | 'reject', reject_reason?: string) {
  return request.post(`/leave/${id}/review`, { action, reject_reason })
}

export function getAllLeaves(status?: string) {
  const params = status ? { status } : {}
  return request.get<LeaveRequestOut[]>('/leave/all', { params })
}

export function analyzeLeave(id: number) {
  return request.get<{ suggestion: string; reason: string }>(`/leave/${id}/analyze`)
}
