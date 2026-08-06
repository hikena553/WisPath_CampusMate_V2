<template>
  <div :class="['sidebar', { collapsed }]">
    <!-- 统一 Header：始终显示切换按钮 -->
    <div class="sidebar-header">
      <div class="header-row">
        <el-tooltip :content="collapsed ? '展开侧边栏' : '收起侧边栏'" placement="right">
          <el-button text circle class="toggle-btn" @click="store.sidebarCollapsed = !store.sidebarCollapsed">
            <el-icon :size="18"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </el-button>
        </el-tooltip>
        <div class="header-title">对话列表</div>
      </div>
      <div class="header-actions">
        <el-input v-model="search" placeholder="搜索..." size="small" clearable class="search-input" :prefix-icon="Search" />
        <div class="action-btns">
          <el-button size="small" type="primary" @click="newNormal"><el-icon><Plus /></el-icon><span>新对话</span></el-button>
          <el-dropdown v-if="props.role !== 'teacher'" trigger="click" @command="newProject">
            <el-button size="small" plain><el-icon><FolderAdd /></el-icon><span>新项目</span></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="competition">学科竞赛</el-dropdown-item>
                <el-dropdown-item command="thesis">毕业论文</el-dropdown-item>
                <el-dropdown-item command="practice">社会实践</el-dropdown-item>
                <el-dropdown-item command="certificate">证书考取</el-dropdown-item>
                <el-dropdown-item command="student_work">学生工作</el-dropdown-item>
                <el-dropdown-item command="custom">自定义项目</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 可滚动列表 -->
    <div class="sidebar-scroll">
      <!-- 项目对话（仅学生端） -->
      <div v-if="props.role !== 'teacher'" class="sidebar-section">
        <div class="section-header" @click="projectExpanded = !projectExpanded">
          <el-icon><CaretRight v-if="!projectExpanded" /><CaretBottom v-else /></el-icon>
          <span>项目</span>
          <el-tag size="small" round>{{ projects.length }}</el-tag>
        </div>
        <Transition name="expand">
          <div v-show="projectExpanded" class="section-items">
            <div v-for="c in projects" :key="c.id"
              :class="['conv-item', { active: c.id === store.activeId }]"
              @click="selectConv(c)">
              <el-icon class="conv-icon"><FolderOpened /></el-icon>
              <div class="conv-info">
                <div class="conv-title">{{ c.title }}</div>
                <div v-if="c.project_stage" class="conv-stage"><span class="stage-text">{{ c.project_stage }}</span></div>
              </div>
              <el-dropdown trigger="click" @command="(cmd: string) => handleConvCmd(cmd, c)" @click.stop>
                <button type="button" class="conv-more" aria-label="更多操作">
                  <el-icon :size="14"><MoreFilled /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu class="conv-dropdown-menu">
                    <el-dropdown-item command="rename" class="conv-dropdown-item">
                      <el-icon class="dropdown-icon"><Edit /></el-icon>
                      <span>重命名</span>
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided class="conv-dropdown-item danger">
                      <el-icon class="dropdown-icon" color="#f56c6c"><Delete /></el-icon>
                      <span>删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </Transition>
      </div>

      <!-- 历史对话 -->
      <div class="sidebar-section">
        <div class="section-header" @click="historyExpanded = !historyExpanded">
          <el-icon><CaretRight v-if="!historyExpanded" /><CaretBottom v-else /></el-icon>
          <span>历史</span>
          <el-tag size="small" round>{{ histories.length }}</el-tag>
        </div>
        <Transition name="expand">
          <div v-show="historyExpanded" class="section-items">
            <div v-for="c in filteredHistories" :key="c.id"
              :class="['conv-item', { active: c.id === store.activeId && !batchMode }]"
              @click="batchMode ? toggleSelect(c.id) : selectConv(c)">
              <div :class="['conv-check-wrap', { show: batchMode }]">
                <el-checkbox :model-value="selectedIds.has(c.id)" @click.stop @change="toggleSelect(c.id)" />
              </div>
              <el-icon class="conv-icon"><ChatDotRound /></el-icon>
              <div class="conv-info">
                <div class="conv-title">{{ c.title }}</div>
                <div class="conv-date">{{ timeLabel(c.updated_at) }}</div>
              </div>
              <el-dropdown v-if="!batchMode" trigger="click" @command="(cmd: string) => handleConvCmd(cmd, c)" @click.stop>
                <button type="button" class="conv-more" aria-label="更多操作">
                  <el-icon :size="16"><MoreFilled /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu class="conv-dropdown-menu">
                    <el-dropdown-item command="rename" class="conv-dropdown-item">
                      <el-icon class="dropdown-icon"><Edit /></el-icon>
                      <span>重命名</span>
                    </el-dropdown-item>
                    <el-dropdown-item command="batch" class="conv-dropdown-item">
                      <el-icon class="dropdown-icon"><FolderChecked /></el-icon>
                      <span>批量管理</span>
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided class="conv-dropdown-item danger">
                      <el-icon class="dropdown-icon" color="#f56c6c"><Delete /></el-icon>
                      <span>删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            <div v-if="filteredHistories.length === 0" class="empty-hint">
              {{ search ? '无匹配对话' : '暂无历史对话' }}
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <Transition name="batch-bar">
      <div v-if="batchMode" class="batch-bar">
        <div class="batch-bar-left">
          <el-checkbox
            :model-value="isAllSelected"
            :indeterminate="isIndeterminate"
            @change="toggleSelectAll"
          >全选</el-checkbox>
          <span class="batch-count">已选 {{ selectedIds.size }} 条</span>
        </div>
        <div class="batch-bar-right">
          <el-button size="small" @click="exitBatchMode">取消</el-button>
          <el-button size="small" type="danger" :disabled="selectedIds.size === 0" @click="batchDelete">删除</el-button>
        </div>
      </div>
    </Transition>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  Search, Plus, FolderAdd, Expand, Fold, CaretRight, CaretBottom,
  FolderOpened, ChatDotRound, Delete, Edit, MoreFilled, FolderChecked,
} from '@element-plus/icons-vue'
import { useConversationStore, type Conversation } from '@/stores/conversation'
import { useTeacherConversationStore } from '@/stores/teacherConversation'
import { useAgentStore } from '@/stores/agent'
import { useTeacherAgentStore } from '@/stores/teacherAgent'

