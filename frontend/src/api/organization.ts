import request from '@/utils/request'
import type { College, Major, ClassGroup } from '@/types'

// ─── 学院 ───────────────────────────────────────────────
export function getColleges() {
  return request.get<College[]>('/admin/colleges')
}
export function createCollege(data: { name: string; code: string; description?: string }) {
  return request.post<College>('/admin/colleges', data)
}
export function updateCollege(id: number, data: { name: string; code: string; description?: string }) {
  return request.put<College>(`/admin/colleges/${id}`, data)
}
export function deleteCollege(id: number) {
  return request.delete(`/admin/colleges/${id}`)
}

// ─── 专业 ───────────────────────────────────────────────
export function getMajors(collegeId?: number) {
  return request.get<Major[]>('/admin/majors', { params: { college_id: collegeId } })
}
export function createMajor(data: { college_id: number; name: string; code: string; description?: string }) {
  return request.post<Major>('/admin/majors', data)
}
export function updateMajor(id: number, data: { college_id: number; name: string; code: string; description?: string }) {
  return request.put<Major>(`/admin/majors/${id}`, data)
}
export function deleteMajor(id: number) {
  return request.delete(`/admin/majors/${id}`)
}

// ─── 班级 ───────────────────────────────────────────────
export function getClassGroups(params?: { major_id?: number; college_id?: number }) {
  return request.get<ClassGroup[]>('/admin/class-groups', { params })
}
export function createClassGroup(data: { major_id: number; name: string; grade: number }) {
  return request.post<ClassGroup>('/admin/class-groups', data)
}
export function updateClassGroup(id: number, data: { major_id: number; name: string; grade: number }) {
  return request.put<ClassGroup>(`/admin/class-groups/${id}`, data)
}
export function deleteClassGroup(id: number) {
  return request.delete(`/admin/class-groups/${id}`)
}
