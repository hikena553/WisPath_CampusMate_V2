<template>
  <div class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel">
    <SubPageHeader
      title="学生成长档案"
      fallback="/teacher"
    />

    <!-- 移动端下拉刷新：指示器插在吸顶栏之后 -->
    <PullRefreshIndicator v-if="isMobile" :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <div class="tui-content">
      <!-- 桌面端特色头部：档案语义色 + 收藏图标；右侧保留本页专属的导出与建档入口 -->
      <TuiPageHero
        v-if="!isMobile"
        title="学生成长档案"
        sub="选择学生查看其成长徽章与成长轨迹，同步维护你的育人档案"
        :icon="Collection"
        tone="violet"
      >
        <div class="tui-hero-metric is-accent"><b>{{ students.length }}</b><span>名下学生</span></div>
        <el-button round :icon="Printer" :loading="reportLoading" @click="openReport">成长报告</el-button>
        <el-button size="small" :icon="Plus" @click="openCreate">新增档案</el-button>
      </TuiPageHero>

      <!-- 移动端高频操作 -->
      <div v-if="isMobile" class="tui-actions pf-topbar">
        <el-button round :icon="Printer" :loading="reportLoading" @click="openReport">成长报告</el-button>
        <el-button size="small" :icon="Plus" @click="openCreate">新增档案</el-button>
      </div>

      <!-- 1. 学生横向选择器 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><User /></el-icon>学生横向选择器</h3>
          <span class="tui-section-extra tui-text-quiet">共 {{ students.length }} 人</span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>左右滑动选择学生，下方徽章墙与成长时间轴会随之切换。</span>
        </div>
        <div v-if="studentsLoading" class="tui-empty">
          <span class="tui-empty-title">学生名单加载中…</span>
        </div>
        <div v-else-if="!students.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><User /></el-icon></span>
          <span class="tui-empty-title">暂无可查看的学生</span>
          <span class="tui-empty-desc">当前账号名下还没有学生，先到「学生管理」导入名单后再查看。</span>
        </div>
        <div v-else class="pf-rail">
          <button
            v-for="s in students"
            :key="s.id"
            type="button"
            class="pf-stu"
            :class="{ active: s.id === activeStudentId }"
            @click="selectStudent(s.id)"
          >
            <span class="pf-stu-avatar">{{ s.name.slice(0, 1) }}</span>
            <span class="pf-stu-name">{{ s.name }}</span>
          </button>
        </div>
      </section>

      <!-- 2. 徽章墙 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Medal /></el-icon>成长徽章墙</h3>
          <span v-if="activeStudent" class="tui-section-extra">
            <el-tag
              :type="activeStudent.crisis_level ? 'danger' : 'success'"
              size="small"
              effect="plain"
              round
            >
              {{ activeStudent.crisis_level ? '心理关注' : '状态平稳' }}
            </el-tag>
          </span>
        </div>
        <div class="tui-section-hint success">
          <el-icon><InfoFilled /></el-icon>
          <span>徽章由学生档案自动派生（成长记录 / 技能 / 兴趣 / 综合评分），无需手工维护。</span>
        </div>
        <div v-if="!activeStudent" class="tui-empty">
          <span class="tui-empty-title">请先选择一名学生</span>
          <span class="tui-empty-desc">在上方选择学生后，这里会展示其成长徽章。</span>
        </div>
        <div v-else class="pf-badges">
          <div v-for="b in badges" :key="b.key" class="pf-badge" :class="b.tone">
            <el-icon :size="16"><component :is="b.icon" /></el-icon>
            <span class="pf-badge-num">{{ b.value }}</span>
            <span class="pf-badge-lb">{{ b.label }}</span>
          </div>
        </div>
      </section>

      <!-- 3. 成长时间轴 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Clock /></el-icon>成长时间轴</h3>
          <span v-if="activeStudent" class="tui-section-extra tui-text-quiet">{{ activeStudent.name }}</span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>汇总该学生的荣誉、竞赛、实践、论文与成果记录，按时间倒序排列。</span>
        </div>
        <div v-if="!activeStudent" class="tui-empty">
          <span class="tui-empty-title">暂无学生上下文</span>
          <span class="tui-empty-desc">选择学生后即可查看其成长轨迹。</span>
        </div>
        <div v-else-if="growthLoading" class="tui-empty">
          <span class="tui-empty-title">成长轨迹加载中…</span>
        </div>
        <div v-else-if="!timeline.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><Clock /></el-icon></span>
          <span class="tui-empty-title">{{ activeStudent.name }} 暂无成长记录</span>
          <span class="tui-empty-desc">学生端录入荣誉 / 竞赛 / 实践后，会在这里自动汇总成时间轴。</span>
        </div>
        <div v-else class="tl">
          <div v-for="r in timeline" :key="r.id" class="tl-item">
            <span class="tl-node"><el-icon :size="11"><component :is="RECORD_META[r.type].icon" /></el-icon></span>
            <div class="tl-body">
              <div class="tl-top">
                <span class="tui-chip tui-chip-brand">{{ RECORD_META[r.type].label }}</span>
                <span class="tl-date">{{ r.date }}</span>
              </div>
              <div class="tl-title">{{ r.title }}</div>
              <p v-if="r.description" class="tl-desc">{{ r.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 4. 我的育人档案（保留原有增删改 + 报告） -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Collection /></el-icon>我的育人档案</h3>
          <span class="tui-section-extra">
            <el-button size="small" :icon="Plus" @click="openCreate">新增档案</el-button>
          </span>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>沉淀你的工作案例、荣誉、研修与研究成果，全部计入成长报告。</span>
        </div>
        <div class="tui-section-tools">
          <button type="button" class="tui-chip" :class="{ 'tui-chip-brand': filter === '' }" @click="setFilter('')">
            全部 {{ items.length }}
          </button>
          <button
            v-for="t in typeOrder"
            :key="t"
            type="button"
            class="tui-chip"
            :class="{ 'tui-chip-brand': filter === t }"
            @click="setFilter(t)"
          >
            {{ PORTFOLIO_TYPE_LABEL[t] }} {{ countOf(t) }}
          </button>
        </div>

        <div v-if="loading" class="tui-empty">
          <span class="tui-empty-title">加载中…</span>
        </div>
        <div v-else-if="!filteredItems.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="24"><Collection /></el-icon></span>
          <span class="tui-empty-title">{{ filter ? '该类型暂无档案' : '还没有育人档案' }}</span>
          <span class="tui-empty-desc">{{ filter ? '换个类型看看，或点击「新增档案」补一条。' : '点击「新增档案」，沉淀第一条育人档案。' }}</span>
        </div>
        <template v-else>
          <div class="tui-groups">
            <section v-for="g in grouped" :key="g.year">
              <div class="tui-group-title">
                {{ g.year }}
                <span class="tui-group-count">{{ g.items.length }} 条</span>
              </div>
              <div class="tui-stack">
                <PortfolioItemCard
                  v-for="it in g.items"
                  :key="it.id"
                  :item="it"
                  @edit="openEdit"
                  @delete="handleDelete"
                />
              </div>
            </section>
          </div>
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="archivePage"
              v-model:page-size="archivePageSize"
              :page-sizes="[10, 20, 50]"
              :total="filteredItems.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleArchiveSizeChange"
              @current-change="handleArchiveCurrentChange"
            />
          </div>
        </template>
      </section>

      <PortfolioItemDialog v-model="dialogVisible" :item="editing" @saved="load" />

      <!-- 成长报告 -->
      <!-- 成长报告（长列表：移动端=全屏子页） -->
      <ResponsivePopup
        v-model="reportVisible"
        title="成长报告"
        width="400px"
        align-center
        :close-on-click-modal="false"
        class="tui-dialog"
        destroy-on-close
      >
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>汇总你的全部育人档案，可直接打印或导出 PDF 存档。</span>
        </div>
        <div v-if="report" class="pf-report">
          <div class="rpt-head">
            <h3>{{ report.teacher_name }} · 教师成长报告</h3>
            <span>{{ (report.generated_at || '').slice(0, 10) }}</span>
          </div>
          <div class="rpt-total">共 {{ report.total }} 条育人档案</div>
          <div class="rpt-types">
            <div v-for="t in report.by_type" :key="t.type" class="rpt-type">
              <span class="rpt-num">{{ t.count }}</span>
              <span class="rpt-lb">{{ t.label }}</span>
            </div>
          </div>
          <div class="rpt-list">
            <div v-for="(it, i) in report.items" :key="it.id" class="rpt-item">
              <span class="rpt-idx">{{ i + 1 }}</span>
              <span class="rpt-title">{{ it.title }}</span>
              <span class="rpt-meta">
                {{ PORTFOLIO_TYPE_LABEL[it.item_type] }}<template v-if="it.occurred_on"> · {{ it.occurred_on }}</template>
              </span>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="reportVisible = false">关闭</el-button>
          <el-button type="primary" :icon="Printer" @click="printReport">打印 / 导出 PDF</el-button>
        </template>
      </ResponsivePopup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
// v6.1 弹窗减负：报告走全屏子页，删除确认走底部动作面板
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import {
  Clock,
  Collection,
  Document,
  InfoFilled,
  Medal,
  Plus,
  Printer,
  Star,
  Suitcase,
  Trophy,
  User,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import {
  deletePortfolioItem,
  getPortfolioItems,
  getPortfolioReport,
  PORTFOLIO_TYPE_LABEL,
  type PortfolioItem,
  type PortfolioItemType,
  type PortfolioReport,
} from '@/api/teacherPortfolio'
import { getStudents, type StudentSummary } from '@/api/teacher'
import { getGrowthRecords } from '@/api/growth'
import type { GrowthRecord } from '@/types'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import PortfolioItemCard from '@/components/teacher/portfolio/PortfolioItemCard.vue'
import PortfolioItemDialog from '@/components/teacher/portfolio/PortfolioItemDialog.vue'

defineOptions({ name: 'teacher-portfolio' })

const { isMobile } = useResponsive()

// 移动端下拉刷新：桌面端不响应手势
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

const typeOrder: PortfolioItemType[] = ['case', 'honor', 'training', 'research']

const items = ref<PortfolioItem[]>([])
const loading = ref(false)
const filter = ref<'' | PortfolioItemType>('')
const dialogVisible = ref(false)
const editing = ref<PortfolioItem | null>(null)
const report = ref<PortfolioReport | null>(null)
const reportVisible = ref(false)
const reportLoading = ref(false)

// 学生成长：横向选择器 + 徽章墙 + 时间轴
const students = ref<StudentSummary[]>([])
const studentsLoading = ref(false)
const activeStudentId = ref<number | null>(null)
const growthRecords = ref<GrowthRecord[]>([])
const growthLoading = ref(false)

// 育人档案分页（契约 §2）
const archivePage = ref(1)
const archivePageSize = ref(10)

const activeStudent = computed(
  () => students.value.find((s) => s.id === activeStudentId.value) ?? null
)

const RECORD_META: Record<GrowthRecord['type'], { label: string; icon: unknown }> = {
  honor: { label: '荣誉', icon: Medal },
  competition: { label: '竞赛', icon: Trophy },
  practice: { label: '实践', icon: Suitcase },
  paper: { label: '论文', icon: Document },
  achievement: { label: '成果', icon: Star },
}

const badges = computed(() => {
  const s = activeStudent.value
  if (!s) return [] as { key: string; label: string; value: number; icon: unknown; tone: string }[]
  return [
    { key: 'growth', label: '成长记录', value: s.growth_count, icon: Collection, tone: 'brand' },
    { key: 'skill', label: '技能标签', value: s.skills_json?.skills?.length ?? 0, icon: Star, tone: '' },
    { key: 'interest', label: '兴趣方向', value: s.skills_json?.interests?.length ?? 0, icon: Medal, tone: '' },
    { key: 'score', label: '综合评分', value: s.score, icon: Trophy, tone: 'success' },
  ]
})

const timeline = computed(() =>
  [...growthRecords.value].sort((a, b) => (a.date < b.date ? 1 : -1))
)

const filteredItems = computed(() =>
  filter.value ? items.value.filter((i) => i.item_type === filter.value) : items.value
)

const pagedItems = computed(() =>
  filteredItems.value.slice(
    (archivePage.value - 1) * archivePageSize.value,
    archivePage.value * archivePageSize.value
  )
)

function countOf(t: PortfolioItemType) {
  return items.value.filter((i) => i.item_type === t).length
}

function setFilter(t: '' | PortfolioItemType) {
  filter.value = filter.value === t ? '' : t
  archivePage.value = 1
}

/** 时间线分组：优先按发生年份，其次按创建年份（对分页后的当页数据分组） */
const grouped = computed(() => {
  const map = new Map<string, PortfolioItem[]>()
  for (const it of pagedItems.value) {
    const year = (it.occurred_on || it.created_at || '').slice(0, 4) || '未标注'
    if (!map.has(year)) map.set(year, [])
    map.get(year)!.push(it)
  }
  return [...map.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([year, its]) => ({ year, items: its }))
})

function selectStudent(id: number) {
  activeStudentId.value = id
}

async function load(silent = false) {
  loading.value = true
  try {
    items.value = await getPortfolioItems()
  } catch {
    if (!silent) ElMessage.error('成长档案加载失败')
  } finally {
    loading.value = false
  }
}

/** 下拉刷新：复用档案与学生名单加载，失败不提示 */
async function refreshAll() {
  await Promise.all([load(true), loadStudents()])
}

async function loadStudents() {
  studentsLoading.value = true
  try {
    students.value = await getStudents()
    if (students.value.length && activeStudentId.value === null) {
      activeStudentId.value = students.value[0].id
    }
  } catch {
    students.value = []
  } finally {
    studentsLoading.value = false
  }
}

async function loadGrowth() {
  if (activeStudentId.value === null) {
    growthRecords.value = []
    return
  }
  growthLoading.value = true
  try {
    growthRecords.value = await getGrowthRecords(activeStudentId.value)
  } catch {
    growthRecords.value = []
  } finally {
    growthLoading.value = false
  }
}

watch(activeStudentId, loadGrowth)

function handleArchiveSizeChange() {
  archivePage.value = 1
}
function handleArchiveCurrentChange() {
  // 页码由 v-model 同步，这里保留契约要求的回调入口
  archivePage.value = archivePage.value || 1
}

function openCreate() {
  editing.value = null
  dialogVisible.value = true
}

function openEdit(item: PortfolioItem) {
  editing.value = item
  dialogVisible.value = true
}

async function handleDelete(item: PortfolioItem) {
  try {
    if (!(await actionConfirm(`确定删除「${item.title}」？删除后不再计入成长报告。`, '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  } catch {
    return
  }
  try {
    await deletePortfolioItem(item.id)
    ElMessage.success('已删除')
    load()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function openReport() {
  reportLoading.value = true
  try {
    report.value = await getPortfolioReport()
    reportVisible.value = true
  } catch {
    ElMessage.error('成长报告生成失败')
  } finally {
    reportLoading.value = false
  }
}

/** 打印 / 导出 PDF：打开独立打印窗口，避免页面样式干扰 */
function printReport() {
  const r = report.value
  if (!r) return
  const rows = r.items
    .map(
      (it, i) =>
        `<tr><td>${i + 1}</td><td>${escapeHtml(it.title)}</td><td>${PORTFOLIO_TYPE_LABEL[it.item_type]}</td><td>${it.occurred_on || '-'}</td></tr>`
    )
    .join('')
  const cards = r.by_type
    .map((t) => `<span class="chip">${t.label} <b>${t.count}</b></span>`)
    .join('')
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" />
<title>${escapeHtml(r.teacher_name)} · 教师成长报告</title>
<style>
  body{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",system-ui,sans-serif;color:#101828;padding:32px;}
  h1{font-size:20px;margin:0 0 4px;}
  .meta{color:#98a2b3;font-size:12px;margin-bottom:18px;}
  .chips{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px;}
  .chip{border:1px solid #eaecf0;border-radius:999px;padding:4px 12px;font-size:12px;color:#475467;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th,td{border-bottom:1px solid #eaecf0;padding:8px 6px;text-align:left;}
  th{color:#667085;font-weight:600;font-size:12px;}
  td:first-child,th:first-child{width:40px;color:#98a2b3;}
</style></head><body>
  <h1>${escapeHtml(r.teacher_name)} · 教师成长报告</h1>
  <div class="meta">生成时间：${(r.generated_at || '').slice(0, 10)} ｜ 共 ${r.total} 条</div>
  <div class="chips">${cards}</div>
  <table><thead><tr><th>#</th><th>标题</th><th>类型</th><th>时间</th></tr></thead><tbody>${rows}</tbody></table>
</body></html>`
  const w = window.open('', '_blank', 'width=900,height=1000')
  if (!w) {
    ElMessage.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
    return
  }
  w.document.write(html)
  w.document.close()
  w.focus()
  w.print()
}

function escapeHtml(s: string) {
  return (s || '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string
  )
}

onMounted(() => {
  load()
  loadStudents()
})
</script>

<style scoped>
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* 移动端高频操作条 */
.pf-topbar {
  margin-bottom: 12px;
}
.pf-topbar .el-button {
  flex: 1;
  margin-left: 0;
}

/* 学生横向选择器 */
.pf-rail {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: none;
}
.pf-rail::-webkit-scrollbar {
  display: none;
}
.pf-stu {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 62px;
  padding: 8px 4px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.18s var(--tui-ease);
}
.pf-stu:active {
  transform: scale(0.97);
}
.pf-stu.active {
  border-color: var(--tui-brand);
  background: var(--tui-brand-soft);
}
.pf-stu-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--tui-surface-sunken);
  color: var(--tui-text-secondary);
  font-size: 13px;
  font-weight: 600;
}
.pf-stu.active .pf-stu-avatar {
  background: var(--tui-brand);
  color: #fff;
}
.pf-stu-name {
  font-size: 11.5px;
  color: var(--tui-text-secondary);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-stu.active .pf-stu-name {
  color: var(--tui-brand-strong);
  font-weight: 600;
}

/* 徽章墙 */
.pf-badges {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.pf-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px 6px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
}
.pf-badge.brand {
  color: var(--tui-brand-strong);
  background: var(--tui-brand-soft);
  border-color: transparent;
}
.pf-badge.success {
  color: var(--tui-success);
  background: var(--tui-success-soft);
  border-color: transparent;
}
.pf-badge-num {
  font-size: 17px;
  font-weight: 700;
  color: inherit;
  font-variant-numeric: tabular-nums;
}
.pf-badge-lb {
  font-size: 10.5px;
  color: var(--tui-text-quiet);
}
.pf-badge.brand .pf-badge-lb,
.pf-badge.success .pf-badge-lb {
  color: inherit;
  opacity: 0.75;
}

/* 时间轴 */
.tl {
  position: relative;
  padding-left: 26px;
}
.tl::before {
  content: '';
  position: absolute;
  left: 9px;
  top: 6px;
  bottom: 6px;
  width: 2px;
  background: var(--tui-border);
}
.tl-item {
  position: relative;
  margin-bottom: 10px;
}
.tl-item:last-child {
  margin-bottom: 0;
}
.tl-node {
  position: absolute;
  left: -26px;
  top: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--tui-surface);
  box-shadow: inset 0 0 0 2px var(--tui-brand);
  color: var(--tui-brand);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tl-body {
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface);
  padding: 8px 10px;
}
.tl-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.tl-date {
  font-size: 11px;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.tl-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--tui-text);
  margin-top: 4px;
}
.tl-desc {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--tui-text-secondary);
  line-height: 1.55;
}

/* 类型筛选：让 chip 作为按钮可点 */
.tui-section-tools button.tui-chip {
  cursor: pointer;
  font-family: inherit;
}

/* 成长报告弹窗内容 */
.pf-report {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rpt-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.rpt-head h3 {
  margin: 0;
  font-size: 14px;
  color: var(--tui-text);
}
.rpt-head span {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}
.rpt-total {
  font-size: 12px;
  color: var(--tui-text-secondary);
}
.rpt-types {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.rpt-type {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 8px 10px;
}
.rpt-num {
  font-size: 17px;
  font-weight: 700;
  color: var(--tui-brand-strong);
  font-variant-numeric: tabular-nums;
}
.rpt-lb {
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.rpt-list {
  display: flex;
  flex-direction: column;
  max-height: 320px;
  overflow-y: auto;
}
.rpt-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 7px 2px;
  border-bottom: 1px solid var(--tui-border);
  font-size: 12.5px;
}
.rpt-item:last-child {
  border-bottom: none;
}
.rpt-idx {
  width: 16px;
  text-align: center;
  color: var(--tui-text-quiet);
  font-size: 11px;
  flex-shrink: 0;
}
.rpt-title {
  color: var(--tui-text-secondary);
  flex: 1;
  min-width: 0;
}
.rpt-meta {
  font-size: 11px;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .pf-badges {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>