<template>
  <div :class="['sidebar', { collapsed }]">
    <!-- 统一 Header：始终显示切换按钮 -->
    <div class="sidebar-header">
      <div class="header-row">
        <el-tooltip :content="collapsed ? '展开侧边栏' : '收起侧边栏'" placement="right">
          <button
            type="button"
            class="toggle-btn"
            :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
            @click="store.sidebarCollapsed = !store.sidebarCollapsed"
          >
            <span class="toggle-icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4.5" width="18" height="15" rx="3.5" />
                <path d="M9.6 4.5v15" />
              </svg>
            </span>
          </button>
        </el-tooltip>
        <div class="search-wrap">
          <el-input
            ref="searchInputRef"
            v-model="search"
            placeholder="搜索对话记录"
            size="small"
            clearable
            class="search-input"
            :prefix-icon="Search"
            @keyup.esc="clearSearch"
          />
          <div v-if="isSearching" class="search-summary">
            <span v-if="totalHits > 0">找到 <b>{{ totalHits }}</b> 条对话</span>
            <span v-else>无匹配结果</span>
            <button type="button" class="search-clear" @click="clearSearch">清除</button>
          </div>
        </div>
        <el-button v-if="isMobile" text circle class="drawer-close" aria-label="关闭" @click="emit('close')">
          <el-icon :size="18"><Close /></el-icon>
        </el-button>
      </div>
      <div class="header-actions">
        <div class="sidebar-menu">
          <!-- 新建入口：点击直接下滑拉出「工作任务」列表（不再用下拉菜单） -->
          <button
            type="button"
            class="menu-row"
            aria-haspopup="listbox"
            :aria-expanded="newTaskPanelOpen"
            @click="toggleNewTaskPanel"
          >
            <span class="menu-icon">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
                <path d="M12 5.2v13.6M5.2 12h13.6" />
              </svg>
            </span>
            <span class="menu-label">新建工作任务</span>
            <svg
              xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
              class="menu-caret" :class="{ open: newTaskPanelOpen }" aria-hidden="true"
            >
              <path d="M6.6 9.4 12 14.8l5.4-5.4" />
            </svg>
          </button>

          <Transition name="task-slide" @before-enter="onTaskPanelBeforeEnter" @after-enter="onTaskPanelEnter" @before-leave="onTaskPanelLeave">
            <div v-show="newTaskPanelOpen && !isTeacher" class="task-slide-panel" ref="taskPanelRef">
              <ul class="task-type-list" role="listbox" aria-label="新建工作任务类型" ref="taskListRef">
                <li v-for="t in TASK_TYPES" :key="t.key" role="option" :aria-selected="false">
                  <button
                    type="button"
                    class="task-type-item"
                    :disabled="creatingTask"
                    @click="pickTaskType(t.key)"
                  >
                    <span class="task-type-icon">
                      <DtIcon :name="t.icon" :size="iconSize" />
                    </span>
                    <span class="task-type-main">
                      <span class="task-type-name">{{ t.label }}</span>
                      <span class="task-type-desc">{{ t.desc }}</span>
                    </span>
                  </button>
                </li>
              </ul>
            </div>
          </Transition>

          <button type="button" class="menu-row" @click="newNormal">
            <span class="menu-icon"><el-icon><ChatRound /></el-icon></span>
            <span class="menu-label">新对话</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 可滚动列表 -->
    <div class="sidebar-scroll" ref="scrollRef" @scroll.passive="onScroll">
      <!-- 置顶：豆包把置顶单独成组，不参与时间分组 -->
      <div v-if="filteredPinned.length" class="sidebar-section">
        <div class="section-header pinned-header">
          <el-icon :size="11"><Top /></el-icon>
          <span>置顶</span>
          <span v-if="isSearching" class="section-count">{{ filteredPinned.length }}</span>
        </div>
        <div class="section-items">
          <ConversationItem
            v-for="c in filteredPinned"
            :key="c.id"
            :conv="c"
            :active="c.id === store.activeId"
            :query="search"
            @select="selectConv(c)"
            @command="(cmd: string) => handleConvCmd(cmd, c)"
            @stage="(s: string) => setStage(c, s)"
          />
        </div>
      </div>

      <!-- 类型分组：普通对话 / 学科竞赛 / 毕业论文 / 社会实践 / 证书考取 / 学生工作 / 自定义项目 -->
      <div v-for="group in typeGroups" :key="group.key" class="sidebar-section">
        <div class="section-header">
          <span>{{ group.label }}</span>
          <span v-if="isSearching" class="section-count">{{ group.items.length }}</span>
        </div>
        <div class="section-items">
          <ConversationItem
            v-for="c in group.items"
            :key="c.id"
            :conv="c"
            :active="c.id === store.activeId"
            :query="search"
            @select="selectConv(c)"
            @command="(cmd: string) => handleConvCmd(cmd, c)"
            @stage="(s: string) => setStage(c, s)"
          />
        </div>
      </div>

      <!-- 搜索无结果 -->
      <div v-if="isSearching && totalHits === 0" class="search-empty">
        <el-icon :size="22"><Search /></el-icon>
        <p>未找到与「{{ keyword }}」相关的对话</p>
        <el-button size="small" text type="primary" @click="clearSearch">清除搜索</el-button>
      </div>

      <!-- 空列表 -->
      <div v-else-if="!isSearching && !store.list.length" class="empty-hint">
        <el-icon :size="26"><ChatDotRound /></el-icon>
        <span>{{ store.loading ? '加载中…' : '还没有对话记录' }}</span>
      </div>

      <!-- 加载更多：滚动到底部会自动触发，这里是手动兜底 -->
      <div v-if="!isSearching && store.hasMore" class="list-paging">
        <el-button
          text
          size="small"
          class="load-more"
          :loading="store.loading"
          @click="store.loadMore()"
        ><el-icon v-if="!store.loading" :size="13"><ArrowDown /></el-icon>加载更多</el-button>
      </div>
    </div>

    <!-- 撤销条：删除后 8 秒内可撤销 -->
    <Transition name="undo">
      <div v-if="undo" class="undo-bar">
        <el-icon :size="14" class="undo-icon"><RefreshLeft /></el-icon>
        <span class="undo-text">{{ undo.label }}</span>
        <button type="button" class="undo-action" @click="runUndo">撤销</button>
      </div>
    </Transition>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Top, Close, ArrowDown, RefreshLeft, ChatDotRound, ChatRound,
} from '@element-plus/icons-vue'
import DtIcon from '@/components/common/DtIcon.vue'
import { useConversationStore, TITLE_MAX_LEN, type Conversation } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useResponsive } from '@/composables/useResponsive'
import { filterConversations } from './conversationSearch'
import { groupByType } from './conversationMeta'
import ConversationItem from './ConversationItem.vue'

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher' }>(), { role: 'student' })
const store = props.role === 'teacher' ? useTeacherConversationStore() : useConversationStore()
const agentStore = props.role === 'teacher' ? useTeacherAgentStore() : useAgentStore()
const { isMobile } = useResponsive()
const emit = defineEmits<{ select: [conv: Conversation]; new: []; close: [] }>()

