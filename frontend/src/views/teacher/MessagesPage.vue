<template>
  <div class="msg-page">
    <Transition name="sidebar">
      <div class="msg-sidebar" v-show="!activeUserId">
      <div class="sidebar-header">
        <h3>消息</h3>
        <span v-if="conversations.length" class="conv-count">{{ conversations.length }} 条对话</span>
      </div>
      <div class="sidebar-search">
        <el-input v-model="search" placeholder="搜索学生姓名或学号" size="small" clearable @input="searchStudents">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
      <div class="sidebar-scroll">
        <template v-if="searched">
          <div v-if="searchResults.length === 0" class="empty-state">
            <el-icon :size="32" color="#ddd"><User /></el-icon>
            <span>未找到学生</span>
          </div>
          <div v-for="s in searchResults" :key="s.id"
            :class="['conv-item', { active: activeUserId === s.id }]"
            @click="selectConversation(s.id, s.name)">
            <el-avatar :size="40" :src="s.avatar || undefined" class="conv-avatar">{{ s.name[0] }}</el-avatar>
            <div class="conv-info">
              <strong>{{ s.name }}</strong>
              <small>{{ s.username }}</small>
            </div>
          </div>
        </template>
        <template v-else>
          <div v-if="conversations.length === 0" class="empty-state">
            <el-icon :size="32" color="#ddd"><ChatDotRound /></el-icon>
            <span>暂无消息</span>
          </div>
          <div v-for="c in conversations" :key="c.user_id"
            :class="['conv-item', { active: activeUserId === c.user_id }]"
            @click="selectConversation(c.user_id, c.user_name)">
            <el-badge :value="c.unread_count" :hidden="!c.unread_count" class="conv-badge">
              <el-avatar :size="40" :src="c.user_avatar || undefined" class="conv-avatar">{{ c.user_name[0] }}</el-avatar>
            </el-badge>
            <div class="conv-info">
              <div class="conv-top">
                <strong>{{ c.user_name }}</strong>
                <small class="conv-time">{{ formatTime(c.last_message_time) }}</small>
              </div>
              <small class="conv-preview">{{ c.last_message.slice(0, 30) }}{{ c.last_message.length > 30 ? '...' : '' }}</small>
            </div>
          </div>
        </template>
      </div>
    </div>
    </Transition>
    <div class="msg-chat">
      <Transition name="slide-right" mode="out-in" @after-enter="scrollToBottom">
        <div v-if="activeUserId" key="chat" class="chat-panel">
          <div class="chat-header">
            <el-button text circle @click="goBack" class="back-btn">
              <el-icon :size="18"><ArrowLeft /></el-icon>
            </el-button>
            <el-avatar :size="32">{{ activeUserName[0] }}</el-avatar>
            <span class="chat-name">{{ activeUserName }}</span>
          </div>
          <div class="msg-list" ref="msgListRef">
            <template v-for="item in messageTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
              <div v-if="item.type === 'date'" class="date-separator">
                <span>{{ item.label }}</span>
              </div>
              <div v-else
                :class="['msg-bubble', item.msg.sender_id === userId ? 'mine' : 'theirs']">
                <div class="bubble-text">{{ item.msg.content }}</div>
                <div class="bubble-time">{{ formatTime(item.msg.created_at) }}</div>
              </div>
            </template>
            <div v-if="messages.length === 0" class="chat-empty">
              <el-icon :size="40" color="#ddd"><ChatLineRound /></el-icon>
              <span>暂无聊天记录</span>
            </div>
          </div>
        <div class="msg-input-bar">
          <el-input v-model="newMsg" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            @keydown.enter.exact.prevent="sendMsg" />
          <el-button type="primary" @click="sendMsg" :disabled="!newMsg.trim()" :icon="Promotion">发送</el-button>
        </div>
        </div>
        <div v-else key="list" class="no-selection">
          <div class="student-list-header">
            <el-icon :size="20" color="#5b8def"><User /></el-icon>
            <span>我的学生</span>
          </div>

          <div class="student-grid">
            <div v-for="s in myStudents" :key="s.id" class="student-item" @click="selectConversation(s.id, s.name)">
              <el-avatar :size="44" :src="s.avatar || undefined" class="student-avatar">{{ s.name[0] }}</el-avatar>
              <div class="student-info">
                <strong>{{ s.name }}</strong>
                <small>{{ s.college || '未分配' }}</small>
              </div>
            </div>
            <div v-if="myStudents.length === 0" class="empty-tip">暂无学生</div>
          </div>

          <!-- AI 推荐区域 -->
          <div class="suggestions-section">
            <div class="suggestions-title">
              <el-icon color="#e6a23c"><Star /></el-icon>
              <span>AI 建议优先联系</span>
            </div>
            <template v-if="suggestLoading">
              <div class="suggestion-loading">
                <el-icon class="is-loading" :size="20"><Loading /></el-icon>
                <span>AI 正在分析中...</span>
              </div>
            </template>
            <template v-else-if="suggestError">
              <div class="suggestion-error">
                <el-icon :size="24" color="#f56c6c"><WarningFilled /></el-icon>
                <p>分析失败，请稍后重试</p>
                <el-button type="primary" size="small" @click="loadSuggestions">
                  <el-icon><RefreshRight /></el-icon> 重试
                </el-button>
              </div>
            </template>
            <template v-else-if="suggestions.length > 0">
              <div v-for="s in suggestions" :key="s.student_id" class="suggestion-item" @click="selectConversation(s.student_id, s.student_name)">
                <div class="suggestion-header">
                  <el-avatar :size="36">{{ s.student_name[0] }}</el-avatar>
                  <div class="suggestion-info">
                    <strong>{{ s.student_name }}</strong>
                    <el-tag :type="s.priority === 'high' ? 'danger' : s.priority === 'medium' ? 'warning' : 'info'" size="small">
                      {{ s.priority === 'high' ? '高优' : s.priority === 'medium' ? '中优' : '低优' }}
                    </el-tag>
                  </div>
                </div>
                <p class="suggestion-reason">{{ s.reason }}</p>
              </div>
            </template>
            <div v-else class="suggestion-default">
              <el-icon :size="24" color="#ccc"><MagicStick /></el-icon>
              <p>暂无推荐</p>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getConversations, getMessages, sendMessage, markRead } from '@/api/messages'
