<template>
  <div v-loading="loading" class="tf-card">
    <div class="tf-head">
      <div class="tf-title">
        <el-icon class="tf-ic"><Sunrise /></el-icon>
        <span>今日重点</span>
        <span class="tf-title-sub">先处理最要紧的一件事</span>
      </div>
      <button class="tf-more" @click="emit('navigate', '/teacher/tasks')">
        全部任务<el-icon :size="12"><ArrowRight /></el-icon>
      </button>
    </div>

    <!-- 今日重点 = 待批请假 + 未闭环心理预警 + 逾期任务，按学生聚合后的最高优先级事项 -->
    <div class="tf-focus">
      <div class="tf-num-wrap">
        <span class="tf-num">{{ focusCount }}</span>
        <span class="tf-num-lb">项待办</span>
      </div>
      <div class="tf-focus-body">
        <span class="tf-focus-title">优先处理</span>
        <span class="tf-focus-sub">{{ priorityText }}</span>
      </div>
      <button v-if="focusLink" class="tf-go" type="button" @click="emit('navigate', focusLink)">
        立即处理
      </button>
    </div>

    <div v-if="breakdown" class="tf-breakdown">{{ breakdown }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { ArrowRight, Sunrise } from '@element-plus/icons-vue'
import { getTeacherTasks, type TeacherTask } from '@/api/teacherTask'
import { getPendingLeaves } from '@/api/leave'
import { getAlerts } from '@/api/crisis'
import type { CrisisAlert, LeaveRequestOut } from '@/types'

const emit = defineEmits<{ navigate: [path: string] }>()

const loading = ref(false)
const overdueTasks = ref<TeacherTask[]>([])
const pendingLeaves = ref<LeaveRequestOut[]>([])
const alerts = ref<CrisisAlert[]>([])

interface FocusItem {
  kind: 'alert' | 'leave' | 'overdue'
  key: string
  student: string
  /** 该事项的动作名，如「请假审批」「心理跟进」 */
  action: string
  title: string
  link: string
  /** 越大越优先：高危预警 > 逾期任务 > 待批请假 */
  weight: number
}

/** 预警等级权重：sever=高危 > moderate=中度 > mild=轻度；normal 不计入今日重点 */
const LEVEL_WEIGHT: Record<string, number> = { severe: 6, moderate: 4, mild: 3 }

const items = computed<FocusItem[]>(() => {
  const out: FocusItem[] = []

  for (const a of alerts.value) {
    if (a.resolved) continue
    const weight = LEVEL_WEIGHT[a.level]
    if (!weight) continue
    out.push({
      kind: 'alert',
      key: `a-${a.id}`,
      student: a.student_name,
      action: '心理跟进',
      title: a.summary,
      link: `/teacher/crisis?student_id=${a.student_id}&alert_id=${a.id}`,
      weight,
    })
  }

  for (const t of overdueTasks.value) {
    out.push({
      kind: 'overdue',
      key: `t-${t.id}`,
      student: t.student_name || '',
      action: '逾期任务',
      title: t.title,
      link: `/teacher/tasks?filter=overdue&task=${t.id}`,
      weight: 5,
    })
  }

  for (const l of pendingLeaves.value) {
    out.push({
      kind: 'leave',
      key: `l-${l.id}`,
      student: l.student_name,
      action: '请假审批',
      title: `${l.student_name} 提交请假申请`,
      link: '/teacher/approval',
      weight: 2,
    })
  }

  return out
})

const focusCount = computed(() => items.value.length)

/** 人均优先级：把同一学生的事项合起来，取分数最高的那位学生作为「优先处理」对象 */
const priority = computed(() => {
  const groups = new Map<string, { name: string; score: number; actions: string[]; first: FocusItem }>()
  for (const item of items.value) {
    const name = item.student || ''
    if (!name) continue
    const g = groups.get(name)
    if (g) {
      g.score += item.weight
      if (!g.actions.includes(item.action)) g.actions.push(item.action)
    } else {
      groups.set(name, {
        name,
        score: item.weight,
        actions: [item.action],
        first: item,
      })
    }
  }
  let top: { name: string; score: number; actions: string[]; first: FocusItem } | null = null
  for (const g of groups.values()) {
    if (!top || g.score > top.score) top = g
  }
  return top
})

const priorityText = computed(() => {
  const p = priority.value
  if (!p) {
    // 没有学生维度的事项（纯个人任务）时直接展示分数最高的那条
    const first = [...items.value].sort((a, b) => b.weight - a.weight)[0]
    return first ? first.title : '今天没有需要优先处理的事项'
  }
  return `${p.name}的${p.actions.join('与')}`
})

const focusLink = computed(() => {
  const p = priority.value
  if (p) return p.first.link
  return [...items.value].sort((a, b) => b.weight - a.weight)[0]?.link || ''
})

/** 口径说明：让「N 项」可被拆开核对，不做无来源的大数字 */
const breakdown = computed(() => {
  const count = (kind: FocusItem['kind']) => items.value.filter((i) => i.kind === kind).length
  const parts: string[] = []
  const lv = count('leave')
  const al = count('alert')
  const od = count('overdue')
  if (lv) parts.push(`${lv} 条请假审批`)
  if (al) parts.push(`${al} 条心理预警跟进`)
  if (od) parts.push(`${od} 项逾期任务`)
  return parts.join(' · ')
})

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    const [od, lv, al] = await Promise.allSettled([
      getTeacherTasks({ due: 'overdue', limit: 100 }),
      getPendingLeaves(),
      getAlerts(false),
    ])
    if (od.status === 'fulfilled') overdueTasks.value = od.value
    if (lv.status === 'fulfilled') pendingLeaves.value = lv.value
    if (al.status === 'fulfilled') alerts.value = al.value
  } catch {
    // 首页卡片各自容错，单块失败不影响其它
  } finally {
    loading.value = false
  }
}