const props = withDefaults(defineProps<{ role?: 'student' | 'teacher' }>(), { role: 'student' })
const store = props.role === 'teacher' ? useTeacherConversationStore() : useConversationStore()
const agentStore = props.role === 'teacher' ? useTeacherAgentStore() : useAgentStore()
const search = ref('')
const projectExpanded = ref(false)
const historyExpanded = ref(true)
const batchMode = ref(false)
const selectedIds = ref(new Set<number>())
const emit = defineEmits<{ select: [conv: Conversation]; new: [] }>()

const projects = computed(() => store.list.filter(c => c.type === 'project'))
const histories = computed(() => store.list.filter(c => c.type === 'normal'))
const filteredHistories = computed(() => {
  if (!search.value) return histories.value
  const q = search.value.toLowerCase()
  return histories.value.filter(c => c.title.toLowerCase().includes(q))
})
const collapsed = computed(() => store.sidebarCollapsed)

const isAllSelected = computed(() => {
  return filteredHistories.value.length > 0 && filteredHistories.value.every(c => selectedIds.value.has(c.id))
})

const isIndeterminate = computed(() => {
  const selected = filteredHistories.value.filter(c => selectedIds.value.has(c.id)).length
  return selected > 0 && selected < filteredHistories.value.length
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(filteredHistories.value.map(c => c.id))
  }
}

function selectConv(c: Conversation) {
  if (c.id === store.activeId) return
  emit('select', c)
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
      const { value } = await ElMessageBox.prompt('请输入竞赛名称', '新建学科竞赛项目')
      if (!value) return; title = value
    } catch { return }
  } else if (template === 'custom') {
    try {
      const { value } = await ElMessageBox.prompt('请输入项目名称', '自定义项目')
      if (!value) return; title = value
    } catch { return }
  }
  const conv = await store.createConversation('project', template, title)
  if (conv) emit('select', conv)
  else emit('new')
}

function handleConvCmd(cmd: string, c: Conversation) {
  if (cmd === 'delete') {
    deleteConv(c)
  } else if (cmd === 'rename') {
    renameConv(c)
  } else if (cmd === 'batch') {
    enterBatchMode()
  }
}

async function renameConv(c: Conversation) {
  try {
    const { value } = await ElMessageBox.prompt('重命名', '', { inputValue: c.title })
    if (value) await store.updateConversation(c.id, { title: value })
  } catch {}
}

function enterBatchMode() {
  batchMode.value = true
  selectedIds.value = new Set()
}

function exitBatchMode() {
  batchMode.value = false
  selectedIds.value = new Set()
}

function toggleSelect(id: number) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

