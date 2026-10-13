import request from '@/utils/request'

export type HelpCategory = 'academic' | 'life' | 'mental' | 'relation' | 'other'
export type HelpStatus = 'pending' | 'processing' | 'resolved'

export interface HelpRequest {
  id: number
  student_id: number
  student_name: string
  anonymous: boolean
  category: HelpCategory
  content: string
  status: HelpStatus
  teacher_id: number | null
  teacher_name: string
  reply: string | null
  replied_at: string
  created_at: string
}

export interface HelpRequestOverview {
  pending: number
  processing: number
  resolved: number
  total: number
}

export const HELP_CATEGORY_LABEL: Record<HelpCategory, string> = {
  academic: '学业困扰',
  life: '生活困难',
  mental: '心理情绪',
  relation: '人际关系',
  other: '其他',
}

export const HELP_STATUS_LABEL: Record<HelpStatus, string> = {
  pending: '待受理',
  processing: '帮扶中',
  resolved: '已帮助',
}

/** 学生：提交求助（可匿名） */
export function createHelpRequest(data: { category?: HelpCategory; content: string; anonymous?: boolean }) {
  return request.post<HelpRequest>('/help-requests', data)
}

/** 学生：查看自己的求助与回复 */
export function fetchMyHelpRequests() {
  return request.get<HelpRequest[]>('/help-requests/mine')
}

/** 辅导员：求助受理概览 */
export function fetchHelpOverview() {
  return request.get<HelpRequestOverview>('/help-requests/overview')
}

/** 辅导员：查看名下学生的求助（可按状态过滤） */
export function fetchHelpRequests(status?: HelpStatus) {
  return request.get<HelpRequest[]>('/help-requests', { params: { status } })
}

/** 辅导员：受理并回复求助 */
export function replyHelpRequest(id: number, data: { reply: string; status?: HelpStatus }) {
  return request.put<HelpRequest>(`/help-requests/${id}/reply`, data)
}