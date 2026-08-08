<template>
  <div class="contact-panel">
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
    <template v-else>
      <!-- 左侧：会话列表 -->
      <div class="conv-sidebar">
        <div class="conv-header">
          <div class="conv-header-left">
            <el-dropdown trigger="click" @command="handleHeaderAction">
              <el-button text circle class="action-btn">
                <el-icon :size="18"><Plus /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="createGroup">
                    <el-icon><ChatRound /></el-icon> 创建群聊
                  </el-dropdown-item>
                  <el-dropdown-item command="addFriend">
                    <el-icon><User /></el-icon> 添加好友
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="conv-header-center">
            <span class="conv-title">消息</span>
          </div>
          <div class="conv-header-right">
            <el-badge :value="totalUnread" :hidden="!totalUnread" :max="99">
              <el-icon :size="16" class="conv-bell"><Bell /></el-icon>
            </el-badge>
          </div>
        </div>

        <div class="conv-search">
          <el-input v-model="searchKeyword" placeholder="搜索会话" size="small" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <div class="conv-list">
          <div v-if="filteredConvItems.length === 0" class="conv-empty">
            <el-icon :size="32" color="#d0d5dd"><ChatDotRound /></el-icon>
            <span>{{ searchKeyword.trim() ? '未匹配到会话' : '暂无会话' }}</span>
          </div>
          <div
            v-for="item in filteredConvItems"
            :key="item._id"
            :class="['conv-item', { active: item.id === activeId && item._type === activeType }]"
            @click="openChat(item)"
          >
            <div class="conv-avatar-wrap">
              <el-badge :value="item.unread_count" :hidden="!item.unread_count" class="conv-badge-avatar">
                <el-avatar :size="40" :src="item.avatar || undefined">{{ item.name[0] }}</el-avatar>
              </el-badge>
              <span v-if="item._type === 'group'" class="g-badge">群</span>
            </div>
            <div class="conv-info">
              <div class="conv-top">
                <span class="conv-name">{{ item.name }}</span>
                <span class="conv-time">{{ formatTime(item.last_message_time) }}</span>
              </div>
              <div class="conv-bottom">
                <span class="conv-preview">{{ previewText(item.last_message) }}</span>
                <el-badge v-if="item.unread_count" :value="item.unread_count" :max="99" class="conv-badge" />
              </div>
              <span v-if="item._type === 'group'" class="conv-count">{{ item.member_count }}人</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：聊天区域 -->
      <div class="chat-area">
        <template v-if="activeId">
          <div class="chat-header">
            <div class="chat-header-info">
              <span class="chat-name">{{ activeName }}</span>
              <small v-if="activeType === 'group'" class="chat-sub">{{ currentGroup?.member_count || 0 }}人</small>
            </div>
            <div class="chat-header-actions">
              <el-popover v-if="activeType === 'group'" trigger="click" width="280" :disabled="!currentGroup?.announcement">
                <template #reference>
                  <el-button text circle :disabled="!currentGroup?.announcement">
                    <el-icon :size="16"><Bell /></el-icon>
                  </el-button>
                </template>
                <div class="ann-box">
                  <strong>群公告</strong>
                  <p class="ann-text">{{ currentGroup?.announcement || '暂无公告' }}</p>
                </div>
              </el-popover>
              <el-dropdown v-if="activeType === 'group'" trigger="click">
                <el-button text circle>
                  <el-icon :size="16"><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="showManageGroup = true">
                      <el-icon><Setting /></el-icon> 群管理
                    </el-dropdown-item>
                    <el-dropdown-item @click="showAddMember = true">
                      <el-icon><Plus /></el-icon> 添加成员
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <div class="msg-list" ref="msgListRef"
            @dragover.prevent="onDragOver"
            @dragleave="onDragLeave"
            @drop.prevent="onDrop">
            <!-- 拖拽遮罩 -->
            <Transition name="fade">
              <div v-if="dragOver" class="drag-overlay">
                <el-icon :size="48"><UploadFilled /></el-icon>
                <span>释放以上传文件</span>
                <small>支持图片、文档，最大 50MB</small>
              </div>
            </Transition>
            <template v-for="item in messageTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
              <div v-if="item.type === 'date'" class="date-separator">
                <span>{{ item.label }}</span>
              </div>
              <div v-else :class="['msg-bubble', item.msg.sender_id === userId ? 'mine' : 'theirs']">
                <div v-if="activeType === 'group' && item.msg.sender_id !== userId" class="sender-info">
                  <span class="sender-name">{{ item.msg.sender_name }}</span>
                </div>
                <template v-if="getMsgMeta(item.msg).isFile">
                  <template v-if="getMsgMeta(item.msg).fileType === 'image'">
                    <div class="bubble-image" @click="previewImage(getMsgMeta(item.msg).url)">
                      <img :src="getMsgMeta(item.msg).url" :alt="getMsgMeta(item.msg).text" />
                    </div>
                  </template>
                  <div v-else class="bubble-file" @click="downloadFile(getMsgMeta(item.msg).url, getMsgMeta(item.msg).text)">
                    <el-icon :size="24"><Document /></el-icon>
                    <div class="bubble-file-info">
                      <span class="bubble-file-name">{{ getMsgMeta(item.msg).text }}</span>
                      <small>点击下载</small>
                    </div>
                  </div>
                </template>
                <div v-else class="bubble-text">{{ item.msg.content }}</div>
                <div class="bubble-time">{{ formatTime(item.msg.created_at) }}</div>
              </div>
            </template>
            <div v-if="messages.length === 0" class="chat-empty">
              <el-icon :size="42"><ChatDotRound /></el-icon>
              <span>暂无消息，发送第一条消息吧</span>
            </div>
          </div>

          <div class="input-bar">
            <div class="input-container">
              <div class="input-toolbar">
                <label class="file-upload-btn" title="发送文件">
                  <el-icon :size="18"><FolderOpened /></el-icon>
                  <input type="file" multiple hidden ref="fileInputRef" @change="onFileSelect" accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.zip,.rar" />
                </label>
              </div>
              <div class="input-field-wrap">
                <textarea
                  ref="textareaRef"
                  v-model="newMsg"
                  placeholder="输入消息..."
                  class="chat-textarea"
                  rows="1"
                  @input="autoResize"
                  @keydown.enter.prevent="sendMsg"
                  @paste="onPaste"
                ></textarea>
              </div>
              <div class="input-actions">
                <button
                  type="button"
                  :class="['action-icon-btn', { active: speech.isListening.value || recorder.isRecording.value }]"
                  @click="toggleMic"
                >
                  <el-icon :size="18"><Microphone /></el-icon>
                </button>
                <button type="button" class="send-btn" :disabled="!newMsg.trim()" @click="sendMsg">
                  <el-icon :size="18"><Top /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="no-selection">
          <el-icon :size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
          <span>选择一个会话开始聊天</span>
        </div>
      </div>
    </template>

    <!-- 图片预览 -->
    <Transition name="fade">
      <div v-if="previewUrl" class="image-preview" @click="previewUrl = ''">
        <img :src="previewUrl" @click.stop />
      </div>
    </Transition>

    <!-- ============= 添加好友弹窗 ============= -->
    <el-dialog v-model="showAddFriend" title="添加好友" width="480px" :close-on-click-modal="false" @opened="focusAddFriendInput">
      <div class="add-friend-dialog">
        <div class="add-friend-search-box">
          <el-input ref="addFriendInputRef" v-model="addFriendSearch" placeholder="输入学号、工号或姓名搜索"
            size="large" clearable @input="onAddFriendSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <div class="add-friend-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>可搜索全校师生进行添加</span>
          </div>
        </div>
        <div class="add-friend-results">
          <div v-if="addFriendSearch.trim() && addFriendLoading" class="search-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>搜索中...</span>
          </div>
          <div v-else-if="addFriendSearch.trim() && !addFriendLoading && addFriendResults.length === 0" class="empty-state">
            <el-icon :size="40" color="#ddd"><User /></el-icon>
            <span>未找到用户</span>
          </div>
          <div v-for="u in addFriendResults" :key="u.id" class="add-friend-item">
            <div class="add-friend-item-left">
              <el-avatar :size="40" :src="u.avatar || undefined">{{ u.name[0] }}</el-avatar>
              <div class="add-friend-item-info">
                <div class="add-friend-item-name">
                  {{ u.name }}
                  <el-tag size="small" :type="u.role === 'teacher' ? 'warning' : 'info'">
                    {{ u.role === 'teacher' ? '教师' : '学生' }}
                  </el-tag>
                </div>
                <div class="add-friend-item-username">{{ u.username }}</div>
              </div>
            </div>
            <el-button type="primary" size="small" @click="addFriendAndChat(u)">
              <el-icon><Plus /></el-icon> 添加
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 创建群聊弹窗 ============= -->
    <el-dialog v-model="showCreateGroup" title="创建群聊" width="480px" :close-on-click-modal="false">
      <div class="create-group-form">
        <el-input v-model="newGroupName" placeholder="请输入群名称" maxlength="20" show-word-limit size="large" />
        <div class="member-search-box" style="margin-top:14px">
          <el-input v-model="memberSearch" placeholder="搜索成员（学号/工号/姓名）" size="small"
            @input="searchMembersForGroup" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div v-if="selectedMembers.length" class="selected-members">
          <el-tag v-for="m in selectedMembers" :key="m.id" closable @close="removeSelectedMember(m.id)">
            {{ m.name }}
          </el-tag>
        </div>
        <div v-if="memberSearchResults.length" class="member-search-results">
          <div v-for="u in memberSearchResults" :key="u.id" class="member-search-item" @click="addSelectedMember(u)">
            <el-avatar :size="32">{{ u.name[0] }}</el-avatar>
            <div class="member-search-info">
              <span class="member-name">{{ u.name }}</span>
              <span class="member-username">{{ u.username }}</span>
            </div>
            <el-icon v-if="selectedMembers.some(m => m.id === u.id)" color="#409eff"><Check /></el-icon>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCreateGroup = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup" :disabled="!newGroupName.trim()">创建</el-button>
      </template>
    </el-dialog>

    <!-- ============= 添加群成员弹窗 ============= -->
    <el-dialog v-model="showAddMember" title="添加成员" width="440px" :close-on-click-modal="false">
      <el-input v-model="addMemberSearch" placeholder="搜索用户" clearable @input="searchMembersToAdd">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div v-if="addMemberResults.length" class="add-member-results">
        <div v-for="u in addMemberResults" :key="u.id" class="add-member-item" @click="handleAddMember(u.id)">
          <el-avatar :size="36">{{ u.name[0] }}</el-avatar>
          <div class="add-member-info">
            <span>{{ u.name }}</span>
            <small>{{ u.username }}</small>
          </div>
          <el-icon color="#409eff"><Plus /></el-icon>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 群管理弹窗 ============= -->
    <el-dialog v-model="showManageGroup" title="群管理" width="520px" :close-on-click-modal="false" @opened="onManageDialogOpened">
      <div class="manage-group-dialog">
        <!-- 群公告 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <el-icon><Bell /></el-icon> 群公告
            </span>
            <el-button v-if="!editingAnnouncement" type="primary" text size="small" @click="startEditAnnouncement">
              {{ currentGroup?.announcement ? '编辑' : '设置公告' }}
            </el-button>
          </div>
          <template v-if="editingAnnouncement">
            <el-input v-model="announcementText" type="textarea" :rows="3" placeholder="请输入群公告..." maxlength="500" show-word-limit />
            <div class="manage-announcement-actions">
              <el-button size="small" @click="cancelEditAnnouncement">取消</el-button>
              <el-button size="small" type="primary" @click="saveAnnouncement" :loading="savingAnnouncement">保存</el-button>
            </div>
          </template>
          <div v-else class="manage-announcement-content">
            <template v-if="currentGroup?.announcement">
              <p>{{ currentGroup.announcement }}</p>
            </template>
            <span v-else class="manage-empty-hint">暂无群公告</span>
          </div>
        </div>

        <el-divider />

        <!-- 群成员 -->
        <div class="manage-section">
          <div class="manage-section-header">
            <span class="manage-section-title">
              <el-icon><User /></el-icon> 群成员
              <span class="member-count-tag">{{ groupMembers.length }}人</span>
            </span>
            <el-button type="primary" text size="small" @click="showManageInvite = !showManageInvite">
              <el-icon><Plus /></el-icon> 邀请成员
            </el-button>
          </div>

          <!-- 邀请成员展开区 -->
          <div v-if="showManageInvite" class="manage-invite-box">
            <el-input v-model="manageInviteSearch" placeholder="搜索用户（学号/工号/姓名）" size="small" clearable @input="searchMembersForManage">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <div v-if="manageInviteResults.length" class="manage-invite-results">
              <div v-for="u in manageInviteResults" :key="u.id" class="manage-invite-item" @click="handleManageAddMember(u.id)">
                <el-avatar :size="32">{{ u.name[0] }}</el-avatar>
                <div class="manage-invite-info">
                  <span>{{ u.name }}</span>
                  <small>{{ u.username }}</small>
                </div>
                <el-icon color="#409eff"><Plus /></el-icon>
              </div>
            </div>
          </div>

          <!-- 成员列表 -->
          <div class="manage-members-list">
            <div v-for="m in groupMembers" :key="m.user_id" class="manage-member-item">
              <div class="manage-member-left">
                <el-avatar :size="34">{{ m.user_name[0] }}</el-avatar>
                <div class="manage-member-info">
                  <span class="manage-member-name">{{ m.user_name }}</span>
                  <el-tag v-if="m.role === 'owner'" type="danger" size="small">群主</el-tag>
                  <el-tag v-else-if="m.role === 'admin'" type="warning" size="small">管理员</el-tag>
                </div>
              </div>
              <el-button
                v-if="m.user_id !== userId && isCurrentUserAdmin"
                type="danger" text size="small"
                @click="handleRemoveMember(m.user_id, m.user_name)">
                移除
              </el-button>
            </div>
          </div>
        </div>

        <el-divider />

        <!-- 危险操作 -->
        <div class="manage-section manage-danger-zone">
          <div class="manage-section-title" style="margin-bottom:12px">
            <el-icon><WarningFilled /></el-icon> 危险操作
          </div>
          <div class="manage-danger-actions">
            <el-button v-if="!isCurrentUserOwner" type="danger" plain @click="handleLeaveGroup">
              <el-icon><SwitchButton /></el-icon> 退出群聊
            </el-button>
            <el-button v-if="isCurrentUserOwner" type="danger" @click="handleDisbandGroup">
              <el-icon><Delete /></el-icon> 解散群聊
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getConversations, getMessages, sendMessage, markRead } from '@/api/messages'
import {
  getGroups, getGroup, getGroupMembers, createGroup as apiCreateGroup,
  addGroupMembers, sendGroupMessage, getGroupMessages, searchUsers,
  updateGroupAnnouncement, leaveGroup, disbandGroup, removeGroupMember,
  markGroupRead,
  type GroupOut, type GroupMemberOut, type UserSearchResult,
} from '@/api/groups'
import { uploadFile } from '@/api/upload'
import { getToken } from '@/utils/token'
import { ElMessage } from 'element-plus'
import {
  Top, Microphone, Bell, ChatDotRound, Document, FolderOpened,
  Search, Plus, User, ChatRound, Check, InfoFilled, Loading,
  MoreFilled, Setting, WarningFilled, Delete, SwitchButton, UploadFilled,
} from '@element-plus/icons-vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import { useMediaRecorder } from '@/composables/useMediaRecorder'

