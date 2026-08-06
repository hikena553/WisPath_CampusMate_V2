import request from '@/utils/request'

// 分页响应类型
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 分页请求参数
export interface PaginationParams {
  page?: number
  page_size?: number
}

// 知识库
export interface KnowledgeItem {
  id: number
  category: string
  question: string
  answer: string
  tags: string | null
}

export interface DocumentInfo {
  id: number
  filename: string
  file_type: string
  status: string
  chunk_count: number
  created_at: string | null
}

export function getKnowledgeList(params?: { category?: string; search?: string } & PaginationParams) {
  return request.get<PaginatedResponse<KnowledgeItem>>('/admin/knowledge', { params })
}

export function createKnowledgeItem(data: { category: string; question: string; answer: string; tags?: string }) {
  return request.post<KnowledgeItem>('/admin/knowledge', data)
}

export function updateKnowledgeItem(id: number, data: Partial<KnowledgeItem>) {
  return request.put<KnowledgeItem>(`/admin/knowledge/${id}`, data)
}

export function deleteKnowledgeItem(id: number) {
  return request.delete(`/admin/knowledge/${id}`)
}

export function uploadDocument(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ message: string; document_id: number; chunk_count: number }>('/admin/knowledge/upload', formData)
}

export function getDocumentList() {
  return request.get<DocumentInfo[]>('/admin/knowledge/documents')
}

export function deleteDocument(id: number) {
  return request.delete(`/admin/knowledge/documents/${id}`)
}

// 教师管理
export interface TeacherInfo {
  id: number
  username: string
  name: string
  college: string | null
  avatar: string | null
  title: string | null
  department: string | null
  student_count: number
}

export interface StudentBrief {
  id: number
  username: string
  name: string
  college: string | null
  class_name: string | null
  avatar: string | null
  score: number
  crisis_level: string | null
}

export function getTeacherList(params?: { search?: string } & PaginationParams) {
  return request.get<PaginatedResponse<TeacherInfo>>('/admin/teachers', { params })
}

export function getTeacherStudents(teacherId: number) {
  return request.get<StudentBrief[]>(`/admin/teachers/${teacherId}/students`)
}

// 教师管理
export function createTeacher(data: { username: string; name: string; college?: string; title?: string; department?: string; gender?: string; phone?: string }) {
  return request.post<TeacherInfo>('/admin/teachers', data)
}

export function deleteTeacher(id: number) {
  return request.delete<{ message: string }>(`/admin/teachers/${id}`)
}

export function batchDeleteTeachers(ids: number[]) {
  return request.delete<{ message: string }>('/admin/teachers/batch', { data: { ids } })
}

// 学生管理
export function getStudentList(params?: { search?: string; college?: string; class_name?: string } & PaginationParams) {
  return request.get<PaginatedResponse<StudentBrief>>('/admin/students', { params })
}

export function updateStudent(id: number, data: Partial<StudentBrief>) {
  return request.put<StudentBrief>(`/admin/students/${id}`, data)
}

export interface StudentStats {
  total: number
  college_stats: { college: string; count: number }[]
  crisis_stats: { level: string; count: number }[]
}

export function getStudentStats() {
  return request.get<StudentStats>('/admin/students/stats')
}

// 密码管理
export function resetPassword(userId: number) {
  return request.post<{ message: string }>(`/admin/reset-password/${userId}`)
}

// 数据导入导出
export function exportData(role: 'student' | 'teacher') {
  return request.get('/admin/export', { params: { role }, responseType: 'blob' })
}

export interface ImportResult {
  total: number
  created: number
  skipped: number
  errors: string[]
}

export function importData(role: 'student' | 'teacher', file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<ImportResult>(`/admin/import?role=${role}`, formData)
}
