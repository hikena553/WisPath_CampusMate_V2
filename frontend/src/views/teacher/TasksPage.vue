<template>
  <div class="tui-page">
    <SubPageHeader title="今日任务清单" sub="按完成度推进 · 勾选即办结" fallback="/teacher" />

    <div class="tui-content">
      <!-- 桌面端特色头部：清单语义色 + 待办图标。
           本页下方已有「本周完成度」环与四宫格指标，头部不重复挂数字。 -->
      <TuiPageHero
        v-if="!isMobile"
        title="今日任务清单"
        sub="按优先级分组推进，勾选任务即办结"
        :icon="List"
        tone="brand"
      />

      <!-- 桌面端：左窄（240px）右宽的工作台骨架。
           为什么这样分栏：清单页的操作节奏是「先按分组把范围收窄 → 再逐条勾选办结」，
           把分组筛选 + 推进度指标固定收进左栏白卡（sticky），右栏只留清单本体，
           这样滚动清单时筛选与进度不会跟着滚走，信息层级也比纵向堆叠更清楚。 -->
      <div v-if="!isMobile" class="tp-workbench">
        <!-- 左栏：分组筛选 / 完成度环 / 四宫格指标 -->
        <aside class="tp-side">
          <div class="tp-side-card">
            <div class="tp-side-block">
              <div class="tp-side-label">分组筛选</div>
              <div class="tp-filters">
                <button
                  v-for="f in filterOptions"
                  :key="f.value"
                  type="button"
                  class="tp-filter"
                  :class="{ 'is-active': activeFilter === f.value }"
                  @click="switchFilter(f.value)"
                >
                  <span class="tp-filter-label">{{ f.label }}</span>
                  <span class="tp-filter-count">{{ f.count }}</span>
                </button>
              </div>
            </div>

            <div class="tp-side-block">
              <div class="tp-side-label">本周完成度</div>
              <!-- 复用页面已有的完成度环 + 细进度条构件，颜色仍由 --ring-color / --bar-color 驱动 -->
              <div class="tp-rate-row">
                <span class="tui-ring" :style="{ '--pct': doneRate / 100, '--ring-color': ringColor }">
                  <span class="tui-ring-num">{{ doneRate }}%</span>
                </span>
                <div class="tui-progress">
                  <div class="tui-progress-track">
                    <span class="tui-progress-fill" :style="{ '--pct': doneRate / 100, '--bar-color': ringColor }" />
                  </div>
                </div>
              </div>
              <p class="tp-rate-note">完成度 = 本周办结 ÷（本周办结 + 待处理），仅统计你名下尚未关闭的跟进任务。</p>
            </div>

            <!-- 四宫格指标：窄栏里排 2×2，数字语义色与移动端保持一致 -->
            <div class="tp-metrics">
              <div class="tui-stat">
                <span class="tui-stat-num">{{ summary.pending }}</span>
                <span class="tui-stat-label">待处理</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num">{{ summary.today }}</span>
                <span class="tui-stat-label">今日到期</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num is-overdue">{{ summary.overdue }}</span>
                <span class="tui-stat-label">已逾期</span>
              </div>
              <div class="tui-stat">
                <span class="tui-stat-num is-done">{{ summary.done_this_week }}</span>
                <span class="tui-stat-label">本周办结</span>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右栏：清单区（区块标题 + 条数 + 列表本体） -->
        <section class="tp-main">
          <div class="tp-main-head">
            <h3><el-icon><List /></el-icon>任务清单</h3>
            <span class="tp-main-count">{{ summary.total }} 条</span>
          </div>
          <!-- key 绑定 activeFilter：切换分组时重建列表实例，
               让列表按新的 initial-filter 重新取数（列表内部筛选逻辑保持不变） -->
          <TeacherTaskList
            ref="listRef"
            :key="activeFilter"
            :initial-filter="activeFilter"
            @record-care="openCare"
          />
        </section>
      </div>

      <!-- 移动端：沿用原有「完成度分区 + 清单」纵向堆叠，节点、顺序、类名保持原样 -->
      <template v-if="isMobile">
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><Odometer /></el-icon>本周完成度</h3>
          </div>
          <div class="tui-section-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>完成度 = 本周办结 ÷（本周办结 + 待处理），仅统计你名下尚未关闭的跟进任务，用来衡量本周推进节奏。</span>
          </div>
          <div class="tp-rate-row">
            <span class="tui-ring" :style="{ '--pct': doneRate / 100, '--ring-color': ringColor }">
              <span class="tui-ring-num">{{ doneRate }}%</span>
            </span>
            <div class="tui-progress">
              <div class="tui-progress-track">
                <span class="tui-progress-fill" :style="{ '--pct': doneRate / 100, '--bar-color': ringColor }" />
              </div>
            </div>
          </div>
          <div class="tui-stat-row cols-4">
            <div class="tui-stat">
              <span class="tui-stat-num">{{ summary.pending }}</span>
              <span class="tui-stat-label">待处理</span>
            </div>
            <div class="tui-stat">
              <span class="tui-stat-num">{{ summary.today }}</span>
              <span class="tui-stat-label">今日到期</span>
            </div>
            <div class="tui-stat">
              <span class="tui-stat-num is-overdue">{{ summary.overdue }}</span>
              <span class="tui-stat-label">已逾期</span>
            </div>
            <div class="tui-stat">
              <span class="tui-stat-num is-done">{{ summary.done_this_week }}</span>
              <span class="tui-stat-label">本周办结</span>
            </div>
          </div>
        </section>

        <TeacherTaskList ref="listRef" :initial-filter="initialFilter" @record-care="openCare" />
      </template>
    </div>

    <CareRecordDialog
      v-model="careVisible"
      :student-id="careTask?.student_id || 0"
      :student-name="careTask?.student_name"
      :task-id="careTask?.id"
      :task-title="careTask?.title"
      @saved="onCareSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { InfoFilled, Odometer, List } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TeacherTaskList from '@/components/teacher/task/TeacherTaskList.vue'
