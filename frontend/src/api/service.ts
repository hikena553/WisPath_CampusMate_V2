import request from '@/utils/request'
import type { ServiceTicket } from '@/types'

export function getTickets(params?: {
  status?: string
  /** 审批视角：queue=共享待办队列（默认）/ mine=我受理的 */
  scope?: 'queue' | 'mine'
  student_id?: number
}) {
  return request.get<ServiceTicket[]>('/service/tickets', { params })
}

/** 受理（认领）工单：待受理 → 处理中，责任人落到受理人名下 */
export function claimTicket(id: number) {
  return request.put<ServiceTicket>(`/service/tickets/${id}/claim`)
}

export function createTicket(data: {
  type: string; title: string; content?: string
  applicant_name?: string; applicant_no?: string; applicant_college?: string
  form_data?: Record<string, any>; attachments?: string[]
}) {
  return request.post<ServiceTicket>('/service/tickets', data)
}

export function approveTicket(id: number, action: string, comment?: string) {
  return request.put(`/service/tickets/${id}/approve`, {
    action,
    ...(comment !== undefined && comment !== '' ? { comment } : {}),
  })
}

export function cancelTicket(id: number) {
  return request.put(`/service/tickets/${id}/cancel`)
}