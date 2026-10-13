import request from '@/utils/request'

export interface OpenSourceReference {
  id: number
  name: string
  repo_url: string
  homepage?: string | null
  license: string
  license_category: 'permissive' | 'weak-copyleft' | 'copyleft' | 'unknown'
  stars: number
  language?: string | null
  tech_tags?: string | null
  summary?: string | null
  reusable_scope?: string | null
  attribution?: string | null
  is_builtin?: boolean
  enabled?: boolean
}

export interface ReferencePayload {
  name: string
  repo_url: string
  homepage?: string | null
  license: string
  license_category: string
  stars: number
  language?: string | null
  tech_tags?: string | null
  summary?: string | null
  reusable_scope?: string | null
  attribution?: string | null
  enabled?: boolean
}

export interface ScaffoldResult {
  page_name: string
  route_path: string
  matched_references: OpenSourceReference[]
  attribution: string
  files: Record<string, string>
  notes: string[]
}

/** 参考库列表（管理端） */
export async function listReferences(params?: {
  search?: string
  license_category?: string
  enabled_only?: boolean
}): Promise<{ items: OpenSourceReference[]; count: number; license_categories: Record<string, string> }> {
  return request.get('/references', { params })
}

/** 按需求检索可复用的开源项目 */
export async function searchReferences(q: string, limit = 5): Promise<OpenSourceReference[]> {
  const res = await request.get<{ results: OpenSourceReference[] }>('/references/search', {
    params: { q, limit },
  })
  return res.results || []
}

/** 按需求生成 Vue 页面骨架（本地模板生成，自带出处署名） */
export async function generateScaffold(payload: {
  requirement: string
  page_name?: string
  include_reference_ids?: number[]
}): Promise<ScaffoldResult> {
  return request.post('/references/scaffold', payload)
}

export async function createReference(payload: ReferencePayload): Promise<OpenSourceReference> {
  return request.post('/references', payload)
}

export async function updateReference(id: number, payload: Partial<ReferencePayload>): Promise<OpenSourceReference> {
  return request.put(`/references/${id}`, payload)
}

export async function deleteReference(id: number): Promise<{ success: boolean }> {
  return request.delete(`/references/${id}`)
}