import { getStudents, suggestContacts, type StudentSummary, type ContactSuggestion } from '@/api/teacher'
import { getToken } from '@/utils/token'
import { ElMessage } from 'element-plus'
import { Search, User, ChatDotRound, ChatLineRound, Promotion, ArrowLeft, MagicStick, Star, Loading, WarningFilled, RefreshRight } from '@element-plus/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const userId = auth.user?.id ?? 0
const conversations = ref<any[]>([])
const activeUserId = ref<number | null>(null)
const activeUserName = ref('')
const messages = ref<any[]>([])
const newMsg = ref('')
const msgListRef = ref<HTMLDivElement>()
const search = ref('')
const searchResults = ref<StudentSummary[]>([])
const searched = ref(false)
const myStudents = ref<StudentSummary[]>([])
const suggestions = ref<ContactSuggestion[]>([])
const suggestLoading = ref(false)
const suggestError = ref(false)
let ws: WebSocket | null = null

// ===== Timeline =====
const messageTimeline = computed(() => {
  const items: Array<{ type: 'date'; date: string; label: string } | { type: 'msg'; msg: any }> = []
  let lastDate = ''
  for (const m of messages.value) {
    const d = getDateStr(m.created_at)
    if (d !== lastDate) {
      items.push({ type: 'date', date: d, label: getDateLabel(m.created_at) })
      lastDate = d
    }
    items.push({ type: 'msg', msg: m })
  }
  return items
})

