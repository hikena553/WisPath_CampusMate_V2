import request from '@/utils/request'

export interface Feedback {
  id: number
  user_id: number
  user_name?: string
  type: string
  title: string
  content: string
  contact?: string
  status: string
  reply?: string
  replied_by?: number
  replier_name?: string
  replied_at?: string
  created_at: string
}

export interface FeedbackCreate {
  type?: string
  title: string
  content: string
  contact?: string
}

export interface FeedbackReply {
  reply: string
  status?: string
}

// 提交反馈
export function createFeedback(data: FeedbackCreate) {
  return request.post<Feedback>('/feedbacks', data)
}

// 获取反馈列表
export function getFeedbacks(params?: {
  status?: string
  type?: string
  page?: number
  page_size?: number
}) {
  return request.get<Feedback[]>('/feedbacks', { params })
}

// 获取反馈详情
export function getFeedback(id: number) {
  return request.get<Feedback>(`/feedbacks/${id}`)
}

// 回复反馈（管理员）
export function replyFeedback(id: number, data: FeedbackReply) {
  return request.put<Feedback>(`/feedbacks/${id}/reply`, data)
}
