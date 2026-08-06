<template>
  <div class="grade-page">
    <div class="stats-row">
      <div class="stat-box" v-for="s in statItems" :key="s.label">
        <span class="stat-num" :style="{ color: s.color }">{{ s.value }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="grade-tabs">
      <el-tab-pane label="成绩详情" name="grades">
        <div v-for="sem in semesters" :key="sem" class="semester-block">
          <div class="semester-header">
            <span class="semester-title">{{ sem }}</span>
            <div class="semester-stats">
              <span>{{ semStats[sem]?.count }} 门</span>
              <span>均分 <b :style="{ color: avgColor(semStats[sem]?.avg) }">{{ semStats[sem]?.avg }}</b></span>
              <span>均绩 <b>{{ semStats[sem]?.gpa }}</b></span>
              <span>学分 <b>{{ semStats[sem]?.credits }}</b></span>
            </div>
          </div>
          <div class="grade-grid">
            <div v-for="g in gradesBySem[sem]" :key="g.id" class="grade-card" :class="scoreLevel(g.score)">
              <div class="gc-top">
                <span class="gc-name">{{ g.course_name }}</span>
                <span class="gc-score">{{ g.score }}</span>
              </div>
              <div class="gc-meta">
                <span>绩点 {{ g.gpa }}</span>
                <span>学分 {{ g.credit }}</span>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-if="!grades.length" description="暂无成绩数据" />
      </el-tab-pane>

      <el-tab-pane label="考试安排" name="exams">
        <div v-if="exams.length" class="exam-list">
          <div v-if="upcomingExams.length" class="exam-group">
            <div class="exam-group-title"><el-icon><WarningFilled /></el-icon> 即将考试</div>
            <div v-for="e in upcomingExams" :key="e.id" class="exam-card">
              <div class="ec-left">
                <div class="ec-date">{{ formatDate(e.exam_date) }}</div>
                <div class="ec-time">{{ e.start_time?.slice(0, 5) }} - {{ e.end_time?.slice(0, 5) }}</div>
              </div>
              <div class="ec-body">
                <div class="ec-name">{{ e.course_name }}</div>
                <div class="ec-location"><el-icon><Location /></el-icon> {{ e.location }}</div>
              </div>
            </div>
          </div>
          <div v-if="pastExams.length" class="exam-group">
            <div class="exam-group-title"><el-icon><CircleCheckFilled /></el-icon> 已结束</div>
            <div v-for="e in pastExams" :key="e.id" class="exam-card past">
              <div class="ec-left">
                <div class="ec-date">{{ formatDate(e.exam_date) }}</div>
                <div class="ec-time">{{ e.start_time?.slice(0, 5) }} - {{ e.end_time?.slice(0, 5) }}</div>
              </div>
              <div class="ec-body">
                <div class="ec-name">{{ e.course_name }}</div>
                <div class="ec-location"><el-icon><Location /></el-icon> {{ e.location }}</div>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无考试安排" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getGrades, getExams } from '@/api/academic'
import { Location, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import type { Grade, Exam } from '@/types'

const activeTab = ref('grades')
const grades = ref<Grade[]>([])
const exams = ref<Exam[]>([])

const semesters = computed(() => [...new Set(grades.value.map(g => g.semester))].sort().reverse())

const gradesBySem = computed(() => {
  const map: Record<string, Grade[]> = {}
  for (const g of grades.value) {
    if (!map[g.semester]) map[g.semester] = []
    map[g.semester].push(g)
  }
  return map
})

const semStats = computed(() => {
  const stats: Record<string, { count: number; avg: number; gpa: string; credits: number }> = {}
  for (const [sem, gs] of Object.entries(gradesBySem.value)) {
    const count = gs.length
    const scores = gs.filter(g => g.score != null).map(g => g.score)
    const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
    const gpa = gs.length ? (gs.reduce((s, g) => s + (g.gpa || 0), 0) / gs.length).toFixed(2) : '0.00'
    const credits = gs.reduce((s, g) => s + (g.credit || 0), 0)
    stats[sem] = { count, avg, gpa, credits }
  }
  return stats
})

const stats = computed(() => {
  const gs = grades.value
  const totalCredits = gs.reduce((s, g) => s + (g.credit || 0), 0)
  const avgGpa = gs.length ? gs.reduce((s, g) => s + (g.gpa || 0), 0) / gs.length : 0
  const scores = gs.filter(g => g.score != null).map(g => g.score)
  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
  const highCount = scores.filter(s => s >= 90).length
  return { courses: gs.length, totalCredits, avgGpa, avgScore, highCount }
})

const statItems = computed(() => [
  { label: '课程总数', value: stats.value.courses, color: '#409eff' },
  { label: '总学分', value: stats.value.totalCredits, color: '#67c23a' },
  { label: '平均绩点', value: stats.value.avgGpa.toFixed(2), color: '#e6a23c' },
  { label: '平均成绩', value: stats.value.avgScore, color: '#f56c6c' },
  { label: '优秀课程', value: stats.value.highCount, color: '#9b59b6' },
])

const upcomingExams = computed(() => {
  const now = new Date()
  return exams.value.filter(e => !e.exam_date || new Date(e.exam_date) >= now)
    .sort((a, b) => (a.exam_date || '').localeCompare(b.exam_date || ''))
})

const pastExams = computed(() => {
  const now = new Date()
  return exams.value.filter(e => e.exam_date && new Date(e.exam_date) < now)
    .sort((a, b) => (b.exam_date || '').localeCompare(a.exam_date || ''))
})

function scoreLevel(s: number) {
  if (s >= 90) return 'level-a'
  if (s >= 80) return 'level-b'
  if (s >= 70) return 'level-c'
  if (s >= 60) return 'level-d'
  return 'level-f'
}

function avgColor(s?: number) {
  if (!s) return '#999'
  if (s >= 90) return '#67c23a'
  if (s >= 80) return '#409eff'
  if (s >= 70) return '#e6a23c'
  return '#f56c6c'
}

function formatDate(d: string) {
  if (!d) return ''
  const parts = d.split('-')
  return parts[1] + '/' + parts[2]
}

onMounted(async () => {
  grades.value = await getGrades() as any
  exams.value = await getExams() as any
})
</script>

<style scoped>
.grade-page { max-width: 1200px; margin: 0 auto; padding: 8px 0 24px; height: 100%; overflow-y: auto; box-sizing: border-box; }

/* 统计数据 */
.stats-row { display: flex; gap: 12px; margin-bottom: 20px; }
.stat-box {
  flex: 1; background: #fff; border-radius: 12px; padding: 14px 10px;
  text-align: center; border: 1px solid rgba(0,0,0,.04); box-shadow: 0 2px 8px rgba(0,0,0,.03);
}
.stat-num { display: block; font-size: 26px; font-weight: 700; }
.stat-label { display: block; font-size: 12px; color: #999; margin-top: 2px; }

/* 标签页 */
.grade-tabs { background: transparent; }
:deep(.el-tabs__item) { font-size: 14px; }

/* 学期 */
.semester-block { margin-bottom: 24px; }
.semester-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0 12px; border-bottom: 2px solid #409eff; margin-bottom: 12px;
}
.semester-title { font-size: 15px; font-weight: 700; color: #1a1a2e; }
.semester-stats { display: flex; gap: 14px; font-size: 12px; color: #999; }
.semester-stats b { color: #1a1a2e; font-weight: 600; }

/* 成绩网格 */
.grade-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
.grade-card {
  background: #fff; border-radius: 10px; padding: 14px 16px;
  border: 1px solid rgba(0,0,0,.04); box-shadow: 0 1px 6px rgba(0,0,0,.02);
  transition: transform .15s;
  border-left: 4px solid #ddd;
}
.grade-card:hover { transform: translateY(-2px); }
.grade-card.level-a { border-left-color: #67c23a; }
.grade-card.level-b { border-left-color: #409eff; }
.grade-card.level-c { border-left-color: #e6a23c; }
.grade-card.level-d { border-left-color: #f56c6c; }
.grade-card.level-f { border-left-color: #c03636; }
.gc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.gc-name { font-size: 14px; font-weight: 600; color: #1a1a2e; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.gc-score { font-size: 22px; font-weight: 700; flex-shrink: 0; margin-left: 8px; }
.level-a .gc-score { color: #67c23a; }
.level-b .gc-score { color: #409eff; }
.level-c .gc-score { color: #e6a23c; }
.level-d .gc-score { color: #f56c6c; }
.level-f .gc-score { color: #c03636; }
.gc-meta { display: flex; gap: 12px; font-size: 12px; color: #999; }

/* 考试 */
.exam-list { display: flex; flex-direction: column; gap: 20px; }
.exam-group { }
.exam-group-title {
  font-size: 15px; font-weight: 700; color: #1a1a2e;
  padding-bottom: 12px; margin-bottom: 10px; border-bottom: 2px solid #e8e8e8;
  display: flex; align-items: center; gap: 6px;
}
.exam-card {
  display: flex; gap: 16px; background: #fff; border-radius: 12px; padding: 14px 18px;
  border: 1px solid rgba(0,0,0,.04); box-shadow: 0 1px 6px rgba(0,0,0,.02);
  transition: transform .15s; margin-bottom: 8px;
}
.exam-card:hover { transform: translateY(-1px); }
.exam-card.past { opacity: .6; }
.ec-left { text-align: center; flex-shrink: 0; width: 80px; padding: 4px 0; }
.ec-date { font-size: 20px; font-weight: 700; color: #409eff; }
.ec-time { font-size: 12px; color: #999; margin-top: 2px; }
.ec-body { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 4px; }
.ec-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.ec-location { font-size: 13px; color: #888; display: flex; align-items: center; gap: 4px; }

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .grade-page { padding: 8px 10px 80px; }
  .stats-row { gap: 6px; margin-bottom: 14px; }
  .stat-box { padding: 10px 6px; }
  .stat-num { font-size: 18px; }
  .stat-label { font-size: 10px; }
  :deep(.el-tabs__item) { font-size: 13px; }
  .semester-header { flex-direction: column; gap: 6px; align-items: flex-start; padding: 6px 0 10px; }
  .semester-stats { gap: 8px; font-size: 11px; }
  .grade-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .grade-card { padding: 10px 12px; }
  .gc-name { font-size: 13px; }
  .gc-score { font-size: 18px; }
  .gc-meta { gap: 8px; font-size: 11px; }
  .exam-card { padding: 12px 14px; gap: 12px; }
  .ec-left { width: 60px; }
  .ec-date { font-size: 16px; }
  .ec-name { font-size: 14px; }
}
</style>
