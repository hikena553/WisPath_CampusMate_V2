import request from '@/utils/request'

/** 日报段落：昨日复盘 / 今日梳理 / 学生成长关注 / 明日规划 */
export type TeacherReportSectionKey = 'review' | 'today' | 'student' | 'plan'

export interface TeacherReportWeather {
  city: string
  temp: number
  feels: number
  desc: string
  emoji: string
  high: number
  low: number
  rain: number
}

export interface TeacherReportFortune {
  level: string
  score: number
  keyword: string
  summary: string
  lucky_color: string
  lucky_time: string
}

export interface TeacherReportSection {
  key: TeacherReportSectionKey
  title: string
  /** 支持 ==重点== 黄标、__留意__ 虚线下划线，由 RichMarkText 渲染 */
  items: string[]
}

/** 今日梳理里的可操作条目：预警 / 请假走跳转，低风险任务可一键完成 */
export interface TeacherReportAction {
  id: string
  kind: 'task' | 'alert' | 'leave'
  group: 'alert' | 'leave' | 'overdue' | 'due'
  label: string
  title: string
  student_id: number | null
  student_name: string
  priority: 'high' | 'mid' | 'low'
  source_label: string
  /** 服务端判定为低风险（非高优先级、未逾期、非预警/审批来源）才为 true */
  can_complete: boolean
  link: string
  action_text?: string
  task_id?: number
}

/** AI 建议：可一键加入今日任务 */
export interface TeacherReportSuggestion {
  priority: 'high' | 'mid' | 'low'
  when?: string
  title: string
  content: string
  student_id?: number | null
  student_name?: string
  task_title: string
}

export interface TeacherReportSummary {
  open: number
  due_today: number
  overdue: number
  high: number
  done_yesterday: number
  alert_total: number
  severe_total: number
  leave_total: number
  student_total: number
}

export interface TeacherDailyReport {
  date: string
  weekday: string
  date_text: string
  greeting: string
  weather: TeacherReportWeather | null
  fortune: TeacherReportFortune
  sections: TeacherReportSection[]
  actions: TeacherReportAction[]
  suggestions: TeacherReportSuggestion[]
  summary: TeacherReportSummary
  generated_at: string
}

/**
 * 教师 AI 日报。
 * @param refresh 传 true 时服务端仍受 10 分钟缓存约束，前端用 locale 时间戳做「换一批」的抖动
 */
export function getTeacherDailyReport() {
  return request.get<TeacherDailyReport>('/agent/teacher-daily-report')
}
