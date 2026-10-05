import request from '@/utils/request'

/** 待办任务来源：AI 建议 / 随访 / 审批 / 关怀计划 / 预警 / 手动 */
export type TaskSourceType =
  | 'ai_suggest'
  | 'follow_up'
  | 'approval'
  | 'care_plan'
  | 'alert'
  | 'manual'

/** 任务状态：待处理 / 已联系 / 已关怀 / 已办结 / 已过期 */
export type TaskStatus = 'pending' | 'contacted' | 'cared' | 'done' | 'expired'

export interface TeacherTask {
  id: number
  teacher_id: number
  source_type: TaskSourceType
  source_id: number | null
  student_id: number | null
  student_name: string
  title: string
  detail: string | null
  /** 来源规则编码（学习预警 pipeline 生成的任务带该字段） */
  rule_code?: string | null
  status: TaskStatus
  due_at: string | null
  overdue: boolean
  done_at: string | null
  created_at: string
}

export interface TeacherTaskSummary {
  pending: number
  overdue: number
  today: number
  done_this_week: number
  total: number
}

export interface TeacherTaskCreate {
  title: string
  detail?: string
  student_id?: number
  due_at?: string
  source_type?: TaskSourceType
  source_id?: number
}

export interface TeacherTaskQuery {
  status?: TaskStatus
  source_type?: TaskSourceType
  /** overdue 逾期 / today 今日到期 */
  due?: 'overdue' | 'today'
  limit?: number
  offset?: number
}

export function getTeacherTaskSummary() {
  return request.get<TeacherTaskSummary>('/teacher-tasks/summary')
}

export function getTeacherTasks(params?: TeacherTaskQuery) {
  return request.get<TeacherTask[]>('/teacher-tasks', { params })
}

export function createTeacherTask(data: TeacherTaskCreate) {
  return request.post<TeacherTask>('/teacher-tasks', data)
}

export function updateTeacherTask(
  id: number,
  data: { status?: TaskStatus; title?: string; detail?: string; due_at?: string }
) {
  return request.patch<TeacherTask>(`/teacher-tasks/${id}`, data)
}

/** 任务状态中文标签 */
export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: '待处理',
  contacted: '已联系',
  cared: '已关怀',
  done: '已办结',
  expired: '已过期',
}

/** 任务来源中文标签 */
export const TASK_SOURCE_LABEL: Record<TaskSourceType, string> = {
  ai_suggest: 'AI 建议',
  follow_up: '随访提醒',
  approval: '审批待办',
  care_plan: '关怀计划',
  alert: '预警',
  manual: '手动',
}

/** 预警 pipeline 规则中文标签（learning_alert 生成的任务带 rule_code） */
export const TASK_RULE_LABEL: Record<string, string> = {
  leave_frequent: '频繁请假',
  low_activity: '近期学情沉默',
}

export function taskRuleLabel(ruleCode?: string | null): string {
  if (!ruleCode) return ''
  return TASK_RULE_LABEL[ruleCode] || ruleCode
}
