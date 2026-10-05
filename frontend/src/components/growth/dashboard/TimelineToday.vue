<template>
  <ol class="tl">
    <li
      v-for="row in rows"
      :key="row.course.id"
      class="tl-row"
      :class="`tl-${row.state}`"
    >
      <span class="tl-time">{{ row.time }}</span>
      <span class="tl-line"><span class="tl-dot"></span></span>
      <div class="tl-body">
        <div class="tl-name">{{ row.course.name }}</div>
        <div class="tl-meta">
          <span>{{ row.course.location }}</span>
          <span v-if="row.course.teacher"> · {{ row.course.teacher }}</span>
        </div>
      </div>
      <span class="tl-tag">{{ row.tag }}</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Course } from '@/types'

const props = defineProps<{
  courses: Course[]
  periodTimes: Record<number, string>
}>()

type State = 'done' | 'active' | 'upcoming'

const now = new Date()
const nowMin = now.getHours() * 60 + now.getMinutes()

function toMin(p: number): number {
  const t = props.periodTimes[p]
  if (!t) return 0
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

const rows = computed(() => {
  const items = props.courses
    .map(course => ({ course, startMin: toMin(course.start_period) }))
    .sort((a, b) => a.startMin - b.startMin)

  let activeIndex = -1
  items.forEach((it, i) => { if (it.startMin <= nowMin) activeIndex = i })

  return items.map((it, i) => {
    const state: State = i < activeIndex ? 'done' : i === activeIndex ? 'active' : 'upcoming'
    const tag = state === 'done' ? '已结束' : state === 'active' ? '进行中' : '待开始'
    return { ...it, state, tag, time: props.periodTimes[it.course.start_period] || '--:--' }
  })
})
</script>

<style scoped>
.tl { list-style: none; margin: 0; padding: 0; }
.tl-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}
.tl-row + .tl-row { border-top: 1px solid var(--gd-border, rgba(0, 0, 0, 0.06)); }
.tl-time {
  flex: none;
  width: 42px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gd-ink-2, #666);
  font-variant-numeric: tabular-nums;
}
.tl-line { flex: none; width: 8px; display: flex; justify-content: center; }
.tl-dot { width: 8px; height: 8px; border-radius: 999px; background: #d5dbe6; }
.tl-body { flex: 1 1 auto; min-width: 0; }
.tl-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--gd-ink, #1a1a2e);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tl-meta {
  font-size: 11.5px;
  color: var(--gd-ink-3, #999);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tl-tag {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--gd-muted, #f6f8fc);
  color: var(--gd-ink-3, #999);
}
.tl-done .tl-name,
.tl-done .tl-time { color: var(--gd-ink-3, #999); }
.tl-done .tl-dot { background: #c8d0dc; }
.tl-active .tl-dot { background: var(--gd-primary, #409eff); box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.18); }
.tl-active .tl-name { color: var(--gd-primary, #409eff); }
.tl-active .tl-tag { background: var(--gd-primary-soft, #eaf3ff); color: var(--gd-primary, #409eff); }
</style>