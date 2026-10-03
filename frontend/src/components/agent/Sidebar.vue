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
          <!-- 豆包式入口：左对齐线性图标 + 无底色整行，新工作任务在前 -->
          <el-dropdown v-if="!isTeacher" trigger="click" placement="bottom-start" @command="newProject">
            <button type="button" class="menu-row">
              <span class="menu-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M11 1.99882C11.5522 1.99882 11.9999 2.44659 12 2.99882C12 3.5511 11.5523 3.99882 11 3.99882C9.58364 3.99882 8.58138 3.99928 7.79785 4.06327C7.02597 4.12634 6.5539 4.2457 6.18359 4.43436C5.43112 4.81782 4.81902 5.42995 4.43555 6.18241C4.24687 6.5527 4.12752 7.02482 4.06445 7.79667C4.00047 8.58018 4 9.58251 4 10.9988V11.9988C4 13.8959 4.00112 15.2389 4.11328 16.2742C4.22343 17.2906 4.43078 17.8922 4.76367 18.3504C5.01032 18.6898 5.309 18.9885 5.64844 19.2351C6.10667 19.5681 6.70818 19.7754 7.72461 19.8855C8.75997 19.9977 10.1029 19.9988 12 19.9988H13C14.4164 19.9988 15.4186 19.9984 16.2021 19.9344C16.9741 19.8713 17.4461 19.752 17.8164 19.5633C18.5689 19.1798 19.181 18.5677 19.5645 17.8152C19.7531 17.4449 19.8725 16.9728 19.9355 16.201C19.9995 15.4175 20 14.4151 20 12.9988C20.0001 12.4466 20.4478 11.9988 21 11.9988C21.5522 11.9988 21.9999 12.4466 22 12.9988C22 14.3823 22.0009 15.4802 21.9287 16.3641C21.8555 17.2596 21.7019 18.0233 21.3457 18.7225C20.7705 19.8514 19.8526 20.7693 18.7236 21.3445C18.0244 21.7008 17.2608 21.8544 16.3652 21.9275C15.4813 21.9997 14.3835 21.9988 13 21.9988H12C10.1475 21.9988 8.67782 22.0003 7.50977 21.8738C6.32316 21.7453 5.32958 21.475 4.47363 20.8533C3.96429 20.4832 3.51557 20.0345 3.14551 19.5252C2.52381 18.6693 2.25356 17.6756 2.125 16.4891C1.99848 15.321 2 13.8512 2 11.9988V10.9988C2 9.61535 1.99909 8.51745 2.07129 7.63358C2.14446 6.73808 2.29807 5.97437 2.6543 5.27518C3.22954 4.14626 4.14743 3.22834 5.27637 2.65311C5.97557 2.29689 6.73923 2.14327 7.63477 2.07011C8.51866 1.9979 9.61648 1.99882 11 1.99882ZM17.0459 2.70683C18.2174 1.53524 20.1174 1.53521 21.2891 2.70683C22.4598 3.87818 22.4598 5.77752 21.2891 6.94901L13.8271 14.4139C13.482 14.7592 13.2298 15.0167 12.9346 15.2254C12.6866 15.4005 12.4187 15.5472 12.1377 15.6619C11.8029 15.7986 11.4497 15.8732 10.9727 15.9783L9.9375 16.2068C9.75332 16.2474 9.54843 16.293 9.37305 16.3152C9.19723 16.3375 8.9042 16.3588 8.59375 16.2332C8.21725 16.0808 7.91905 15.7815 7.7666 15.4051C7.64121 15.0951 7.66139 14.8026 7.68359 14.6267C7.70579 14.4513 7.75139 14.2456 7.79199 14.0613L8.02149 13.0242C8.12639 12.5482 8.20065 12.1964 8.33692 11.8621C8.45152 11.5812 8.59848 11.3131 8.77344 11.0652C8.98179 10.7702 9.23812 10.5177 9.58301 10.1726L17.0459 2.70683ZM19.875 4.12089C19.4844 3.73029 18.8505 3.73117 18.46 4.12186L10.9971 11.5867C10.6059 11.9781 10.4944 12.0952 10.4072 12.2185C10.3199 12.3423 10.2457 12.4757 10.1885 12.616C10.1314 12.756 10.0939 12.9138 9.97461 13.4549L9.8125 14.1853L10.542 14.0252C11.084 13.9057 11.2417 13.8666 11.3818 13.8094C11.5222 13.752 11.6564 13.68 11.7803 13.5926C11.9038 13.5053 12.0203 13.3928 12.4121 13.0008L19.875 5.53495C20.2649 5.14455 20.2648 4.5113 19.875 4.12089Z" />
                </svg>
              </span>
              <span class="menu-label">新工作任务</span>
            </button>
            <template #dropdown>
              <el-dropdown-menu class="template-dropdown-menu">
                <el-dropdown-item command="competition">学科竞赛</el-dropdown-item>
                <el-dropdown-item command="thesis">毕业论文</el-dropdown-item>
                <el-dropdown-item command="practice">社会实践</el-dropdown-item>
                <el-dropdown-item command="certificate">证书考取</el-dropdown-item>
                <el-dropdown-item command="student_work">学生工作</el-dropdown-item>
                <el-dropdown-item command="custom">自定义项目</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

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
            @menu="openSheet(c)"
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
            @menu="openSheet(c)"
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

    <!-- 移动端：豆包式底部会话操作面板（列表 ⋯ 打开） -->
    <ConversationActionsSheet
      v-model:visible="sheetVisible"
      :conv="sheetConv"
      @command="onSheetCommand"
      @stage="onSheetStage"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Top, Close, ArrowDown, RefreshLeft, ChatDotRound, ChatRound,
} from '@element-plus/icons-vue'
import { useConversationStore, TITLE_MAX_LEN, type Conversation } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'
import { useResponsive } from '@/composables/useResponsive'
import { filterConversations } from './conversationSearch'
import { groupByType } from './conversationMeta'
import ConversationItem from './ConversationItem.vue'
import ConversationActionsSheet from './ConversationActionsSheet.vue'

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
/** 移动端底部操作面板：绑定的会话与显隐 */
const sheetVisible = ref(false)
const sheetConv = ref<Conversation | null>(null)
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

