<template>
  <div class="notification-panel">
    <div class="panel-header">
      <h3>通知中心</h3>
      <div class="header-actions">
        <el-button text size="small" @click="handleMarkAllRead" :disabled="unreadCount === 0">
          全部已读
        </el-button>
      </div>
    </div>

    <div class="panel-tabs">
      <div 
        v-for="tab in tabs" 
        :key="tab.key"
        :class="['tab-item', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
      </div>
    </div>

    <div class="notification-list" v-loading="loading">
      <div v-if="notifications.length === 0" class="empty-state">
        <el-empty description="暂无通知" :image-size="80" />
      </div>
      
      <div 
        v-for="item in notifications" 
        :key="item.id"
        :class="['notification-item', { unread: !item.is_read }]"
        @click="handleClick(item)"
      >
        <div class="item-icon" :class="item.type">
          <el-icon :size="18">
            <component :is="getIcon(item.type)" />
          </el-icon>
        </div>
        <div class="item-content">
          <div class="item-title">{{ item.title }}</div>
          <div class="item-desc">{{ item.content }}</div>
          <div class="item-meta">
            <span class="meta-time">{{ formatTime(item.created_at) }}</span>
            <span v-if="item.sender_name" class="meta-sender">来自 {{ item.sender_name }}</span>
          </div>
        </div>
        <div class="item-actions">
          <el-button 
            v-if="!item.is_read" 
            text 
            size="small" 
            @click.stop="handleMarkRead(item)"
          >
            标为已读
          </el-button>
          <el-button 
            text 
            size="small" 
            type="danger" 
            @click.stop="handleDelete(item)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <div v-if="notifications.length > 0" class="panel-footer">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        small
        @current-change="loadNotifications"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Bell, Check, Warning, Message, Document, 
  ChatDotRound, Setting 
} from '@element-plus/icons-vue'
import { 
  getNotifications, 
  getNotificationCount, 
  markNotificationsRead, 
  markAllNotificationsRead,
  deleteNotification,
  type Notification 
} from '@/api/notification'

const emit = defineEmits(['close', 'navigate'])

const loading = ref(false)
const notifications = ref<Notification[]>([])
const activeTab = ref('all')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const unreadCount = ref(0)

const tabs = computed(() => [
  { key: 'all', label: '全部', count: 0 },
  { key: 'unread', label: '未读', count: unreadCount.value },
  { key: 'system', label: '系统', count: 0 },
  { key: 'approval', label: '审批', count: 0 },
  { key: 'message', label: '消息', count: 0 },
])

function getIcon(type: string) {
  const iconMap: Record<string, any> = {
    system: Setting,
    approval: Check,
    leave: Document,
    crisis: Warning,
    announcement: Bell,
    message: ChatDotRound,
    feedback: Message,
  }
  return iconMap[type] || Bell
}

function formatTime(time: string) {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return time.slice(0, 10)
}

async function loadNotifications() {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize,
    }
    
    if (activeTab.value === 'unread') {
      params.is_read = false
    } else if (activeTab.value !== 'all') {
      params.type = activeTab.value
    }
    
    const data = await getNotifications(params)
    notifications.value = data
  } catch (error) {
    console.error('加载通知失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadCount() {
  try {
    const data = await getNotificationCount()
    unreadCount.value = data.unread
  } catch (error) {
    console.error('加载通知数量失败:', error)
  }
}

async function handleMarkRead(item: Notification) {
  try {
    await markNotificationsRead([item.id])
    item.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    ElMessage.success('已标记为已读')
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function handleMarkAllRead() {
  try {
    await markAllNotificationsRead()
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
    ElMessage.success('已全部标记为已读')
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function handleDelete(item: Notification) {
  try {
    await deleteNotification(item.id)
    notifications.value = notifications.value.filter(n => n.id !== item.id)
    if (!item.is_read) {
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

function handleClick(item: Notification) {
  if (!item.is_read) {
    handleMarkRead(item)
  }
  if (item.link) {
    emit('navigate', item.link)
    emit('close')
  }
}

watch(activeTab, () => {
  currentPage.value = 1
  loadNotifications()
})

onMounted(() => {
  loadNotifications()
  loadCount()
})

defineExpose({
  loadCount
})
</script>

<style scoped>
.notification-panel {
  width: 400px;
  max-height: 500px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.panel-tabs {
  display: flex;
  padding: 0 20px;
  border-bottom: 1px solid #f0f0f0;
}

.tab-item {
  padding: 12px 16px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
}

.tab-item:hover {
  color: #409eff;
}

.tab-item.active {
  color: #409eff;
  font-weight: 600;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 2px;
  background: #409eff;
  border-radius: 1px;
}

.tab-badge {
  display: inline-block;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  font-size: 10px;
  background: #f56c6c;
  color: #fff;
  border-radius: 8px;
  margin-left: 4px;
  padding: 0 4px;
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 20px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #f5f5f5;
}

.notification-item:hover {
  background: #f8f9fa;
}

.notification-item.unread {
  background: #f0f7ff;
}

.notification-item.unread:hover {
  background: #e8f4ff;
}

.item-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f0f7ff;
  color: #409eff;
}

.item-icon.crisis {
  background: #fef0f0;
  color: #f56c6c;
}

.item-icon.approval {
  background: #f0f9eb;
  color: #67c23a;
}

.item-icon.message {
  background: #fdf6ec;
  color: #e6a23c;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-desc {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #999;
}

.item-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.notification-item:hover .item-actions {
  opacity: 1;
}

.empty-state {
  padding: 40px 0;
}

.panel-footer {
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: center;
}
</style>
