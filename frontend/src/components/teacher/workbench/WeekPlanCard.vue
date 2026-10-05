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

async function load() {
  loading.value = true
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
onActivated(load)
defineExpose({ reload: load })
</script>

<style scoped>
.wb-card {
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 172px;
}

.wb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wb-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: #101828;
}
.wb-ic { color: #2563eb; }
.wb-ic.purple { color: #7c3aed; }
.wb-range {
  font-size: 11.5px;
  font-weight: 400;
  color: #98a2b3;
}
.wb-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: #667085;
  cursor: pointer;
  font-family: inherit;
}
.wb-more:hover { color: #2563eb; }

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
  width: 66px;
  flex-shrink: 0;
}
.wk-week {
  font-size: 12px;
  color: #667085;
}
.wk-row.today .wk-week { color: #2563eb; font-weight: 600; }
.wk-day {
  font-size: 12px;
  color: #98a2b3;
}
.wk-items {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-width: 0;
}
.wk-none {
  font-size: 12px;
  color: #d0d5dd;
}
.wk-chip {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f2f4f7;
  color: #475467;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wk-chip.u-important { background: #fffaeb; color: #b54708; }
.wk-chip.u-urgent { background: #fef3f2; color: #d92d20; }
.wk-chip.done { opacity: 0.55; text-decoration: line-through; }
</style>