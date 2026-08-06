import { getToken } from '@/utils/token'

export async function sendChatMessage(
  message: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
  onDone: (full: string) => void,
  onSuggestions: (suggestions: any[]) => void,
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

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value)
    if (text.includes('__SUGGESTIONS__:')) {
      const parts = text.split('__SUGGESTIONS__:')
      if (parts[0]) {
        onChunk(parts[0])
        full += parts[0]
      }
      try {
        const suggestions = JSON.parse(parts[1])
        onSuggestions(suggestions)
      } catch { /* ignore parse error */ }
    } else {
      onChunk(text)
      full += text
    }
  }
  onDone(full)
}
