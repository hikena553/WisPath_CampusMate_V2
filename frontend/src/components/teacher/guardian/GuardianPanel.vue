<template>
  <div class="gp-panel">
    <!-- 当前学生：与关怀中心聚焦保持同步 -->
    <div class="gp-who">
      <span class="gp-avatar">{{ avatarOf(currentName) }}</span>
      <div class="gp-who-info">
        <b>{{ currentName }}</b>
        <i>{{ currentMeta }}</i>
      </div>
      <el-select
        :model-value="studentId ?? undefined"
        class="gp-who-select"
        size="small"
        filterable
        placeholder="选择学生"
        @change="onPickStudent"
      >
        <el-option v-for="s in students" :key="s.id" :label="`${s.name}${s.username ? ' · ' + s.username : ''}`" :value="s.id" />
      </el-select>
    </div>

    <!-- 三个视图：联系人 / 台账 / 统计 -->
    <div class="gp-tabs" role="tablist">
      <button
        v-for="t in TAB_OPTIONS"
        :key="t.value"
        class="gp-tab"
        :class="{ 'is-active': tab === t.value }"
        type="button"
        role="tab"
        @click="tab = t.value"
      >
        {{ t.label }}<span v-if="t.count" class="gp-tab-count">{{ t.count }}</span>
      </button>
    </div>

    <!-- ============ 家长联系人 ============ -->
    <section v-if="tab === 'contacts'" class="gp-sect">
      <div class="gp-toolbar">
        <span class="gp-meta">{{ studentId ? `共 ${guardians.length} 位联系人` : '请先选择学生' }}</span>
        <button class="gp-btn is-sm" type="button" @click="openGuardianCreate">
          <el-icon :size="13"><Plus /></el-icon>新增联系人
        </button>
      </div>

      <div v-if="!studentId" class="gp-empty">在上方选择一名学生后建档家长联系人。</div>
      <div v-else-if="!guardians.length" class="gp-empty">
        <span>暂无联系人</span>
        <button class="gp-link" type="button" @click="openGuardianCreate">建档第一位家长</button>
      </div>
      <div v-else class="gp-list">
        <div v-for="g in guardians" :key="g.id" class="gp-row">
          <div class="gp-row-top">
            <span class="gp-avatar is-sm">{{ avatarOf(g.name) }}</span>
            <div class="gp-row-id">
              <div class="gp-row-name">
                {{ g.name }}
                <span class="gp-tag">{{ g.relation }}</span>
                <span v-if="g.is_primary" class="gp-tag is-brand">主要</span>
              </div>
              <div class="gp-row-sub">
                <el-icon :size="12"><Phone /></el-icon>{{ g.phone_masked || '未填手机号' }}
              </div>
            </div>
            <div class="gp-row-ops">
              <button class="gp-link" type="button" @click="openGuardianEdit(g)">编辑</button>
              <button class="gp-link is-danger" type="button" @click="removeGuardian(g)">删除</button>
            </div>
          </div>
          <div class="gp-row-acts">
            <button class="gp-act" type="button" @click="openQuickLog(g, 'note')">通话留痕</button>
            <button class="gp-act" type="button" @click="openQuickLog(g, 'sms')">短信留痕</button>
            <button class="gp-act" type="button" @click="openQuickLog(g, 'note')">微信留痕</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ 沟通台账 ============ -->
    <section v-else-if="tab === 'logs'" class="gp-sect">
      <div class="gp-toolbar">
        <el-input
          v-model="filters.keyword"
          class="gp-search"
          placeholder="搜索沟通内容 / 家长"
          clearable
          :prefix-icon="Search"
          @input="onKeywordInput"
        />
        <button
          class="gp-filter-btn"
          :class="{ 'is-open': filterOpen || hasFilters }"
          type="button"
          @click="filterOpen = !filterOpen"
        >
          <el-icon :size="13"><Filter /></el-icon>筛选
          <span v-if="hasFilters" class="gp-filter-dot" aria-hidden="true"></span>
        </button>
        <button class="gp-btn is-sm" type="button" :disabled="!studentId" @click="openLogCreate">
          <el-icon :size="13"><Plus /></el-icon>记录
        </button>
        <el-dropdown trigger="click" @command="onHeadCommand">
          <button class="gp-icon-btn" type="button" aria-label="更多操作">
            <el-icon :size="16"><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="export"><el-icon><Download /></el-icon>导出台账 Excel</el-dropdown-item>
              <el-dropdown-item command="template"><el-icon><Document /></el-icon>下载导入模板</el-dropdown-item>
              <el-dropdown-item command="import" divided><el-icon><Upload /></el-icon>导入台账 Excel</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="filterOpen" class="gp-filters">
        <el-select v-model="filters.scene" size="small" placeholder="场景" clearable @change="onFilterChange">
          <el-option v-for="s in SCENE_OPTIONS" :key="s" :label="GUARDIAN_SCENE_LABEL[s]" :value="s" />
        </el-select>
        <el-select v-model="filters.channel" size="small" placeholder="渠道" clearable @change="onFilterChange">
          <el-option v-for="c in CHANNEL_OPTIONS" :key="c" :label="GUARDIAN_CHANNEL_LABEL[c]" :value="c" />
        </el-select>
        <el-select v-model="filters.status" size="small" placeholder="状态" clearable @change="onFilterChange">
          <el-option v-for="st in STATUS_OPTIONS" :key="st" :label="GUARDIAN_STATUS_LABEL[st]" :value="st" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          size="small"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          class="gp-range"
          @change="onFilterChange"
        />
        <button v-if="hasFilters" class="gp-link gp-reset" type="button" @click="resetFilters">重置筛选</button>
      </div>

      <div v-if="!studentId" class="gp-empty">在上方选择一名学生后查看沟通台账。</div>
      <div v-else-if="!logs.length" class="gp-empty">
        {{ hasFilters ? '没有符合条件的记录' : '暂无沟通记录，点「记录」留一条' }}
      </div>
      <template v-else>
        <div class="gp-list">
          <div v-for="l in logs" :key="l.id" class="gp-row">
            <div class="gp-row-top">
              <span class="gp-dot" :class="`tone-${channelTone(l.channel)}`"></span>
              <div class="gp-row-id">
                <div class="gp-row-name">
                  {{ GUARDIAN_SCENE_LABEL[l.scene] }}
                  <span class="gp-tag">{{ GUARDIAN_CHANNEL_LABEL[l.channel] }}</span>
                  <span class="gp-status" :class="`is-${l.status}`">{{ GUARDIAN_STATUS_LABEL[l.status] }}</span>
                </div>
                <div class="gp-row-sub">
                  <template v-if="l.guardian_name">对象：{{ l.guardian_name }} · </template>{{ (l.created_at || '').slice(0, 10) }}
                </div>
              </div>
            </div>
            <div class="gp-row-text">{{ l.content_summary }}</div>
            <div class="gp-row-acts">
              <template v-if="links[l.id] && !links[l.id].revoked">
                <span class="gp-link-valid">链接有效至 {{ (links[l.id].expires_at || '').slice(0, 10) }} · 访问 {{ links[l.id].view_count }} 次</span>
                <button class="gp-link" type="button" @click="copyLink(links[l.id])">复制链接</button>
                <button class="gp-link is-danger" type="button" @click="revoke(links[l.id])">撤销链接</button>
              </template>
              <button v-else-if="l.scene !== 'crisis'" class="gp-link" type="button" @click="makeLink(l)">生成只读链接</button>
              <span v-else class="gp-link-locked"><el-icon :size="11"><Lock /></el-icon>危机记录不生成链接</span>
              <button class="gp-link is-danger is-tail" type="button" @click="removeLog(l)">删除</button>
            </div>
          </div>
        </div>
        <div v-if="logTotal > 0" class="gp-pagination">
          <el-pagination
            v-model:current-page="pageLogs"
            v-model:page-size="pageSizeLogs"
            :page-sizes="[10, 20, 50]"
            :total="logTotal"
            :pager-count="5"
            small
            background
            layout="total, prev, pager, next"
            @size-change="onSizeChange"
            @current-change="loadLogs"
          />
        </div>
      </template>
    </section>

    <!-- ============ 沟通统计 ============ -->
    <section v-else class="gp-sect">
      <GuardianOverviewPanel
        :overview="overview"
        :days="OVERVIEW_DAYS"
        :student-name="studentId ? currentName : ''"
        @focus="onFocusFromStats"
      />
    </section>

    <GuardianDialog
      v-model="guardianVisible"
      :student-id="studentId || 0"
      :student="student"
      :guardian="editingGuardian"
      @saved="loadAll"
    />
    <ContactLogDialog
      v-model="logVisible"
      :student-id="studentId || 0"
      :student="student"
      :guardians="guardians"
      :initial-content="logPresetContent"
      :initial-scene="logPresetScene"
      :initial-channel="logPresetChannel"
      :initial-guardian-id="logPresetGuardianId"
      @saved="loadAll"
    />
    <input ref="importInput" class="gp-file-input" type="file" accept=".xlsx,.xls" @change="handleImportFile" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Document, Download, Filter, Lock, MoreFilled, Phone, Plus, Search, Upload,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { actionConfirm } from '@/composables/useActionSheet'
