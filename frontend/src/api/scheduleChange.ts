import request from '@/utils/request'

/** 排课调整申请（调课 / 增课） */
export type ScheduleChangeKind = 'swap' | 'add'
export type ScheduleChangeStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface ScheduleChangeItem {
  id: number
  kind: ScheduleChangeKind
  kind_label: string
  status: ScheduleChangeStatus
  status_label: string

  applicant_id: number
  applicant_name: string

  /** 调课时被调整的课程 id；增课为 null */
  course_id: number | null
  origin_day_of_week: number | null
  origin_start_period: number | null
  origin_end_period: number | null
  origin_location: string | null
  origin_teacher: string | null
  origin_week_start: number | null
  origin_week_end: number | null
  /** 单次调课：被调走的是第几教学周 */
  origin_week_no: number | null

  class_group_id: number
  class_name: string
  course_name: string
  teacher_id: number | null
  teacher_name: string
  location: string
  day_of_week: number
  start_period: number
  end_period: number
  week_start: number
  week_end: number
  semester: string
  credit: number | null

  reason: string
  approver_name: string
  reject_reason: string
  reviewed_at: string
  applied_course_id: number | null

  created_at: string
  updated_at: string
  /** 服务端评估的冲突提示（仅待审时有意义） */
  conflicts: string[]
}

export interface ScheduleChangeCreatePayload {
  kind: ScheduleChangeKind
  course_id?: number | null
  class_group_id?: number | null
  course_name?: string | null
  teacher_id?: number | null
  location?: string
  day_of_week: number
  start_period: number
  end_period: number
  week_start?: number
  week_end?: number
  /** 单次调课：origin_week_no = 挪走哪一周，target_week = 补到哪一周 */
  origin_week_no?: number | null
  target_week?: number | null
  semester?: string | null
  credit?: number | null
  reason?: string
}

/** 教师：我提交的申请 */
export function getMyScheduleChanges(params?: { status?: string }) {
  return request.get<ScheduleChangeItem[]>('/schedule-change/my', { params })
}

/** 教师：发起调课 / 增课申请 */
export function createScheduleChange(payload: ScheduleChangeCreatePayload) {
  return request.post<ScheduleChangeItem>('/schedule-change/create', payload)
}

/** 教师：撤回待审批的申请 */
export function cancelScheduleChange(id: number) {
  return request.delete(`/schedule-change/${id}`)
}

/** 审批队列（管理员看全部；教师看自己提交的待审） */
export function getPendingScheduleChanges(params?: { kind?: string; semester?: string }) {
  return request.get<ScheduleChangeItem[]>('/schedule-change/pending', { params })
}

/** 台账（管理员看全部；教师看自己的） */
export function getAllScheduleChanges(params?: { status?: string; kind?: string; semester?: string }) {
  return request.get<ScheduleChangeItem[]>('/schedule-change/all', { params })
}

/** 管理员：审批 */
export function reviewScheduleChange(id: number, action: 'approve' | 'reject', reject_reason?: string) {
  return request.post<{ message: string; course_id?: number; note?: string }>(
    `/schedule-change/${id}/review`,
    { action, reject_reason },
  )
}

export const SCHEDULE_CHANGE_KIND_LABEL: Record<string, string> = {
  swap: '调课',
  add: '增课',
}

export const SCHEDULE_CHANGE_STATUS_LABEL: Record<string, string> = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
  cancelled: '已撤回',
}

export const WEEKDAY_LABELS = ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日']

export function scheduleWhen(d: {
  day_of_week: number
  start_period: number
  end_period: number
  location?: string | null
}) {
  const day = WEEKDAY_LABELS[d.day_of_week] || `周${d.day_of_week}`
  const when = `${day} 第${d.start_period}-${d.end_period}节`
  return d.location ? `${when} · ${d.location}` : when
}
