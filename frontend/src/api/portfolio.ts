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