const emit = defineEmits<{ read: [] }>()
const auth = useAuthStore()
const userId = auth.user?.id ?? 0

interface ConvItem {
  _id: string
  _type: 'single' | 'group'
  id: number
  name: string
  avatar: string | undefined
  member_count: number
  last_message: string
  last_message_time: string | null
  unread_count: number
}

// 会话数据
const conversations = ref<any[]>([])
const groups = ref<GroupOut[]>([])
const activeId = ref<number | null>(null)
const activeName = ref('')
const activeType = ref<'single' | 'group'>('single')
const messages = ref<any[]>([])
const currentGroup = ref<GroupOut | null>(null)

// 输入
const newMsg = ref('')
const msgListRef = ref<HTMLDivElement>()
const textareaRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()
const previewUrl = ref('')

// 语音
const speech = useSpeechRecognition()
const recorder = useMediaRecorder()
const loading = ref(true)

// 搜索
const searchKeyword = ref('')

// 拖拽上传
const dragOver = ref(false)

// 添加好友
const showAddFriend = ref(false)
const addFriendSearch = ref('')
const addFriendResults = ref<UserSearchResult[]>([])
const addFriendLoading = ref(false)
const addFriendInputRef = ref()
let addFriendTimer: ReturnType<typeof setTimeout> | null = null

