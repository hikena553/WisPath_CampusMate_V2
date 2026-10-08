import { getToken } from '@/utils/token'

/** SSE 末尾回传的会话元信息（见后端 agent_service.chat 的 meta 事件） */
export interface ChatMeta {
  conversation_id: number | null
  title: string | null
  /** 服务端是否已把本轮回复落库；false/缺失时前端可兜底写入 */
  saved: boolean
}

export async function sendChatMessage(
  message: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
  onDone: (full: string) => void,
  onSuggestions: (suggestions: any[]) => void,
  onReasoning: (text: string) => void,
  fileUrl?: string,
  conversationId?: number,
  deepThink?: boolean,
  skipConv?: boolean,
  onMeta?: (meta: ChatMeta) => void,
) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch('/api/agent/chat', {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, history, file_url: fileUrl, conversation_id: conversationId, deep_think: deepThink || false, skip_conversation: skipConv || false }),
  })

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`)
  }

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let full = ''
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // 按 SSE 事件分割（双换行符）
    const events = buffer.split('\n\n')
    buffer = events.pop() || ''  // 保留不完整的事件

    for (const event of events) {
      if (!event.trim()) continue

      const lines = event.split('\n')
      let eventType = 'message'
      let data = ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7)
        } else if (line.startsWith('data: ')) {
          data = line.slice(6)
        }
      }

      if (!data) continue

      try {
        const parsed = JSON.parse(data)
        console.log('[SSE] event:', eventType, 'data length:', typeof parsed === 'string' ? parsed.length : 'non-string')
        switch (eventType) {
          case 'reasoning':
            console.log('[SSE] reasoning content:', parsed.substring(0, 100))
            onReasoning(parsed)
            break
          case 'suggestions':
            onSuggestions(parsed)
            break
          case 'meta':
            onMeta?.(parsed as ChatMeta)
            break
          default:  // 'content' 或 'message'
            onChunk(parsed)
            full += parsed
        }
      } catch {
        // 兼容旧协议
        if (data.startsWith('__REASONING__:')) {
          onReasoning(data.slice(14))
        } else if (data.startsWith('__SUGGESTIONS__:')) {
          try { onSuggestions(JSON.parse(data.slice(16))) } catch { /* ignore */ }
        } else {
          onChunk(data)
          full += data
        }
      }
    }
  }

  // 处理缓冲区剩余内容
  if (buffer.trim()) {
    const lines = buffer.split('\n')
    let eventType = 'message'
    let data = ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7)
      } else if (line.startsWith('data: ')) {
        data = line.slice(6)
      }
    }

    if (data) {
      try {
        const parsed = JSON.parse(data)
        switch (eventType) {
          case 'reasoning':
            onReasoning(parsed)
            break
          case 'suggestions':
            onSuggestions(parsed)
            break
          case 'meta':
            onMeta?.(parsed as ChatMeta)
            break
          default:
            onChunk(parsed)
            full += parsed
        }
      } catch {
        if (data.startsWith('__REASONING__:')) {
          onReasoning(data.slice(14))
        } else if (data.startsWith('__SUGGESTIONS__:')) {
          try { onSuggestions(JSON.parse(data.slice(16))) } catch { /* ignore */ }
        } else {
          onChunk(data)
          full += data
        }
      }
    }
  }

  onDone(full)
}


export interface ProactiveAction {
  trigger: string
  student_id: number
  priority: number
  action_type: string
  title: string
  content: string
  target_role: string
}

/** 主动发现完整载荷：动作列表 + （服务端命中缓存时的）LLM 洞察 */
export interface ProactiveFeed {
  actions: ProactiveAction[]
  insight: string | null
}

/**
 * 拉取主动发现完整载荷。
 * 后端只回规则文案以保证首屏速度；insight 仅在服务端 30 分钟缓存命中时非空，
 * 未命中时前端再调 fetchProactiveInsight() 在后台补一句个性化洞察。
 */
export async function fetchProactiveFeed(): Promise<ProactiveFeed> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  try {
    const resp = await fetch('/api/agent/proactive', { headers })
    if (resp.ok) {
      const data = await resp.json()
      return { actions: data.actions || [], insight: data.insight ?? null }
    }
  } catch (e) {
    console.error('获取主动发现动作失败', e)
  }
  return { actions: [], insight: null }
}

/** AI 主动发现驾驶舱：拉取当前角色相关的主动触达动作 */
export async function fetchProactiveActions(): Promise<ProactiveAction[]> {
  return (await fetchProactiveFeed()).actions
}

/**
 * AI 主动发现：LLM 个性化洞察。
 * 服务端按「学生 + 动作指纹」缓存 30 分钟；未配置 LLM / 超时 / 异常均返回 null，
 * 前端保持规则文案即可（调用方不得阻塞卡片渲染）。
 */
export async function fetchProactiveInsight(): Promise<string | null> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  try {
    const resp = await fetch('/api/agent/proactive/insight', { headers })
    if (resp.ok) {
      const data = await resp.json()
      return data.insight ?? null
    }
  } catch (e) {
    console.error('获取 AI 洞察失败', e)
  }
  return null
}


export async function fetchRecommendations(): Promise<string[]> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  try {
    const resp = await fetch('/api/agent/recommendations', { headers })
    if (resp.ok) {
      const data = await resp.json()
      return data.recommendations || []
    }
  } catch (e) {
    console.error('获取推荐失败', e)
  }
  return []
}
