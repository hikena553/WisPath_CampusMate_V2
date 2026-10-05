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

/** 销假确认：审批通过的请假，学生返校后由教师确认闭环 */
export function confirmLeaveReturn(id: number) {
  return request.post<{ message: string; return_confirmed: boolean }>(
    `/leave/${id}/confirm-return`
  )
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
  /** 已通过但尚未销假确认的数量 */
  awaiting_return: number
  by_type: LeaveStatsItem[]
  by_class: LeaveStatsItem[]
}

export function getLeaveStats() {
  return request.get<LeaveStats>('/leave/stats')
}
