import request from '@/utils/request'

export type GuardianScene = 'leave' | 'crisis' | 'academic' | 'care' | 'other'
export type GuardianChannel = 'sms' | 'report' | 'link' | 'note'
export type GuardianContactStatus = 'draft' | 'sent' | 'pending' | 'failed'

export interface Guardian {
  id: number
  student_id: number
  student_name: string
  name: string
  relation: string
  phone_masked: string
  is_primary: boolean
  remark: string | null
  created_at: string
}

export interface ContactLog {
  id: number
  student_id: number
  student_name: string
  guardian_id: number | null
  guardian_name: string
  teacher_id: number
  scene: GuardianScene
  channel: GuardianChannel
  status: GuardianContactStatus
  content_summary: string
  created_at: string
}

export interface ShareLink {
  id: number
  log_id: number
  token: string
  path: string
  expires_at: string
  revoked: boolean
  view_count: number
  last_viewed_at: string | null
}

export interface SharedLogView {
  scene: GuardianScene
  scene_label: string
  content_summary: string
  teacher_name: string
  created_at: string
  expires_at: string
}

export const GUARDIAN_SCENE_LABEL: Record<GuardianScene, string> = {
  leave: '请假告知',
  crisis: '危机干预',
  academic: '学业预警',
  care: '日常关怀',
  other: '其他',
}

export const GUARDIAN_CHANNEL_LABEL: Record<GuardianChannel, string> = {
  sms: '短信提示',
  report: '报告导出',
  link: '只读链接',
  note: '内部留痕',
}

export const GUARDIAN_STATUS_LABEL: Record<GuardianContactStatus, string> = {
  draft: '草稿',
  sent: '已送达',
  pending: '待发送',
  failed: '发送失败',
}

export function getGuardians(studentId: number) {
  return request.get<Guardian[]>('/guardians', { params: { student_id: studentId } })
}

export function createGuardian(data: {
  student_id: number
  name: string
  relation?: string
  phone?: string | null
  is_primary?: boolean
  remark?: string | null
}) {
  return request.post<Guardian>('/guardians', data)
}

export function updateGuardian(id: number, data: Record<string, unknown>) {
  return request.patch<Guardian>(`/guardians/${id}`, data)
}

export function deleteGuardian(id: number) {
  return request.delete(`/guardians/${id}`)
}

export function getContactLogs(studentId?: number) {
  return request.get<ContactLog[]>('/guardians/logs', { params: { student_id: studentId } })
}

export function createContactLog(data: {
  student_id: number
  guardian_id?: number | null
  scene?: GuardianScene
  channel?: GuardianChannel
  content_summary: string
  send_sms?: boolean
}) {
  return request.post<ContactLog>('/guardians/logs', data)
}

export function deleteContactLog(id: number) {
  return request.delete(`/guardians/logs/${id}`)
}

export function createShareLink(logId: number) {
  return request.post<ShareLink>(`/guardians/logs/${logId}/share-link`)
}

export function getLogShareLink(logId: number) {
  return request.get<ShareLink | null>(`/guardians/logs/${logId}/share-link`)
}

export function revokeShareLink(linkId: number) {
  return request.post<ShareLink>(`/guardians/share-links/${linkId}/revoke`)
}

/** 家长只读页（免登录） */
export function viewSharedLog(token: string) {
  return request.get<SharedLogView>(`/guardians/share/${token}`)
}