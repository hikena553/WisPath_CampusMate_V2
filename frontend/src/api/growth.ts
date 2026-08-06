import request from '@/utils/request'
import type { GrowthRecord } from '@/types'

export interface GrowthProfile {
  total_score: number
  radar: { name: string; value: number }[]
  stats_by_type: { name: string; value: number }[]
  monthly_trend: { month: string; count: number; type: string }[]
  skills: string[]
  interests: string[]
  total_records: number
  total_skills: number
  gpa_trend: { semester: string; gpa: number }[]
}

export function getGrowthProfile() {
  return request.get<GrowthProfile>('/growth/profile')
}

export function getGrowthRecords(studentId?: number) {
  return request.get<GrowthRecord[]>('/growth/records', { params: { student_id: studentId } })
}

export function createGrowthRecord(data: Partial<GrowthRecord>) {
  return request.post<GrowthRecord>('/growth/records', data)
}

export function deleteGrowthRecord(id: number) {
  return request.delete(`/growth/records/${id}`)
}

// ---- Project Showcase ----
export interface StudentProject {
  id: number
  student_id: number
  project_name: string
  start_date: string
  end_date: string | null
  is_team: boolean
  team_members: string | null
  attachment_url: string | null
}

export function getProjects() {
  return request.get<StudentProject[]>('/growth/projects')
}

export function createProject(data: Partial<StudentProject>) {
  return request.post<StudentProject>('/growth/projects', data)
}

export function updateProject(id: number, data: Partial<StudentProject>) {
  return request.put<StudentProject>(`/growth/projects/${id}`, data)
}

export function deleteProject(id: number) {
  return request.delete(`/growth/projects/${id}`)
}

export function updateSkills(data: { skills: string[]; interests: string[] }) {
  return request.put('/growth/skills', data)
}
