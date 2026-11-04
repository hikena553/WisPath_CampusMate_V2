import request from '@/utils/request'

/**
 * 教师个人成长 API（后端 app/api/teacher_me.py → teacher_growth_service.build_my_growth）
 *
 * 类型严格对齐服务端实际返回结构（teacher / level / badges / duty / timeline / impact / teaching / radar）。
 */

export interface GrowthTeacher {
  id: number
  name: string
  avatar: string | null
  college: string | null
  title: string | null
  signature: string | null
  department: string | null
}

/** 等级：教师端用「辅导员」语言阶梯，不是学生端的「新芽/繁花」 */
export interface GrowthLevel {
  /** 等级序号 1..6 */
  level: number
  name: string
  desc: string
  points: number
  /** 下一级所需分数，已满级为 null */
  next_points: number | null
  /** 距下一级进度百分比 0-100 */
  progress: number
}

export interface GrowthBadge {
  code: string
  name: string
  desc: string
  icon: string
  tier: 'bronze' | 'silver' | 'gold' | 'diamond' | string
  category: string
  earned: boolean
  awarded_at: string | null
  /** 未获得时的进度 0-100 */
  progress: number
  target_label: string
}

export interface GrowthBadges {
  earned: GrowthBadge[]
  locked: GrowthBadge[]
  earned_count: number
  total_count: number
}

/** 单项履职指标（本月 vs 上月） */
export interface DutyMetric {
  key: 'care' | 'visit' | 'guardian' | 'praise' | string
  label: string
  icon: string
  unit: string
  value: number
  previous: number
  /** 环比变化率（%），上期为 0 时为 null */
  trend: number | null
  hint: string
}

export interface DutyTasks {
  total: number
  done: number
  open: number
  overdue: number
  done_rate: number
}

export interface DutyTeaching {
  courses: number
  sessions_month: number
  homeworks: number
  graded: number
}

export interface DutyProfile {
  student_total: number
  cared_students_month: number
  coverage_rate: number
  metrics: DutyMetric[]
  tasks: DutyTasks
  /** 已排期但未留痕的家访数 */
  pending_visits: number
  teaching: DutyTeaching
  period: { care_month: string; care_previous: string }
}

export interface GrowthTimelineItem {
  kind: 'badge' | 'portfolio' | 'care' | 'other' | string
  type: string
  title: string
  desc: string | null
  date: string
  icon: string
}

export interface ImpactPoint {
  /** 周起始日 */
  week: string
  value: number
}

export interface ImpactCurve {
  points: ImpactPoint[]
  total: number
  avg: number
  /** 影响力最高的一周（周起始日） */
  best_week: string
}

export interface TeachingScale {
  course_count: number
  class_count: number
  student_count: number
  /** 既教又带的学生（育人 ∩ 教学） */
  overlap_count: number
  attendance_sessions: number
  absent_total: number
  homework_count: number
}

/** 九项职业能力中的一项 */
export interface CapabilityItem {
  key: string
  name: string
  icon: string
  desc: string
  score: number
  behaviour_score: number
  /** 学生互评折算分，无样本为 null */
  peer_score: number | null
  has_peer: boolean
}

export interface CapabilityRadar {
  items: CapabilityItem[]
  avg: number
  /** [能力名, 分数] 形式的最强/最弱项 */
  top: [string, number] | null
  weak: [string, number] | null
  /** 参与互评的能力项数量 */
  peer_coverage: number
}

export interface TeacherGrowth {
  teacher: GrowthTeacher
  level: GrowthLevel
  badges: GrowthBadges
  duty: DutyProfile
  timeline: GrowthTimelineItem[]
  impact: ImpactCurve
  teaching: TeachingScale
  radar: CapabilityRadar
  generated_at: string
}

export function getMyGrowth() {
  return request.get<TeacherGrowth>('/teacher/me/growth')
}

/** 只取能力雷达（轻量场景用） */
export function getMyCapabilities() {
  return request.get<CapabilityRadar>('/teacher/me/capabilities')
}
