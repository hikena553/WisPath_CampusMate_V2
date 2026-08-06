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