const isTeacher = computed(() => props.role === 'teacher')
const search = ref('')
const searchInputRef = ref<{ focus: () => void; blur: () => void } | null>(null)
const scrollRef = ref<HTMLElement | null>(null)
const undo = ref<{ label: string; run: () => Promise<void> } | null>(null)
let undoTimer: ReturnType<typeof setTimeout> | undefined
let searchTimer: ReturnType<typeof setTimeout> | undefined

/** 关键词：去掉首尾空格，避免只打空格时误判为搜索态 */
const keyword = computed(() => search.value.trim())
const isSearching = computed(() => keyword.value.length > 0)

/**
 * 分组：置顶单独成组（学生/教师一致），其余按对话类型分类：
 * 普通对话 / 学科竞赛 / 毕业论文 / 社会实践 / 证书考取 / 学生工作 / 自定义项目。
 * 展示层由本地过滤决定（标题/阶段/类型标签），服务端搜索只负责扩大候选集，
 * 因此即使服务端按英文 key 命中，界面也不会出现"没有可见匹配"的条目。
 */
const filteredPinned = computed(() => filterConversations(store.list.filter(c => c.pinned), search.value))
const typeGroups = computed(() => groupByType(filterConversations(store.list.filter(c => !c.pinned), search.value)))
const totalHits = computed(() =>
  filteredPinned.value.length + typeGroups.value.reduce((sum, g) => sum + g.items.length, 0),
)