import CareRecordDialog from '@/components/teacher/care/CareRecordDialog.vue'
import { useResponsive } from '@/composables/useResponsive'
import { getTeacherTaskSummary, type TeacherTask, type TeacherTaskSummary } from '@/api/teacherTask'

defineOptions({ name: 'teacher-tasks' })

const { isMobile } = useResponsive()
const route = useRoute()

const filterMap: Record<string, string> = { overdue: 'overdue', today: 'today', pending: 'pending' }
const rawFilter = Array.isArray(route.query.filter) ? route.query.filter[0] : route.query.filter
const initialFilter = rawFilter ? (filterMap[rawFilter] ?? 'all') : 'all'

const listRef = ref<InstanceType<typeof TeacherTaskList> | null>(null)
const summary = ref<TeacherTaskSummary>({ pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0 })

/** 左栏分组筛选的当前值：初值沿用深链解析出的 initialFilter */
const activeFilter = ref(initialFilter)

/** 左栏分组选项：取值与 TeacherTaskList 的 initialFilter 对齐，条数复用页面已拉取的 summary */
const filterOptions = computed(() => [
  { value: 'all', label: '全部', count: summary.value.total },
  { value: 'today', label: '今日到期', count: summary.value.today },
  { value: 'overdue', label: '已逾期', count: summary.value.overdue },
  { value: 'pending', label: '待处理', count: summary.value.pending },
])

/** 切换分组：仅改 activeFilter，右栏列表通过 :key 重建并按其重新取数 */
function switchFilter(value: string) {
  activeFilter.value = value
}

const careVisible = ref(false)
const careTask = ref<TeacherTask | null>(null)

/** 本周完成度：完全基于现有 summary 字段派生，不新增接口 */
const doneRate = computed(() => {
  const denom = summary.value.done_this_week + summary.value.pending
  if (!denom) return 0
  return Math.min(100, Math.round((summary.value.done_this_week / denom) * 100))
})

const rateTone = computed(() => {
  const r = doneRate.value
  if (r >= 80) return 'is-success'
  if (r >= 50) return 'is-brand'
  if (r >= 25) return 'is-warn'
  return 'is-danger'
})

/** 完成度配色：与 rateTone 同源，供进度条 / 完成度环的 --bar-color、--ring-color 使用 */
const ringColor = computed(() => {
  switch (rateTone.value) {
    case 'is-success': return 'var(--tui-success)'
    case 'is-warn': return 'var(--tui-warn)'
    case 'is-danger': return 'var(--tui-danger)'
    default: return 'var(--tui-brand)'
  }
})

async function loadSummary() {
  try {
    summary.value = await getTeacherTaskSummary()
  } catch {
    /* 指标拉取失败不影响列表 */
  }
}

function openCare(task: TeacherTask) {
  careTask.value = task
  careVisible.value = true
}

function onCareSaved() {
  listRef.value?.reload()
}

onMounted(loadSummary)
</script>

<style scoped>
/* ========== 桌面端双栏工作台（仅 !isMobile 生效，移动端不引用这些类） ========== */
.tp-workbench {
  display: grid;
  /* 左栏固定 240px，右栏吃掉剩余宽度；minmax(0,1fr) 防止长标题把网格撑破 */
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

/* 左栏粘性常驻：滚动容器是 .tui-page，因此 sticky 相对页面滚动生效 */
.tp-side {
  position: sticky;
  top: 12px;
}

/* 左栏白卡：发丝边框 + 极轻投影，内部按「筛选 / 完成度 / 指标」三段排布 */
.tp-side-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 13px 12px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
}

.tp-side-block { display: flex; flex-direction: column; gap: 8px; }
.tp-side-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--tui-text-quiet);
}

/* 分组筛选：纵向列表式按钮，激活项用左缘语义色细线 + 品牌色底强调 */
.tp-filters { display: flex; flex-direction: column; gap: 3px; }

.tp-filter {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  padding: 7px 9px 7px 12px;
  border: none;
  border-radius: var(--tui-radius-xs);
  background: transparent;
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), color 0.15s var(--tui-ease);
}
.tp-filter::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  bottom: 7px;
  width: 2px;
  border-radius: 999px;
  background: transparent;
}
.tp-filter:hover { background: var(--tui-surface-muted); color: var(--tui-text); }
.tp-filter.is-active {
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-weight: 600;
}
.tp-filter.is-active::before { background: var(--tui-brand); }

.tp-filter-count {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text-tertiary);
}
.tp-filter.is-active .tp-filter-count { color: var(--tui-brand-strong); }

/* 完成度：完成度环 + 进度条并排，颜色由 --ring-color / --bar-color 驱动 */
.tp-rate-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
/* 左栏里由 .tp-side-card 的 gap 控距，去掉分区版式的下外边距 */
.tp-side-card .tp-rate-row { margin-bottom: 0; }
.tp-rate-note {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--tui-text-quiet);
}

/* 四宫格指标在 240px 窄栏里排 2×2 */
.tp-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.tui-stat-num.is-overdue { color: var(--tui-danger); }
.tui-stat-num.is-done { color: var(--tui-success); }

/* ========== 右栏清单区：区块标题 + 条数 ========== */
.tp-main {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.tp-main-head {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 2px;
}
.tp-main-head h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
}
.tp-main-head h3 :deep(.el-icon) { font-size: 15px; color: var(--tui-text-tertiary); }
.tp-main-count {
  margin-left: auto;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text-quiet);
}
</style>