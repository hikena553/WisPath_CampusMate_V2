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
}

export function getTeacherSchedules(year: number, month: number) {
  return request.get<ScheduleItem[]>('/teacher/schedules', {
    params: { year, month },
  })
}

export function createTeacherSchedule(date: string, content: string) {
  return request.post<ScheduleItem>('/teacher/schedules', { date, content })
}

export function deleteTeacherSchedule(id: number) {
  return request.delete(`/teacher/schedules/${id}`)
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
