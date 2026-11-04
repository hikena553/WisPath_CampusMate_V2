import request from '@/utils/request'

/** AI 帮我写：场景 / 描述 / 要点 / 本地参考草稿 → 可直接编辑的文案 */
export interface AiDraftPayload {
  scene: string
  brief?: string
  points?: string[]
  reference?: string
  max_length?: number
}

export interface AiDraftResult {
  text: string
  /** ai=大模型生成；rule=模型不可用时的本地兜底 */
  source: 'ai' | 'rule'
}

export function aiDraftText(payload: AiDraftPayload) {
  return request.post<AiDraftResult>('/teacher-ai/draft', payload)
}
