/**
 * 对话（项目）元信息：阶段流转与文案
 *
 * 注意：PROJECT_STAGES 必须与后端 backend/app/models/conversation.py 的
 * PROJECT_STAGES 保持一致；后端在 PUT /agent/conversations/{id} 时会校验阶段合法性。
 */
export const PROJECT_STAGES: Record<string, string[]> = {
  competition: ['赛前准备', '方案设计', '实施优化', '答辩展示'],
  thesis: ['选题开题', '文献综述', '实验/调研', '撰写修改', '答辩'],
  practice: ['方案申报', '前期准备', '实施执行', '总结评优'],
  certificate: ['考情分析', '学习规划', '备考刷题', '考前冲刺'],
  student_work: ['活动策划', '审批协调', '执行落地', '复盘总结'],
  custom: [],
}

/** 项目类型 → 中文名（与 conversationSearch.ts 中的匹配标签保持一致） */
export const PROJECT_TEMPLATE_LABELS: Record<string, string> = {
  competition: '学科竞赛',
  thesis: '毕业论文',
  practice: '社会实践',
  certificate: '证书考取',
  student_work: '学生工作',
  custom: '自定义项目',
}

/** 该项目的可选阶段；非阶段性项目返回空数组 */
export function stagesOf(template?: string | null): string[] {
  if (!template) return []
  return PROJECT_STAGES[template] ?? []
}

/** 阶段在流程中的序号（1 起），未知阶段返回 0 */
export function stageIndex(template: string | null | undefined, stage?: string | null): number {
  if (!stage) return 0
  const idx = stagesOf(template).indexOf(stage)
  return idx < 0 ? 0 : idx + 1
}

/** 「第 2/5 步 · 文献综述」这样的阶段进度文案 */
export function stageLabel(template: string | null | undefined, stage?: string | null): string {
  if (!stage) return ''
  const stages = stagesOf(template)
  if (!stages.length) return stage
  const idx = stageIndex(template, stage)
  return idx ? `第 ${idx}/${stages.length} 步 · ${stage}` : stage
}

/** 相对时间文案：刚刚 / 今天 / 昨天 / 三天前 / 一周前 / 具体日期 */
export function relativeTime(dateStr?: string | null, now: Date = new Date()): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return ''
  // 按「自然日」比较，而不是按小时差取整：否则今天 09:00 会被算成 -1 天（显示"刚刚"），
  // 昨天 09:00 会被算成 0 天（显示"今天"）。旧实现的 timeLabel 就有这个错位。
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const dayDiff = Math.round((startOfToday.getTime() - startOfDate.getTime()) / 86400000)
  if (dayDiff < 0) return '刚刚'
  if (dayDiff === 0) return '今天'
  if (dayDiff === 1) return '昨天'
  if (dayDiff <= 3) return '三天前'
  if (dayDiff <= 7) return '一周前'
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/* ── 按对话类型分类：普通对话 + 各类项目（与「新工作任务」的类型一一对应） ── */

/** 分组 key：normal 为普通对话，其余为 project_template，other 兜底未知/空模板的项目 */
export type ConvTypeKey =
  | 'normal' | 'competition' | 'thesis' | 'practice'
  | 'certificate' | 'student_work' | 'custom' | 'other'

/** 分组顺序：普通对话在前，项目类型按「新工作任务」下拉里的顺序 */
export const CONV_TYPE_ORDER: ConvTypeKey[] = [
  'normal', 'competition', 'thesis', 'practice', 'certificate', 'student_work', 'custom', 'other',
]

export const CONV_TYPE_LABELS: Record<ConvTypeKey, string> = {
  normal: '普通对话',
  competition: PROJECT_TEMPLATE_LABELS.competition,
  thesis: PROJECT_TEMPLATE_LABELS.thesis,
  practice: PROJECT_TEMPLATE_LABELS.practice,
  certificate: PROJECT_TEMPLATE_LABELS.certificate,
  student_work: PROJECT_TEMPLATE_LABELS.student_work,
  custom: PROJECT_TEMPLATE_LABELS.custom,
  other: '项目',
}

/** 一条对话属于哪个类型分组 */
export function convTypeKey(conv: { type?: string | null; project_template?: string | null }): ConvTypeKey {
  if (conv.type !== 'project') return 'normal'
  const template = conv.project_template
  if (template && template in PROJECT_TEMPLATE_LABELS) return template as ConvTypeKey
  return 'other'
}

export interface ConvTypeGroup<T> {
  key: ConvTypeKey
  label: string
  items: T[]
}

/** 按类型分组并保持桶内原有顺序（后端已按置顶 + 最近更新倒序）；空分类不返回 */
export function groupByType<T extends { type?: string | null; project_template?: string | null }>(
  list: T[],
): ConvTypeGroup<T>[] {
  const buckets = new Map<ConvTypeKey, T[]>()
  for (const item of list) {
    const key = convTypeKey(item)
    const bucket = buckets.get(key)
    if (bucket) bucket.push(item)
    else buckets.set(key, [item])
  }
  return CONV_TYPE_ORDER
    .filter(key => buckets.has(key))
    .map(key => ({ key, label: CONV_TYPE_LABELS[key] || key, items: buckets.get(key) as T[] }))
}

/** 会话副标题：更新时间 + 项目阶段进度（用于移动端操作面板） */
export function conversationSubtitle(
  conv: { updated_at?: string | null; project_template?: string | null; project_stage?: string | null } | null | undefined,
): string {
  if (!conv) return ''
  const parts = [relativeTime(conv.updated_at)]
  const stage = stageLabel(conv.project_template, conv.project_stage)
  if (stage) parts.push(stage)
  return parts.filter(Boolean).join(' · ')
}