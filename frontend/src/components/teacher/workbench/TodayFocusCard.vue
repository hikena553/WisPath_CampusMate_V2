<template>
  <div v-loading="loading" class="tf-card">
    <div class="tf-head">
      <div class="tf-title">
        <el-icon class="tf-ic"><Sunrise /></el-icon>
        <span>今日重点</span>
        <span class="tf-title-sub">我的待办与待批事项</span>
      </div>
      <button class="tf-more" @click="emit('navigate', '/teacher/tasks')">
        全部任务<el-icon :size="12"><ArrowRight /></el-icon>
      </button>
    </div>

    <!-- 指标带仅移动端：移动端概览 KPI 只放班级维度统计，个人待办数字落在这里；
         桌面端这些数字已统一收敛到页头主控台的指标带（避免上下两块数字带重复），
         卡片只保留事项清单本身。 -->
    <div v-if="isMobile" class="tf-metrics">
      <button class="tf-metric" @click="emit('navigate', '/teacher/tasks?filter=overdue')">
        <span class="tf-num" :class="{ danger: summary.overdue > 0 }">{{ summary.overdue }}</span>
        <span class="tf-lb">逾期未办</span>
      </button>
      <button class="tf-metric" @click="emit('navigate', '/teacher/tasks?filter=today')">
        <span class="tf-num">{{ summary.today }}</span>
        <span class="tf-lb">今日到期</span>
      </button>
      <button class="tf-metric" @click="emit('navigate', '/teacher/approval')">
        <span class="tf-num" :class="{ warn: pendingLeaves.length > 0 }">{{ pendingLeaves.length }}</span>
        <span class="tf-lb">待批请假</span>
      </button>
    </div>

    <!-- 本周推进进度（仅桌面端）：桌面仪表盘第一屏就能看到「办了多少 / 还剩多少」。
         移动端保持原有卡片结构不变，故不渲染。
         使用教师端统一进度构件（宽度由 --pct 驱动，无过渡动效，不与首页零动效约束冲突） -->
    <div v-if="!isMobile" class="tf-rate">
      <span class="tf-rate-lb">本周推进</span>
      <div class="tui-progress-track">
        <span class="tui-progress-fill" :style="{ '--pct': weekRate }" />
      </div>
      <span class="tf-rate-val">{{ summary.done_this_week }} / {{ weekTotal }}</span>
    </div>

    <div class="tf-list">
      <div v-if="!loading && !rows.length" class="tf-empty">今天没有需要处理的事项</div>
      <button v-for="row in rows" :key="row.key" class="tf-item" @click="emit('navigate', row.link)">
        <span class="tf-tag" :class="`is-${row.kind}`">{{ row.tagText }}</span>
        <span class="tf-item-title">{{ row.title }}</span>
        <span v-if="row.sub" class="tf-item-sub">{{ row.sub }}</span>
        <el-icon :size="13" class="tf-arrow"><ArrowRight /></el-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { ArrowRight, Sunrise } from '@element-plus/icons-vue'
import {
  getTeacherTaskSummary,
  getTeacherTasks,
  type TeacherTask,
  type TeacherTaskSummary,
} from '@/api/teacherTask'
import { getPendingLeaves } from '@/api/leave'
import { useResponsive } from '@/composables/useResponsive'
import type { LeaveRequestOut } from '@/types'

const emit = defineEmits<{ navigate: [path: string] }>()

const { isMobile } = useResponsive()

const loading = ref(false)
const summary = ref<TeacherTaskSummary>({
  pending: 0,
  overdue: 0,
  today: 0,
  done_this_week: 0,
  total: 0,
})
const overdueTasks = ref<TeacherTask[]>([])
const todayTasks = ref<TeacherTask[]>([])
const pendingLeaves = ref<LeaveRequestOut[]>([])

interface FocusRow {
  kind: 'overdue' | 'today' | 'leave'
  key: string
  title: string
  sub: string
  link: string
  tagText: string
}

