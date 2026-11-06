<template>
  <div class="files-page">
    <!-- 移动端吸顶子页头；桌面端学生布局有侧边栏，不渲染该头，标题由下方 .files-title 承担 -->
    <SubPageHeader title="我的文件" :fallback="messagesPath" />

    <div class="files-inner">
      <h2 class="files-title">我的文件</h2>

      <div class="files-toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索文件名"
          clearable
          :prefix-icon="Search"
          @input="onSearch"
        />
        <span v-if="files.length" class="files-summary">{{ summaryText }}</span>
      </div>

      <div v-if="loading" class="files-skeleton" aria-hidden="true">
        <div v-for="i in 4" :key="i" class="sk-row">
          <span class="sk-thumb"></span>
          <span class="sk-lines"><i></i><i></i></span>
        </div>
      </div>

      <div v-else-if="!files.length" class="files-state">
        <span class="files-state-ico"><el-icon :size="26"><FolderOpened /></el-icon></span>
        <p class="files-state-title">
          {{ keyword.trim() ? `没有找到「${keyword.trim()}」` : '还没有聊天文档' }}
        </p>
        <p class="files-state-hint">
          <span v-if="keyword.trim()">换个关键词试试，或者清空搜索看全部文档</span>
          <template v-else>
            <span>聊过的 Word / Excel / PDF 会汇总在这里</span>
            <span>图片和语音请回到对应聊天里查看</span>
          </template>
        </p>
        <button v-if="keyword.trim()" type="button" class="files-state-reset" @click="resetSearch">
          清空搜索
        </button>
      </div>

      <template v-else>
        <section v-for="g in groups" :key="g.key" class="files-group">
          <h3 class="files-group-title">
            {{ g.label }}<span class="files-group-count">{{ g.items.length }}</span>
          </h3>
          <div class="files-card">
            <button
              v-for="f in g.items"
              :key="f.id"
              type="button"
              class="file-row"
              :title="`下载 ${f.name || '文件'}`"
              @click="openFile(f)"
            >
              <span class="file-thumb" :style="thumbStyle(f.name)">{{ extLabel(f.name) }}</span>
              <span class="file-main">
                <span class="file-name">{{ f.name || '未命名文件' }}</span>
                <span class="file-meta">
                  <template v-if="f.size">{{ formatSize(f.size) }}</template>
                  <i v-if="f.size" class="file-dot" aria-hidden="true"></i>
                  <span class="file-source" @click.stop="openSession(f)">{{ sourceLabel(f) }}</span>
                </span>
              </span>
              <span class="file-time">{{ formatRowTime(f.created_at) }}</span>
            </button>
          </div>
        </section>

        <p v-if="total > files.length" class="files-more">
          仅展示最近 {{ files.length }} 个文档，更早的可以回到聊天里翻
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FolderOpened, Search } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { getSharedFiles, type SharedFile } from '@/api/messages'
import { parseServerTime } from '@/utils/datetime'

/**
 * 我的文件（跨会话文档汇总）。
 *
 * 从旧「工作台」页抽出来的独立页：工作台页签在 v5 已被消息页取代、整页下线，
 * 但这张汇总表还在用（消息页 ＋ →「我的文件」），于是单独给它一个地址 /student/files。
 *
 * 只汇总**文档**：图片与语音留在聊天上下文里看（缩略图/语音条脱离会话没有意义，
 * 也把文件页冲成流水账），因此接口固定带 `file_type=file`，页面上不再给类型切换。
 */

const router = useRouter()
const route = useRoute()

/**
 * 角色前缀：本页学生端与教师端共用（/student/files、/teacher/files）。
 * 返回与「来源会话」都要落回**当前角色**的消息页，不能写死 /student ——
 * 教师从文件页点来源会被弹到学生的消息页（路由不存在 → 兜底 404 / 被守卫踢走）。
 */