// 创建群聊
const showCreateGroup = ref(false)
const newGroupName = ref('')
const memberSearch = ref('')
const memberSearchResults = ref<UserSearchResult[]>([])
const selectedMembers = ref<UserSearchResult[]>([])

// 添加群成员
const showAddMember = ref(false)
const addMemberSearch = ref('')
const addMemberResults = ref<UserSearchResult[]>([])

// 群管理
const showManageGroup = ref(false)
const editingAnnouncement = ref(false)
const announcementText = ref('')
const savingAnnouncement = ref(false)
const showManageInvite = ref(false)
const manageInviteSearch = ref('')
const manageInviteResults = ref<UserSearchResult[]>([])
let manageInviteTimer: ReturnType<typeof setTimeout> | null = null
const groupMembers = ref<GroupMemberOut[]>([])

const isCurrentUserOwner = computed(() => {
  const me = groupMembers.value.find(m => m.user_id === userId)
  return me?.role === 'owner'
})
const isCurrentUserAdmin = computed(() => {
  const me = groupMembers.value.find(m => m.user_id === userId)
  return me?.role === 'owner' || me?.role === 'admin'
})

const totalUnread = computed(() => {
  const c = conversations.value.reduce((s: number, x: any) => s + (x.unread_count ?? 0), 0)
  const g = groups.value.reduce((s: number, x: GroupOut) => s + (x.unread_count ?? 0), 0)
  return c + g
})