const collapsed = computed(() => !isMobile.value && store.sidebarCollapsed)

function errorText(e: unknown, fallback: string): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}

function clearSearch() {
  search.value = ''
  searchInputRef.value?.blur()
}

/** 滚动到底部附近自动加载下一页 */
function onScroll() {
  const el = scrollRef.value
  if (!el || isSearching.value || !store.hasMore || store.loading) return
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 80) store.loadMore()
}

function selectConv(c: Conversation) {
  if (c.id === store.activeId) return
  emit('select', c)
}

/** 撤销条：8 秒后自动消失 */
function showUndo(label: string, run: () => Promise<void>) {
  undo.value = { label, run }
  if (undoTimer) clearTimeout(undoTimer)
  undoTimer = setTimeout(() => { undo.value = null }, 8000)
}

async function runUndo() {
  const pending = undo.value
  undo.value = null
  if (undoTimer) clearTimeout(undoTimer)
  if (!pending) return
  try {
    await pending.run()
    ElMessage.success('已撤销')
  } catch (e) {
    ElMessage.error(errorText(e, '撤销失败'))
  }
}

/** 当前会话被删除后，切到列表里的下一个会话（没有则回到新对话） */
function switchAfterRemoval() {
  const next = store.list[0]
  if (next) emit('select', next)
  else emit('new')
}

async function newNormal() {
  closeNewTaskPanel()
  if (agentStore.messages.length > 0 && !store.activeId) {
    await store.createConversation('normal')
  }
  store.setActive(null)
  agentStore.clearMessages()
  emit('new')
}

/* ── 新建工作任务：点击直接下滑拉出类型列表 ──
   顺序与 conversationMeta.ts 的 CONV_TYPE_ORDER / PROJECT_TEMPLATE_LABELS 保持一致，
   列表里新增类型时两处一起改，会话分组才不会漏项。 */
interface TaskType {
  key: string
  label: string
  desc: string
  /** DtIcon 图标名：与入口行同一套线条语言（24 网格 / 1.7 描边），不用 EP 的实心面图标 */
  icon: string
}

const TASK_TYPES: TaskType[] = [
  { key: 'competition', label: '学科竞赛', desc: '赛程拆解、备赛计划与进度跟踪', icon: 'trophy' },
  { key: 'thesis', label: '毕业论文', desc: '选题开题、文献综述到答辩', icon: 'book' },
  { key: 'practice', label: '社会实践', desc: '方案申报、执行落地与总结评优', icon: 'compass' },
  { key: 'certificate', label: '证书考取', desc: '考情分析、学习规划与备考', icon: 'medal' },
  { key: 'student_work', label: '学生工作', desc: '活动策划、审批协调与复盘', icon: 'clipboard' },
  { key: 'custom', label: '自定义项目', desc: '按自己的目标自由命名', icon: 'pencil' },
]

/** 图标按视口取尺寸：24 网格线条图标在 15px 以下细节会糊，移动端不低于 18px */
const iconSize = computed(() => (isMobile.value ? 18 : 16))
const newTaskPanelOpen = ref(false)
const creatingTask = ref(false)
const taskListRef = ref<HTMLElement | null>(null)
const taskPanelRef = ref<HTMLElement | null>(null)

function toggleNewTaskPanel() {
  if (isTeacher.value) return
  newTaskPanelOpen.value = !newTaskPanelOpen.value
}

function closeNewTaskPanel() {
  newTaskPanelOpen.value = false
}

/**
 * 展开前先量出列表的真实高度写入 --panel-h：
 * 之前用 max-height: 46vh 这类估算值，内容一旦超出估算高度，最后一行就会被裁掉
 * （截图里面板底部边框压在「按自己的目标自由命名」上就是这个原因）。
 */
