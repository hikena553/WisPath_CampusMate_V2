<template>
  <div class="tui-page">
    <SubPageHeader title="人文关怀中心" sub="关怀日历 · 家访台账 · 正向激励" fallback="/teacher/more">
      <template #right>
        <el-button text circle aria-label="新增事项" @click="eventVisible = true">
          <el-icon :size="19"><Plus /></el-icon>
        </el-button>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">人文关怀中心</h2>
          <p class="tui-header-sub">关怀日历 · 家访台账 · 正向激励，让关心有迹可循</p>
        </div>
        <div class="tui-header-actions">
          <el-button round :icon="Refresh" :loading="genLoading" @click="handleGenerate">自动生成</el-button>
          <el-button round :icon="ChatDotRound" @click="helpVisible = true">匿名求助</el-button>
          <el-button type="primary" round :icon="Plus" @click="eventVisible = true">新增事项</el-button>
        </div>
      </header>

      <!-- 移动端高频操作：页头仅保留「新增事项」图标按钮 -->
      <div v-if="isMobile" class="tui-actions cc-mobile-ops">
        <el-button round :icon="Refresh" :loading="genLoading" @click="handleGenerate">自动生成</el-button>
        <el-button round :icon="ChatDotRound" @click="helpVisible = true">匿名求助</el-button>
      </div>

      <!-- 概览 -->
      <div class="tui-stat-row">
        <div class="tui-stat">
          <span class="tui-stat-num">{{ overview.event_count }}</span>
          <span class="tui-stat-label">本月关怀事项</span>
        </div>
        <div class="tui-stat">
          <span class="tui-stat-num">{{ overview.visit_count }}</span>
          <span class="tui-stat-label">本月家访</span>
        </div>
        <div class="tui-stat">
          <span class="tui-stat-num">{{ overview.praise_count }}</span>
          <span class="tui-stat-label">本月激励</span>
        </div>
      </div>

      <div class="tui-seg-wrap">
        <TuiSegmented
          v-model="tab"
          :options="[
            { value: 'calendar', label: '关怀日历', count: events.length },
            { value: 'visits', label: '家访记录', count: visits.length },
            { value: 'praises', label: '正向激励', count: praises.length },
          ]"
        />
      </div>

      <!-- 关怀日历 -->
      <template v-if="tab === 'calendar'">
        <div class="cc-cal-head">
          <el-button text circle @click="shiftMonth(-1)"><el-icon><ArrowLeft /></el-icon></el-button>
          <span class="cc-cal-title">{{ calYear }} 年 {{ calMonth }} 月</span>
          <el-button text circle @click="shiftMonth(1)"><el-icon><ArrowRight /></el-icon></el-button>
        </div>

        <div class="cc-week">
          <span v-for="w in WEEK_LABELS" :key="w">{{ w }}</span>
        </div>
        <div class="cc-grid">
          <div v-for="(cell, i) in calendarCells" :key="i" class="cc-cell"
            :class="{ muted: !cell.inMonth, today: cell.isToday }">
            <div class="cc-cell-top">
              <span class="cc-day">{{ cell.day }}</span>
              <span v-if="cell.events.length" class="cc-dot-count">{{ cell.events.length }}</span>
            </div>
            <div class="cc-cell-events">
              <span v-for="e in cell.events.slice(0, 2)" :key="e.id" class="cc-chip"
                :style="{ background: tintOf(e.event_type), color: CARE_EVENT_COLOR[e.event_type] }"
                :title="e.title">{{ e.title }}</span>
              <span v-if="cell.events.length > 2" class="cc-more">+{{ cell.events.length - 2 }}</span>
            </div>
          </div>
        </div>

        <div class="cc-event-list">
          <div class="cc-list-title">本月事项（{{ events.length }}）</div>
          <div v-if="!events.length" class="tui-card">
            <div class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="26"><Calendar /></el-icon></span>
              <span class="tui-empty-title">本月暂无关怀事项</span>
              <span class="tui-empty-desc">点击「自动生成」按学生情况智能生成关怀事项</span>
            </div>
          </div>
          <div v-for="e in events" :key="e.id" class="cc-event-item">
            <span class="cc-event-badge" :style="{ background: tintOf(e.event_type), color: CARE_EVENT_COLOR[e.event_type] }">
              {{ CARE_EVENT_LABEL[e.event_type] }}
            </span>
            <span class="cc-event-title">{{ e.title }}</span>
            <span v-if="e.student_name" class="cc-event-who">{{ e.student_name }}</span>
            <el-tag v-if="e.auto_generated" size="small" effect="plain" round>自动</el-tag>
            <span class="cc-event-date">{{ e.event_date }}</span>
            <button class="cc-link cc-link-danger" @click="removeEvent(e)">删除</button>
          </div>
        </div>
      </template>

      <!-- 家访记录 -->
      <template v-else-if="tab === 'visits'">
        <div class="tui-actions cc-panel-ops">
          <el-button size="small" round type="primary" :icon="Plus" @click="visitVisible = true">新增家访</el-button>
        </div>
        <div v-if="!visits.length" class="tui-card">
          <div class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><Document /></el-icon></span>
            <span class="tui-empty-title">暂无家访记录</span>
            <span class="tui-empty-desc">记录每次家访与沟通，形成可追溯的台账</span>
          </div>
        </div>
        <div v-for="v in visits" :key="v.id" class="cc-record">
          <div class="cc-record-head">
            <span class="cc-record-name">{{ v.student_name }}</span>
            <el-tag size="small" effect="plain" round>{{ VISIT_METHOD_LABEL[v.method] }}</el-tag>
            <span class="cc-record-date">{{ v.visit_date }}</span>
          </div>
          <div class="cc-record-body">{{ v.content }}</div>
          <div v-if="v.follow_up" class="cc-record-follow">后续：{{ v.follow_up }}</div>
          <div class="cc-record-ops">
            <button class="cc-link cc-link-danger" @click="removeVisit(v)">删除</button>
          </div>
        </div>
      </template>

      <!-- 正向激励 -->
      <template v-else>
        <div class="tui-actions cc-panel-ops">
          <el-button size="small" round type="primary" :icon="Plus" @click="praiseVisible = true">新增激励</el-button>
        </div>
        <div v-if="!praises.length" class="tui-card">
          <div class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><Star /></el-icon></span>
            <span class="tui-empty-title">暂无激励记录</span>
            <span class="tui-empty-desc">及时表扬与发放徽章，让正向反馈被看见</span>
          </div>
        </div>
        <div v-for="p in praises" :key="p.id" class="cc-record">
          <div class="cc-record-head">
            <span class="cc-record-name">{{ p.student_name }}</span>
            <el-tag size="small" :type="p.praise_type === 'badge' ? 'warning' : 'success'" effect="plain" round>
              {{ p.badge_name || PRAISE_TYPE_LABEL[p.praise_type] }}
            </el-tag>
            <span class="cc-record-date">{{ p.occurred_on }}</span>
          </div>
          <div class="cc-record-body">{{ p.reason }}</div>
          <div class="cc-record-ops">
            <button class="cc-link cc-link-danger" @click="removePraise(p)">删除</button>
          </div>
        </div>
      </template>

      <CareEventDialog v-model="eventVisible" @saved="loadAll" />
      <HomeVisitDialog v-model="visitVisible" @saved="loadAll" />
      <PraiseDialog v-model="praiseVisible" @saved="loadAll" />

      <!-- 匿名求助：复用既有反馈通道，不新建表 -->
      <el-dialog v-model="helpVisible" title="匿名求助" :width="isMobile ? '94%' : '480px'" align-center destroy-on-close>
        <div class="tui-notice tui-notice-success">
          <el-icon><Lock /></el-icon>
          <span>求助内容通过既有匿名反馈通道提交，可留联系方式便于回访（选填）</span>
        </div>
        <el-input v-model="helpContent" type="textarea" :rows="4" maxlength="500" show-word-limit
          placeholder="说说你遇到的困难或需要学校支持的地方……" style="margin-top:12px" />
        <el-input v-model="helpContact" placeholder="联系方式（选填）" style="margin-top:10px" />
        <template #footer>
          <el-button @click="helpVisible = false">取消</el-button>
          <el-button type="primary" :loading="helpSaving" :disabled="!helpContent.trim()" @click="submitHelp">提交</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowLeft, ArrowRight, Calendar, ChatDotRound, Document, Lock, Plus, Refresh, Star,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { createFeedback } from '@/api/feedback'
