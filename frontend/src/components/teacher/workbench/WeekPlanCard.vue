<template>
  <div v-loading="loading" class="wb-card">
    <div class="wb-head">
      <div class="wb-title">
        <el-icon class="wb-ic purple"><Calendar /></el-icon>
        <span>本周计划</span>
        <span class="wb-range">{{ rangeLabel }}</span>
      </div>
      <button class="wb-more" @click="emit('open-schedule')">
        去安排<el-icon :size="12"><ArrowRight /></el-icon>
      </button>
    </div>

    <div class="wk-list">
      <div v-for="d in weekDays" :key="d.key" class="wk-row" :class="{ today: d.isToday }">
        <div class="wk-date">
          <span class="wk-week">{{ d.weekLabel }}</span>
          <span class="wk-day">{{ d.dayNum }}</span>
        </div>
        <div class="wk-items">
          <template v-if="d.items.length">
            <span
              v-for="it in d.items"
              :key="it.id"
              class="wk-chip"
              :class="[`u-${it.urgency}`, { done: it.completed }]"
              :title="it.content"
            >{{ it.content }}</span>
          </template>
          <span v-else class="wk-none">无安排</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { ArrowRight, Calendar } from '@element-plus/icons-vue'
import { getTeacherSchedules, type ScheduleItem } from '@/api/teacher'

const emit = defineEmits<{ 'open-schedule': [] }>()

const loading = ref(false)
const items = ref<ScheduleItem[]>([])

const WEEK_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function ymd(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 本周一 00:00 */
const monday = computed(() => {
  const now = new Date()
  const wd = now.getDay() || 7
  const d = new Date(now)
  d.setDate(now.getDate() - (wd - 1))
  d.setHours(0, 0, 0, 0)
  return d
})

const weekDays = computed(() => {
  const todayKey = ymd(new Date())
  return WEEK_LABELS.map((weekLabel, i) => {
    const d = new Date(monday.value)
    d.setDate(monday.value.getDate() + i)
    const key = ymd(d)
    return {
      key,
      weekLabel,
      dayNum: d.getDate(),
      isToday: key === todayKey,
      items: items.value.filter((it) => (it.date || '').slice(0, 10) === key),
    }
  })
})

const rangeLabel = computed(() => {
  const end = new Date(monday.value)
  end.setDate(monday.value.getDate() + 6)
  const f = (d: Date) => `${d.getMonth() + 1}/${d.getDate()}`
  return `${f(monday.value)} - ${f(end)}`
})

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    // 一周可能跨月，取涉及到的月份并合并
    const start = monday.value
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    const months = new Set<string>([
      `${start.getFullYear()}-${start.getMonth()}`,
      `${end.getFullYear()}-${end.getMonth()}`,
    ])
    const results = await Promise.all(
      [...months].map((m) => {
        const [y, mo] = m.split('-').map(Number)
        return getTeacherSchedules(y, mo + 1)
      })
    )
    const merged = results.flat()
    const seen = new Set<number>()
    items.value = merged.filter((it) => (seen.has(it.id) ? false : seen.add(it.id)))
  } catch {
    // 容错：本块失败不影响其它工作台卡片
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
.wb-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  padding: 16px;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 172px;
}

.wb-head {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: space-between;
}
.wb-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: #2b3245;
}
.wb-ic {
  color: #2563eb;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
  font-size: 13px;
}
.wb-ic.purple {
  background: color-mix(in srgb, #7c3aed 12%, #fff);
  color: #7c3aed;
}
.wb-range {
  font-size: 11.5px;
  font-weight: 400;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.wb-more {
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
}
.wb-more:hover { color: var(--tui-brand); }

.wk-list {
  display: flex;
  flex-direction: column;
}
.wk-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
}
.wk-row.today { background: #eff4ff; }
.wk-date {
  display: flex;
  align-items: baseline;
  gap: 5px;
  width: 58px;
  flex-shrink: 0;
}
.wk-week {
  font-size: 12px;
  color: var(--tui-text-secondary);
}
.wk-row.today .wk-week { color: #2563eb; font-weight: 600; }
.wk-day {
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.wk-items {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-width: 0;
}
.wk-none {
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.wk-chip {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-secondary);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wk-chip.u-important { background: #fffaeb; color: #b54708; }
.wk-chip.u-urgent { background: #fef3f2; color: #d92d20; }
.wk-chip.done { opacity: 0.55; text-decoration: line-through; }
</style>