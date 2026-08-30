import { ref } from 'vue'
import { getToken } from '@/utils/token'

const MAX_CACHE_SIZE = 50
const cacheMap = new Map<string, string>()

function cacheKey(pageType: string, prompt: string) {
  return `${pageType}::${prompt}`
}

export function useAiAnalysis(pageType: string) {
  const loading = ref(false)
  const rawResult = ref('')
  const renderedResult = ref('')
  const fromCache = ref(false)

  async function analyze(prompt: string, options?: { skipCache?: boolean; onStream?: (chunk: string) => void }) {
    const key = cacheKey(pageType, prompt)

    if (!options?.skipCache && cacheMap.has(key)) {
      rawResult.value = cacheMap.get(key)!
      renderedResult.value = rawResult.value
      fromCache.value = true
      return
    }

    fromCache.value = false
    loading.value = true
    rawResult.value = ''
    renderedResult.value = ''

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      const token = getToken()
      if (token) headers['Authorization'] = `Bearer ${token}`

      const resp = await fetch('/api/agent/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: prompt,
          history: [],
          skip_conversation: true,
        }),
      })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const parseEvent = (raw: string): { type: string; text: string } | null => {
        if (!raw.trim()) return null
        let type = 'message'
        let data = ''
        for (const line of raw.split('\n')) {
          if (line.startsWith('event: ')) type = line.slice(7).trim()
          else if (line.startsWith('data: ')) data = line.slice(6)
        }
        if (!data) return null
        let text = data
        try {
          const parsed = JSON.parse(data)
          if (typeof parsed === 'string') text = parsed
        } catch {
          /* 兼容旧协议，直接使用原始 data */
        }
        return { type, text }
      }

      const append = (text: string) => {
        rawResult.value += text
        renderedResult.value = rawResult.value
        if (options?.onStream) {
          options.onStream(text)
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const event of events) {
          const parsed = parseEvent(event)
          if (!parsed) continue
          // 仅保留正文内容，忽略 reasoning 思考片段和 suggestions
          if (parsed.type === 'content' || parsed.type === 'message') {
            append(parsed.text)
          }
        }
      }

      if (buffer.trim()) {
        const parsed = parseEvent(buffer)
        if (parsed && (parsed.type === 'content' || parsed.type === 'message')) {
          append(parsed.text)
        }
      }

      if (cacheMap.size >= MAX_CACHE_SIZE) {
        const oldest = cacheMap.keys().next().value
        if (oldest !== undefined) cacheMap.delete(oldest)
      }
      cacheMap.set(key, rawResult.value)
    } finally {
      loading.value = false
    }
  }

  function reset() {
    rawResult.value = ''
    renderedResult.value = ''
    fromCache.value = false
  }

  return { loading, rawResult, renderedResult, fromCache, analyze, reset }
}