import {
  deleteCareEvent, deleteHomeVisit, deletePraise, generateCareEvents, getCareEvents,
  getCareOverview, getHomeVisits, getPraises, CARE_EVENT_COLOR, CARE_EVENT_LABEL,
  PRAISE_TYPE_LABEL, VISIT_METHOD_LABEL,
  type CareCenterOverview, type CareEvent, type CareEventType, type HomeVisit, type Praise,
} from '@/api/careCenter'
import CareEventDialog from '@/components/teacher/carecenter/CareEventDialog.vue'
import HomeVisitDialog from '@/components/teacher/carecenter/HomeVisitDialog.vue'
import PraiseDialog from '@/components/teacher/carecenter/PraiseDialog.vue'

defineOptions({ name: 'teacher-care-center' })

const { isMobile } = useResponsive()

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']

const tab = ref('calendar')
const today = new Date()
const calYear = ref(today.getFullYear())
const calMonth = ref(today.getMonth() + 1)

const overview = ref<CareCenterOverview>({ month: '', event_count: 0, visit_count: 0, praise_count: 0, pending_events: 0 })
const events = ref<CareEvent[]>([])
const visits = ref<HomeVisit[]>([])
const praises = ref<Praise[]>([])

const eventVisible = ref(false)
const visitVisible = ref(false)
const praiseVisible = ref(false)
const helpVisible = ref(false)
const genLoading = ref(false)
const helpSaving = ref(false)
const helpContent = ref('')
const helpContact = ref('')

