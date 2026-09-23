import request from '@/utils/request'

export interface KnowledgeHit {
  type: 'qa' | 'document'
  category?: string
  question?: string
  answer?: string
  content?: string
  document_id?: number
}

/** AI 资源空间：RAG 知识库混合检索（全端可用） */
export async function searchKnowledge(q: string, limit = 10): Promise<KnowledgeHit[]> {
  const res = await searchKnowledgeRaw(q, limit)
  return res.results
}

/** RAG 检索原始响应：含 results 与 trace_id（管理端链路追踪用） */
export async function searchKnowledgeRaw(q: string, limit = 10): Promise<{ results: KnowledgeHit[]; trace_id: string }> {
  try {
    const res = await request.get('/knowledge/search', { params: { q, limit } })
    return {
      results: (res as { results?: KnowledgeHit[] }).results || [],
      trace_id: (res as { trace_id?: string }).trace_id || '',
    }
  } catch {
    return { results: [], trace_id: '' }
  }
}