async function onTaskPanelBeforeEnter() {
  await nextTick()
  const panel = taskPanelRef.value
  if (!panel) return
  const contentH = panel.scrollHeight
  // 可用高度 = 侧栏可视高度 - 面板顶部的偏移，留一点余量；超出则面板内滚动
  const list = taskListRef.value
  const top = list ? list.getBoundingClientRect().top : 0
  const avail = Math.max(160, window.innerHeight - top - 16)
  panel.style.setProperty('--panel-h', Math.min(contentH, avail) + 'px')
}

/** 面板落下后：内容超高时让它可滚动，并保证列表整体可见 */
async function onTaskPanelEnter() {
  const panel = taskPanelRef.value
  if (!panel) return
  const overflow = panel.scrollHeight > panel.clientHeight + 1
  panel.style.overflowY = overflow ? 'auto' : ''
  panel.scrollTop = 0
}

function onTaskPanelLeave() {
  creatingTask.value = false
  const panel = taskPanelRef.value
  if (panel) {
    panel.style.removeProperty('--panel-h')
    panel.style.overflowY = ''
  }
}

async function pickTaskType(template: string) {
  closeNewTaskPanel()
  await newProject(template)
}

async function newProject(template: string) {
  creatingTask.value = true
  try {
    await createProject(template)
  } finally {
    creatingTask.value = false
  }
}

async function createProject(template: string) {
  let title = ''
  if (template === 'competition') {
    try {
      const { value } = await ElMessageBox.prompt('', '新建学科竞赛项目', {
        inputPlaceholder: '请输入竞赛名称',
        customClass: 'sidebar-msgbox',
      })
      if (!value) return; title = value
    } catch { return }
  } else if (template === 'custom') {
    try {
      const { value } = await ElMessageBox.prompt('', '自定义项目', {
        inputPlaceholder: '请输入项目名称',
        customClass: 'sidebar-msgbox',
      })
      if (!value) return; title = value
    } catch { return }
  }
  const conv = await store.createConversation('project', template, title)
  if (conv) emit('select', conv)
  else emit('new')
}

/** 会话操作统一由列表行的 ⋯ 菜单触发（桌面/移动同一套实现） */
function handleConvCmd(cmd: string, c: Conversation) {
  switch (cmd) {
    case 'rename': return renameConv(c)
    case 'delete': return removeConv(c)
    case 'pin': return setPinned(c, true)
    case 'unpin': return setPinned(c, false)
  }
}

async function renameConv(c: Conversation) {
  let value: string
  try {
    const res = await ElMessageBox.prompt(' ', '重命名对话', {
      inputValue: c.title,
      inputPlaceholder: '请输入对话标题',
      customClass: 'sidebar-msgbox',
      inputValidator: (v: string) => {
        const t = (v || '').trim()
        if (!t) return '标题不能为空'
        if (t.length > TITLE_MAX_LEN) return `标题不能超过 ${TITLE_MAX_LEN} 个字符`
        return true
      },
    })
    value = (res.value || '').trim()
  } catch {
    return
  }
  if (!value || value === c.title) return
  try {
    await store.updateConversation(c.id, { title: value })
    ElMessage.success('已重命名')
  } catch (e) {
    ElMessage.error(errorText(e, '重命名失败'))
  }
}

async function setPinned(c: Conversation, pinned: boolean) {
  try {
    await store.updateConversation(c.id, { pinned })
    ElMessage.success(pinned ? '已置顶' : '已取消置顶')
  } catch (e) {
    ElMessage.error(errorText(e, pinned ? '置顶失败' : '取消置顶失败'))
  }
}

async function setStage(c: Conversation, stage: string) {
  if (stage === c.project_stage) return
  try {
    await store.updateConversation(c.id, { project_stage: stage })
    ElMessage.success(`阶段已更新为「${stage}」`)
  } catch (e) {
    ElMessage.error(errorText(e, '阶段更新失败'))
  }
}

async function removeConv(c: Conversation) {
  const wasActive = store.activeId === c.id
  try {
    await store.deleteConversation(c.id)
    if (wasActive) switchAfterRemoval()
    showUndo(`已删除「${c.title}」`, async () => {
      const restored = await store.restoreConversation(c.id)
      if (wasActive && restored) emit('select', restored)
    })
  } catch (e) {
    ElMessage.error(errorText(e, '删除失败'))
  }
}

