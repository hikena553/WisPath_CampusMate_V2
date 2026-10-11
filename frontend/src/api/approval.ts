import request from '@/utils/request'

export interface ApprovalItem {
  kind: 'leave' | 'ticket' | 'material'
  id: number
  title: string
  applicant_id: number
  applicant_name: string
  status: string
  created_at: string
  detail?: string
}

export interface ApprovalByKind {
  label: string
  count: number
  pending: number
}

export interface ApprovalStats {
  total: number
  pending: number
  approved: number
  rejected: number
  by_kind: Record<string, ApprovalByKind>
  trend: Array<{ day: string; count: number }>
}

// 教师/管理员：聚合待审（按 kind/status/student_id 过滤）
export function getApprovalPending(params?: { status?: string; kind?: string; student_id?: number }) {
  return request.get<ApprovalItem[]>('/approval/pending', { params })
}

// 统一审核
export function reviewApproval(kind: string, id: number, action: 'approve' | 'reject', reject_reason?: string) {
  return request.post(`/approval/${kind}/${id}/review`, { action, reject_reason })
}

// 数据统计
export function getApprovalStats(days = 30, studentId?: number) {
  const params: Record<string, unknown> = { days }
  if (studentId != null) params.student_id = studentId
  return request.get<ApprovalStats>('/approval/stats', { params })
}

export const APPROVAL_KIND_LABEL: Record<string, string> = {
  leave: '请假申请',
  ticket: '办事工单',
  material: '材料档案',
}