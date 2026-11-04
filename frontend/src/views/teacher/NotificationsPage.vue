<template>
  <div class="tui-page notif-page">
    <!-- 移动端吸顶子页头；桌面端由教师布局的页签承担导航，这里只留返回语义 -->
    <SubPageHeader title="通知" sub="审批 · 预警 · 公告" fallback="/teacher/messages" />

    <div class="notif-inner">
      <!-- 桌面端特色头部（教师子页统一规范）；移动端标题由子页头承担 -->
      <TuiPageHero
        v-if="!isMobile"
        title="通知"
        sub="审批 · 预警 · 公告，点开直达对应页面"
        :icon="Bell"
        tone="brand"
      />

      <div v-if="notifications.length" class="notif-toolbar">
        <span class="notif-count">{{ unreadCount ? `${unreadCount} 条未读` : '全部已读' }}</span>
        <button type="button" class="notif-readall" :disabled="!unreadCount" @click="readAll">
          全部标为已读
        </button>
      </div>

      <div v-if="loading" class="notif-skeleton" aria-hidden="true">
        <div v-for="i in 5" :key="i" class="sk-row">
          <span class="sk-icon"></span>
          <span class="sk-lines"><i></i><i></i></span>
        </div>
      </div>

      <div v-else-if="!notifications.length" class="notif-empty">
        <span class="notif-empty-ico"><el-icon :size="24"><Bell /></el-icon></span>
        <p class="notif-empty-title">还没有通知</p>
        <p class="notif-empty-hint">审批、预警、班级公告会汇总在这里</p>
      </div>

      <div v-else class="notif-card">
        <button
          v-for="n in notifications"
          :key="n.id"
          type="button"
          class="notif-row"
          :class="{ unread: !n.is_read }"
          @click="openNotification(n)"
        >
          <span
            class="notif-icon"
            :style="{ background: notifMeta(n.type).tint, color: notifMeta(n.type).color }"
          >
            <el-icon :size="16"><component :is="notifMeta(n.type).icon" /></el-icon>
          </span>
          <span class="notif-main">
            <span class="notif-top">
              <span class="notif-title">{{ n.title }}</span>
              <span class="notif-time">{{ formatTime(n.created_at) }}</span>
            </span>
            <span class="notif-content">{{ n.content }}</span>
          </span>
          <span v-if="!n.is_read" class="notif-dot" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Bell,
  ChatDotRound,
  ChatLineRound,
  InfoFilled,
  Setting,
  Stamp,
  WarningFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import { useResponsive } from '@/composables/useResponsive'
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationsRead,
  type Notification as NotificationItem,
} from '@/api/notification'

/**
 * 教师端「通知」独立页。
 *
 * 从消息页的第四个视图抽出来：消息页页签收敛为「消息 / 通讯录」两枚（对齐学生端），
 * 通知这类**按时间倒序直出、不参与会话**的流改由页头铃铛进入本页，未读数在铃铛角标上。
 */

const router = useRouter()
const { isMobile } = useResponsive()

const notifications = ref<NotificationItem[]>([])
const loading = ref(true)
const unreadCount = computed(() => notifications.value.filter((n) => !n.is_read).length)

async function load() {
  loading.value = true
  try {
    notifications.value = await getNotifications({ page_size: 50 })
  } catch {
    /* 拉取失败按空态呈现，不阻断页面 */
  } finally {
    loading.value = false
  }
}

async function readAll() {
  if (!unreadCount.value) return
  try {
    await markAllNotificationsRead()
    await load()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function openNotification(n: NotificationItem) {
  if (!n.is_read) {
    try {
      await markNotificationsRead([n.id])
      n.is_read = true
    } catch {
      /* 标记失败不阻断跳转 */
    }
  }
  // 历史通知可能只写了 /teacher/students 而没带学生参数：用 related_id 补上，
  // 保证点进去直接聚焦到该学生，而不是落在一张全量列表上。
  let link = n.link || ''
  if (link.startsWith('/teacher/students') && n.related_id && !link.includes('student=')) {
    link += `${link.includes('?') ? '&' : '?'}student=${n.related_id}`
  }
  if (link) {
    void router.push(link)
  } else {
    ElMessage.info(n.content || '该通知暂无关联页面')
  }
}

/** 通知类型 → 图标与语义色（与学生端消息页的语义色板同源） */
function notifMeta(type: string): { icon: any; color: string; tint: string } {
  switch (type) {
    case 'approval':
    case 'leave':
      return { icon: Stamp, color: '#b54708', tint: '#fffaeb' }
    case 'crisis':
      return { icon: WarningFilled, color: '#d92d20', tint: '#fef3f2' }
    case 'announcement':
      return { icon: Bell, color: '#2563eb', tint: '#eef4ff' }
    case 'feedback':
      return { icon: ChatLineRound, color: '#079455', tint: '#ecfdf3' }
    case 'message':
      return { icon: ChatDotRound, color: '#0891b2', tint: '#ecfeff' }
    case 'system':
      return { icon: Setting, color: '#2563eb', tint: '#eef4ff' }
    default:
      return { icon: InfoFilled, color: '#6b7280', tint: '#f2f3f5' }
  }
}

/** 后端返回无时区的 UTC 串，补 Z 再解析，否则相对时间会整体偏 8 小时 */
function parseTime(t: string): Date {
  return new Date(t + (t.includes('Z') || t.includes('+') ? '' : 'Z'))
}

function formatTime(t: string | null) {
  if (!t) return ''
  try {
    const date = parseTime(t)
    const diff = Date.now() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
  } catch {
    return t
  }
}

onMounted(load)
</script>

<style scoped>
.notif-page {
  background: #f5f6f7;
}

/* 移动端：页头由 .tui-page > .tui-appbar 的 sticky 规则接管，这里只收窄内容边距 */
@media (max-width: 767px) {
  .notif-inner {
    padding: 12px 12px 96px;
  }
}

/* 桌面端交给教师布局的 .tui-content 规范（20 18 40），与其它子页等宽；
   移动端收窄边距，底部留出安全距离 */
.notif-inner {
  padding: 20px 18px 40px;
}

.notif-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px 10px;
}
.notif-count {
  font-size: 12px;
  color: #9aa0a6;
}
.notif-readall {
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12.5px;
  color: #0070d9;
  cursor: pointer;
}
.notif-readall:disabled {
  color: #b6bcc4;
  cursor: default;
}

.notif-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.notif-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-bottom: 1px solid #f2f3f5;
  background: #fff;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}
.notif-row:last-child {
  border-bottom: none;
}
.notif-row:active {
  background: #f2f3f5;
}

.notif-icon {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notif-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.notif-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.notif-title {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notif-time {
  font-size: 11px;
  color: #9aa0a6;
  flex-shrink: 0;
}

.notif-content {
  font-size: 12px;
  line-height: 1.5;
  color: #8a9099;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.notif-row.unread .notif-content {
  color: #5c6269;
}

.notif-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d93026;
  flex-shrink: 0;
  margin-top: 8px;
}

/* 骨架屏 */
.notif-skeleton {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}
.sk-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
}
.sk-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #f0f1f3;
  flex-shrink: 0;
}
.sk-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.sk-lines i {
  display: block;
  height: 10px;
  border-radius: 5px;
  background: #f0f1f3;
}
.sk-lines i:last-child {
  width: 62%;
}

/* 空态 */
.notif-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64px 20px 0;
  text-align: center;
}
.notif-empty-ico {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  background: #fff;
  color: #b6bcc4;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.notif-empty-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
}
.notif-empty-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #9aa0a6;
  max-width: 240px;
}
</style>