/** 逾期任务 → 今日任务 → 待批请假，按 id 去重后取前 5 条 */
const rows = computed<FocusRow[]>(() => {
  const out: FocusRow[] = []
  const seenTask = new Set<number>()
  for (const t of overdueTasks.value) {
    if (seenTask.has(t.id)) continue
    seenTask.add(t.id)
    out.push({
      kind: 'overdue',
      key: `t-${t.id}`,
      title: t.title,
      sub: t.student_name,
      link: `/teacher/tasks?filter=overdue&task=${t.id}`,
      tagText: '逾期',
    })
  }
  for (const t of todayTasks.value) {
    if (seenTask.has(t.id)) continue
    seenTask.add(t.id)
    out.push({
      kind: 'today',
      key: `t-${t.id}`,
      title: t.title,
      sub: t.student_name,
      link: `/teacher/tasks?filter=today&task=${t.id}`,
      tagText: '今日',
    })
  }
  const seenLeave = new Set<number>()
  for (const l of pendingLeaves.value.slice(0, 3)) {
    if (seenLeave.has(l.id)) continue
    seenLeave.add(l.id)
    out.push({
      kind: 'leave',
      key: `l-${l.id}`,
      title: `${l.student_name} 提交请假申请`,
      sub: `${l.start_date} ~ ${l.end_date}`,
      link: '/teacher/approval',
      tagText: '请假',
    })
  }
  return out.slice(0, 5)
})

/** 本周推进进度：已办结占总量的比例（总量 = 本周办结 + 当前待处理） */
const weekTotal = computed(() => summary.value.done_this_week + summary.value.pending)
const weekRate = computed(() => (weekTotal.value ? summary.value.done_this_week / weekTotal.value : 0))

async function load() {
  loading.value = true
  try {
    const [s, od, td, lv] = await Promise.allSettled([
      getTeacherTaskSummary(),
      getTeacherTasks({ due: 'overdue', limit: 5 }),
      getTeacherTasks({ due: 'today', limit: 5 }),
      getPendingLeaves(),
    ])
    if (s.status === 'fulfilled') summary.value = s.value
    if (od.status === 'fulfilled') overdueTasks.value = od.value
    if (td.status === 'fulfilled') todayTasks.value = td.value
    if (lv.status === 'fulfilled') pendingLeaves.value = lv.value
  } catch {
    // 首页卡片各自容错，单块失败不影响其它
  } finally {
    loading.value = false
  }
}

onMounted(load)
onActivated(load)
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
  gap: 14px;
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
  background: color-mix(in srgb, #2563eb 12%, #fff);
  color: #2563eb;
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
.tf-more:hover { color: var(--tui-brand); }

.tf-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.tf-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-start;
  min-width: 0;
  background: var(--tui-surface-muted);
  border: none;
  border-radius: var(--tui-radius-xs);
  padding: 9px 12px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.tf-metric:hover { background: var(--tui-surface-sunken); }
.tf-num {
  font-size: 20px;
  font-weight: 600;
  color: var(--tui-text);
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
}
.tf-num.danger { color: #d92d20; }
.tf-num.warn { color: #b54708; }
.tf-lb {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}

/* 本周推进进度行 */
.tf-rate {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tf-rate-lb {
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.tf-rate-val {
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--tui-text-secondary);
  font-variant-numeric: tabular-nums;
}

.tf-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.tf-empty {
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  padding: 6px 0;
}
.tf-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  border-radius: var(--tui-radius-xs);
  background: var(--tui-surface-muted);
  border: 1px solid var(--tui-border);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.tf-item:hover { border-color: var(--tui-brand); }
.tf-tag {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  padding: 1px 7px;
  border-radius: 999px;
}
.tf-tag.is-overdue { background: #fef3f2; color: #d92d20; }
.tf-tag.is-today { background: #eff4ff; color: #1d4ed8; }
.tf-tag.is-leave { background: #fffaeb; color: #b54708; }
.tf-item-title {
  font-size: 12.5px;
  color: var(--tui-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tf-item-sub {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}
.tf-arrow {
  margin-left: auto;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}
</style>