/** 打开移动端底部操作面板 */
function openSheet(c: Conversation) {
  sheetConv.value = c
  sheetVisible.value = true
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
  if (agentStore.messages.length > 0 && !store.activeId) {
    await store.createConversation('normal')
  }
  store.setActive(null)
  agentStore.clearMessages()
  emit('new')
}

async function newProject(template: string) {
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

function handleConvCmd(cmd: string, c: Conversation) {
  switch (cmd) {
    case 'rename': return renameConv(c)
    case 'delete': return removeConv(c)
    case 'pin': return setPinned(c, true)
    case 'unpin': return setPinned(c, false)
  }
}

/** 移动端底部面板：动作与桌面端菜单共用同一套实现 */
function onSheetCommand(cmd: string) {
  const c = sheetConv.value
  if (!c) return
  handleConvCmd(cmd, c)
}

function onSheetStage(stage: string) {
  const c = sheetConv.value
  if (!c) return
  setStage(c, stage)
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
.menu-row:active { background: rgba(15,23,42,.08); }
.menu-icon {
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; font-size: 16px; color: #6b7280;
  transition: color .15s ease;
}
.menu-icon svg { width: 100%; height: 100%; display: block; }
.menu-icon :deep(.el-icon) { font-size: inherit; }
.menu-row:hover .menu-icon { color: #374151; }
.menu-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

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
  .menu-row:active { background: rgba(15,23,42,.07); }
  .menu-icon { width: 20px; height: 20px; font-size: 20px; color: #4b5563; }

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