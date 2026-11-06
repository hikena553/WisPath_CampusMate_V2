import request from '@/utils/request'

export interface AnnouncementItem {
  id: number
  teacher_id: number
  teacher_name: string
  title: string
  content: string
  urgency: 'normal' | 'important' | 'urgent'
  attachment_url: string | null
  /** 发布目标班级；null 表示发给名下全体学生 */
  class_group_id: number | null
  /** 后端冗余回传的班级名，null/空串表示「全体学生」 */
  class_name: string
  created_at: string
}

/** 教师可选的可发布班级（来自名下学生实际所属班级） */
export interface TeacherClassOption {
  id: number
  name: string
  student_count: number
}

// 教师端
export function getTeacherAnnouncements() {
  return request.get<AnnouncementItem[]>('/teacher/announcements')
}

/** 发布公告时可选的班级列表，只含该教师名下有学生的班级 */
export function getAnnouncementClasses() {
  return request.get<TeacherClassOption[]>('/teacher/announcement-classes')
}

export function createAnnouncement(formData: FormData) {
  // 不要手写 Content-Type: multipart/form-data —— 那样会丢掉 boundary，
  // 后端无法解析表单体。交给 axios/浏览器按 FormData 自动生成带 boundary 的头。
  return request.post<AnnouncementItem>('/teacher/announcements', formData)
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

/** 对最近公告中仍未读的学生补发站内提醒 */
export function remindAnnouncementUnread() {
  return request.post<{ ok: boolean; reminded: number }>('/teacher/announcements/remind')
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
