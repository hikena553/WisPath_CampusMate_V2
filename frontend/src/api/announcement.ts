import request from '@/utils/request'

export interface AnnouncementItem {
  id: number
  teacher_id: number
  teacher_name: string
  title: string
  content: string
  urgency: 'normal' | 'important' | 'urgent'
  attachment_url: string | null
  created_at: string
}

// 教师端
export function getTeacherAnnouncements() {
  return request.get<AnnouncementItem[]>('/teacher/announcements')
}

export function createAnnouncement(formData: FormData) {
  return request.post<AnnouncementItem>('/teacher/announcements', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteAnnouncement(id: number) {
  return request.delete(`/teacher/announcements/${id}`)
}

export interface AnnouncementReachItem {
  announcement_id: number
  title: string
  urgency: 'normal' | 'important' | 'urgent'
  total: number
  read: number
  rate: number
}

export interface AnnouncementReach {
  items: AnnouncementReachItem[]
  total: number
  read: number
  rate: number
}

/** 触达回执：真实已读/应读统计（替代按紧急程度估算的假数据） */
export function getAnnouncementReach() {
  return request.get<AnnouncementReach>('/teacher/announcements/reach')
}

// 学生端
export function getStudentAnnouncements(unreadOnly = false) {
  return request.get<AnnouncementItem[]>('/student/announcements', {
    params: { unread_only: unreadOnly },
  })
}

export function getUnreadCount() {
  return request.get<{ count: number }>('/student/announcements/unread-count')
}

export function markAnnouncementRead(id: number) {
  return request.post(`/student/announcements/${id}/read`)
}