function tintOf(t: CareEventType) {
  return `${CARE_EVENT_COLOR[t]}1a`
}

const monthKey = computed(() => `${calYear.value}-${String(calMonth.value).padStart(2, '0')}`)

const calendarCells = computed(() => {
  const first = new Date(calYear.value, calMonth.value - 1, 1)
  const offset = (first.getDay() + 6) % 7 // 周一为第一列
  const daysInMonth = new Date(calYear.value, calMonth.value, 0).getDate()
  const prevDays = new Date(calYear.value, calMonth.value - 1, 0).getDate()
  const todayKey = new Date().toISOString().slice(0, 10)
  const cells: { day: number; inMonth: boolean; isToday: boolean; events: CareEvent[] }[] = []

  for (let i = offset - 1; i >= 0; i--) {
    cells.push({ day: prevDays - i, inMonth: false, isToday: false, events: [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const key = `${monthKey.value}-${String(d).padStart(2, '0')}`
    cells.push({
      day: d,
      inMonth: true,
      isToday: key === todayKey,
      events: events.value.filter((e) => (e.event_date || '').slice(0, 10) === key),
    })
  }
  while (cells.length % 7 !== 0) {
    cells.push({ day: cells.length - offset - daysInMonth + 1, inMonth: false, isToday: false, events: [] })
  }
  return cells
})

function shiftMonth(delta: number) {
  const d = new Date(calYear.value, calMonth.value - 1 + delta, 1)
  calYear.value = d.getFullYear()
  calMonth.value = d.getMonth() + 1
  loadAll()
}

async function loadAll() {
  const month = monthKey.value
  const [o, e, v, p] = await Promise.allSettled([
    getCareOverview(month),
    getCareEvents(month),
    getHomeVisits(),
    getPraises(),
  ])
  if (o.status === 'fulfilled') overview.value = o.value
  if (e.status === 'fulfilled') events.value = e.value
  if (v.status === 'fulfilled') visits.value = v.value
  if (p.status === 'fulfilled') praises.value = p.value
}

async function handleGenerate() {
  genLoading.value = true
  try {
    const res = await generateCareEvents(monthKey.value)
    ElMessage.success(res.message)
    loadAll()
  } catch {
    ElMessage.error('自动生成失败')
  } finally {
    genLoading.value = false
  }
}

async function removeEvent(e: CareEvent) {
  try {
    await ElMessageBox.confirm(`确定删除「${e.title}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteCareEvent(e.id)
  ElMessage.success('已删除')
  loadAll()
}

async function removeVisit(v: HomeVisit) {
  try {
    await ElMessageBox.confirm(`确定删除 ${v.student_name} 的家访记录？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteHomeVisit(v.id)
  ElMessage.success('已删除')
  loadAll()
}

async function removePraise(p: Praise) {
  try {
    await ElMessageBox.confirm(`确定删除 ${p.student_name} 的激励记录？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deletePraise(p.id)
  ElMessage.success('已删除')
  loadAll()
}

async function submitHelp() {
  if (!helpContent.value.trim()) return
  helpSaving.value = true
  try {
    await createFeedback({
      type: '求助',
      title: '人文关怀中心 · 匿名求助',
      content: helpContent.value.trim(),
      contact: helpContact.value.trim() || undefined,
    })
    ElMessage.success('已提交，我们会尽快跟进')
    helpVisible.value = false
    helpContent.value = ''
    helpContact.value = ''
  } catch {
    ElMessage.error('提交失败')
  } finally {
    helpSaving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.cc-mobile-ops { margin-bottom: 12px; }

.cc-panel-ops { justify-content: flex-end; margin-bottom: 10px; }

.cc-cal-head { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 8px; }
.cc-cal-title { font-size: 14px; font-weight: 600; color: #101828; min-width: 130px; text-align: center; }

.cc-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.cc-week span { text-align: center; font-size: 11.5px; color: #98a2b3; }

.cc-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cc-cell {
  min-height: 62px; border: 1px solid #f2f4f7; border-radius: 8px; padding: 4px 5px;
  background: #fff; display: flex; flex-direction: column; gap: 3px; overflow: hidden;
}
.cc-cell.muted { background: #fcfcfd; opacity: 0.55; }
.cc-cell.today { border-color: #5b8def; box-shadow: 0 0 0 2px rgba(91, 141, 239, 0.12); }
.cc-cell-top { display: flex; align-items: center; justify-content: space-between; }
.cc-day { font-size: 11.5px; color: #475467; font-weight: 600; }
.cc-dot-count { font-size: 10px; color: #fff; background: #5b8def; border-radius: 999px; padding: 0 5px; }
.cc-cell-events { display: flex; flex-direction: column; gap: 2px; }
.cc-chip {
  font-size: 10px; padding: 1px 5px; border-radius: 999px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cc-more { font-size: 10px; color: #98a2b3; }

.cc-event-list { margin-top: 16px; display: flex; flex-direction: column; gap: 7px; }
.cc-list-title { font-size: 13px; font-weight: 600; color: #101828; }
.cc-event-item {
  display: flex; align-items: center; gap: 8px;
  border: 1px solid #f2f4f7; border-radius: 10px; padding: 8px 11px; background: #fff;
}
.cc-event-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; flex-shrink: 0; }
.cc-event-title { font-size: 13px; color: #344054; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-event-who { font-size: 11.5px; color: #98a2b3; flex-shrink: 0; }
.cc-event-date { font-size: 11.5px; color: #98a2b3; flex-shrink: 0; }

.cc-record { border: 1px solid #f0f1f3; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; background: #fff; }
.cc-record-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.cc-record-name { font-size: 14px; font-weight: 600; color: #101828; }
.cc-record-date { margin-left: auto; font-size: 11.5px; color: #98a2b3; }
.cc-record-body { font-size: 13px; color: #475467; line-height: 1.65; white-space: pre-wrap; }
.cc-record-follow { font-size: 12.5px; color: #6941c6; background: #f4f3ff; border-radius: 8px; padding: 6px 10px; margin-top: 7px; }
.cc-record-ops { display: flex; gap: 12px; margin-top: 8px; }

.cc-link { border: none; background: none; padding: 0; font-size: 12px; color: #2563eb; cursor: pointer; font-family: inherit; }
.cc-link-danger { color: #d92d20; }

@media (max-width: 767px) {
  .cc-mobile-ops .el-button,
  .cc-panel-ops .el-button { flex: 1; min-height: 40px; margin-left: 0 !important; }
  .cc-panel-ops { justify-content: stretch; }
  .cc-cell { min-height: 54px; }
  .cc-cell-events { display: none; }
}
</style>