import request from '@/utils/request'

export interface KnowledgeHit {
  type: 'qa' | 'document'
  category?: string
  question?: string
  answer?: string
  content?: string
  document_id?: number
  score?: number | null
}

export interface KnowledgeSearchMeta {
  engine: string
  segmenter: string
  segment_tokens: string[]
  retrieval: string
  embedding_model: string | null
  indexed_chunks: number
  note?: string
  elapsed_ms: number
}

/** AI 资源空间：RAG 知识库混合检索（全端可用） */
export async function searchKnowledge(q: string, limit = 10): Promise<KnowledgeHit[]> {
  const res = await searchKnowledgeRaw(q, limit)
  return res.results
}

/** RAG 检索原始响应：含 results / trace_id / meta（检索与向量分词模型信息，管理端展示用） */
export async function searchKnowledgeRaw(q: string, limit = 10): Promise<{ results: KnowledgeHit[]; trace_id: string; meta: KnowledgeSearchMeta | null }> {
  try {
    const res = await request.get('/knowledge/search', { params: { q, limit } })
    return {
      results: (res as { results?: KnowledgeHit[] }).results || [],
      trace_id: (res as { trace_id?: string }).trace_id || '',
      meta: (res as { meta?: KnowledgeSearchMeta }).meta || null,
    }
  } catch {
    return { results: [], trace_id: '', meta: null }
  }
}