async function batchDelete() {
  if (selectedIds.value.size === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.size} 个对话？`)
    const ids = [...selectedIds.value]
    for (const id of ids) {
      await store.deleteConversation(id)
    }
    if (ids.includes(store.activeId ?? -1)) {
      const remaining = store.list.filter(x => !ids.includes(x.id))
      if (remaining.length > 0) {
        const next = remaining.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0]
        emit('select', next)
      } else {
        emit('new')
      }
    }
    exitBatchMode()
  } catch {}
}

async function deleteConv(c: Conversation) {
  try {
    await ElMessageBox.confirm(`确定删除「${c.title}」？`)
    const wasActive = store.activeId === c.id
    await store.deleteConversation(c.id)
    if (wasActive) {
      const remaining = store.list.filter(x => x.id !== c.id)
      if (remaining.length > 0) {
        const next = remaining.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0]
        emit('select', next)
      } else {
        emit('new')
      }
    }
  } catch {}
}

function timeLabel(d: string): string {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const dayDiff = Math.floor((startOfToday.getTime() - date.getTime()) / 86400000)
  if (dayDiff < 0) return '刚刚'
  if (dayDiff === 0) return '今天'
  if (dayDiff === 1) return '昨天'
  if (dayDiff <= 3) return '三天前'
  if (dayDiff <= 7) return '一周前'
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

onMounted(() => {
  store.fetchList()
})
</script>

<style scoped>
.sidebar {
  width: 100%; height: 100%;
  background: #fafafa; border-right: 1px solid #f0f0f0;
  display: flex; flex-direction: column; flex-shrink: 0;
  overflow: hidden;
}
.sidebar.collapsed .header-title,
.sidebar.collapsed .header-actions,
.sidebar.collapsed .sidebar-scroll { display: none; }

/* 头部区域 */
.sidebar-header { 
  flex-shrink: 0; 
  padding: 12px 10px 8px;
}

.header-row { display: flex; align-items: center; gap: 2px; margin-bottom: 10px; }
.toggle-btn { 
  width: 28px; height: 28px; flex-shrink: 0; color: #999; border-radius: 6px;
}
.toggle-btn:hover { 
  color: #6366f1; 
  background: rgba(99,102,241,.06);
}
.header-title { font-size: 13px; font-weight: 600; color: #333; letter-spacing: .5px; }
.header-actions { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.search-input :deep(.el-input__wrapper) { border-radius: 8px; background: #f0f0f0; box-shadow: none; border: 1px solid transparent; }
.search-input :deep(.el-input__wrapper:hover) { border-color: #e0e0e0; }
.search-input :deep(.el-input__wrapper.is-focus) { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,.08); }
.action-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; width: 100%; }
.action-btns .el-button {
  font-size: 12px; border-radius: 8px; height: 30px;
  width: 100%;
}
.action-btns :deep(.el-dropdown) {
  display: block;
}
.action-btns :deep(.el-dropdown .el-button) {
  width: 100%;
}
.action-btns .el-button :deep(.el-icon) {
  margin-right: 4px;
}
.action-btns .el-button:hover {
}
.action-btns .el-button--primary { background: #6366f1; border-color: #6366f1; }
.action-btns .el-button--primary:hover { background: #5558e6; border-color: #5558e6; }

/* 可滚动列表 */
.sidebar-scroll { 
  flex: 1; overflow-y: auto; min-height: 0; padding: 0 4px 8px; 
  scrollbar-width: none; -ms-overflow-style: none;
}
.sidebar-scroll::-webkit-scrollbar { display: none; }

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 分组区域 */
.sidebar-section { margin-bottom: 4px; }
.section-header {
  display: flex; align-items: center; gap: 4px; padding: 6px 8px;
  font-size: 11px; color: #999; cursor: pointer; user-select: none;
  border-radius: 6px; transition: background .2s ease, color .2s ease; letter-spacing: .5px;
}
.section-header:hover { 
  background: rgba(0,0,0,.03); 
  color: #666;
}
.section-header .el-icon { font-size: 10px; }
.section-header .el-tag { height: 16px; padding: 0 5px; font-size: 10px; border-radius: 8px; background: #f0f0f0; color: #999; border: none; }
.section-items { margin: 2px 0; }

/* Expand/Collapse transition */
.expand-enter-active {
  transition: opacity 0.2s ease;
}
.expand-leave-active {
  transition: opacity 0.15s ease;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
}

.conv-item {
  display: flex; align-items: center; gap: 8px; padding: 7px 8px;
  cursor: pointer; border-radius: 8px; margin: 1px 4px;
  transition: background 0.15s ease;
}
.conv-item:hover { 
  background: rgba(99,102,241,.05);
}
.conv-item.active { background: rgba(99,102,241,.08); }
.conv-icon { 
  font-size: 14px; color: #c0c4cc; flex-shrink: 0; 
  transition: color .2s ease;
}
.conv-item.active .conv-icon { color: #6366f1; }
.conv-item:hover .conv-icon { 
  color: #909399;
}
.conv-info { flex: 1; min-width: 0; }
.conv-title { 
  font-size: 12px; color: #444; overflow: hidden; 
  text-overflow: ellipsis; white-space: nowrap; line-height: 1.4;
  transition: color 0.2s ease;
}
.conv-item.active .conv-title { color: #6366f1; font-weight: 500; }
.conv-date { font-size: 10px; color: #bbb; margin-top: 1px; }
.conv-stage { margin-top: 2px; }
.stage-text { font-size: 10px; color: #aaa; }
.conv-more {
  opacity: 0;
  flex-shrink: 0;
  color: #9ca3af;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: opacity 0.15s ease, color 0.15s ease, background 0.15s ease;
  padding: 0;
}

.conv-more:hover {
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.conv-more:active {
  transform: scale(0.92);
  background: rgba(99, 102, 241, 0.12);
}

.conv-item:hover .conv-more { opacity: 1; }

/* 下拉菜单样式 */
.conv-dropdown-menu {
  min-width: 140px;
  padding: 4px;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.04);
}

.conv-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
  transition: background 0.12s ease, color 0.12s ease;
  margin: 2px 0;
}

.conv-dropdown-item:hover {
  background: rgba(99, 102, 241, 0.06);
  color: #6366f1;
}

.conv-dropdown-item:active {
  background: rgba(99, 102, 241, 0.1);
}

.conv-dropdown-item.danger:hover {
  background: rgba(245, 108, 108, 0.06);
  color: #f56c6c;
}

.dropdown-icon {
  font-size: 15px;
  flex-shrink: 0;
}
.empty-hint { 
  text-align: center; font-size: 11px; color: #ccc; padding: 20px 0;
  animation: fadeIn 0.3s ease-out;
}

/* 头部操作按钮 */
.section-header { position: relative; }
.header-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.action-link {
  font-size: 11px; color: #999; cursor: pointer; transition: color .2s ease, background .2s ease;
  white-space: nowrap; user-select: none; padding: 4px 8px; border-radius: 6px;
}
.action-link:hover { 
  color: #6366f1; 
  background: rgba(99,102,241,.06);
}
.action-link.danger { color: #f56c6c; }
.action-link.danger:hover { 
  color: #e04848; 
  background: rgba(245,108,108,.06);
}
.action-link.disabled { opacity: .4; pointer-events: none; }
.action-divider { color: #ddd; font-size: 11px; user-select: none; }

/* 会话项复选框 */
.conv-check-wrap {
  flex-shrink: 0;
  width: 0;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.2s ease, width 0.2s ease, margin-right 0.2s ease;
  display: flex;
  align-items: center;
}
.conv-check-wrap.show {
  width: 20px;
  opacity: 1;
  margin-right: 4px;
}
.conv-item.active .conv-check-wrap :deep(.el-checkbox__label) { color: #6366f1; }

/* 批量操作栏 */
.batch-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

/* 批量操作栏过渡动画 */
.batch-bar-enter-active,
.batch-bar-leave-active {
  transition: opacity 0.25s ease;
}
.batch-bar-enter-from,
.batch-bar-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  border-top-width: 0;
}
.batch-bar-enter-to,
.batch-bar-leave-from {
  opacity: 1;
  max-height: 60px;
}

.batch-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.batch-bar-left :deep(.el-checkbox__label) {
  font-size: 12px;
}

.batch-count {
  font-size: 12px;
  color: #999;
}

.batch-bar-right {
  display: flex;
  gap: 8px;
}

.batch-bar-right .el-button {
  border-radius: 6px;
}

/* 会话更多按钮 */
.conv-more { opacity: 0; flex-shrink: 0; color: #ccc; }
.conv-more:hover { color: #6366f1; }
.conv-item:hover .conv-more { opacity: 1; }

/* 移动端适配 */
@media (max-width: 767px) {
  .sidebar { width: 100%; border-right: none; }
  .sidebar.collapsed { width: 100%; }
  .toggle-btn { display: none; }
  .conv-more { opacity: 1; }
}
</style>