const basePath = computed(() => (route.path.startsWith('/teacher') ? '/teacher' : '/student'))
const messagesPath = computed(() => `${basePath.value}/messages`)

const files = ref<SharedFile[]>([])
const total = ref(0)
const loading = ref(true)
const keyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

/** 文档扩展名 → 色块配色（钉钉色系，和消息页的语义色保持一致） */
const EXT_STYLES: Record<string, { fg: string; bg: string }> = {
  doc: { fg: '#0070d9', bg: '#e8f3ff' },
  docx: { fg: '#0070d9', bg: '#e8f3ff' },
  wps: { fg: '#0070d9', bg: '#e8f3ff' },
  xls: { fg: '#009a29', bg: '#e8ffea' },
  xlsx: { fg: '#009a29', bg: '#e8ffea' },
  csv: { fg: '#009a29', bg: '#e8ffea' },
  ppt: { fg: '#d96a00', bg: '#fff7e8' },
  pptx: { fg: '#d96a00', bg: '#fff7e8' },
  pdf: { fg: '#d93026', bg: '#ffece8' },
  zip: { fg: '#6a3ad4', bg: '#f3ebff' },
  rar: { fg: '#6a3ad4', bg: '#f3ebff' },
  '7z': { fg: '#6a3ad4', bg: '#f3ebff' },
  txt: { fg: '#5c6269', bg: '#f2f3f5' },
  md: { fg: '#5c6269', bg: '#f2f3f5' },
  json: { fg: '#5c6269', bg: '#f2f3f5' },
}
const EXT_FALLBACK = { fg: '#5c6269', bg: '#f2f3f5' }

function extOf(name: string) {
  const m = /\.([a-zA-Z0-9]{1,6})$/.exec(name || '')
  return m ? m[1].toLowerCase() : ''
}

function extLabel(name: string) {
  const ext = extOf(name)
  if (!ext) return '文件'
  return ext.length > 3 ? ext.slice(0, 3).toUpperCase() : ext.toUpperCase()
}

function thumbStyle(name: string) {
  const s = EXT_STYLES[extOf(name)] || EXT_FALLBACK
  return { color: s.fg, background: s.bg }
}

/** 大小口径：小于 1KB 也按 KB 展示，避免满屏「0.3 KB」式的零碎小数 */
function formatSize(bytes: number) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb < 10 ? kb.toFixed(1) : Math.round(kb)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb < 10 ? mb.toFixed(1) : Math.round(mb)} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

const summaryText = computed(() => {
  const bytes = files.value.reduce((sum, f) => sum + (f.size || 0), 0)
  const size = formatSize(bytes)
  return size ? `${files.value.length} 个 · ${size}` : `${files.value.length} 个`
})

const DAY = 24 * 60 * 60 * 1000
const GROUP_LABELS: Record<string, string> = {
  today: '今天',
  yesterday: '昨天',
  week: '近 7 天',
  earlier: '更早',
}

