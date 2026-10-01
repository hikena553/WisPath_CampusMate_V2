import request from '@/utils/request'
import type { Course, Grade, Exam } from '@/types'

export function getCourses(params?: { semester?: string }) {
  return request.get<Course[]>('/academic/courses', { params })
}
export function getGrades() { return request.get<Grade[]>('/academic/grades') }
export function getExams() { return request.get<Exam[]>('/academic/exams') }

// ─── 管理员课程管理 ─────────────────────────────────────
export function adminGetCourses(params?: { class_group_id?: number; semester?: string; college_id?: number; major_id?: number }) {
  return request.get<Course[]>('/admin/courses', { params })
}
export function adminCreateCourse(data: any) {
  return request.post<Course>('/admin/courses', data)
}
export function adminUpdateCourse(id: number, data: any) {
  return request.put<Course>(`/admin/courses/${id}`, data)
}
export function adminDeleteCourse(id: number) {
  return request.delete(`/admin/courses/${id}`)
}
export function adminBatchDeleteCourses(ids: number[]) {
  return request.delete('/admin/courses/batch', { data: { ids } })
}

export function adminGetSemesters() {
  return request.get<{ value: string; label: string }[]>('/admin/semesters')
}

// ─── 学期管理 ───────────────────────────────────────────
export interface ManagedSemester {
  id: number | null
  value: string
  label: string
  managed: boolean
  course_count: number
}
export function adminGetManagedSemesters() {
  return request.get<ManagedSemester[]>('/admin/semesters/managed')
}
export function adminCreateSemester(data: { year: string; term: number; label?: string }) {
  return request.post<ManagedSemester>('/admin/semesters', data)
}
export function adminUpdateSemester(id: number, data: { label: string }) {
  return request.put<ManagedSemester>(`/admin/semesters/${id}`, data)
}
export function adminDeleteSemester(id: number) {
  return request.delete<{ ok: boolean }>(`/admin/semesters/${id}`)
}

// ─── 课程表总览统计 ─────────────────────────────────────
export interface ScheduleSummaryItem {
  class_group_id: number
  class_name: string
  grade: number
  student_count: number | null
  major_name: string | null
  college_name: string | null
  course_count: number
  filled_slots: number
  total_slots: number
}
export interface ScheduleSummary {
  semesters: { value: string; label: string; schedule_count: number; course_count: number }[]
  schedules: ScheduleSummaryItem[]
  total_courses: number
}
export function adminGetCoursesSummary(params?: { semester?: string; college_id?: number; major_id?: number }) {
  return request.get<ScheduleSummary>('/admin/courses/summary', { params })
}

export function adminImportCourses(formData: FormData) {
  return request.post('/admin/courses/import', formData)
}

// ─── 喜鹊儿（青果教务）课表同步 ─────────────────────────
export interface XiqueConfig {
  configured: boolean
  root_url: string
  username: string
  password_set: boolean
  school_year: number
  term: number
  semester: string
  hint: string
}
export function adminGetXiqueConfig() {
  return request.get<XiqueConfig>('/admin/courses/xique/config')
}
export function adminSaveXiqueConfig(data: { root_url: string; username: string; password?: string; school_year: number; term: number }) {
  return request.post<XiqueConfig>('/admin/courses/xique/config', data)
}
export function adminSyncXique(data?: { root_url?: string; username?: string; password?: string; school_year?: number; term?: number }) {
  return request.post<{
    success: boolean; message: string; semester: string; class_name: string
    total: number; created: number; updated: number; skipped: number
  }>('/admin/courses/sync/xique', data || {})
}
