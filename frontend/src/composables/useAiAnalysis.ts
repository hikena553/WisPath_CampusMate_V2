import { ref } from 'vue'
import { getToken } from '@/utils/token'

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

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        rawResult.value += text
        renderedResult.value = rawResult.value
        if (options?.onStream) {
          options.onStream(text)
        }
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
