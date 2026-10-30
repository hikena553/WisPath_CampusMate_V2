import request from '@/utils/request'

// ---------- 证书荣誉 ----------
export interface Certificate {
  id: number
  student_id: number
  title: string
  competition_name: string | null
  award_level: string | null
  date: string | null
  description: string | null
  image_url: string | null
  status: string
  created_at: string | null
}

export function getCertificates() {
  return request.get<Certificate[]>('/portfolio/certificates')
}

export function createCertificate(data: Partial<Certificate>) {
  return request.post<Certificate>('/portfolio/certificates', data)
}

export function updateCertificate(id: number, data: Partial<Certificate>) {
  return request.put<Certificate>(`/portfolio/certificates/${id}`, data)
}

export function deleteCertificate(id: number) {
  return request.delete(`/portfolio/certificates/${id}`)
}

// ---------- 个人简历 ----------
export interface Resume {
  id: number
  filename: string
  url: string
  file_size: number | null
  is_current: number
  created_at: string | null
}

export function getResumes() {
  return request.get<Resume[]>('/portfolio/resumes')
}

export function createResume(data: { filename: string; url: string; file_size?: number | null }) {
  return request.post<Resume>('/portfolio/resumes', data)
}

export function setCurrentResume(id: number) {
  return request.put<Resume>(`/portfolio/resumes/${id}/current`)
}

export function deleteResume(id: number) {
  return request.delete(`/portfolio/resumes/${id}`)
}

// ---------- 简历导出 ----------
export interface ResumeJobRef {
  key: string
  label: string
}

export interface ResumeIndustry {
  key: string
  label: string
  jobs: ResumeJobRef[]
}

export interface ResumeTemplate {
  key: string
  name: string
  tag: string
  desc: string
  accent: string
  accent_soft: string
}

export interface ResumeOptions {
  industries: ResumeIndustry[]
  job_types: string[]
  templates: ResumeTemplate[]
}

export interface ResumeDim {
  key: string
  label: string
  score: number
  weight: number
  note: string
}

export interface ResumeSuggest {
  job_key: string
  label: string
  score: number
  why: string
}

export interface ResumeMatch {
  job: { key: string; label: string; industry: string; industry_label: string }
  score: number
  level: string
  dims: ResumeDim[]
  hits: string[]
  gaps: string[]
  suggest: ResumeSuggest[]
  tips: string[]
}

export interface ResumeTarget {
  job_key?: string | null
  industry?: string | null
  /** job_key='custom' 时的手动输入岗位名 */
  custom_job?: string | null
  job_type?: string
  city?: string
}

export interface ResumeFile {
  filename: string
  mime: string
  size: number
  format: 'docx' | 'pdf'
  match: ResumeMatch
  sections: { key: string; title: string; count: number }[]
  resume_id: number | null
  b64: string
}

export function getResumeOptions() {
  return request.get<ResumeOptions>('/portfolio/resume/options')
}

/** 模板真实渲染预览：后端用学生档案按该模板渲染一页 PDF 转 PNG，所见即所得 */
export function getTemplatePreview(
  templateKey: string,
  photoUrl?: string | null,
  target?: {
    industry?: string | null
    job_key?: string | null
    custom_job?: string | null
    job_type?: string
    city?: string
  },
) {
  return request.get<{ template_key: string; image: string }>('/portfolio/resume/template-preview', {
    params: {
      template_key: templateKey,
      photo_url: photoUrl || undefined,
      industry: target?.industry || undefined,
      job_key: target?.job_key || undefined,
      custom_job: target?.custom_job || undefined,
      job_type: target?.job_type || undefined,
      city: target?.city || undefined,
    },
  })
}

export function matchResume(data: ResumeTarget) {
  return request.post<ResumeMatch>('/portfolio/resume/match', data)
}

export function generateResume(
  data: ResumeTarget & { template_key: string; fmt: 'docx' | 'pdf'; objective?: string | null; save?: boolean; photo_url?: string | null },
) {
  return request.post<ResumeFile>('/portfolio/resume/generate', data)
}