import {
  createShareLink, deleteContactLog, deleteGuardian, downloadContactLogTemplate,
  exportContactLogs, getContactLogsPaged, getGuardianOverview, getGuardians,
  getLogShareLink, importContactLogs, revokeShareLink,
  GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL, GUARDIAN_STATUS_LABEL,
  type ContactLog, type Guardian, type GuardianChannel, type GuardianContactStatus,
  type GuardianOverview, type GuardianScene, type ShareLink,
} from '@/api/guardian'
import type { StudentSummary } from '@/api/teacher'
import GuardianDialog from './GuardianDialog.vue'
import ContactLogDialog from './ContactLogDialog.vue'
import GuardianOverviewPanel from './GuardianOverview.vue'

const props = withDefaults(
  defineProps<{
    /** 全量学生名单：用于子页内切换聚焦 */
    students?: StudentSummary[]
    studentId?: number | null
    student?: StudentSummary | null
    studentName?: string
    /** 从成长档案闭环带来的反馈事由 */
    presetContent?: string
    presetScene?: GuardianScene
  }>(),
  {
    students: () => [],
    studentId: null,
    student: null,
    studentName: '',
    presetContent: '',
    presetScene: 'care',
  }
)

const emit = defineEmits<{ 'select-student': [s: StudentSummary | null] }>()

