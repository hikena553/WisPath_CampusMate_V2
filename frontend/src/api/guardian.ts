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

export interface ContactLogQuery {
  student_id?: number
  keyword?: string
  scene?: GuardianScene
  channel?: GuardianChannel
  status?: GuardianContactStatus
  start?: string
  end?: string
  page?: number
  page_size?: number
}

export interface ContactLogPage {
  items: ContactLog[]
  total: number
}

/** 台账分页查询（服务端筛选 + 分页，供页面台账区使用） */
export function getContactLogsPaged(params: ContactLogQuery) {
  return request.get<ContactLogPage>('/guardians/logs/page', { params })
}

export interface GuardianOverviewCountItem {
  key: string
  label: string
  count: number
}

export interface GuardianOverview {
  totals: { students: number; contacts: number; logs: number; sms: number }
  by_scene: GuardianOverviewCountItem[]
  by_channel: GuardianOverviewCountItem[]
  trend: Array<{ day: string; count: number }>
  top_students: Array<{ student_id: number; student_name: string; count: number }>
}

/** 家校沟通聚合（概览图表数据源，与台账筛选同口径） */
export function getGuardianOverview(params: { days?: number; student_id?: number } = {}) {
  return request.get<GuardianOverview>('/guardians/overview', { params })
}

/** 导出台账（xlsx blob） */
export function exportContactLogs(params: ContactLogQuery = {}) {
  return request.get<Blob>('/guardians/logs/export', { params, responseType: 'blob' })
}

/** 下载导入模板 */
export function downloadContactLogTemplate() {
  return request.get<Blob>('/guardians/logs/import-template', { responseType: 'blob' })
}

export interface ContactLogImportResult {
  created: number
  skipped: string[]
  errors: string[]
}

/** 导入台账（xlsx） */
export function importContactLogs(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return request.post<ContactLogImportResult>('/guardians/logs/import', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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