const convItems = computed<ConvItem[]>(() => {
  const items: ConvItem[] = []
  for (const g of groups.value) {
    items.push({
      _id: 'g-' + g.id,
      _type: 'group',
      id: g.id,
      name: g.name,
      avatar: g.avatar || undefined,
      member_count: g.member_count,
      last_message: g.last_message,
      last_message_time: g.last_message_time,
      unread_count: g.unread_count,
    })
  }
  for (const c of conversations.value) {
    items.push({
      _id: 's-' + c.user_id,
      _type: 'single',
      id: c.user_id,
      name: c.user_name,
      avatar: c.user_avatar || undefined,
      member_count: 0,
      last_message: c.last_message,
      last_message_time: c.last_message_time,
      unread_count: c.unread_count,
    })
  }
  items.sort((a, b) =>
    (b.last_message_time || '').localeCompare(a.last_message_time || '')
  )
  console.log('[DEBUG] convItems:', items.map(i => ({ name: i.name, unread: i.unread_count })))
  return items
})

// 搜索过滤
const filteredConvItems = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return convItems.value
  return convItems.value.filter(item =>
    item.name.toLowerCase().includes(kw) ||
    String(item.id).includes(kw)
  )
})

// 消息时间线
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

function previewText(text: string) {
  const c = text || ''
  if (c.startsWith('{') && c.includes('"type"')) {
    try {
      const p = JSON.parse(c)
      return p.type === 'image' ? '[图片] ' + (p.text || '') : '[文件] ' + (p.text || '')
    } catch {}
  }
  return c
}

function getMsgMeta(msg: any) {
  const c = msg.content || ''
  if (c.startsWith('{') && c.includes('"type"')) {
    try {
      const parsed = JSON.parse(c)
      if (parsed.type === 'file' || parsed.type === 'image') {
        return { isFile: true, fileType: parsed.type, text: parsed.text || '', url: parsed.url || '' }
      }
    } catch {}
  }
  return { isFile: false, fileType: '', text: '', url: '' }
}

// 日期工具
function parseDate(t: string) {
  if (!t) return new Date()
  let dateStr = t
  if (!dateStr.endsWith('Z') && !dateStr.includes('+') && dateStr.includes('T')) {
    dateStr += 'Z'
  }
  return new Date(dateStr)
}

