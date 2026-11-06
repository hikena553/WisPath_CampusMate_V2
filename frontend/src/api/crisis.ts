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

/* ============================ 处置态势智能分析 ============================ */

export interface CrisisInsight {
  /** 一段态势研判（60~100 字） */
  summary: string
  /** 今日可执行的处置建议（2~3 条） */
  advice: string[]
  /** ai：模型生成；rule：模型不可用时的指标规则兜底 */
  source: 'ai' | 'rule'
  /** ISO 时间 */
  generated_at: string
}

/** 基于聚合指标生成态势研判与处置建议；后端保证始终返回结论 */
export function getCrisisInsight(days = 30) {
  return request.get<CrisisInsight>('/crisis/analytics/insight', { params: { days } })
}

/* ============================ AI 处置建议 ============================ */

export interface CrisisAdvice {
  /** 推荐处置路径：谈话 / 转介心理咨询 / 约谈家长 / 建议休养观察 */
  scheme: string
  /** 具体动作步骤（2~4 步） */
  steps: string[]
  /** 推荐理由（只引用事实清单） */
  rationale: string
  /** 沟通禁忌（2~3 条） */
  taboo: string[]
  /** ai：模型生成；rule：规则兜底 */
  source: 'ai' | 'rule'
  generated_at: string
}

/** 单条预警的 AI 处置建议（severe 强制附 24h 面谈） */
export function getAlertAdvice(id: number) {
  return request.get<CrisisAdvice>(`/crisis/${id}/advice`)
}

/* ============================ 干预档案导出 ============================ */

export interface CrisisExportParams {
  start?: string
  end?: string
  level?: string
  intervention_type?: string
  resolved?: boolean
}

/** 按学生导出干预档案 Excel（时间/等级/干预类型/闭环状态可筛选，脱敏序列化） */
export function exportStudentCrisisArchive(studentId: number, params: CrisisExportParams = {}) {
  return request.download(`/crisis/students/${studentId}/export`, { params })
}
