import { getToken } from '@/utils/token'

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
) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
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
