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
  embedded_count?: number
  source_type?: 'file' | 'url'
  source_url?: string | null
  created_at: string | null
}

export interface KnowledgeIndexStatus {
  segmenter: string
  embedding_model: string | null
  embedding_configured: boolean
  qa_count: number
  document_count: number
  total_chunks: number
  indexed_chunks: number
  index_coverage: number
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

// 外部数据源（网络数据位置）引进知识库
export interface ExternalSourceStats {
  total: number
  file_count: number
  url_count: number
}

export function getExternalSourceStats() {
  return request.get<ExternalSourceStats>('/admin/knowledge/source-stats')
}

export function addKnowledgeUrlSource(data: { url: string; title?: string }) {
  return request.post<{ message: string; document_id: number; chunk_count: number; source_url: string }>(
    '/admin/knowledge/sources/url',
    data,
  )
}

export function refetchDocument(id: number) {
  return request.post<{ message: string; document_id: number; chunk_count: number }>(
    `/admin/knowledge/documents/${id}/refetch`,
  )
}

export function reindexKnowledge() {
  return request.post<{ message: string; model: string | null; indexed: number; skipped: number; error: string }>('/admin/knowledge/reindex')
}

export function getKnowledgeIndexStatus() {
  return request.get<KnowledgeIndexStatus>('/admin/knowledge/index-status')
}

// 向量模型（embedding）配置
export interface EmbeddingConfig {
  model: string
  base_url: string
  api_key_set: boolean
  configured: boolean
  using_env_fallback: boolean
  hint: string
}
export function getEmbeddingConfig() {
  return request.get<EmbeddingConfig>('/admin/knowledge/embedding-config')
}
export function saveEmbeddingConfig(data: { model?: string; base_url?: string; api_key?: string }) {
  return request.post<EmbeddingConfig>('/admin/knowledge/embedding-config', data)
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

// ===== 顶栏消息中心（密码重置申请 / 待处理反馈） =====
export interface AdminMessageItem {
  id: string
  kind: 'password_reset' | 'feedback' | 'system'
  level: 'urgent' | 'important' | 'normal'
  title: string
  content: string
  link: string | null
  created_at: string
}

export interface AdminMessageOverview {
  items: AdminMessageItem[]
  /** 待处理事项总数（顶栏红点） */
  unread: number
  counts: { password_reset: number; feedback: number }
}

export function getAdminMessages() {
  return request.get<AdminMessageOverview>('/admin/messages')
}

/** 驳回（忽略）某条忘记密码申请，申请人会收到站内通知 */
export function rejectPasswordReset(id: number, note?: string) {
  return request.post<{ message: string }>(`/admin/password-reset-requests/${id}/reject`, null, {
    params: { note },
  })
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

// 任务下发：管理员指派任务给教师，自动进入该教师的日程任务清单
export interface AdminTaskCreate {
  teacher_id: number
  title: string
  detail?: string | null
  priority?: 'high' | 'mid' | 'low'
  remind_at?: string | null
  due_at?: string | null
}

export function dispatchTeacherTask(data: AdminTaskCreate) {
  return request.post('/admin/tasks', data)
}

export interface DashboardStats {
  teacher_count: number
  student_count: number
  college_count: number
  knowledge_count: number
  document_count: number
  student_gender_stats: Record<string, number>
  teacher_gender_stats: Record<string, number>
  conversation_count: number
  message_count: number
  college_stats: { college: string; count: number }[]
  teacher_college_stats: { college: string; count: number }[]
  crisis_stats: { level: string; count: number }[]
  avg_response_time?: number
}

export function getDashboardStats() {
  return request.get<DashboardStats>('/admin/dashboard')
}

// ==================== 外部资讯统一管理（管理端） ====================

export type FeedSourceType = 'papers' | 'agents' | 'opensource' | 'news' | 'ai_news' | 'rankings' | 'cn_ai'

export interface AdminFeedSource {
  id: number
  name: string
  kind: 'rss' | 'html' | 'arxiv' | 'github' | 'gitee' | 'lmarena'
  source_type: FeedSourceType
  url: string
  query: string | null
  base_url: string | null
  filter_kw: string[]
  date_only: boolean
  per_page: number
  is_builtin: boolean
  enabled: boolean
  sort_order: number
  item_count: number
  last_ingested_at: string | null
}

export interface AdminFeedItem {
  id: number
  source_type: FeedSourceType
  feed_key: string
  title: string
  summary: string | null
  link: string
  author: string | null
  source_name: string | null
  is_highlight: boolean
  meta: Record<string, any>
  published_at: string | null
  created_at: string | null
}

export function getAdminFeedSources(sourceType: FeedSourceType | 'all' = 'all') {
  return request.get<AdminFeedSource[]>('/admin/feeds/sources', { params: { source_type: sourceType } })
}

export function createAdminFeedSource(body: Partial<AdminFeedSource>) {
  return request.post<AdminFeedSource>('/admin/feeds/sources', body)
}

export function updateAdminFeedSource(id: number, body: Partial<AdminFeedSource>) {
  return request.patch<AdminFeedSource>(`/admin/feeds/sources/${id}`, body)
}

export function deleteAdminFeedSource(id: number) {
  return request.delete<{ ok: boolean; message?: string }>(`/admin/feeds/sources/${id}`)
}

export function getAdminFeedItems(params: {
  source_type?: FeedSourceType | 'all'
  q?: string
  feed_key?: string
  page?: number
  page_size?: number
}) {
  return request.get<PaginatedResponse<AdminFeedItem>>('/admin/feeds/items', { params })
}

export function updateAdminFeedItem(id: number, body: { is_highlight?: boolean }) {
  return request.patch<AdminFeedItem>(`/admin/feeds/items/${id}`, body)
}

export function deleteAdminFeedItem(id: number) {
  return request.delete<{ ok: boolean }>(`/admin/feeds/items/${id}`)
}

export function refreshAdminFeeds(sourceType: FeedSourceType | 'all' = 'all') {
  return request.post<{ inserted: number; sources: Record<string, { fetched: number; inserted: number }>; errors: string[] }>(
    `/admin/feeds/refresh?source_type=${sourceType}`,
  )
}

// ==================== 系统监控与运维 ====================

export interface SystemServiceInfo {
  status: string
  version: string
  env: string
  log_level: string
  python: string
  platform: string
  uptime_seconds: number
  started_at: string
  server_time: string
}

export interface SystemDatabaseInfo {
  reachable: boolean
  dialect: string
  target: string
  table_counts: Record<string, number>
}

export interface SystemTaskInfo {
  name: string
  interval_seconds: number
  desc: string
}

export interface SystemFeedStatus {
  source_total: number
  source_enabled: number
  item_total: number
  type_counts: Record<string, number>
  last_ingested_at: string | null
}

export interface SystemIntegrations {
  llm_configured: boolean
  embedding_configured: boolean
  embedding_model: string | null
  github_token_set: boolean
  gitee_token_set: boolean
  sentry_configured: boolean
}

export interface SystemModuleInfo {
  prefix: string
  tags: string[]
  route_count: number
}

export interface SystemOverview {
  service: SystemServiceInfo
  database: SystemDatabaseInfo
  background_tasks: SystemTaskInfo[]
  feeds: SystemFeedStatus
  knowledge: KnowledgeIndexStatus
  integrations: SystemIntegrations
  modules: SystemModuleInfo[]
}

export function getSystemOverview() {
  return request.get<SystemOverview>('/admin/system/overview')
}

export function runMaintenance(action: 'refresh_feeds' | 'reindex_knowledge') {
  return request.post<{ action: string; ok: boolean; result: any }>('/admin/system/maintenance', { action })
}