const OVERVIEW_DAYS = 30
type Tab = 'contacts' | 'logs' | 'stats'
const SCENE_OPTIONS: GuardianScene[] = ['leave', 'crisis', 'academic', 'care', 'other']
const CHANNEL_OPTIONS: GuardianChannel[] = ['sms', 'report', 'link', 'note']
const STATUS_OPTIONS: GuardianContactStatus[] = ['draft', 'sent', 'pending', 'failed']

const tab = ref<Tab>('contacts')

const guardians = ref<Guardian[]>([])
const logs = ref<ContactLog[]>([])
const logTotal = ref(0)
const links = ref<Record<number, ShareLink>>({})
const overview = ref<GuardianOverview | null>(null)

const currentName = computed(() => props.student?.name || props.studentName || '未选择学生')
const currentMeta = computed(() => {
  if (!props.studentId) return '选择一名学生开始沟通留痕'
  const meta = [props.student?.username, props.student?.college].filter(Boolean).join(' · ')
  return meta || '家长联系方式与沟通台账'
})

const TAB_OPTIONS = computed(() => [
  { value: 'contacts' as Tab, label: '联系人', count: guardians.value.length },
  { value: 'logs' as Tab, label: '沟通台账', count: logTotal.value },
  { value: 'stats' as Tab, label: '统计', count: 0 },
])