function getDateStr(t: string) {
  const d = new Date(t)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

function getDateLabel(t: string) {
  const date = new Date(t)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.floor((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function connectWs() {
  const token = getToken()
  if (!token) return
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${window.location.host}/api/messages/ws?token=${token}`)
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'new_message') {
        loadConversations()
        if (data.sender_id === activeUserId.value) {
          messages.value.push({
            id: data.id || Date.now(),
            sender_id: data.sender_id,
            content: data.content,
            created_at: data.created_at,
            read: true,
          })
          nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' }))
        }
      }
    } catch {}
  }
  ws.onclose = () => { ws = null }
}

function disconnectWs() {
  if (ws) { ws.close(); ws = null }
}

async function loadConversations() {
  try { conversations.value = await getConversations() } catch {}
}

async function searchStudents() {
  if (!search.value.trim()) {
    searchResults.value = []
    searched.value = false
    return
  }
  try {
    searchResults.value = await getStudents(search.value.trim())
    searched.value = true
  } catch { searchResults.value = [] }
}

async function selectConversation(uid: number, uname: string) {
  activeUserId.value = uid
  activeUserName.value = uname
  search.value = ''
  searchResults.value = []
  searched.value = false
  try {
    messages.value = await getMessages(uid)
    await markRead(uid)
    loadConversations()
  } catch {}
}

function scrollToBottom() {
  nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' }))
}

function goBack() {
  activeUserId.value = null
  activeUserName.value = ''
  messages.value = []
}

async function sendMsg() {
  if (!newMsg.value.trim() || !activeUserId.value) return
  try {
    await sendMessage(activeUserId.value, newMsg.value.trim())
    messages.value.push({
      id: Date.now(), sender_id: userId, receiver_id: activeUserId.value,
      content: newMsg.value.trim(), read: true, created_at: new Date().toISOString()
    })
    newMsg.value = ''
    nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' }))
  } catch { ElMessage.error('发送失败') }
}

async function loadSuggestions() {
  suggestLoading.value = true
  suggestError.value = false
  try {
    suggestions.value = await suggestContacts()
  } catch {
    suggestError.value = true
  } finally {
    suggestLoading.value = false
  }
}

function formatTime(t: string | null) {
  if (!t) return ''
  try {
    let dateStr = t
    if (!dateStr.endsWith('Z') && !dateStr.includes('+') && dateStr.includes('T')) {
      dateStr += 'Z'
    } else if (!dateStr.endsWith('Z') && !dateStr.includes('+', 10)) {
      dateStr += 'Z'
    }
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return timeStr
  } catch { return t }
}

async function loadMyStudents() {
  try { myStudents.value = await getStudents() } catch {}
}

onMounted(async () => {
  connectWs()
  await Promise.all([loadConversations(), loadMyStudents()])
  if (route.query.studentId) {
    const sid = Number(route.query.studentId)
    const sname = (route.query.studentName as string) || ''
    selectConversation(sid, sname)
    router.replace({ query: {} })
  } else {
    loadSuggestions()
  }
})

onUnmounted(() => disconnectWs())
</script>

<style scoped>
/* ===== Sidebar Transition ===== */
.sidebar-enter-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.sidebar-leave-active {
  transition: all 0.15s cubic-bezier(0.4, 0, 1, 1);
}
.sidebar-enter-from {
  opacity: 0;
  transform: translateX(-24px);
}
.sidebar-leave-to {
  opacity: 0;
  transform: translateX(-24px);
}

/* ===== Chat Panel Transition ===== */
.slide-right-enter-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-right-leave-active {
  transition: all 0.15s cubic-bezier(0.4, 0, 1, 1);
}
.slide-right-enter-from {
  opacity: 0;
  transform: translateX(24px) scale(0.98);
}
.slide-right-leave-to {
  opacity: 0;
  transform: translateX(24px) scale(0.98);
}

.chat-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; }

.msg-page {
  display: flex; height: 100%;
  background: #fff; border-radius: 14px; overflow: hidden;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}

/* ===== Sidebar ===== */
.msg-sidebar {
  width: 300px; flex-shrink: 0; display: flex; flex-direction: column;
  border-right: 1px solid #f0f0f0;
}
.sidebar-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 16px 0;
}
.sidebar-header h3 { font-size: 16px; font-weight: 600; color: #1a1a2e; margin: 0; }
.conv-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 22px; padding: 0 6px;
  font-size: 12px; font-weight: 600; color: #5b8def;
  background: rgba(91,141,239,0.1); border-radius: 11px;
}
.sidebar-search { padding: 12px 16px; }
.sidebar-scroll { flex: 1; overflow-y: auto; min-height: 0; }

.conv-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; cursor: pointer; transition: background .15s;
  border-left: 3px solid transparent;
}
.conv-item:hover { background: rgba(64,158,255,0.04); }
.conv-item.active { background: rgba(64,158,255,0.08); border-left-color: #409eff; }
.conv-avatar { flex-shrink: 0; }
.conv-info { flex: 1; min-width: 0; }
.conv-top { display: flex; justify-content: space-between; align-items: baseline; }
.conv-top strong { font-size: 14px; color: #333; }
.conv-time { font-size: 11px; color: #bbb; flex-shrink: 0; margin-left: 8px; }
.conv-preview { font-size: 12px; color: #999; display: block; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-badge { --el-badge-bg-color: #f56c6c; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 40px 0; color: #bbb; font-size: 13px;
}

/* ===== Chat ===== */
.msg-chat { flex: 1; display: flex; flex-direction: column; }
.chat-header {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px; font-size: 15px; font-weight: 600;
  border-bottom: 1px solid #f0f0f0; background: #fafafa;
}
.back-btn { margin-right: 4px; }
.chat-name { color: #1a1a2e; }
.msg-list { flex: 1; overflow-y: auto; padding: 20px; background: #f8faff; }

/* 日期分隔符 */
.date-separator { text-align: center; margin: 16px 0; }
.date-separator span {
  display: inline-block; padding: 3px 14px; border-radius: 10px;
  font-size: 11px; color: #999; background: rgba(0,0,0,.04);
}

.msg-bubble { margin-bottom: 12px; max-width: min(65%, 380px); width: fit-content; }
.msg-bubble.mine { margin-left: auto; }
.msg-bubble.theirs { margin-right: auto; }
.bubble-text {
  padding: 10px 14px; border-radius: 16px;
  font-size: 14px; line-height: 1.5;
}
.mine .bubble-text { background: linear-gradient(135deg, #409eff, #337ecc); color: #fff; border-bottom-right-radius: 4px; }
.theirs .bubble-text { background: #fff; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.bubble-time {
  font-size: 11px; color: #aaa; margin-top: 4px; padding: 0 4px;
  display: flex; align-items: center; gap: 4px;
}
.mine .bubble-time { justify-content: flex-end; }

.chat-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 60px 0; color: #bbb; font-size: 13px;
}

.msg-input-bar {
  display: flex; gap: 10px; padding: 12px 16px;
  border-top: 1px solid #f0f0f0; align-items: flex-end; background: #fff;
}
.msg-input-bar .el-textarea { flex: 1; }
.msg-input-bar .el-textarea__inner { min-height: auto !important; padding: 8px 12px; line-height: 1.4; resize: none; border-radius: 10px; }

.no-selection {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; padding: 32px 24px; gap: 16px;
  overflow-y: auto;
}
.student-list-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 15px; font-weight: 600; color: #1a1a2e;
  padding-bottom: 12px; border-bottom: 1px solid #f0f0f0;
  width: 100%;
}
/* ===== AI Suggestions ===== */
.suggestions-section {
  width: 100%; background: linear-gradient(135deg, #fef9e7 0%, #fdf2e9 100%);
  border-radius: 12px; padding: 16px; margin-bottom: 8px;
  border: 1px solid rgba(230,162,60,0.2);
}
.suggestions-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 600; color: #e6a23c; margin-bottom: 12px;
}
.suggestion-item {
  padding: 12px; border-radius: 10px; cursor: pointer;
  transition: all 0.15s; background: rgba(255,255,255,0.7);
  margin-bottom: 8px;
}
.suggestion-item:last-child { margin-bottom: 0; }
.suggestion-item:hover { background: rgba(255,255,255,0.95); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.suggestion-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.suggestion-info { display: flex; align-items: center; gap: 8px; }
.suggestion-info strong { font-size: 14px; color: #333; }
.suggestion-reason { font-size: 12px; color: #666; line-height: 1.5; margin: 0; }
.suggestion-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 20px 0; color: #909399; font-size: 13px;
}
.suggestion-error {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 16px 0; text-align: center;
}
.suggestion-error p { font-size: 12px; color: #f56c6c; margin: 0; }
.suggestion-default {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 16px 0; color: #bbb; text-align: center;
}
.suggestion-default p { font-size: 12px; margin: 0; line-height: 1.5; }
.student-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px; width: 100%;
}
.student-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border-radius: 12px; cursor: pointer;
  transition: all 0.15s; background: #fff;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}
.student-item:hover {
  background: rgba(64,158,255,0.06);
  box-shadow: 0 4px 12px rgba(64,158,255,0.12);
  transform: translateY(-1px);
}
.student-avatar { flex-shrink: 0; }
.student-info { display: flex; flex-direction: column; min-width: 0; }
.student-info strong { font-size: 14px; color: #333; }
.student-info small { font-size: 11px; color: #999; margin-top: 2px; }
.empty-tip { grid-column: 1 / -1; text-align: center; color: #bbb; padding: 32px 0; font-size: 13px; }
</style>
