/**
 * 关键词高亮的通用实现：把命中片段包成 `<mark class="hl">`，返回**已转义**的 HTML。
 *
 * 为什么强调「已转义」：调用方普遍用 v-html 渲染这段字符串，而标题/昵称/消息内容
 * 都来自用户输入。这里先把每一段纯文本转义、再拼标签，所以文本里的尖括号
 * 永远不会被当成标签执行（不引入 Markdown 解析器，XSS 面就只剩这一处拼接）。
 *
 * 原先这套逻辑只服务于智能体侧栏的会话检索（components/agent/conversationSearch.ts），
 * 消息搜索子页也要用同一套口径，故下沉到 utils；原模块改为从这里 re-export，调用方零改动。
 */

/** 归一化关键词：去掉首尾空格并转小写，避免只打空格被当成搜索态 */
export function normalizeQuery(raw: string): string {
  return (raw || '').trim().toLowerCase()
}

/** 转义 HTML，避免用户自定义标题通过 v-html 注入 */
export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch] as string))
}

/**
 * 高亮命中的关键词，返回可直接交给 v-html 的安全 HTML。
 * 关键词为空时返回原文（同样已转义）。
 */
export function highlightMatches(text: string, query: string): string {
  if (!text) return ''
  const q = normalizeQuery(query)
  if (!q) return escapeHtml(text)
  const src = text.toLowerCase()
  let out = ''
  let i = 0
  while (i < text.length) {
    const idx = src.indexOf(q, i)
    if (idx < 0) {
      out += escapeHtml(text.slice(i))
      break
    }
    out += escapeHtml(text.slice(i, idx))
    out += `<mark class="hl">${escapeHtml(text.slice(idx, idx + q.length))}</mark>`
    i = idx + q.length
  }
  return out
}