function avatarOf(name?: string) {
  return (name || '家').trim().charAt(0) || '家'
}

function channelTone(c: GuardianChannel): 'brand' | 'success' | 'muted' {
  if (c === 'sms') return 'brand'
  if (c === 'link') return 'success'
  if (c === 'report') return 'muted'
  return 'brand'
}

/* ===== 学生切换 ===== */
function onPickStudent(id: number) {
  const hit = props.students.find((s) => s.id === id) || null
  emit('select-student', hit)
}

/* ===== 过滤与分页 ===== */
const filterOpen = ref(false)
const filters = reactive<{
  keyword: string
  scene?: GuardianScene
  channel?: GuardianChannel
  status?: GuardianContactStatus
}>({ keyword: '', scene: undefined, channel: undefined, status: undefined })
const dateRange = ref<[string, string] | null>(null)
const pageLogs = ref(1)
const pageSizeLogs = ref(10)
const hasFilters = computed(() =>
  Boolean(filters.keyword || filters.scene || filters.channel || filters.status || dateRange.value)
)

let keywordTimer: ReturnType<typeof setTimeout> | undefined
function onKeywordInput() {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => { pageLogs.value = 1; void loadLogs() }, 300)
}
function onFilterChange() {
  pageLogs.value = 1
  void loadLogs()
}
function resetFilters() {
  filters.keyword = ''
  filters.scene = undefined
  filters.channel = undefined
  filters.status = undefined
  dateRange.value = null
  onFilterChange()
}
function onSizeChange() {
  pageLogs.value = 1
  void loadLogs()
}

/* ===== 弹窗 ===== */
const guardianVisible = ref(false)
const editingGuardian = ref<Guardian | null>(null)
const logVisible = ref(false)
const logPresetContent = ref('')
const logPresetScene = ref<GuardianScene>('care')
const logPresetChannel = ref<GuardianChannel>('note')
const logPresetGuardianId = ref<number | undefined>(undefined)

function openGuardianCreate() {
  if (!props.studentId) { ElMessage.info('请先选择一名学生'); return }
  editingGuardian.value = null
  guardianVisible.value = true
}
function openGuardianEdit(g: Guardian) {
  editingGuardian.value = g
  guardianVisible.value = true
}
function openLogCreate() {
  if (!props.studentId) { ElMessage.info('请先选择一名学生'); return }
  logPresetContent.value = ''
  logPresetScene.value = 'care'
  logPresetChannel.value = 'note'
  logPresetGuardianId.value = undefined
  logVisible.value = true
}
function openQuickLog(g: Guardian, channel: GuardianChannel) {
  logPresetContent.value = ''
  logPresetScene.value = 'care'
  logPresetChannel.value = channel
  logPresetGuardianId.value = g.id
  logVisible.value = true
}

