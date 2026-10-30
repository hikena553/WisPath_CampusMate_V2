<!-- 管理端顶栏消息组件：待处理密码重置申请 + 用户反馈，红点提醒，点击跳转到对应管理页处理 -->
<template>
  <div class="msg-bell" ref="rootRef">
    <el-tooltip content="消息提醒" placement="bottom">
      <button
        type="button"
        class="bell-btn"
        :class="{ open: panelOpen }"
        aria-label="消息提醒"
        @click="toggle"
      >
        <el-icon :size="18"><Bell /></el-icon>
        <span v-if="displayUnread > 0" class="bell-badge">{{ displayUnread > 99 ? '99+' : displayUnread }}</span>
      </button>
    </el-tooltip>

    <transition name="msg-pop">
      <div v-if="panelOpen" class="msg-panel">
        <div class="msg-head">
          <span class="msg-head-title">消息</span>
          <span class="msg-head-sub">{{ loading ? '刷新中…' : displayUnread > 0 ? `${displayUnread} 条待处理` : '暂无待处理' }}</span>
        </div>

        <div v-if="displayItems.length" class="msg-list">
          <div
            v-for="item in displayItems"
            :key="item.id"
            class="msg-row"
            role="button"
            tabindex="0"
            @click="openItem(item)"
            @keydown.enter="openItem(item)"
          >
            <span class="msg-icon" :class="item.kind">
              <el-icon :size="15"><component :is="iconOf(item.kind)" /></el-icon>
            </span>
            <span class="msg-body">
              <span class="msg-row-title">{{ item.title }}</span>
              <span class="msg-row-desc">{{ item.content }}</span>
              <span class="msg-row-time">{{ formatTime(item.created_at) }}</span>
            </span>
            <span class="msg-side">
              <span class="msg-dot"></span>
              <button
                v-if="item.kind === 'password_reset'"
                type="button"
                class="msg-ignore"
                @click.stop="ignoreReset(item)"
              >
                忽略
              </button>
            </span>
          </div>
        </div>

        <div v-else class="msg-empty">
          <el-icon :size="20"><BellOff /></el-icon>
          <span>暂无新消息</span>
        </div>

        <div class="msg-foot">仅展示待处理事项，处理完成后自动消失</div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, BellOff, KeyRound, MessageSquare, TriangleAlert } from 'lucide-vue-next'
import {
  getAdminMessages,
  rejectPasswordReset,
  type AdminMessageItem,
} from '@/api/admin'

const router = useRouter()
const rootRef = ref<HTMLElement | null>(null)
const panelOpen = ref(false)
const loading = ref(false)
const items = ref<AdminMessageItem[]>([])
const unread = ref(0)
/** 拉取消息失败时（接口不可用 / 服务异常）在面板顶部给出系统提示 */
const systemOffline = ref(false)
const offlineSince = ref(new Date().toISOString())

let timer: number | undefined

const offlineItem = computed<AdminMessageItem>(() => ({
  id: 'system-offline',
  kind: 'system',
  level: 'urgent',
  title: '系统服务连接异常',
  content: '暂时无法获取最新消息，请前往系统监控查看服务状态',
  link: '/admin/system',
  created_at: offlineSince.value,
}))

const displayItems = computed<AdminMessageItem[]>(() =>
  systemOffline.value ? [offlineItem.value, ...items.value] : items.value
)
const displayUnread = computed(() => unread.value + (systemOffline.value ? 1 : 0))

const ICONS = {
  password_reset: KeyRound,
  feedback: MessageSquare,
  system: TriangleAlert,
}
function iconOf(kind: AdminMessageItem['kind']) {
  return ICONS[kind] || TriangleAlert
}

async function load() {
  loading.value = true
  try {
    const res = await getAdminMessages()
    items.value = res.items || []
    unread.value = res.unread || 0
    systemOffline.value = false
  } catch {
    // 网络 / 服务异常：保留上一次结果，并追加一条可跳转的系统提醒
    offlineSince.value = new Date().toISOString()
    systemOffline.value = true
  } finally {
    loading.value = false
  }
}

function toggle() {
  panelOpen.value = !panelOpen.value
  if (panelOpen.value) void load()
}

function close() {
  panelOpen.value = false
}

function openItem(item: AdminMessageItem) {
  close()
  if (!item.link) {
    ElMessage.info('该消息暂无关联页面')
    return
  }
  router.push(item.link)
}

async function ignoreReset(item: AdminMessageItem) {
  try {
    await ElMessageBox.confirm('忽略后申请人会收到站内通知，确认忽略这条重置申请？', '忽略重置申请', {
      confirmButtonText: '忽略',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  const requestId = Number(item.id.split('-').pop())
  if (!Number.isFinite(requestId)) return
  try {
    await rejectPasswordReset(requestId, '身份信息核验未通过')
    ElMessage.success('已忽略该申请')
    await load()
  } catch {
    ElMessage.error('操作失败，请稍后重试')
  }
}

function formatTime(value: string) {
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return ''
  const diff = Date.now() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function onDocumentClick(event: MouseEvent) {
  if (!panelOpen.value) return
  const el = rootRef.value
  if (el && !el.contains(event.target as Node)) close()
}

function onMessagesRefresh() {
  void load()
}

onMounted(() => {
  void load()
  timer = window.setInterval(() => { void load() }, 45000)
  document.addEventListener('click', onDocumentClick)
  window.addEventListener('admin:messages-refresh', onMessagesRefresh)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  document.removeEventListener('click', onDocumentClick)
  window.removeEventListener('admin:messages-refresh', onMessagesRefresh)
})
</script>

<style scoped>
.msg-bell {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.bell-btn {
  position: relative;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #475569;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.bell-btn:hover,
.bell-btn.open {
  background: #f1f5f9;
  color: #1e293b;
}

.bell-badge {
  position: absolute;
  top: -2px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 0 0 2px #fff;
}

.msg-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: min(340px, calc(100vw - 24px));
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.16);
  z-index: 1200;
  overflow: hidden;
}

.msg-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f7;
}
.msg-head-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.msg-head-sub {
  font-size: 11px;
  color: #94a3b8;
}

.msg-list {
  max-height: 360px;
  overflow-y: auto;
  scrollbar-width: thin;
}

.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
  outline: none;
}
.msg-row:last-child { border-bottom: none; }
.msg-row:hover,
.msg-row:focus-visible { background: #f8fafc; }

.msg-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #f1f5f9;
  color: #475569;
}
.msg-icon.password_reset { background: #fef3c7; color: #b45309; }
.msg-icon.feedback { background: #eff6ff; color: #2563eb; }
.msg-icon.system { background: #fef2f2; color: #dc2626; }

.msg-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.msg-row-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msg-row-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.msg-row-time {
  font-size: 11px;
  color: #94a3b8;
}

.msg-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  padding-top: 2px;
  flex-shrink: 0;
}
.msg-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
}
.msg-ignore {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
}
.msg-ignore:hover { color: #b45309; }

.msg-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 0;
  font-size: 12px;
  color: #94a3b8;
}

.msg-foot {
  padding: 8px 14px;
  border-top: 1px solid #f1f5f9;
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
}

.msg-pop-enter-active,
.msg-pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.33, 1, 0.68, 1);
}
.msg-pop-enter-from,
.msg-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}
</style>
