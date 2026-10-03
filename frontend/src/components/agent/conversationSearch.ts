import type { Conversation } from '@/stores/conversation'

/** 项目类型 → 中文标签，用于「学科竞赛」这类关键词也能命中 */
export const PROJECT_TEMPLATE_LABELS: Record<string, string> = {
  competition: '学科竞赛',
  thesis: '毕业论文',
  practice: '社会实践',
  certificate: '证书考取',
  student_work: '学生工作',
  custom: '自定义项目',
}

/** 归一化关键词：去掉首尾空格并转小写，避免只打空格被当成搜索态 */
export function normalizeQuery(raw: string): string {
  return (raw || '').trim().toLowerCase()
}

/** 一条对话参与匹配的全部文本：标题 + 项目阶段 + 项目类型中文名 */
export function conversationMatchText(c: Conversation): string {
  const parts = [c.title || '', c.project_stage || '']
  if (c.project_template) {
    parts.push(PROJECT_TEMPLATE_LABELS[c.project_template] || c.project_template)
  }
  return parts.join(' ').toLowerCase()
}

/** 关键词是否命中一条对话；关键词为空时全部命中 */
export function matchesQuery(c: Conversation, query: string): boolean {
  const q = normalizeQuery(query)
  if (!q) return true
  return conversationMatchText(c).includes(q)
}

/** 按标题 / 项目阶段 / 项目类型过滤对话列表 */
export function filterConversations<T extends Conversation>(list: T[], query: string): T[] {
  const q = normalizeQuery(query)
  if (!q) return list
  return list.filter(c => conversationMatchText(c).includes(q))
}

/** 转义 HTML，避免用户自定义标题通过 v-html 注入 */
export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch] as string))
}

/**
 * 高亮命中的关键词，返回可直接交给 v-html 的安全 HTML。
 * 文本先逐段转义再拼 <mark>，因此标题里的尖括号不会变成标签。
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