async function removeGuardian(g: Guardian) {
  if (!(await actionConfirm(`确定删除联系人「${g.name}」？`, '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  await deleteGuardian(g.id)
  ElMessage.success('已删除')
  void loadAll()
}

/* ===== 数据加载 ===== */
async function loadGuardians() {
  if (!props.studentId) { guardians.value = []; return }
  try {
    guardians.value = await getGuardians(props.studentId)
  } catch {
    guardians.value = []
  }
}

async function loadLinks() {
  const map: Record<number, ShareLink> = {}
  await Promise.all(
    logs.value.map(async (log) => {
      try {
        const link = await getLogShareLink(log.id)
        if (link) map[log.id] = link
      } catch {
        /* 忽略单条失败 */
      }
    })
  )
  links.value = map
}

async function loadLogs() {
  if (!props.studentId) { logs.value = []; logTotal.value = 0; links.value = {}; return }
  const range = Array.isArray(dateRange.value) ? dateRange.value : []
  try {
    const res = await getContactLogsPaged({
      student_id: props.studentId,
      keyword: filters.keyword || undefined,
      scene: filters.scene || undefined,
      channel: filters.channel || undefined,
      status: filters.status || undefined,
      start: range[0] || undefined,
      end: range[1] || undefined,
      page: pageLogs.value,
      page_size: pageSizeLogs.value,
    })
    logs.value = res.items
    logTotal.value = res.total
  } catch {
    logs.value = []
    logTotal.value = 0
  }
  await loadLinks()
}

async function loadOverview() {
  try {
    overview.value = await getGuardianOverview({ days: OVERVIEW_DAYS, student_id: props.studentId || undefined })
  } catch {
    overview.value = null
  }
}

async function loadAll() {
  pageLogs.value = 1
  await Promise.all([loadGuardians(), loadLogs(), loadOverview()])
}

/* ===== 分享链接 ===== */
async function makeLink(log: ContactLog) {
  try {
    const link = await createShareLink(log.id)
    links.value = { ...links.value, [log.id]: link }
    ElMessage.success('已生成，7 天内有效')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '生成失败')
  }
}
async function copyLink(link: ShareLink) {
  const url = `${window.location.origin}${link.path}`
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.info(url)
  }
}
async function revoke(link: ShareLink) {
  if (!(await actionConfirm('撤销后家长将无法再打开该链接，确定撤销？', '撤销确认', { danger: true, confirmButtonText: '撤销' }))) return
  const updated = await revokeShareLink(link.id)
  links.value = { ...links.value, [updated.log_id]: updated }
  ElMessage.success('已撤销')
}
async function removeLog(log: ContactLog) {
  if (!(await actionConfirm('确定删除这条沟通记录？', '删除确认', { danger: true, confirmButtonText: '删除' }))) return
  await deleteContactLog(log.id)
  ElMessage.success('已删除')
  await Promise.all([loadLogs(), loadOverview()])
}

/* ===== 导入 / 导出 ===== */
const importInput = ref<HTMLInputElement | null>(null)

function onHeadCommand(cmd: string) {
  if (cmd === 'export') void handleExport()
  else if (cmd === 'template') void handleDownloadTemplate()
  else if (cmd === 'import') importInput.value?.click()
}

function buildFilterParams() {
  const range = Array.isArray(dateRange.value) ? dateRange.value : []
  return {
    student_id: props.studentId || undefined,
    keyword: filters.keyword || undefined,
    scene: filters.scene || undefined,
    channel: filters.channel || undefined,
    status: filters.status || undefined,
    start: range[0] || undefined,
    end: range[1] || undefined,
  }
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

async function handleExport() {
  try {
    const blob = await exportContactLogs(buildFilterParams())
    saveBlob(blob, '家校沟通台账.xlsx')
    ElMessage.success('台账已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function handleDownloadTemplate() {
  try {
    const blob = await downloadContactLogTemplate()
    saveBlob(blob, '家校沟通台账导入模板.xlsx')
    ElMessage.success('模板已下载')
  } catch {
    ElMessage.error('模板下载失败')
  }
}

async function handleImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const res = await importContactLogs(file)
    await Promise.all([loadLogs(), loadOverview()])
    const skipped = res.skipped.length ? `，跳过 ${res.skipped.length} 条` : ''
    const errors = res.errors.length ? `，失败 ${res.errors.length} 条` : ''
    ElMessage.success(`导入完成：新增 ${res.created} 条${skipped}${errors}`)
  } catch {
    ElMessage.error('导入失败，请检查文件格式')
  }
}

/* ===== 统计榜单聚焦 ===== */
function onFocusFromStats(id: number, name: string) {
  const hit = props.students.find((s) => s.id === id)
  if (hit) emit('select-student', hit)
  else emit('select-student', { id, name } as StudentSummary)
}

/* ===== 学生变化时重载 ===== */
watch(
  () => props.studentId,
  () => { void loadAll() }
)

onMounted(() => {
  logPresetContent.value = props.presetContent
  logPresetScene.value = props.presetScene
  if (props.presetContent && props.studentId) logVisible.value = true
  void loadAll()
})
</script>

<style scoped>
.gp-panel { display: flex; flex-direction: column; gap: 14px; }

/* 当前学生 */
.gp-who {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--tui-surface);
  border-top: 1px solid var(--tui-border);
  border-bottom: 1px solid var(--tui-border);
}
.gp-avatar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--tui-surface-muted);
  color: var(--tui-text);
  font-size: 14px;
  font-weight: 650;
}
.gp-avatar.is-sm { width: 34px; height: 34px; border-radius: 9px; font-size: 13px; }
.gp-who-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.gp-who-info b { font-size: 14px; font-weight: 650; color: var(--tui-text); }
.gp-who-info i { font-style: normal; font-size: 11.5px; color: var(--tui-text-quiet); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gp-who-select { flex: 0 0 118px; width: 118px; }

/* 视图切换 */
.gp-tabs {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 14px;
  background: var(--tui-surface);
  border-bottom: 1px solid var(--tui-border);
}
.gp-tab {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 10px 0 9px;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  font-family: inherit;
  font-size: 13px;
  color: var(--tui-text-tertiary);
  cursor: pointer;
}
.gp-tab.is-active { color: var(--tui-text); border-bottom-color: var(--tui-text); font-weight: 650; }
.gp-tab-count { font-size: 10.5px; color: var(--tui-text-quiet); font-variant-numeric: tabular-nums; }

.gp-sect { display: flex; flex-direction: column; gap: 10px; }

/* 工具条 */
.gp-toolbar { display: flex; align-items: center; gap: 8px; padding: 0 14px; flex-wrap: wrap; }
.gp-meta { flex: 1; min-width: 0; font-size: 11.5px; color: var(--tui-text-quiet); }
.gp-search { flex: 1; min-width: 120px; }
.gp-filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 9px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 8px;
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.gp-filter-btn.is-open { border-color: var(--tui-brand); color: var(--tui-brand-strong); }
.gp-filter-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--tui-brand); }
.gp-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--tui-text-tertiary);
  cursor: pointer;
}
.gp-icon-btn:hover { background: var(--tui-surface-muted); color: var(--tui-text); }

