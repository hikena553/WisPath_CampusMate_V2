import type { Conversation } from '@/stores/conversation'
import { escapeHtml, highlightMatches, normalizeQuery } from '@/utils/textHighlight'

/**
 * 高亮 / 转义已在 utils/textHighlight.ts 收敛成一份实现（消息搜索子页同样在用），
 * 这里原样转出，历史上从本模块导入的调用方无需改动。
 */
export { escapeHtml, highlightMatches, normalizeQuery }

/** 项目类型 → 中文标签，用于「学科竞赛」这类关键词也能命中 */
export const PROJECT_TEMPLATE_LABELS: Record<string, string> = {
  competition: '学科竞赛',
  thesis: '毕业论文',
  practice: '社会实践',
  certificate: '证书考取',
  student_work: '学生工作',
  custom: '自定义项目',
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