/** 搜索：本地即时过滤 + 防抖请求服务端候选集（覆盖全部会话，而非仅已加载部分） */
watch(search, (v) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    await store.setQuery(v.trim())
    if (scrollRef.value) scrollRef.value.scrollTop = 0
  }, 250)
})

/** 新会话创建后回到列表顶部，避免看不到刚建的对话 */
watch(() => store.total, (n, o) => {
  if (n > o && scrollRef.value && scrollRef.value.scrollTop < 40) scrollRef.value.scrollTop = 0
})

onMounted(() => {
  // ChatShell 已经拉过一次；仅在独立挂载（列表为空）时补一次
  if (!store.list.length) store.fetchList()
})

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
  if (undoTimer) clearTimeout(undoTimer)
})

/** 从移动端切到桌面端（或反向）时收起下滑列表，避免残留展开态 */
watch(isMobile, () => closeNewTaskPanel())
</script>

<style scoped>
.sidebar {
  width: 100%; height: 100%;
  background: #fafafa; border-right: 1px solid #f0f0f0;
  display: flex; flex-direction: column; flex-shrink: 0;
  overflow: hidden;
}
.sidebar.collapsed .search-wrap,
.sidebar.collapsed .header-actions,
.sidebar.collapsed .sidebar-scroll { display: none; }

/* 头部区域 */
.sidebar-header {
  flex-shrink: 0;
  padding: 6px 10px 4px;
}

