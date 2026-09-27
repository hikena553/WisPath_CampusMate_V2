import request from '@/utils/request'

export interface EmotionRecordItem {
  id: number
  emotion: string
  label: string
  confidence: number
  source: string | null
  conversation_id: number | null
  created_at: string
}

export interface EmotionStat {
  emotion: string
  label: string
  count: number
  percent: number
}

export interface EmotionTrend {
  week: string
  emotion: string
  label: string
}

export interface EmotionStats {
  total: number
  breakdown: EmotionStat[]
  trending: EmotionTrend[]
}

/** 记录单条情绪 */
export function recordEmotion(
  emotion: string,
  confidence = 0,
  source = 'voice_call',
  conversationId?: number | null,
) {
  return request.post('/emotions/record', null, {
    params: { emotion, confidence, source, conversation_id: conversationId },
  })
}

/** 批量记录情绪 */
export function batchRecordEmotion(
  records: Array<{ emotion: string; confidence: number; source?: string; conversation_id?: number | null }>,
) {
  return request.post('/emotions/record/batch', { records })
}

/** 情绪历史记录 */
export function fetchEmotionHistory(days = 30, limit = 200) {
  return request.get<EmotionRecordItem[]>('/emotions/history', { params: { days, limit } })
}

/** 情绪统计（垃圾桶） */
export function fetchEmotionStats(days = 30) {
  return request.get<EmotionStats>('/emotions/stats', { params: { days } })
}

/** 清空情绪记录 */
export function clearEmotions(days = 3650) {
  return request.delete('/emotions/clear', { params: { days } })
}