import request from '@/utils/request'

/** 资讯条目：小绵管家推送的单条校园/行业资讯 */
export interface ButlerFeedItem {
  id: number
  title: string
  summary: string
  link: string
  source_name: string
  source_type: string
  source_label: string
  published_at: string | null
}

/** 资讯简报：管家自动推送消息的载荷 */
export interface ButlerBriefing {
  generated_at: string
  greeting: string
  digest: string
  items: ButlerFeedItem[]
}

export interface ButlerChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** 拉取「最新资讯简报」（管家自动推送内容） */
export function getButlerBriefing(limit = 5, sourceType = 'all') {
  return request.get<ButlerBriefing>('/butler/briefing', {
    params: { limit, source_type: sourceType },
  })
}

/** 与管家对话（含总结意图识别） */
export function butlerChat(message: string, history: ButlerChatMessage[]) {
  return request.post<{ reply: string }>('/butler/chat', { message, history })
}

/** 总结对话内容 */
export function butlerSummarize(messages: ButlerChatMessage[]) {
  return request.post<{ reply: string }>('/butler/summarize', { messages })
}