.gp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 30px;
  padding: 0 11px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 8px;
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}
.gp-btn:hover { border-color: #b9c0cc; color: var(--tui-text); }
.gp-btn:disabled { opacity: 0.55; cursor: default; }
.gp-btn.is-sm { height: 28px; padding: 0 9px; }

.gp-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 0 14px;
}
.gp-filters .gp-range { grid-column: 1 / -1; width: 100%; }
.gp-reset { grid-column: 1 / -1; justify-self: start; }

/* 列表：单容器 + 发丝分割，不做逐条卡片 */
.gp-list { background: var(--tui-surface); border-top: 1px solid var(--tui-border); border-bottom: 1px solid var(--tui-border); }
.gp-row { padding: 11px 14px; border-top: 1px solid var(--tui-hairline); }
.gp-list .gp-row:first-child { border-top: none; }
.gp-row-top { display: flex; align-items: center; gap: 10px; }
.gp-row-id { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.gp-row-name { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--tui-text); }
.gp-row-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gp-row-ops { flex: 0 0 auto; display: flex; gap: 10px; }
.gp-row-text {
  margin-top: 5px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tui-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}
.gp-row-acts {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 7px;
  flex-wrap: wrap;
}
.gp-act {
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
  cursor: pointer;
}
.gp-act:hover { color: var(--tui-text); }
.gp-tag {
  display: inline-block;
  padding: 1px 5px;
  border-radius: 5px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
  font-size: 10.5px;
  font-weight: 500;
}
.gp-tag.is-brand { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.gp-status { font-size: 10.5px; font-weight: 600; }
.gp-status.is-sent { color: var(--tui-success); }
.gp-status.is-pending { color: var(--tui-warn); }
.gp-status.is-failed { color: var(--tui-danger); }
.gp-status.is-draft { color: var(--tui-text-quiet); }
.gp-dot { flex: 0 0 auto; width: 6px; height: 6px; border-radius: 50%; background: #98a2b3; }
.gp-dot.tone-brand { background: var(--tui-brand); }
.gp-dot.tone-success { background: var(--tui-success); }
.gp-dot.tone-muted { background: var(--tui-text-quiet); }

.gp-link {
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-brand);
  cursor: pointer;
}
.gp-link.is-danger { color: var(--tui-danger); }
.gp-link.is-tail { margin-left: auto; }
.gp-link-valid { font-size: 11px; color: var(--tui-success); }
.gp-link-locked { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--tui-text-quiet); }