onMounted(load)
/** 从其它页签切回首页时静默刷新：数据已在，不再亮 loading，避免切页瞬间闪一下 */
let activatedOnce = false
onActivated(() => {
  if (activatedOnce) load(true)
  else activatedOnce = true
})
defineExpose({ reload: load })
</script>

<style scoped>
.tf-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  box-shadow: none;
  padding: 16px;
  /* 移动端首页直接把这张卡插在文档流里，需要自带下间距；桌面端由 .dash-cell 统一归零 */
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.tf-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.tf-title > span:nth-child(2) {
  font-size: 14px;
  font-weight: 600;
  color: #2b3245;
}
/* 卡头图标块：22×22 圆角色块（与本周计划 / 工作量 / 成长带同一套卡头语言） */
.tf-ic {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--tui-surface-muted);
  color: #475467;
  font-size: 13px;
  flex-shrink: 0;
}
.tf-title-sub {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tf-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  background: none;
  padding: 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  cursor: pointer;
  font-family: inherit;
  flex-shrink: 0;
}
.tf-more:hover { color: var(--tui-text-secondary); }

/* 今日重点主体：左侧数字 + 中间优先事项 + 右侧动作，单行读完 */
.tf-focus {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 12px;
  border-radius: var(--tui-radius-xs);
  border: 1px solid var(--tui-border);
  background: var(--tui-surface-muted);
}
.tf-num-wrap {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 46px;
  padding-right: 12px;
  border-right: 1px solid var(--tui-border);
}
.tf-num {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.05;
  color: #1f2329;
  font-variant-numeric: tabular-nums;
}
.tf-num-lb {
  margin-top: 2px;
  font-size: 10.5px;
  color: var(--tui-text-quiet);
}
.tf-focus-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.tf-focus-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--tui-text-quiet);
}
.tf-focus-sub {
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.45;
  color: #2b3245;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
/* 主操作：黑底白字，避开蓝色实心按钮 */
.tf-go {
  flex-shrink: 0;
  align-self: center;
  padding: 7px 13px;
  border: none;
  border-radius: 8px;
  background: #1f2329;
  color: #fff;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
}
.tf-go:active { background: #101318; }

.tf-breakdown {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  padding-left: 1px;
}
</style>