function getDateStr(t: string) {
  const d = parseDate(t)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

function getDateLabel(t: string) {
  const date = parseDate(t)
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

// 语音
function toggleMic() {
  if (!speech.isSupported.value && recorder.isSupported.value) {
    if (recorder.isRecording.value) recorder.stop()
    else recorder.start()
    return
  }
  if (speech.isListening.value) {
    speech.stop()
    if (speech.transcript.value) newMsg.value += speech.transcript.value
  } else {
    speech.start()
  }
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

// +号菜单
function handleHeaderAction(cmd: string) {
  if (cmd === 'createGroup') showCreateGroup.value = true
  else if (cmd === 'addFriend') showAddFriend.value = true
}

// 添加好友
function focusAddFriendInput() {
  nextTick(() => addFriendInputRef.value?.focus())
}

function onAddFriendSearch() {
  if (addFriendTimer) clearTimeout(addFriendTimer)
  if (!addFriendSearch.value.trim()) {
    addFriendResults.value = []
    return
  }
  addFriendLoading.value = true
  addFriendTimer = setTimeout(async () => {
    try {
      addFriendResults.value = await searchUsers(addFriendSearch.value.trim())
    } catch { addFriendResults.value = [] }
    finally { addFriendLoading.value = false }
  }, 300)
}

async function addFriendAndChat(user: UserSearchResult) {
  showAddFriend.value = false
  addFriendSearch.value = ''
  addFriendResults.value = []
  await openChat({ _id: 's-' + user.id, _type: 'single', id: user.id, name: user.name, avatar: user.avatar || undefined, member_count: 0, last_message: '', last_message_time: null, unread_count: 0 })
  ElMessage.success(`已添加 ${user.name}，可以开始聊天了`)
}

// 创建群聊
async function searchMembersForGroup() {
  if (!memberSearch.value.trim()) { memberSearchResults.value = []; return }
  try { memberSearchResults.value = await searchUsers(memberSearch.value.trim()) } catch { memberSearchResults.value = [] }
}

function addSelectedMember(u: UserSearchResult) {
  if (!selectedMembers.value.some(m => m.id === u.id)) selectedMembers.value.push(u)
}

function removeSelectedMember(id: number) {
  selectedMembers.value = selectedMembers.value.filter(m => m.id !== id)
}

async function handleCreateGroup() {
  if (!newGroupName.value.trim()) return
  try {
    const result = await apiCreateGroup({
      name: newGroupName.value.trim(),
      member_ids: selectedMembers.value.map(m => m.id)
    })
    ElMessage.success('群聊创建成功')
    showCreateGroup.value = false
    newGroupName.value = ''
    selectedMembers.value = []
    await loadGroups()
    openChat({ _id: 'g-' + result.id, _type: 'group', id: result.id, name: result.name, avatar: undefined, member_count: 0, last_message: '', last_message_time: null, unread_count: 0 })
  } catch { ElMessage.error('创建失败') }
}

// 添加群成员
async function searchMembersToAdd() {
  if (!addMemberSearch.value.trim()) { addMemberResults.value = []; return }
  try { addMemberResults.value = await searchUsers(addMemberSearch.value.trim()) } catch { addMemberResults.value = [] }
}

async function handleAddMember(uid: number) {
  if (!activeId.value || activeType.value !== 'group') return
  try {
    await addGroupMembers(activeId.value, [uid])
    ElMessage.success('已添加')
    addMemberSearch.value = ''
    addMemberResults.value = []
    showAddMember.value = false
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('添加失败') }
}

// 群管理
async function onManageDialogOpened() {
  if (!activeId.value) return
  try {
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
    announcementText.value = currentGroup.value?.announcement || ''
    editingAnnouncement.value = false
    showManageInvite.value = false
    manageInviteSearch.value = ''
    manageInviteResults.value = []
  } catch {}
}

function startEditAnnouncement() {
  announcementText.value = currentGroup.value?.announcement || ''
  editingAnnouncement.value = true
}

function cancelEditAnnouncement() {
  editingAnnouncement.value = false
  announcementText.value = currentGroup.value?.announcement || ''
}

async function saveAnnouncement() {
  if (!activeId.value) return
  savingAnnouncement.value = true
  try {
    await updateGroupAnnouncement(activeId.value, announcementText.value)
    ElMessage.success('群公告已更新')
    editingAnnouncement.value = false
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('更新失败') }
  finally { savingAnnouncement.value = false }
}

function searchMembersForManage() {
  if (manageInviteTimer) clearTimeout(manageInviteTimer)
  if (!manageInviteSearch.value.trim()) { manageInviteResults.value = []; return }
  manageInviteTimer = setTimeout(async () => {
    try { manageInviteResults.value = await searchUsers(manageInviteSearch.value.trim()) } catch { manageInviteResults.value = [] }
  }, 300)
}

async function handleManageAddMember(uid: number) {
  if (!activeId.value) return
  try {
    await addGroupMembers(activeId.value, [uid])
    ElMessage.success('已添加')
    manageInviteSearch.value = ''
    manageInviteResults.value = []
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('添加失败') }
}

async function handleRemoveMember(uid: number, name: string) {
  if (!activeId.value) return
  try {
    await removeGroupMember(activeId.value, uid)
    ElMessage.success(`已移除 ${name}`)
    groupMembers.value = await getGroupMembers(activeId.value)
    currentGroup.value = await getGroup(activeId.value)
  } catch { ElMessage.error('移除失败') }
}

async function handleLeaveGroup() {
  if (!activeId.value) return
  try {
    await leaveGroup(activeId.value)
    ElMessage.success('已退出群聊')
    showManageGroup.value = false
    goBack()
    await loadGroups()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '退群失败')
  }
}

async function handleDisbandGroup() {
  if (!activeId.value) return
  try {
    await disbandGroup(activeId.value)
    ElMessage.success('群聊已解散')
    showManageGroup.value = false
    goBack()
    await loadGroups()
  } catch { ElMessage.error('解散失败') }
}

function goBack() {
  activeId.value = null
  activeName.value = ''
  messages.value = []
  currentGroup.value = null
}

// 打开会话
async function openChat(item: ConvItem) {
  console.log('[DEBUG] openChat:', item)
  activeId.value = item.id
  activeName.value = item.name
  activeType.value = item._type
  if (item._type === 'single') {
    currentGroup.value = null
  }
  try {
    if (item._type === 'single') {
      messages.value = await getMessages(item.id)
      console.log('[DEBUG] markRead for user:', item.id)
      const markResult = await markRead(item.id)
      console.log('[DEBUG] markRead result:', markResult)
      console.log('[DEBUG] loadConversations after markRead')
      const freshConvs = await getConversations()
      console.log('[DEBUG] freshConvs:', JSON.stringify(freshConvs))
      // 强制更新响应式数据
      conversations.value = [...freshConvs]
      await nextTick()
      emit('read')
      // 从最新的会话列表中获取名字
      const latestConv = conversations.value.find((c: any) => c.user_id === item.id)
      console.log('[DEBUG] latestConv:', latestConv)
      if (latestConv) {
        activeName.value = latestConv.user_name
      }
    } else {
      messages.value = await getGroupMessages(item.id)
      currentGroup.value = await getGroup(item.id)
      console.log('[DEBUG] markGroupRead for group:', item.id)
      const markResult = await markGroupRead(item.id)
      console.log('[DEBUG] markGroupRead result:', markResult)
      console.log('[DEBUG] loadGroups after markGroupRead')
      const freshGroups = await getGroups()
      console.log('[DEBUG] freshGroups:', JSON.stringify(freshGroups))
      // 强制更新响应式数据
      groups.value = [...freshGroups]
      await nextTick()
      emit('read')
      // 从最新的群组列表中获取名字
      const latestGroup = groups.value.find(g => g.id === item.id)
      console.log('[DEBUG] latestGroup:', latestGroup)
      if (latestGroup) {
        activeName.value = latestGroup.name
      } else if (currentGroup.value) {
        activeName.value = currentGroup.value.name
      }
    }
    scrollToBottom()
  } catch (e) { console.error('[DEBUG] openChat error:', e) }
}

// 发送
async function sendMsg() {
  if (!newMsg.value.trim() || !activeId.value) return
  const text = newMsg.value.trim()
  try {
    if (activeType.value === 'single') {
      await sendMessage(activeId.value, text)
      messages.value.push({
        id: Date.now(), sender_id: userId, receiver_id: activeId.value,
        content: text, read: true, created_at: new Date().toISOString(),
      })
      loadConversations()
    } else {
      await sendGroupMessage(activeId.value, text)
      messages.value.push({
        id: Date.now(), group_id: activeId.value, sender_id: userId, sender_name: auth.user?.name || '我',
        content: text, created_at: new Date().toISOString(),
      })
      loadGroups()
    }
    newMsg.value = ''
    autoResize()
    scrollToBottom()
  } catch { ElMessage.error('发送失败') }
}

// 文件消息
function makeFileContent(fileType: string, filename: string, url: string) {
  return JSON.stringify({ type: fileType, text: filename, url })
}

function downloadFile(url: string, name: string) {
  const a = document.createElement('a')
  a.href = url; a.download = name; a.click()
}
function previewImage(url: string) { previewUrl.value = url }

async function uploadAndSend(file: File) {
  try {
    const result = await uploadFile(file)
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)
    const content = makeFileContent(isImage ? 'image' : 'file', file.name, result.url)
    await sendTextContent(content)
  } catch { ElMessage.error(`上传 ${file.name} 失败`) }
}

async function sendTextContent(content: string) {
  if (!activeId.value) return
  if (activeType.value === 'single') {
    await sendMessage(activeId.value, content)
    messages.value.push({
      id: Date.now(), sender_id: userId, receiver_id: activeId.value,
      content, read: true, created_at: new Date().toISOString(),
    })
    await loadConversations()
  } else {
    await sendGroupMessage(activeId.value, content)
    messages.value.push({
      id: Date.now(), group_id: activeId.value, sender_id: userId, sender_name: auth.user?.name || '我',
      content, created_at: new Date().toISOString(),
    })
    await loadGroups()
  }
  scrollToBottom()
}

async function uploadFiles(files: FileList | File[]) {
  for (const f of files) {
    if (f.size > 50 * 1024 * 1024) { ElMessage.warning(`${f.name} 超过 50MB 限制`); continue }
    await uploadAndSend(f)
  }
}
function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) uploadFiles(input.files)
  input.value = ''
}
async function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  const files: File[] = []
  for (let i = 0; i < items.length; i++) {
    const blob = items[i].getAsFile()
    if (blob) files.push(blob)
  }
  if (files.length) {
    e.preventDefault()
    await uploadFiles(files)
  }
}

