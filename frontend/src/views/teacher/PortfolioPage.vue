<template>
  <div class="tui-page">
    <SubPageHeader
      title="成长档案"
      sub="把日常育人经验沉淀成看得见的成长轨迹"
      fallback="/teacher/more"
    />

    <div class="tui-content">
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">成长档案</h2>
          <p class="tui-header-sub">把日常育人经验沉淀成看得见的成长轨迹</p>
        </div>
        <div class="tui-header-actions">
          <el-button round :icon="Printer" :loading="reportLoading" @click="openReport">成长报告</el-button>
          <el-button type="primary" round :icon="Plus" @click="openCreate">新增档案</el-button>
        </div>
      </header>

      <!-- 移动端高频操作 -->
      <div v-if="isMobile" class="tui-actions pf-topbar">
        <el-button round :icon="Printer" :loading="reportLoading" @click="openReport">成长报告</el-button>
        <el-button type="primary" round :icon="Plus" @click="openCreate">新增档案</el-button>
      </div>

      <!-- 类型统计兼筛选 -->
      <div class="tui-stat-row">
        <button
          type="button"
          class="tui-stat"
          :class="{ 'is-active': filter === '' }"
          @click="setFilter('')"
        >
          <span class="tui-stat-num">{{ items.length }}</span>
          <span class="tui-stat-label">全部</span>
        </button>
        <button
          v-for="t in typeOrder"
          :key="t"
          type="button"
          class="tui-stat"
          :class="{ 'is-active': filter === t }"
          @click="setFilter(t)"
        >
          <span class="tui-stat-num" :style="{ color: PORTFOLIO_TYPE_COLOR[t] }">{{ countOf(t) }}</span>
          <span class="tui-stat-label">{{ PORTFOLIO_TYPE_LABEL[t] }}</span>
        </button>
      </div>

      <div v-if="loading" class="tui-empty">
        <span class="tui-empty-title">加载中…</span>
      </div>
      <div v-else-if="!grouped.length" class="tui-empty">
        <span class="tui-empty-icon"><el-icon :size="28"><Collection /></el-icon></span>
        <span class="tui-empty-title">{{ filter ? '该类型暂无档案' : '还没有成长档案' }}</span>
        <span class="tui-empty-desc">{{ filter ? '换个类型看看，或点击「新增档案」' : '点击「新增档案」沉淀第一条' }}</span>
      </div>

      <!-- 时间线：按年份分组 -->
      <div v-else class="tui-groups">
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

      <PortfolioItemDialog v-model="dialogVisible" :item="editing" @saved="load" />

      <!-- 成长报告 -->
      <el-dialog
        v-model="reportVisible"
        title="成长报告"
        :width="isMobile ? '94%' : '720px'"
        align-center
        destroy-on-close
      >
        <div v-if="report" class="pf-report">
          <div class="rpt-head">
            <h3>{{ report.teacher_name }} · 教师成长报告</h3>
            <span>{{ (report.generated_at || '').slice(0, 10) }}</span>
          </div>
          <div class="rpt-total">共 {{ report.total }} 条成长档案</div>
          <div class="rpt-types">
            <div v-for="t in report.by_type" :key="t.type" class="rpt-type">
              <span class="rpt-num" :style="{ color: PORTFOLIO_TYPE_COLOR[t.type] }">{{ t.count }}</span>
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
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Collection, Plus, Printer } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import {
  deletePortfolioItem,
  getPortfolioItems,
  getPortfolioReport,
  PORTFOLIO_TYPE_COLOR,
  PORTFOLIO_TYPE_LABEL,
  type PortfolioItem,
  type PortfolioItemType,
  type PortfolioReport,
} from '@/api/teacherPortfolio'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PortfolioItemCard from '@/components/teacher/portfolio/PortfolioItemCard.vue'
import PortfolioItemDialog from '@/components/teacher/portfolio/PortfolioItemDialog.vue'

defineOptions({ name: 'teacher-portfolio' })

const { isMobile } = useResponsive()

const typeOrder: PortfolioItemType[] = ['case', 'honor', 'training', 'research']

const items = ref<PortfolioItem[]>([])
const loading = ref(false)
const filter = ref<'' | PortfolioItemType>('')
const dialogVisible = ref(false)
const editing = ref<PortfolioItem | null>(null)
const report = ref<PortfolioReport | null>(null)
const reportVisible = ref(false)
const reportLoading = ref(false)

function countOf(t: PortfolioItemType) {
  return items.value.filter((i) => i.item_type === t).length
}

function setFilter(t: '' | PortfolioItemType) {
  filter.value = filter.value === t ? '' : t
}

/** 时间线分组：优先按发生年份，其次按创建年份 */
const grouped = computed(() => {
  const list = filter.value ? items.value.filter((i) => i.item_type === filter.value) : items.value
  const map = new Map<string, PortfolioItem[]>()
  for (const it of list) {
    const year = (it.occurred_on || it.created_at || '').slice(0, 4) || '未标注'
    if (!map.has(year)) map.set(year, [])
    map.get(year)!.push(it)
  }
  return [...map.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([year, its]) => ({ year, items: its }))
})

async function load() {
  loading.value = true
  try {
    items.value = await getPortfolioItems()
  } catch {
    ElMessage.error('成长档案加载失败')
  } finally {
    loading.value = false
  }
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
    await ElMessageBox.confirm(`确定删除「${item.title}」？删除后不再计入成长报告。`, '删除确认', {
      type: 'warning',
    })
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

onMounted(load)
</script>

<style scoped>
/* 移动端高频操作条 */
.pf-topbar {
  margin-bottom: 12px;
}
.pf-topbar .el-button {
  flex: 1;
  margin-left: 0;
}

/* 成长报告弹窗内容 */
.pf-report {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rpt-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.rpt-head h3 {
  margin: 0;
  font-size: 16px;
  color: #101828;
}
.rpt-head span {
  font-size: 12px;
  color: #98a2b3;
}
.rpt-total {
  font-size: 12.5px;
  color: #667085;
}
.rpt-types {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.rpt-type {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #f9fafb;
  border-radius: 10px;
  padding: 9px 10px;
}
.rpt-num {
  font-size: 18px;
  font-weight: 700;
}
.rpt-lb {
  font-size: 11px;
  color: #98a2b3;
}
.rpt-list {
  display: flex;
  flex-direction: column;
}
.rpt-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 2px;
  border-bottom: 1px solid #f2f4f7;
  font-size: 13px;
}
.rpt-idx {
  width: 18px;
  text-align: center;
  color: #98a2b3;
  font-size: 12px;
  flex-shrink: 0;
}
.rpt-title {
  color: #344054;
  flex: 1;
  min-width: 0;
}
.rpt-meta {
  font-size: 11.5px;
  color: #98a2b3;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .rpt-types {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>