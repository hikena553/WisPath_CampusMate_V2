/**
 * 学生端驾驶舱数据缓存（模块级单例）
 *
 * 为什么需要它：StudentLayout 常驻，但驾驶舱/课程表等页面在切换时组件会重建，
 * 每次重建都要重新拉取课程、画像、AI 主动发现、今日待办，于是出现
 * 「骨架 → 内容」的高度跳变（下方卡片被推动，视觉上像抽搐）。
 *
 * 做法：布局空闲时把数据灌入这份模块级缓存，页面组件用缓存值作为初始值，
 * 命中即可首帧渲染真实内容；挂载后仍静默刷新，保证数据不过期。
 *
 * 语义约定：
 * - 字段为 null 表示「尚未加载过」，页面据此显示骨架；
 * - 加载失败不得把结果写回 null（避免把「请求失败」当成「确实没有数据」）；
 * - 空数组是合法值（确实无课/无待办），命中后直接显示空态而不闪骨架。
 */

import type { Course } from '@/types'
import type { GrowthProfile } from '@/api/growth'
import type { ProactiveAction } from '@/api/agent'
import type { TodayTask } from '@/api/plan'

export interface StudentDataCache {
  /** 课程表全量课程 */
  courses: Course[] | null
  /** 成长画像（五维/总分） */
  profile: GrowthProfile | null
  /** AI 主动发现动作（仅 target_role === 'student'） */
  actions: ProactiveAction[] | null
  /** 今日学习计划任务 */
  tasks: TodayTask[] | null
  /** LLM 个性化洞察文案（服务端缓存 30 分钟） */
  insight: string | null
  /** 洞察对应的动作指纹，用于判断旧洞察是否已过时 */
  insightSig: string | null
}

/** 模块级单例：跨页面/跨组件重建共享，仅在会话内有效（刷新即清空） */
export const studentDataCache: StudentDataCache = {
  courses: null,
  profile: null,
  actions: null,
  tasks: null,
  insight: null,
  insightSig: null,
}

/** 清空缓存（登出或切换账号时调用，避免下一个账号看到上一个账号的数据） */
export function resetStudentDataCache(): void {
  studentDataCache.courses = null
  studentDataCache.profile = null
  studentDataCache.actions = null
  studentDataCache.tasks = null
  studentDataCache.insight = null
  studentDataCache.insightSig = null
}