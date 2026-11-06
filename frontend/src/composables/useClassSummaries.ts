import { ref, computed, type Ref } from 'vue'
import { getClassGroups } from '@/api/organization'
import type { StudentSummary } from '@/api/teacher'
import type { ClassGroup } from '@/types'

/**
 * 学生名单的「班级视角」：把教师名下的学生按班级聚合，供 L1 班级总览使用。
 *
 * 为什么在前端聚合而不是让后端算：
 * 1. 教师名下学生本来就要一次性全量拉（搜索、数据分析都用这份），再按班级分组不增加任何请求；
 * 2. 班级卡上的「重点关注 N 人」与点进去名单里的行来自**同一份数组**，
 *    不会出现「卡片说 3 人、进去只有 2 人」这种两次独立统计导致的对不上；
 * 3. 后端 `GET /teacher/students` 已支持 class_group_id，但逐个班拉会变成 N 次请求，
 *    且无法在 L1 一次性展示全部分布。
 *
 * 一旦教师带班数增长到前端吃不消（本模型下一个教师的学生规模远未到），
 * 只需把 `buildClassSummaries` 换成后端聚合接口的返回，组件层不用改。
 */

/** 一个学生的分诊档位：只按危机等级分，口径单一，避免前后端各算一套 */
export type TriageKey = 'severe' | 'moderate' | 'calm'

export interface ClassSummary {
  /** 班级 id；未分班学生归入 id === 0 的虚拟班级 */
  id: number
  name: string
  majorName: string | null
  collegeName: string | null
  grade: number | null
  /** 本班学生数（真实归属，不是 ClassGroup.student_count 冗余字段） */
  total: number
  /** 必须今天处理：最新危机为 severe */
  severe: number
  /** 这周要跟进：最新危机为 moderate */
  moderate: number
  /** 状态平稳：mild / 无预警 */
  calm: number
  /** 重点关注人数 = severe + moderate */
  focus: number
  /** 本班最近一条预警时间（ISO），无预警为 null */
  latestCrisisTime: string | null
  /** 是否未分班兜底卡 */
  unassigned: boolean
}

/** 未分班学生的虚拟班级 id（后端 class_group_id 为 NULL 时） */
export const UNASSIGNED_ID = 0

/** 判定学生档位。单一入口，卡片计数与分层列表都调它，保证口径永远一致。 */
export function triageOf(s: Pick<StudentSummary, 'crisis_level'>): TriageKey {
  if (s.crisis_level === 'severe') return 'severe'
  if (s.crisis_level === 'moderate') return 'moderate'
  return 'calm'
}

/**
 * 把学生数组按班级聚合成 ClassSummary[]。
 *
 * 排序：重点关注人数倒序 → 学生总数倒序 → 班级名。让「有事的班」浮到最上面，
 * 未分班卡与普通班级同等参与排序。
 */
export function buildClassSummaries(
  students: (StudentSummary & { class_group_id?: number | null })[],
  classGroups: ClassGroup[],
): ClassSummary[] {
  const metaMap = new Map<number, ClassGroup>()
  for (const cg of classGroups) metaMap.set(cg.id, cg)

  const buckets = new Map<number, ClassSummary>()

  const ensure = (id: number): ClassSummary => {
    let item = buckets.get(id)
    if (item) return item
    if (id === UNASSIGNED_ID) {
      item = {
        id: UNASSIGNED_ID,
        name: '未分班学生',
        majorName: null,
        collegeName: null,
        grade: null,
        total: 0,
        severe: 0,
        moderate: 0,
        calm: 0,
        focus: 0,
        latestCrisisTime: null,
        unassigned: true,
      }
    } else {
      const cg = metaMap.get(id)
      item = {
        id,
        name: cg?.name || `班级 #${id}`,
        majorName: cg?.major_name ?? null,
        collegeName: cg?.college_name ?? null,
        grade: cg?.grade ?? null,
        total: 0,
        severe: 0,
        moderate: 0,
        calm: 0,
        focus: 0,
        latestCrisisTime: null,
        unassigned: false,
      }
    }
    buckets.set(id, item)
    return item
  }

  for (const s of students) {
    const id = s.class_group_id ?? UNASSIGNED_ID
    const bucket = ensure(id)
    bucket.total += 1
    bucket[triageOf(s)] += 1
    const t = s.latest_crisis_time
    // 只在学生「真的带预警」时参与最近时间统计，避免把 null 当成最新
    if (t && (bucket.latestCrisisTime === null || t > bucket.latestCrisisTime)) {
      bucket.latestCrisisTime = t
    }
  }

  const list = [...buckets.values()]
  for (const c of list) {
    c.focus = c.severe + c.moderate
  }
  return list.sort((a, b) => {
    if (b.focus !== a.focus) return b.focus - a.focus
    if (b.total !== a.total) return b.total - a.total
    return a.name.localeCompare(b.name, 'zh-Hans-CN')
  })
}

/**
 * 拉一次班级字典并保持。班级字典很长（全校），只在挂载时取一次，
 * 教师端本身带 keep-alive + 实时刷新，字典变化极少，不需要跟着学生数据一起轮询。
 */
export function useClassDirectory() {
  const classGroups = ref<ClassGroup[]>([])
  let loading = false
  let loaded = false

  async function load(force = false) {
    if (loading || (loaded && !force)) return
    loading = true
    try {
      classGroups.value = await getClassGroups()
      loaded = true
    } catch {
      // 班级字典拉不到不阻塞名单：退回只显示「班级 #id」
    } finally {
      loading = false
    }
  }

  return { classGroups, load }
}

/** 把「学生数组 + 班级字典」组装成班级总览，组件里直接消费 */
export function useClassSummaries(
  students: Ref<(StudentSummary & { class_group_id?: number | null })[]>,
  classGroups: Ref<ClassGroup[]>,
) {
  return computed(() => buildClassSummaries(students.value, classGroups.value))
}
