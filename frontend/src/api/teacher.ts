import request from '@/utils/request'

export interface StudentSummary {
  id: number
  name: string
  college: string | null
  username: string
  avatar: string | null
  skills_json: { skills: { name: string; context: string }[]; interests: string[] } | null
  growth_count: number
  leave_count: number
  crisis_level: string | null
  latest_crisis_summary: string | null
  latest_crisis_time: string | null
  score: number
}

export interface StudentProject {
  id: number
  project_name: string
  start_date: string
  end_date: string | null
  is_team: boolean
  team_members: string | null
  attachment_url: string | null
}

export interface StudentDetail {
  id: number
  name: string
  college: string | null
  username: string
  avatar: string | null
  skills_json: any
  growth_records: any[]
  projects: StudentProject[]
  crisis_alerts: any[]
  leave_requests: any[]
}

export function getStudents(search?: string) {
  const params = search ? { search } : {}
  return request.get<StudentSummary[]>('/teacher/students', { params })
}

export function getStudentDetail(id: number) {
  return request.get<StudentDetail>(`/teacher/students/${id}`)
}

export interface StudentImportResult {
  created: number
  skipped: string[]
}

export interface StudentImportItem {
  username: string
  name: string
  college?: string
  gender?: string
  class_name?: string
}

export function importStudents(students: StudentImportItem[]) {
  return request.post<StudentImportResult>('/teacher/students/import', { students })
}

export interface DashboardStats {
  total_students: number
  alert_count: number
  pending_leave_count: number
  severe_alert_count: number
  resolved_alert_count: number
}

export function getDashboardStats() {
  return request.get<DashboardStats>('/teacher/dashboard')
}

export interface GrowthStats {
  honor: number
  competition: number
  practice: number
  paper: number
  achievement: number
}

export function getTeacherGrowthStats() {
  return request.get<GrowthStats>('/teacher/growth-stats')
}

export interface ClassEvaluation {
  total_students: number
  avg_gpa: number
  avg_score: number
  growth: Record<string, number>
  crisis: Record<string, number>
  pending_leaves: number
}

export function getClassEvaluation() {
  return request.get<ClassEvaluation>('/teacher/class-evaluation')
}

export interface ScheduleItem {
  id: number
  date: string
  content: string
  urgency: string
  completed: boolean
  completed_at: string | null
}

export type ScheduleUrgency = 'normal' | 'important' | 'urgent'

export function getTeacherSchedules(year: number, month: number) {
  return request.get<ScheduleItem[]>('/teacher/schedules', {
    params: { year, month },
  })
}

/** 逾期未完成任务提醒（已过期且未完成） */
export function getOverdueSchedules() {
  return request.get<ScheduleItem[]>('/teacher/schedules/overdue')
}

export function createTeacherSchedule(date: string, content: string, urgency: ScheduleUrgency = 'normal') {
  return request.post<ScheduleItem>('/teacher/schedules', { date, content, urgency })
}

/** 标记任务完成 / 取消完成 */
export function updateTeacherSchedule(id: number, completed: boolean) {
  return request.patch<ScheduleItem>(`/teacher/schedules/${id}`, { completed })
}

export function deleteTeacherSchedule(id: number) {
  return request.delete(`/teacher/schedules/${id}`)
}

export interface ClassStats {
  total_students: number
  gender_stats: Record<string, number>
  crisis_stats: Record<string, number>
  grade_stats: Record<string, number>
  political_stats: Record<string, number>
  hometown_stats: Record<string, number>
  crisis_trend: { month: string; count: number }[]
}

export function getClassStats() {
  return request.get<ClassStats>('/teacher/class-stats')
}

export interface ContactSuggestion {
  student_id: number
  student_name: string
  reason: string
  priority: 'high' | 'medium' | 'low'
}

export function suggestContacts() {
  return request.get<ContactSuggestion[]>('/teacher/suggest-contacts')
}