function startOfToday() {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

function tsOf(iso: string) {
  const ts = parseServerTime(iso)
  return Number.isNaN(ts) ? 0 : ts
}

function groupKeyOf(ts: number) {
  const base = startOfToday()
  if (ts >= base) return 'today'
  if (ts >= base - DAY) return 'yesterday'
  if (ts >= base - 6 * DAY) return 'week'
  return 'earlier'
}

/** 按「今天 / 昨天 / 近 7 天 / 更早」分组，组内保持接口给的倒序 */
const groups = computed(() => {
  const buckets = new Map<string, SharedFile[]>()
  for (const f of files.value) {
    const key = groupKeyOf(tsOf(f.created_at))
    const arr = buckets.get(key)
    if (arr) arr.push(f)
    else buckets.set(key, [f])
  }
  return ['today', 'yesterday', 'week', 'earlier']
    .filter((k) => buckets.has(k))
    .map((k) => ({ key: k, label: GROUP_LABELS[k], items: buckets.get(k)! }))
})

/** 行尾时间：今天/昨天只给时分，今年给月日，跨年补上年份 */
function formatRowTime(iso: string) {
  const ts = tsOf(iso)
  if (!ts) return ''
  const d = new Date(ts)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const key = groupKeyOf(ts)
  if (key === 'today' || key === 'yesterday') return `${hh}:${mm}`
  if (d.getFullYear() === new Date().getFullYear()) return `${d.getMonth() + 1}月${d.getDate()}日`
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}

function sourceLabel(f: SharedFile) {
  const name = f.session_name || '会话'
  return f.is_group ? `群 · ${name}` : name
}

async function load() {
  loading.value = true
  try {
    const params: { keyword?: string; file_type: string } = { file_type: 'file' }
    const kw = keyword.value.trim()
    if (kw) params.keyword = kw
    const res = await getSharedFiles(params)
    files.value = res.items || []
    total.value = res.total ?? files.value.length
  } catch {
    files.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/** 输入防抖 300ms：边打边搜，但不必每个字符都打一次接口 */
function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { void load() }, 300)
}

function resetSearch() {
  keyword.value = ''
  void load()
}

/** 打开文件：文档直接下载（与消息气泡内的点击行为一致） */
function openFile(f: SharedFile) {
  const a = document.createElement('a')
  a.href = f.url
  a.rel = 'noopener'
  a.download = f.name || '文件'
  a.click()
}

/** 点来源会话 → 回到消息页并打开那条会话（消息页按 ?chat= 认路由参数） */
function openSession(f: SharedFile) {
  void router.push({ path: messagesPath.value, query: { chat: f.session_key } })
}

onMounted(load)
onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.files-page {
  min-height: 100%;
  background: var(--dt-bg, #f5f6f7);
}

/* 移动端：整屏覆盖子页（与作品集 / 资讯搜索同一形式）。
   **必须是 fixed**：路由返回时离场页与进场页同时在场，两者若都留在
   .main-area（flex column）里就会互相分摊高度 —— 实测消息页被压成 height:0，
   子页滑出的那 320ms 里看到的就是一片底色空白。fixed 后离场页不在流内，
   消息页照常占满整屏。根元素同时自滚（原来靠外层滚动，fixed 后没人替它滚）。
   z-index 1500：盖过顶栏(100)与底部导航(1000)，低于 Element Plus 弹层基准(2000+)。 */
@media (max-width: 767px) {
  .files-page {
    position: fixed;
    inset: 0;
    z-index: 1500;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
  }
  /* 页头吸顶：滚动容器换成根元素后，子页头要自己贴住顶部 */
  .files-page > .tui-appbar {
    position: sticky;
    top: 0;
    left: auto;
    right: auto;
    z-index: 5;
  }
  /* 整屏子页没有底部导航，末行要自己让出手势条 */
  .files-inner { padding-bottom: calc(96px + env(safe-area-inset-bottom, 0px)); }
}

.files-inner {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px 16px 96px;
}

/* 桌面端标题：移动端由 SubPageHeader 承担，这里隐藏避免重复 */
.files-title {
  margin: 0 0 14px;
  font-size: 20px;
  font-weight: 680;
  letter-spacing: -0.2px;
  color: var(--dt-text, #1f2430);
}

.files-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.files-toolbar :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: var(--dt-surface, #fff);
  box-shadow: none;
  border: 1px solid transparent;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.files-toolbar :deep(.el-input__wrapper.is-focus) {
  border-color: var(--dt-primary, #0089ff);
  box-shadow: 0 0 0 3px var(--dt-primary-ghost, rgba(0, 137, 255, 0.08));
}

.files-summary {
  flex-shrink: 0;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--dt-text-tertiary, #8a9099);
  white-space: nowrap;
}

/* ===== 分组 ===== */
.files-group + .files-group {
  margin-top: 18px;
}

.files-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 18px 4px 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--dt-text-tertiary, #8a9099);
}

.files-group:first-child .files-group-title {
  margin-top: 16px;
}

.files-group-count {
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--dt-text-quiet, #b6bcc4);
}

.files-card {
  background: var(--dt-surface, #fff);
  border-radius: var(--dt-radius, 12px);
  overflow: hidden;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 14px;
  border: none;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.14s ease;
}

.file-row + .file-row {
  box-shadow: inset 0 1px 0 var(--dt-divider, rgba(0, 0, 0, 0.06));
}

.file-row:hover {
  background: var(--dt-hover, rgba(0, 0, 0, 0.02));
}

.file-row:active {
  background: var(--dt-surface-press, #eaebed);
}

/* 扩展名色块：比通用文件图标更快认出「这是 Excel 还是 PDF」 */
.file-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.2px;
  text-transform: uppercase;
}

.file-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.25;
  color: var(--dt-text, #171a1d);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  line-height: 1.2;
  color: var(--dt-text-tertiary, #8a9099);
  font-variant-numeric: tabular-nums;
}

.file-dot {
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.6;
}

.file-source {
  max-width: 60%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: var(--dt-primary-strong, #0070d9);
}

.file-source:active {
  opacity: 0.7;
}

.file-time {
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--dt-text-quiet, #b6bcc4);
  font-variant-numeric: tabular-nums;
}

.files-more {
  margin: 14px 4px 0;
  font-size: 11.5px;
  text-align: center;
  color: var(--dt-text-quiet, #b6bcc4);
}

/* ===== 骨架屏：首屏不再空着等接口 ===== */
.files-skeleton {
  margin-top: 16px;
  padding: 4px 14px;
  border-radius: var(--dt-radius, 12px);
  background: var(--dt-surface, #fff);
}

.sk-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
}

.sk-row + .sk-row {
  box-shadow: inset 0 1px 0 var(--dt-divider, rgba(0, 0, 0, 0.06));
}

.sk-thumb,
.sk-lines i {
  background: linear-gradient(90deg, #eef0f3 25%, #f6f7f9 37%, #eef0f3 63%);
  background-size: 400% 100%;
  animation: sk-shimmer 1.3s ease-in-out infinite;
}

.sk-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 10px;
}

.sk-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sk-lines i {
  height: 10px;
  border-radius: 5px;
}

.sk-lines i:last-child {
  width: 42%;
  height: 9px;
}

@keyframes sk-shimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

@media (prefers-reduced-motion: reduce) {
  .sk-thumb,
  .sk-lines i { animation: none; }
}

/* ===== 空态 / 无结果 ===== */
.files-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 56px 24px 40px;
  text-align: center;
}

.files-state-ico {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 6px;
  border-radius: 18px;
  background: var(--dt-surface, #fff);
  color: var(--dt-text-quiet, #b6bcc4);
}

.files-state-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--dt-text-secondary, #5c6269);
}

.files-state-hint {
  margin: 0;
  max-width: 280px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--dt-text-quiet, #b6bcc4);
}

.files-state-hint span {
  display: block;
}

.files-state-reset {
  margin-top: 10px;
  padding: 7px 16px;
  border: none;
  border-radius: 999px;
  background: var(--dt-primary-soft, #e8f3ff);
  color: var(--dt-primary-strong, #0070d9);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}

@media (max-width: 767px) {
  .files-title { display: none; }
  .files-inner { padding: 12px 12px 96px; }
  .files-toolbar { gap: 10px; }
  .files-group:first-child .files-group-title { margin-top: 14px; }
}

/* 桌面端：两列独立卡片，信息密度更高，行分割线交给卡片间距 */
@media (min-width: 900px) {
  .files-card {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    background: transparent;
    overflow: visible;
  }

  .file-row {
    background: var(--dt-surface, #fff);
    border-radius: var(--dt-radius, 12px);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }

  .file-row + .file-row {
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }

  .file-row:hover {
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  }
}
</style>