.gp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 22px 14px;
  background: var(--tui-surface);
  border-top: 1px solid var(--tui-border);
  border-bottom: 1px solid var(--tui-border);
  text-align: center;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.gp-pagination { display: flex; justify-content: center; }
.gp-file-input { display: none; }

/* ================= 方案 C · 关系地图（家校沟通同主题） ================= */
.gp-panel {
  --gp-ink: #12554a;
  --gp-ink-soft: #e9f4ef;
  --gp-ink-line: #cfe0d7;
}
.gp-who { background: transparent; border-color: var(--gp-ink-line); }
.gp-avatar { border-radius: 50%; background: var(--gp-ink); color: #fff; }
.gp-avatar.is-sm { border-radius: 50%; }
.gp-who-info b { color: #14201c; }
.gp-who-info i { color: #71867c; }
.gp-tabs { background: transparent; border-bottom-color: var(--gp-ink-line); }
.gp-tab { color: #71867c; }
.gp-tab.is-active { color: var(--gp-ink); border-bottom-color: var(--gp-ink); }
.gp-tab-count {
  min-width: 16px;
  padding: 1px 5px;
  border-radius: 999px;
  background: var(--gp-ink-soft);
  color: #2c6b59;
  text-align: center;
}
.gp-toolbar { padding-top: 2px; }
.gp-meta { color: #71867c; }
.gp-filter-btn { border-color: var(--gp-ink-line); background: #fff; color: #4f6b60; }
.gp-filter-btn.is-open { border-color: var(--gp-ink); color: var(--gp-ink); }
.gp-filter-dot { background: var(--gp-ink); }
.gp-btn { border-color: var(--gp-ink-line); background: #fff; color: #3f5c50; border-radius: 6px; }
.gp-btn:hover { border-color: #b9d2c6; color: var(--gp-ink); }
.gp-list { background: #fff; border-color: var(--gp-ink-line); }
.gp-row { border-top-color: #e5eee8; }
.gp-row:hover { background: #fbfefc; }
.gp-row-name { color: #14201c; }
.gp-row-sub { color: #71867c; }
.gp-row-text { color: #5f776c; }
.gp-tag { background: #f0f4f2; color: #6c8177; border-radius: 3px; }
.gp-tag.is-brand { background: var(--gp-ink-soft); color: #2c6b59; }
.gp-status.is-sent { color: #2c6b59; }
.gp-dot.tone-brand { background: #2c6b59; }
.gp-link { color: var(--gp-ink); }
.gp-act:hover { color: var(--gp-ink); }
.gp-empty { background: transparent; border-color: var(--gp-ink-line); color: #71867c; }
/* 统计区沿用 tui 的提示条 / 标签，但把蓝色换成关系地图的墨绿 */
.gp-panel :deep(.tui-section-hint) { background: var(--gp-ink-soft); color: #2c6b59; }
.gp-panel :deep(.tui-chip-brand) { background: var(--gp-ink-soft); color: #2c6b59; }

@media (max-width: 767px) {
  .gp-toolbar, .gp-filters { padding: 0 14px; }
  .gp-search { flex: 1 0 100%; order: -1; }
}
</style>