// 拖拽上传
function onDragOver() {
  dragOver.value = true
}

function onDragLeave(e: DragEvent) {
  if (!(e.currentTarget as HTMLElement)?.contains(e.relatedTarget as HTMLElement)) {
    dragOver.value = false
  }
}

async function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files.length) await uploadFiles(e.dataTransfer.files)
}

// WebSocket
let ws: WebSocket | null = null
function connectWs() {
  const token = getToken()
  if (!token) return
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/api/messages/ws?token=${token}`)
  ws.onmessage = async (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'new_message') {
        await loadConversations()
        emit('read')
        if (data.sender_id === activeId.value && activeType.value === 'single') {
          messages.value.push({
            id: data.id || Date.now(), sender_id: data.sender_id, content: data.content,
            created_at: data.created_at, read: true,
          })
          scrollToBottom()
        }
      } else if (data.type === 'new_group_message') {
        await loadGroups()
        if (data.group_id === activeId.value && activeType.value === 'group') {
          messages.value.push({
            id: data.id || Date.now(), group_id: data.group_id, sender_id: data.sender_id,
            sender_name: data.sender_name, content: data.content, created_at: data.created_at,
          })
          scrollToBottom()
        }
      }
    } catch {}
  }
  ws.onclose = () => { ws = null }
}
function disconnectWs() { if (ws) { ws.close(); ws = null } }

// 加载会话
async function loadConversations() {
  try {
    const data = await getConversations()
    console.log('[DEBUG] loadConversations:', data)
    conversations.value = data
  } catch (e) { console.error('[DEBUG] loadConversations error:', e) }
}
async function loadGroups() {
  try {
    const data = await getGroups()
    console.log('[DEBUG] loadGroups:', data)
    groups.value = data
  } catch (e) { console.error('[DEBUG] loadGroups error:', e) }
}

function formatTime(t: string | null) {
  if (!t) return ''
  try {
    const date = parseDate(t)
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

function scrollToBottom() {
  nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' }))
}

onMounted(async () => {
  await Promise.all([loadConversations(), loadGroups()])
  loading.value = false
  connectWs()

  if (conversations.value.length || groups.value.length) {
    const first = convItems.value[0]
    if (first) openChat(first)
  }
})
onUnmounted(() => disconnectWs())
</script>

<style scoped>
.contact-panel { display: flex; height: 100%; background: #fff; border-radius: 10px; overflow: hidden; }

/* ===== 左侧会话列表 ===== */
.conv-sidebar { width: 260px; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid #f0f0f0; background: #f7f8fa; }
.conv-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid #eee; }
.conv-header-left, .conv-header-right { width: 36px; display: flex; align-items: center; }
.conv-header-right { justify-content: flex-end; }
.conv-header-center { flex: 1; text-align: center; }
.conv-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.action-btn { font-size: 18px; color: #409eff; }
.conv-bell { color: #666; cursor: pointer; }
.conv-search { padding: 8px 12px; }
.conv-list { flex: 1; overflow-y: auto; min-height: 0; }
.conv-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px 0; color: #bbb; font-size: 13px; }
.conv-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; transition: background .15s; border-left: 3px solid transparent; }
.conv-item:hover { background: rgba(64,158,255,0.06); }
.conv-item.active { background: rgba(64,158,255,0.12); border-left-color: #409eff; }
.conv-avatar-wrap { position: relative; flex-shrink: 0; line-height: 0; }
.conv-badge-avatar { line-height: 0; }
.g-badge { position: absolute; bottom: -2px; right: -2px; width: 16px; height: 16px; border-radius: 4px; background: #409eff; color: #fff; font-size: 9px; display: flex; align-items: center; justify-content: center; border: 2px solid #f7f8fa; }
.conv-info { flex: 1; min-width: 0; }
.conv-top { display: flex; justify-content: space-between; align-items: center; }
.conv-name { font-size: 13px; font-weight: 500; color: #333; }
.conv-time { font-size: 10px; color: #bbb; margin-left: 6px; flex-shrink: 0; }
.conv-bottom { display: flex; align-items: center; justify-content: space-between; margin-top: 2px; }
.conv-preview { font-size: 11px; color: #999; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-badge { --el-badge-bg-color: #f56c6c; flex-shrink: 0; }
.conv-count { font-size: 10px; color: #bbb; }

/* ===== 右侧聊天区域 ===== */
.chat-area { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.chat-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid #f0f0f0; background: #fafafa; }
.chat-header-info { display: flex; flex-direction: column; }
.chat-header-actions { display: flex; align-items: center; gap: 4px; }
.chat-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.chat-sub { font-size: 12px; color: #999; margin-top: 2px; }
.ann-box { max-height: 180px; overflow-y: auto; }
.ann-box strong { font-size: 14px; }
.ann-text { margin: 8px 0 0; font-size: 13px; color: #555; line-height: 1.6; white-space: pre-wrap; }

.msg-list { flex: 1; overflow-y: auto; padding: 14px 16px; background: #f8faff; position: relative; }
.date-separator { text-align: center; margin: 12px 0; }
.date-separator span { display: inline-block; padding: 3px 12px; border-radius: 10px; font-size: 11px; color: #999; background: rgba(0,0,0,.04); }
.msg-bubble { margin-bottom: 10px; max-width: 75%; width: fit-content; }
.msg-bubble.mine { margin-left: auto; }
.msg-bubble.theirs { margin-right: auto; }
.sender-info { margin-bottom: 3px; }
.sender-name { font-size: 12px; color: #999; }
.bubble-text { padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.5; word-break: break-word; }
.mine .bubble-text { background: linear-gradient(135deg, #409eff, #337ecc); color: #fff; border-bottom-right-radius: 3px; }
.theirs .bubble-text { background: #f0f4f9; color: #333; border-bottom-left-radius: 3px; }
.bubble-time { font-size: 10px; color: #aaa; margin-top: 3px; padding: 0 4px; display: flex; align-items: center; gap: 4px; }
.mine .bubble-time { justify-content: flex-end; }
.chat-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 50px 0; color: #bbb; font-size: 13px; }
.no-selection { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; color: #999; font-size: 14px; }

/* ===== 输入栏 ===== */
.input-bar { flex-shrink: 0; padding: 10px 16px 14px; background: #fff; }
.input-container { background: #fff; border-radius: 14px; padding: 8px 12px 8px; border: 1px solid #e5e7eb; box-shadow: 0 2px 12px rgba(0,0,0,.04); transition: border-color .2s, box-shadow .2s; }
.input-container:focus-within { border-color: #409eff; box-shadow: 0 2px 16px rgba(64,158,255,.12); }
.input-toolbar { display: flex; gap: 8px; }
.file-upload-btn { cursor: pointer; color: #909399; display: inline-flex; align-items: center; transition: color .15s; }
.file-upload-btn:hover { color: #409eff; }
.input-field-wrap { position: relative; margin-top: 6px; }
.chat-textarea { width: 100%; border: none; background: transparent; outline: none; font-size: 15px; font-family: inherit; color: #1f2937; resize: none; line-height: 1.5; padding: 4px 6px; min-height: 24px; max-height: 120px; overflow-y: auto; }
.chat-textarea::placeholder { color: #9ca3af; }
.chat-textarea::-webkit-scrollbar { width: 4px; }
.chat-textarea::-webkit-scrollbar-track { background: transparent; }
.chat-textarea::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
.chat-textarea::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
.input-actions { display: flex; align-items: center; gap: 2px; margin-top: 6px; padding: 0 2px; }
.action-icon-btn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; border: none; background: transparent; color: #6b7280; cursor: pointer; transition: all .15s; padding: 0; }
.action-icon-btn:hover:not(:disabled) { background: #f3f4f6; color: #374151; }
.action-icon-btn.active { background: rgba(64,158,255,.1); color: #409eff; }
.send-btn { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 50%; border: none; background: #409eff; color: #fff; cursor: pointer; transition: background .15s, transform .1s; padding: 0; flex-shrink: 0; margin-left: auto; }
.send-btn:hover:not(:disabled) { background: #337ecc; }
.send-btn:active:not(:disabled) { transform: scale(.94); }
.send-btn:disabled { opacity: .5; cursor: not-allowed; }

/* 文件/图片消息 */
.bubble-image { max-width: 220px; cursor: pointer; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,.1); }
.bubble-image img { width: 100%; height: auto; display: block; }
.bubble-file { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; cursor: pointer; min-width: 180px; }
.mine .bubble-file { background: linear-gradient(135deg, #409eff, #337ecc); color: #fff; border-bottom-right-radius: 3px; }
.theirs .bubble-file { background: #f0f4f9; color: #333; border-bottom-left-radius: 3px; }
.bubble-file-info { flex: 1; min-width: 0; }
.bubble-file-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
.bubble-file-info small { font-size: 11px; opacity: .7; }

/* 拖拽上传 */
.drag-overlay {
  position: absolute; inset: 0; z-index: 10;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  background: rgba(64,158,255,0.92); color: #fff; border-radius: 8px;
}
.drag-overlay span { font-size: 16px; font-weight: 600; }
.drag-overlay small { font-size: 12px; opacity: .85; }

/* 图片预览 */
.image-preview { position: fixed; inset: 0; z-index: 3000; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; cursor: zoom-out; }
.image-preview img { max-width: 90vw; max-height: 90vh; border-radius: 8px; box-shadow: 0 8px 40px rgba(0,0,0,0.4); }

/* 加载态 */
.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 12px; color: #9ca3af; font-size: 14px; }
.loading-spinner { width: 32px; height: 32px; border: 3px solid #e5e7eb; border-top-color: #409eff; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ===== 添加好友弹窗 ===== */
.add-friend-dialog { }
.add-friend-search-box { margin-bottom: 12px; }
.add-friend-hint { display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 12px; color: #909399; }
.add-friend-results { max-height: 360px; overflow-y: auto; }
.add-friend-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-radius: 10px; transition: background .15s; }
.add-friend-item:hover { background: #f5f7fa; }
.add-friend-item-left { display: flex; align-items: center; gap: 12px; }
.add-friend-item-info { }
.add-friend-item-name { font-size: 14px; font-weight: 500; color: #333; display: flex; align-items: center; gap: 8px; }
.add-friend-item-username { font-size: 12px; color: #999; margin-top: 3px; }
.search-loading { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 30px 0; color: #909399; font-size: 13px; }

/* ===== 创建群聊 ===== */
.create-group-form { }
.member-search-box { margin-bottom: 8px; }
.selected-members { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.member-search-results { max-height: 200px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; margin-top: 8px; }
.member-search-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; transition: background .15s; }
.member-search-item:hover { background: #f5f7fa; }
.member-search-info { flex: 1; display: flex; flex-direction: column; }
.member-name { font-size: 14px; color: #333; }
.member-username { font-size: 12px; color: #999; }

/* ===== 添加成员 ===== */
.add-member-results { max-height: 300px; overflow-y: auto; margin-top: 12px; }
.add-member-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; cursor: pointer; border-radius: 8px; transition: background .15s; }
.add-member-item:hover { background: #f5f7fa; }
.add-member-info { flex: 1; display: flex; flex-direction: column; }
.add-member-info span { font-size: 14px; color: #333; }
.add-member-info small { font-size: 12px; color: #999; }

/* ===== 群管理弹窗 ===== */
.manage-group-dialog { }
.manage-section { margin-bottom: 4px; }
.manage-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.manage-section-title { font-size: 14px; font-weight: 600; color: #333; display: flex; align-items: center; gap: 6px; }
.member-count-tag { font-size: 12px; color: #999; font-weight: 400; }
.manage-announcement-content { padding: 10px 12px; background: #f5f7fa; border-radius: 8px; min-height: 40px; }
.manage-announcement-content p { margin: 0; font-size: 13px; color: #555; line-height: 1.6; white-space: pre-wrap; }
.manage-empty-hint { font-size: 13px; color: #bbb; }
.manage-announcement-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
.manage-invite-box { margin-bottom: 12px; padding: 12px; background: #fafafa; border-radius: 8px; border: 1px solid #f0f0f0; }
.manage-invite-results { max-height: 180px; overflow-y: auto; margin-top: 8px; }
.manage-invite-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; border-radius: 8px; transition: background .15s; }
.manage-invite-item:hover { background: #e8f3ff; }
.manage-invite-info { flex: 1; display: flex; flex-direction: column; }
.manage-invite-info span { font-size: 14px; color: #333; }
.manage-invite-info small { font-size: 12px; color: #999; }
.manage-members-list { max-height: 240px; overflow-y: auto; }
.manage-member-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.manage-member-item:last-child { border-bottom: none; }
.manage-member-left { display: flex; align-items: center; gap: 10px; }
.manage-member-info { display: flex; align-items: center; gap: 8px; }
.manage-member-name { font-size: 14px; color: #333; }
.manage-danger-zone { padding: 12px; background: #fef0f0; border-radius: 8px; border: 1px solid #fde2e2; }
.manage-danger-actions { display: flex; gap: 10px; }
</style>