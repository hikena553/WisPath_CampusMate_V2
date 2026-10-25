import request from '@/utils/request'
import type { CrisisAlert } from '@/types'

export interface CrisisConfig {
  keywords: string[]
  notify_counselor: boolean
  default_keywords: string[]
}

export function getAlerts(resolved?: boolean) {
  const params = resolved !== undefined ? { resolved } : {}
  return request.get<CrisisAlert[]>('/crisis/alerts', { params })
}

export function getCrisisConfig() {
  return request.get<CrisisConfig>('/crisis/config')
}

export function updateCrisisConfig(data: { keywords: string[]; notify_counselor: boolean }) {
  return request.put<{ message: string; keywords: string[]; notify_counselor: boolean }>('/crisis/config', data)
}

export function getStudentAlerts(studentId: number) {
  return request.get<CrisisAlert[]>(`/crisis/students/${studentId}/alerts`)
}

export function resolveAlert(id: number, resolved = true) {
  return request.post(`/crisis/${id}/resolve`, { resolved })
}

export function interveneAlert(id: number, data: {
  intervention_type: string
  intervention_note?: string
  follow_up_date?: string
  resolved?: boolean
}) {
  return request.post(`/crisis/${id}/intervene`, data)
}

/** 待随访列表：随访日期已到期且未闭环的预警 */
export function getFollowUpDue() {
  return request.get<CrisisAlert[]>('/crisis/follow-up-due')
}

/* ============================ 工作台聚合分析 ============================ */

export interface CrisisLevelDist {
  severe: number
  moderate: number
  mild: number
  normal: number
}

export interface CrisisStage {
  found: number
  intervened: number
  following: number
  closed: number
}

export interface CrisisTrendPoint {
  /** MM-DD */
  day: string
  count: number
}

export interface CrisisKeyword {
  word: string
  count: number
}

export interface CrisisSlaItem {
  id: number
  student_name: string
  summary: string
  created_at: string
}

export interface CrisisSla {
  /** 未闭环且创建超 24 小时 */
  overdue: number
  /** 未闭环且创建 12~24 小时 */
  due_soon: number
  items: CrisisSlaItem[]
}

export interface CrisisAnalytics {
  level_dist: CrisisLevelDist
  stage: CrisisStage
  trend: CrisisTrendPoint[]
  keywords: CrisisKeyword[]
  sla: CrisisSla
  total: number
  unresolved: number
  high_risk: number
}

/** 心理预警聚合分析：等级分布 / 处置阶段 / 趋势 / 敏感词 / 处置时限 */
export function getCrisisAnalytics(days = 30, topN = 40) {
  return request.get<CrisisAnalytics>('/crisis/analytics', { params: { days, top_n: topN } })
}