/* 头部首行：桌面端收起按钮 + 搜索框（搜索框占满整行，自动换行到第二行） */
.header-row { display: flex; align-items: center; flex-wrap: wrap; gap: 2px; row-gap: 6px; margin-bottom: 6px; }
/* 折叠按钮（照搬豆包：无边框幽灵按钮 + 线性侧边栏图标，hover 中性浅灰） */
.toggle-btn {
  width: 28px; height: 28px; flex-shrink: 0; padding: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; background: transparent; border-radius: 8px;
  color: #6b7280; cursor: pointer;
  transition: background .15s ease, color .15s ease;
}
.toggle-btn:hover { background: rgba(15,23,42,.05); color: #1f2937; }
.toggle-btn:active { background: rgba(15,23,42,.08); }
.toggle-icon { display: flex; width: 17px; height: 17px; }
.toggle-icon svg { width: 100%; height: 100%; display: block; }
.header-actions { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.search-input :deep(.el-input__wrapper) { border-radius: 6px; background: #f0f0f0; box-shadow: none; border: 1px solid transparent; padding: 0 6px; min-height: 24px; }
.search-input :deep(.el-input__inner) { font-size: 11px; height: 22px; }
.search-input :deep(.el-input__prefix) { font-size: 12px; }
.search-input :deep(.el-input__wrapper:hover) { border-color: #e0e0e0; }
.search-input :deep(.el-input__wrapper.is-focus) { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,.08); }
.search-wrap { width: 100%; }
.search-summary {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 4px 2px 0; font-size: 10px; color: #9aa0a6;
}
.search-summary b { color: #6366f1; font-weight: 600; }
.search-clear {
  border: none; background: transparent; padding: 0; font-size: 10px;
  color: #909399; cursor: pointer; transition: color .15s ease;
}
.search-clear:hover { color: #6366f1; }
.section-count {
  margin-left: auto; font-size: 10px; color: #b0b3b8;
  font-variant-numeric: tabular-nums;
}
.search-empty {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 28px 16px; color: #c0c4cc; text-align: center;
  animation: fadeIn 0.2s ease-out;
}
.search-empty p { margin: 6px 0 0; font-size: 12px; color: #b0b3b8; word-break: break-all; }

/* 顶部入口（照搬豆包：左对齐线性图标 + 无底色整行） */
.sidebar-menu { display: flex; flex-direction: column; gap: 2px; width: 100%; }
.sidebar-menu :deep(.el-dropdown) { display: block; width: 100%; }
.menu-row {
  display: flex; align-items: center; gap: 10px;
  width: 100%; min-height: 32px; padding: 0 8px;
  border: none; background: transparent; border-radius: 8px;
  font-size: 12.5px; color: #4b5563; text-align: left; cursor: pointer;
  transition: background .15s ease, color .15s ease;
}
.menu-row:hover { background: rgba(15,23,42,.05); color: #1f2937; }
.menu-row:active { background: rgba(15,23,42,.1); transition-duration: 0s; }
.menu-icon {
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; font-size: 16px; color: #6b7280;
  transition: color .15s ease;
}
.menu-icon svg { width: 100%; height: 100%; display: block; }
.menu-icon :deep(.el-icon) { font-size: inherit; }
.menu-row:hover .menu-icon { color: #374151; }
.menu-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.menu-caret {
  flex-shrink: 0; width: 14px; height: 14px; color: #9aa0a6;
  transition: transform .22s cubic-bezier(.4, 0, .2, 1), color .15s ease;
}
.menu-caret.open { transform: rotate(180deg); color: #6b7280; }

/* ── 新建工作任务：点击后自入口下方下滑展开的类型列表 ── */
.task-slide-panel {
  overflow: hidden;
  padding: 2px 0 4px;
  /* 展开高度由 JS 量取的真实内容高度写入 --panel-h；
     只有内容超出可用高度时才在面板内滚动，避免把最后一行裁掉 */
  max-height: none;
}
.task-type-list {
  list-style: none; margin: 0; padding: 0;
  border-radius: 10px;
  background: #fff;
  box-shadow: inset 0 0 0 1px #f0f1f4;
  overflow: visible;
}
.task-type-item {
  display: flex; align-items: center; gap: 9px;
  width: 100%; padding: 8px 10px;
  border: none; border-radius: 0; background: transparent;
  cursor: pointer; text-align: left; font-family: inherit;
  transition: background .15s ease;
}
.task-type-list li:first-child .task-type-item { border-radius: 10px 10px 0 0; }
.task-type-list li:last-child .task-type-item { border-radius: 0 0 10px 10px; }
/* 点击反馈：只在按下的瞬间变暗，松手立刻恢复（::active 只在按住期间生效） */
.task-type-item:active:not(:disabled) { background: rgba(15, 23, 42, .1); transition-duration: 0s; }
.task-type-item:disabled { opacity: .55; cursor: default; }
/* 图标保持单色：与「新对话」入口同一灰阶，不做彩色底、不做彩色前景 */
.task-type-icon {
  flex-shrink: 0; width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  color: #6b7280;
}
.task-type-icon :deep(.dt-icon) { display: block; }
.task-type-item:active:not(:disabled) .task-type-icon { color: #1f2937; }
.task-type-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.task-type-name {
  font-size: 12.5px; font-weight: 500; color: #1f2937;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.task-type-desc {
  font-size: 10.5px; color: #9aa0a6;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 下滑展开 / 收起（max-height 过渡，收起时高度平滑归零） */
.task-slide-enter-active,
.task-slide-leave-active {
  overflow: hidden;
  transition: max-height .26s cubic-bezier(.4, 0, .2, 1), opacity .2s ease;
}
.task-slide-enter-from,
.task-slide-leave-to {
  max-height: 0;
  opacity: 0;
}
.task-slide-enter-to,
.task-slide-leave-from { max-height: var(--panel-h, 1000px); opacity: 1; }

/* 可滚动列表 */
.sidebar-scroll {
  flex: 1; overflow-y: auto; min-height: 0; padding: 0 4px 8px;
  scrollbar-width: none; -ms-overflow-style: none;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
.sidebar-scroll::-webkit-scrollbar { display: none; }

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 时间分组标题：豆包式静态小标题，不可点击、无折叠箭头 */
.sidebar-section { margin-bottom: 4px; }
.section-header {
  display: flex; align-items: center; gap: 4px; padding: 6px 8px 2px;
  font-size: 11px; color: #a8adb5; user-select: none;
  letter-spacing: .5px;
}
.section-header .el-icon { font-size: 10px; }
.pinned-header { color: #8a8f98; }
.section-items { margin: 2px 0; }

/* 列表分页（随列表滚动） */
.list-paging {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 6px 4px 2px;
}
.load-more { font-size: 11px; color: #6366f1; }
.load-more :deep(.el-icon) { margin-right: 4px; vertical-align: -2px; }

/* 空列表提示 */
.empty-hint {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  text-align: center; font-size: 11px; color: #c2c6cc; padding: 26px 12px;
  animation: fadeIn 0.3s ease-out;
}
.empty-hint :deep(.el-icon) { color: #d7dae0; }

/* 撤销条：深色胶囊，移动端为 44px 可点高度 */
.undo-bar {
  flex-shrink: 0; display: flex; align-items: center; gap: 8px;
  margin: 6px 10px 8px; padding: 9px 12px;
  border-radius: 999px;
  background: #1f2937; color: #f9fafb;
  box-shadow: 0 6px 18px rgba(15, 23, 42, .22);
}
.undo-icon { flex-shrink: 0; color: #a5b4fc; }
.undo-text {
  flex: 1; min-width: 0; font-size: 11.5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.undo-action {
  flex-shrink: 0; border: none; background: transparent; padding: 3px 4px;
  font-size: 12px; font-weight: 600; color: #a5b4fc; cursor: pointer;
}
.undo-action:hover { color: #ffffff; text-decoration: underline; }

/* 撤销条淡入淡出（删除后 8 秒内可撤销） */
.undo-enter-active,
.undo-leave-active { transition: opacity 0.25s ease; }
.undo-enter-from,
.undo-leave-to {
  opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; border-top-width: 0;
}
.undo-enter-to,
.undo-leave-from { opacity: 1; max-height: 140px; }

/* 新建项目类型下拉：移动端整行 44px */
.template-dropdown-menu { padding: 6px; border-radius: 12px; }
.template-dropdown-menu :deep(.el-dropdown-menu__item) { font-size: 13px; border-radius: 8px; }
.template-dropdown-menu :deep(.el-dropdown-menu__item:hover) { background: rgba(99,102,241,.06); color: #6366f1; }

/* 移动端适配 */
@media (max-width: 767px) {
  .sidebar { width: 100%; border-right: none; }
  .sidebar.collapsed { width: 100%; }
  .sidebar.collapsed .header-actions,
  .sidebar.collapsed .sidebar-scroll { display: block !important; }
  .sidebar.collapsed .header-actions { display: flex !important; }
  .toggle-btn { display: none; }

  /* 抽屉顶部：搜索框（原「对话记录」标题位置）+ 关闭按钮 */
  .sidebar-header {
    padding: calc(12px + env(safe-area-inset-top, 0px)) 12px 14px;
    border-bottom: 1px solid #f0f1f4;
    background: #fff;
  }
  .header-row { margin-bottom: 10px; gap: 6px; row-gap: 6px; flex-wrap: nowrap; }
  /* 搜索框紧随收起按钮的位置，占满剩余宽度；关闭按钮固定在右侧 */
  .search-wrap { flex: 1 1 auto; width: auto; min-width: 0; }
  .drawer-close {
    width: 34px; height: 34px; flex-shrink: 0;
    color: #9aa0a6; border-radius: 10px;
  }
  .drawer-close:active { background: rgba(15, 23, 42, .06); }

  /* ── 移动端对话记录搜索框 ──
     触屏可点区域：高度 42px、字号 14px（桌面端为 24px / 11px 的紧凑密度） */
  .search-input :deep(.el-input__wrapper) {
    min-height: 42px;
    padding: 0 10px;
    border-radius: 12px;
    background: #f4f5f7;
    border: 1px solid #eceef2;
  }
  .search-input :deep(.el-input__inner) { height: 40px; font-size: 14px; }
  .search-input :deep(.el-input__prefix) { font-size: 16px; color: #9aa0a6; margin-right: 2px; }
  .search-input :deep(.el-input__suffix) { font-size: 15px; color: #b0b3b8; }
  .search-input :deep(.el-input__wrapper:hover) { border-color: #e2e4ea; }
  .search-input :deep(.el-input__wrapper.is-focus) {
    background: #fff;
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99,102,241,.12);
  }
  .search-summary { font-size: 12px; padding: 7px 2px 0; }
  .search-clear { font-size: 12px; padding: 4px 2px; }
  .search-empty { padding: 40px 20px; }
  .search-empty p { font-size: 13px; }

  /* 新建入口：照搬豆包的整行列表（左对齐线性图标 + 无底色，非胶囊） */
  .header-actions { gap: 12px; }
  .sidebar-menu { gap: 2px; }
  .menu-row {
    min-height: 46px; gap: 12px; padding: 0 10px;
    border-radius: 10px; font-size: 15px; color: #1f2937;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
  .menu-row:active { background: rgba(15,23,42,.1); transition-duration: 0s; }
  .menu-icon { width: 20px; height: 20px; font-size: 20px; color: #4b5563; }

  /* 工作任务下滑列表：整行 48px，字号放大到触屏可读 */
  .menu-caret { width: 16px; height: 16px; }
  .task-slide-panel { max-height: none; }
  .task-type-list { border-radius: 12px; }
  .task-type-item {
    gap: 12px; padding: 12px 14px; border-radius: 0;
    min-height: 52px;
    /* manipulation：保留滚动/缩放，去掉 300ms 双击缩放延迟；按住滑过不计为按下 */
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    transition: background .12s ease;
  }
  .task-type-list li:first-child .task-type-item { border-radius: 12px 12px 0 0; }
  .task-type-list li:last-child .task-type-item { border-radius: 0 0 12px 12px; }
  .task-type-icon { width: 22px; height: 22px; color: #4b5563; }
  .task-type-name { font-size: 15px; }
  .task-type-desc { font-size: 12px; }

  /* 分组标题：静态小标题，触屏下只作为分节留白 */
  .section-header {
    min-height: 30px; padding: 10px 8px 2px; font-size: 12px;
  }
  .section-header .el-icon { font-size: 12px; }
  .section-count { font-size: 11px; }
  .pinned-header { min-height: 26px; }

  /* 列表分页：整行可点 */
  .list-paging { gap: 0; padding: 8px 4px 4px; }
  .load-more {
    font-size: 13px; min-height: 44px; width: 100%;
    border-radius: 10px; color: #6366f1;
    touch-action: manipulation;
  }
  .load-more:active { background: rgba(99,102,241,.08); }
  .empty-hint { font-size: 13px; padding: 44px 16px; gap: 10px; }

  /* 撤销条：底部留白交给安全区 */
  .undo-bar {
    margin: 6px 10px calc(10px + env(safe-area-inset-bottom, 0px));
    padding: 11px 14px;
  }
  .undo-icon { font-size: 16px; }
  .undo-text { font-size: 12.5px; }
  .undo-action { font-size: 13px; padding: 6px 8px; touch-action: manipulation; }

  /* 项目类型下拉：整行可点 */
  .template-dropdown-menu :deep(.el-dropdown-menu__item) {
    min-height: 44px; font-size: 14px; padding: 10px 14px;
    touch-action: manipulation;
  }
}
</style>

<style>
.sidebar-msgbox {
  border-radius: 24px !important;
  padding: 24px 28px 20px !important;
}
.sidebar-msgbox .el-message-box__header {
  padding-bottom: 12px !important;
}
.sidebar-msgbox .el-message-box__title {
  font-size: 15px !important;
  font-weight: 600 !important;
}
.sidebar-msgbox .el-message-box__content {
  padding: 0 !important;
}
.sidebar-msgbox .el-message-box__input {
  padding-top: 0 !important;
}
.sidebar-msgbox .el-input__wrapper {
  border-radius: 12px !important;
  box-shadow: 0 0 0 1px #e4e7ed inset !important;
}
.sidebar-msgbox .el-input__wrapper:focus-within {
  box-shadow: 0 0 0 1px #6366f1 !important;
}
.sidebar-msgbox .el-message-box__btns {
  padding-top: 16px !important;
}
.sidebar-msgbox .el-message-box__btns .el-button {
  border-radius: 10px !important;
  height: 34px !important;
}
</style>