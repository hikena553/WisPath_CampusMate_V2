import request from '@/utils/request'

/** 待办任务来源：AI 建议 / 随访 / 审批 / 关怀计划 / 预警 / 手动 / 管理员下发 */
export type TaskSourceType =
  | 'ai_suggest'
  | 'follow_up'
  | 'approval'
  | 'care_plan'
  | 'alert'
  | 'manual'
  | 'admin'

/** 任务状态：待处理 / 已联系 / 已关怀 / 已办结 / 已过期 */
export type TaskStatus = 'pending' | 'contacted' | 'cared' | 'done' | 'expired'

/** 任务优先级：高 / 中 / 低（教师可显式调整） */
export type TaskPriority = 'high' | 'mid' | 'low'

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
  /** 优先级：驱动清单分组与左侧色条（旧数据可能缺省，按中优先级兜底） */
  priority?: TaskPriority
  /** 提醒日：与截止日分离，用于「今天提醒我处理」 */
  remind_at?: string | null
  /** 今日是否应提醒（后端按 remind_at/due_at 判定） */
  remind_due?: boolean
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
  /** 未办结的高优先级任务数 */
  high?: number
  /** 今日应提醒的任务数 */
  remind_today?: number
}

export interface TeacherTaskCreate {
  title: string
  detail?: string
  student_id?: number
  priority?: TaskPriority
  remind_at?: string
  due_at?: string
  source_type?: TaskSourceType
  source_id?: number
}

export interface TeacherTaskQuery {
  status?: TaskStatus
  source_type?: TaskSourceType
  priority?: TaskPriority
  /** overdue 逾期 / today 今日到期 / remind 今日提醒 */
  due?: 'overdue' | 'today' | 'remind'
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
  data: {
    status?: TaskStatus
    title?: string
    detail?: string | null
    student_id?: number | null
    priority?: TaskPriority
    remind_at?: string | null
    due_at?: string | null
  }
) {
  return request.patch<TeacherTask>(`/teacher-tasks/${id}`, data)
}

/** 删除任务（仅本人名下任务） */
export function deleteTeacherTask(id: number) {
  return request.delete(`/teacher-tasks/${id}`)
}

/** 任务状态中文标签 */
export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: '待处理',
  contacted: '已联系',
  cared: '已关怀',
  done: '已办结',
  expired: '已过期',
}

/** 任务优先级中文标签 */
export const TASK_PRIORITY_LABEL: Record<TaskPriority, string> = {
  high: '高优先级',
  mid: '中优先级',
  low: '低优先级',
}

/** 任务来源中文标签 */
export const TASK_SOURCE_LABEL: Record<TaskSourceType, string> = {
  ai_suggest: 'AI 建议',
  follow_up: '随访提醒',
  approval: '审批待办',
  care_plan: '关怀计划',
  alert: '预警',
  manual: '手动',
  admin: '管理员下发',
}

export interface TaskAutoGenItem {
  student_id: number | null
  student_name: string
  rule: string
}

export interface TaskAutoGenResult {
  created: number
  date: string
  breakdown: { rule?: number; crisis?: number; suggest?: number } | Record<string, number>
  items: TaskAutoGenItem[]
}

/** 智能生成：评估名下学生的待干预信号（学情规则 / 未闭环心理预警），自动建为带日期的任务 */
export function autoGenerateTeacherTasks() {
  return request.post<TaskAutoGenResult>('/teacher-tasks/auto-generate')
}

/** 预警 pipeline 规则中文标签（learning_alert 生成的任务带 rule_code） */
export const TASK_RULE_LABEL: Record<string, string> = {
  leave_frequent: '频繁请假',
  low_activity: '近期学情沉默',
  crisis_open: '未闭环心理预警',
}

export function taskRuleLabel(ruleCode?: string | null): string {
  if (!ruleCode) return ''
  return TASK_RULE_LABEL[ruleCode] || ruleCode
}
