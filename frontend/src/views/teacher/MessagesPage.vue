<template>
  <div class="msg-page">
    <div class="msg-sidebar">
      <div class="sidebar-header">
        <div class="header-left">
          <el-dropdown trigger="click" @command="handleHeaderAction">
            <el-button text circle class="action-btn">
              <el-icon :size="20"><Plus /></el-icon>
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
        <div class="header-center">
          <span class="header-title">消息</span>
        </div>
        <div class="header-right">
          <el-badge :value="totalUnread" :hidden="!totalUnread" :max="99">
            <el-icon :size="18" class="header-icon"><Bell /></el-icon>
          </el-badge>
        </div>
      </div>

      <div class="sidebar-search">
        <el-input v-model="search" placeholder="搜索已有会话" size="small" clearable
          @input="filterConversations">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>

      <div class="sidebar-scroll">
        <template v-if="filteredList.length === 0">
          <div class="empty-state">
            <el-icon :size="40" color="#ddd"><ChatDotRound /></el-icon>
            <span>{{ search.trim() ? '未匹配到会话' : '暂无消息' }}</span>
          </div>
        </template>

        <template v-for="item in filteredList" :key="item._key">
          <!-- 群聊 -->
          <template v-if="item._type === 'group'">
            <div :class="['conv-item', { active: activeId === item.id && activeType === 'group' }]"
              @click="openChat(item.id, item.name, 'group')">
              <div class="conv-avatar-wrapper">
                <el-avatar :size="36">{{ item.name[0] }}</el-avatar>
                <span class="group-badge">群</span>
              </div>
              <div class="conv-info">
                <div class="conv-top">
                  <span class="conv-name">{{ item.name }}</span>
                  <span class="conv-time">{{ formatTime(item.last_message_time) }}</span>
                </div>
                <div class="conv-bottom">
                  <span class="conv-preview">{{ item.last_message || '暂无消息' }}</span>
                  <span class="conv-member-count">{{ item.member_count }}人</span>
                  <el-badge v-if="item.unread_count" :value="item.unread_count" :max="99" class="conv-badge" />
                </div>
              </div>
            </div>
          </template>
          <!-- 单聊 -->
          <template v-else>
            <div :class="['conv-item', { active: activeId === item.id && activeType === 'single' }]"
              @click="openChat(item.id, item.name, 'single')">
              <div class="conv-avatar-wrapper">
                <el-badge :value="item.unread_count" :hidden="!item.unread_count" class="conv-badge-avatar">
                  <el-avatar :size="36" :src="item.user_avatar || undefined">{{ item.name[0] }}</el-avatar>
                </el-badge>
              </div>
              <div class="conv-info">
                <div class="conv-top">
                  <span class="conv-name">{{ item.name }}</span>
                  <span class="conv-time">{{ formatTime(item.last_message_time) }}</span>
                </div>
                <div class="conv-bottom">
                  <span class="conv-preview">{{ item.last_message }}</span>
                </div>
              </div>
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="msg-chat">
      <template v-if="activeId">
        <div class="chat-header">
          <div class="chat-header-left">
            <el-button text circle @click="goBack" class="back-btn">
              <el-icon :size="18"><ArrowLeft /></el-icon>
            </el-button>
            <div class="chat-header-info">
              <div class="chat-name">{{ activeName }}</div>
              <div v-if="activeType === 'group'" class="chat-member-count">
                {{ currentGroup?.member_count || 0 }}人
              </div>
            </div>
          </div>
          <div class="chat-header-right">
            <el-dropdown v-if="activeType === 'group'" trigger="click">
              <el-button text circle><el-icon :size="18"><MoreFilled /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="showManageGroup = true">
                    <el-icon><Setting /></el-icon> 群管理
                  </el-dropdown-item>
                  <el-dropdown-item @click="showAddMember = true">
                    <el-icon><Plus /></el-icon> 添加成员
                  </el-dropdown-item>
                  <el-dropdown-item @click="openMemberList">
                    <el-icon><User /></el-icon> 查看成员
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="msg-list" ref="msgListRef"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
          @paste="onPaste">
          <!-- 拖拽遮罩 -->
          <Transition name="fade">
            <div v-if="dragOver" class="drag-overlay">
              <el-icon :size="56"><UploadFilled /></el-icon>
              <span>释放以上传文件</span>
              <small>支持图片、文档、压缩包，最大 50MB</small>
            </div>
          </Transition>
          <!-- 上传进度条 -->
          <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress-bar">
            <div class="upload-progress-inner" :style="{ width: uploadProgress + '%' }"></div>
            <span>上传中 {{ uploadProgress }}%</span>
          </div>
          <template v-for="item in messageTimeline" :key="item.type === 'date' ? 'd-' + item.date : item.msg.id">
            <div v-if="item.type === 'date'" class="date-separator"><span>{{ item.label }}</span></div>
            <div v-else :class="['msg-bubble', item.msg.sender_id === userId ? 'mine' : 'theirs']">
              <div v-if="activeType === 'group' && item.msg.sender_id !== userId" class="sender-info">
                <el-avatar :size="28">{{ (item.msg.sender_name || '?')[0] }}</el-avatar>
                <span class="sender-name">{{ item.msg.sender_name }}</span>
              </div>
              <!-- 文件/图片消息 -->
              <template v-if="getMsgMeta(item.msg).isFile">
                <template v-if="getMsgMeta(item.msg).fileType === 'image'">
                  <div class="bubble-image" @click="previewImage(getMsgMeta(item.msg).url)">
                    <img :src="getMsgMeta(item.msg).url" :alt="getMsgMeta(item.msg).text" />
                  </div>
                </template>
                <div v-else class="bubble-file" @click="downloadFile(getMsgMeta(item.msg).url, getMsgMeta(item.msg).text)">
                  <el-icon :size="28"><Document /></el-icon>
                  <div class="bubble-file-info">
                    <span class="bubble-file-name">{{ getMsgMeta(item.msg).text }}</span>
                    <small>点击下载</small>
                  </div>
                </div>
              </template>
              <!-- 文本消息 -->
              <div v-else class="bubble-text">{{ item.msg.content }}</div>
              <div class="bubble-time">{{ formatTime(item.msg.created_at) }}</div>
            </div>
          </template>
          <div v-if="messages.length === 0" class="chat-empty">
            <el-icon :size="48" color="#ddd"><ChatLineRound /></el-icon>
            <span>暂无聊天记录</span>
          </div>
        </div>

        <div class="msg-input-bar">
          <div class="input-toolbar">
            <label class="file-upload-btn" title="发送文件">
              <el-icon :size="20"><FolderOpened /></el-icon>
              <input type="file" multiple hidden ref="fileInputRef" @change="onFileSelect" accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf,.doc,.docx,.zip,.rar" />
            </label>
          </div>
          <div class="input-main">
            <el-input v-model="newMsg" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行，可直接粘贴图片或拖拽文件)"
              @keydown.enter.exact.prevent="sendMsg" />
          </div>
          <div class="input-footer">
            <el-button type="primary" @click="sendMsg" :disabled="!newMsg.trim()">发送(S)</el-button>
          </div>
        </div>
      </template>

      <div v-else class="no-selection">
        <el-icon :size="80" color="#e0e0e0"><ChatLineRound /></el-icon>
        <h2>智慧校园消息中心</h2>
        <p>选择一个会话开始聊天</p>
        <div class="quick-actions">
          <el-button type="primary" @click="showAddFriend = true">
            <el-icon><User /></el-icon> 添加好友
          </el-button>
          <el-button type="primary" @click="showCreateGroup = true">
            <el-icon><ChatRound /></el-icon> 创建群聊
          </el-button>
        </div>
      </div>
    </div>

    <!-- ============= 添加好友弹窗 ============= -->
    <el-dialog v-model="showAddFriend" title="添加好友" width="520px" :close-on-click-modal="false" @opened="focusAddFriendInput">
      <div class="add-friend-dialog">
        <div class="add-friend-search-box">
          <el-input ref="addFriendInputRef" v-model="addFriendSearch" placeholder="输入学号、工号或姓名搜索"
            size="large" clearable @input="onAddFriendSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <div class="add-friend-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>可搜索全校师生进行添加，支持学号/工号/姓名检索</span>
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
              <el-avatar :size="44" :src="u.avatar || undefined">{{ u.name[0] }}</el-avatar>
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
    <el-dialog v-model="showCreateGroup" title="创建群聊" width="520px" :close-on-click-modal="false">
      <div class="create-group-form">
        <el-input v-model="newGroupName" placeholder="必填，请输入群名称" maxlength="20" show-word-limit size="large" />
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
    <el-dialog v-model="showAddMember" title="添加成员" width="480px" :close-on-click-modal="false">
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

    <!-- ============= 群成员列表弹窗 ============= -->
    <el-dialog v-model="showGroupMembers" title="群成员" width="400px">
      <div class="group-members-list">
        <div v-for="m in groupMembers" :key="m.user_id" class="group-member-item">
          <el-avatar :size="36">{{ m.user_name[0] }}</el-avatar>
          <div class="member-info">
            <span class="member-name">{{ m.user_name }}</span>
            <el-tag v-if="m.role === 'owner'" type="danger" size="small">群主</el-tag>
            <el-tag v-else-if="m.role === 'admin'" type="warning" size="small">管理员</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ============= 群管理弹窗 ============= -->
    <el-dialog v-model="showManageGroup" title="群管理" width="560px" :close-on-click-modal="false" @opened="onManageDialogOpened">
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

    <!-- ============= 图片预览 ============= -->
    <Transition name="fade">
      <div v-if="previewUrl" class="image-preview-overlay" @click="previewUrl = ''">
        <img :src="previewUrl" @click.stop />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getConversations, getMessages, sendMessage, markRead } from '@/api/messages'
import {
  getGroups, getGroup, getGroupMembers, createGroup as apiCreateGroup,
  addGroupMembers, sendGroupMessage, getGroupMessages, searchUsers,
  updateGroupAnnouncement, leaveGroup, disbandGroup, removeGroupMember,
  type GroupOut, type GroupMemberOut, type UserSearchResult
} from '@/api/groups'
import { uploadFile } from '@/api/upload'
import { getToken } from '@/utils/token'
import { ElMessage } from 'element-plus'
import {
  Search, User, ChatDotRound, ChatLineRound, ArrowLeft, Plus,
  Bell, MoreFilled, Loading, Check, InfoFilled, ChatRound,
  UploadFilled, Document, FolderOpened, Setting, WarningFilled, Delete, SwitchButton
} from '@element-plus/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const userId = auth.user?.id ?? 0

const conversations = ref<any[]>([])
const groups = ref<GroupOut[]>([])

const activeId = ref<number | null>(null)
const activeName = ref('')
const activeType = ref<'single' | 'group'>('single')
const messages = ref<any[]>([])
const newMsg = ref('')
const msgListRef = ref<HTMLDivElement>()

// 侧边栏 — 筛选已有会话
const search = ref('')
const filteredList = computed(() => {
  const kw = search.value.trim().toLowerCase()
  const fmt = (m: string) => {
    if (m.startsWith('{') && m.includes('"type"')) {
      try { const p = JSON.parse(m); return p.type === 'image' ? '[图片] ' + (p.text||'') : '[文件] ' + (p.text||'') } catch {}
    }
    return m
  }
  if (!kw) {
    const groupItems = groups.value.map(g => ({ ...g, _key: 'g-' + g.id, _type: 'group', last_message: fmt(g.last_message) }))
    const convItems = conversations.value.map(c => ({
      id: c.user_id, name: c.user_name, user_avatar: c.user_avatar,
      last_message: fmt(c.last_message), last_message_time: c.last_message_time,
      unread_count: c.unread_count, _key: 's-' + c.user_id, _type: 'single'
    }))
    return [...groupItems, ...convItems]
  }
  const result: any[] = []
  for (const g of groups.value) {
    if (g.name.toLowerCase().includes(kw)) {
      result.push({ ...g, _key: 'g-' + g.id, _type: 'group', last_message: fmt(g.last_message) })
    }
  }
  for (const c of conversations.value) {
    if (c.user_name.toLowerCase().includes(kw) || String(c.user_id).includes(kw)) {
      result.push({
        id: c.user_id, name: c.user_name, user_avatar: c.user_avatar,
        last_message: fmt(c.last_message), last_message_time: c.last_message_time,
        unread_count: c.unread_count, _key: 's-' + c.user_id, _type: 'single'
      })
    }
  }
  return result
})

function filterConversations() {}

// 添加好友
const showAddFriend = ref(false)
const addFriendSearch = ref('')
const addFriendResults = ref<UserSearchResult[]>([])
const addFriendLoading = ref(false)
const addFriendInputRef = ref()
let addFriendTimer: ReturnType<typeof setTimeout> | null = null

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
  await openChat(user.id, user.name, 'single')
  ElMessage.success(`已添加 ${user.name}，可以开始聊天了`)
}

// 创建群聊弹窗
const showCreateGroup = ref(false)
const newGroupName = ref('')
const memberSearch = ref('')
const memberSearchResults = ref<UserSearchResult[]>([])
const selectedMembers = ref<UserSearchResult[]>([])

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
    openChat(result.id, result.name, 'group')
  } catch { ElMessage.error('创建失败') }
}

// 群管理
const showAddMember = ref(false)
const addMemberSearch = ref('')
const addMemberResults = ref<UserSearchResult[]>([])
const showGroupMembers = ref(false)
const groupMembers = ref<GroupMemberOut[]>([])
const currentGroup = ref<GroupOut | null>(null)

const showManageGroup = ref(false)
const editingAnnouncement = ref(false)
const announcementText = ref('')
const savingAnnouncement = ref(false)
const showManageInvite = ref(false)
const manageInviteSearch = ref('')
const manageInviteResults = ref<UserSearchResult[]>([])
let manageInviteTimer: ReturnType<typeof setTimeout> | null = null

const isCurrentUserOwner = computed(() => {
  const me = groupMembers.value.find(m => m.user_id === userId)
  return me?.role === 'owner'
})
const isCurrentUserAdmin = computed(() => {
  const me = groupMembers.value.find(m => m.user_id === userId)
  return me?.role === 'owner' || me?.role === 'admin'
})

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
  if (!announcementText.value.trim()) {
    ElMessage.warning('请输入群公告内容')
    return
  }
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

// 文件上传
const dragOver = ref(false)
const uploadProgress = ref(0)
const fileInputRef = ref<HTMLInputElement>()
const previewUrl = ref('')

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
async function openMemberList() {
  showGroupMembers.value = true
  try { groupMembers.value = await getGroupMembers(activeId.value!) } catch {}
}

// 总未读
const totalUnread = computed(() => {
  const convUnread = conversations.value.reduce((s: number, c: any) => s + (c.unread_count || 0), 0)
  const groupUnread = groups.value.reduce((s: number, g) => s + (g.unread_count || 0), 0)
  return convUnread + groupUnread
})

// 时间线
const messageTimeline = computed(() => {
  const items: Array<{ type: 'date'; date: string; label: string } | { type: 'msg'; msg: any }> = []
  let lastDate = ''
  for (const m of messages.value) {
    const d = getDateStr(m.created_at)
    if (d !== lastDate) { items.push({ type: 'date', date: d, label: getDateLabel(m.created_at) }); lastDate = d }
    items.push({ type: 'msg', msg: m })
  }
  return items
})

function getDateStr(t: string) { const d = new Date(t); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` }
function getDateLabel(t: string) {
  const date = new Date(t); const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.floor((today.getTime() - target.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff === 2) return '前天'
  if (diff < 7) return `${diff}天前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatTime(t: string | null) {
  if (!t) return ''
  try {
    const date = new Date(t + (t.includes('Z') || t.includes('+') ? '' : 'Z'))
    const now = new Date(); const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000); const hours = Math.floor(diff / 3600000)
    const ts = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    return ts
  } catch { return t }
}

// WebSocket
let ws: WebSocket | null = null
function connectWs() {
  const token = getToken()
  if (!token) return
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/api/messages/ws?token=${token}`)
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'new_message') {
        loadConversations()
        if (data.sender_id === activeId.value && activeType.value === 'single') {
          messages.value.push({ id: data.id || Date.now(), sender_id: data.sender_id, content: data.content, created_at: data.created_at, read: true })
          scrollToBottom()
        }
      } else if (data.type === 'new_group_message') {
        loadGroups()
        if (data.group_id === activeId.value && activeType.value === 'group') {
          messages.value.push({ id: data.id || Date.now(), group_id: data.group_id, sender_id: data.sender_id, sender_name: data.sender_name, content: data.content, created_at: data.created_at })
          scrollToBottom()
        }
      }
    } catch {}
  }
  ws.onclose = () => { ws = null }
}
function disconnectWs() { if (ws) { ws.close(); ws = null } }

async function loadConversations() { try { conversations.value = await getConversations() } catch {} }
async function loadGroups() { try { groups.value = await getGroups() } catch {} }

// 打开聊天
async function openChat(id: number, name: string, type: 'single' | 'group') {
  activeId.value = id; activeName.value = name; activeType.value = type
  try {
    if (type === 'single') {
      messages.value = await getMessages(id)
      await markRead(id)
      loadConversations()
    } else {
      messages.value = await getGroupMessages(id)
      currentGroup.value = await getGroup(id)
      loadGroups()
    }
    scrollToBottom()
  } catch {}
}
function goBack() { activeId.value = null; activeName.value = ''; messages.value = []; currentGroup.value = null }
function scrollToBottom() { nextTick(() => msgListRef.value?.scrollTo({ top: msgListRef.value.scrollHeight, behavior: 'smooth' })) }

// 发送
async function sendMsg() {
  if (!activeId.value) return
  if (newMsg.value.trim()) {
    await sendTextMsg(newMsg.value.trim())
  }
}

async function sendTextMsg(text: string) {
  if (!activeId.value) return
  try {
    if (activeType.value === 'single') {
      await sendMessage(activeId.value, text)
      messages.value.push({ id: Date.now(), sender_id: userId, receiver_id: activeId.value, content: text, read: true, created_at: new Date().toISOString() })
      await loadConversations()
    } else {
      await sendGroupMessage(activeId.value, text)
      messages.value.push({ id: Date.now(), group_id: activeId.value, sender_id: userId, sender_name: auth.user?.name || '我', content: text, created_at: new Date().toISOString() })
      await loadGroups()
    }
    newMsg.value = ''
    scrollToBottom()
  } catch { ElMessage.error('发送失败') }
}

// 文件/图片消息
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

function makeFileContent(fileType: string, filename: string, url: string) {
  return JSON.stringify({ type: fileType, text: filename, url })
}

function downloadFile(url: string, name: string) {
  const a = document.createElement('a')
  a.href = url; a.download = name; a.click()
}
function previewImage(url: string) { previewUrl.value = url }

async function uploadAndSend(file: File) {
  uploadProgress.value = 10
  try {
    const result = await uploadFile(file)
    uploadProgress.value = 100
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)
    const content = makeFileContent(isImage ? 'image' : 'file', file.name, result.url)
    await sendTextMsg(content)
  } catch {
    ElMessage.error(`上传 ${file.name} 失败`)
  } finally {
    uploadProgress.value = 0
  }
}

async function uploadFiles(files: FileList | File[]) {
  for (const f of files) {
    if (f.size > 50 * 1024 * 1024) {
      ElMessage.warning(`${f.name} 超过 50MB 限制`)
      continue
    }
    await uploadAndSend(f)
  }
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) uploadFiles(input.files)
  input.value = ''
}

function onDragOver() { dragOver.value = true }
function onDragLeave(e: DragEvent) {
  if (!(e.currentTarget as HTMLElement)?.contains(e.relatedTarget as HTMLElement)) {
    dragOver.value = false
  }
}
async function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files.length) await uploadFiles(e.dataTransfer.files)
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

// +号菜单
function handleHeaderAction(cmd: string) {
  if (cmd === 'createGroup') { showCreateGroup.value = true }
  else if (cmd === 'addFriend') { showAddFriend.value = true }
}

onMounted(async () => {
  connectWs()
  await Promise.all([loadConversations(), loadGroups()])
  if (route.query.groupId) {
    openChat(Number(route.query.groupId), (route.query.groupName as string) || '', 'group')
    router.replace({ query: {} })
  } else if (route.query.studentId) {
    openChat(Number(route.query.studentId), (route.query.studentName as string) || '', 'single')
    router.replace({ query: {} })
  }
})
onUnmounted(() => disconnectWs())
</script>

<style scoped>
.msg-page {
  display: flex; height: 100%;
  background: #fff;   border-radius: 10px; overflow: hidden;
  border: 1px solid rgba(0,0,0,0.04); box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}

/* ===== 侧边栏 ===== */
.msg-sidebar { width: 280px; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid #f0f0f0; background: #f7f8fa; }
.sidebar-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid #eee; }
.header-left,.header-right { width: 36px; display: flex; align-items: center; }
.header-right { justify-content: flex-end; }
.header-center { flex: 1; text-align: center; }
.header-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.action-btn { font-size: 18px; color: #409eff; }
.header-icon { color: #666; cursor: pointer; }
.header-icon:hover { color: #409eff; }
.sidebar-search { padding: 8px 12px; }
.sidebar-scroll { flex: 1; overflow-y: auto; min-height: 0; }

.conv-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; transition: all .15s; border-left: 3px solid transparent; }
.conv-item:hover { background: rgba(64,158,255,0.06); }
.conv-item.active { background: rgba(64,158,255,0.12); border-left-color: #409eff; }
.conv-avatar-wrapper { position: relative; flex-shrink: 0; line-height: 0; }
.group-badge { position: absolute; bottom: -2px; right: -2px; width: 16px; height: 16px; border-radius: 4px; background: #409eff; color: #fff; font-size: 9px; display: flex; align-items: center; justify-content: center; border: 2px solid #f7f8fa; }
.conv-badge-avatar { line-height: 0; }
.conv-avatar { flex-shrink: 0; }
.conv-info { flex: 1; min-width: 0; }
.conv-top { display: flex; justify-content: space-between; align-items: center; }
.conv-name { font-size: 13px; font-weight: 500; color: #333; }
.conv-time { font-size: 10px; color: #bbb; flex-shrink: 0; margin-left: 8px; }
.conv-bottom { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
.conv-preview { font-size: 11px; color: #999; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-badge { --el-badge-bg-color: #f56c6c; flex-shrink: 0; }
.conv-member-count { font-size: 10px; color: #bbb; flex-shrink: 0; }

.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px 0; color: #bbb; font-size: 13px; }

/* ===== 聊天区域 ===== */
.msg-chat { flex: 1; display: flex; flex-direction: column; }
.chat-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; border-bottom: 1px solid #f0f0f0; background: #fafafa; }
.chat-header-left { display: flex; align-items: center; gap: 10px; }
.chat-name { font-size: 16px; font-weight: 600; color: #1a1a2e; }
.chat-member-count { font-size: 12px; color: #999; margin-top: 2px; }
.msg-list { flex: 1; overflow-y: auto; padding: 20px; background: #f8faff; }
.date-separator { text-align: center; margin: 16px 0; }
.date-separator span { display: inline-block; padding: 3px 14px; border-radius: 10px; font-size: 11px; color: #999; background: rgba(0,0,0,.04); }
.msg-bubble { margin-bottom: 12px; max-width: min(65%, 380px); width: fit-content; }
.msg-bubble.mine { margin-left: auto; }
.msg-bubble.theirs { margin-right: auto; }
.sender-info { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.sender-name { font-size: 12px; color: #666; }
.bubble-text { padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.5; word-break: break-word; }
.mine .bubble-text { background: linear-gradient(135deg, #409eff, #337ecc); color: #fff; border-bottom-right-radius: 4px; }
.theirs .bubble-text { background: #fff; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.bubble-time { font-size: 11px; color: #aaa; margin-top: 4px; padding: 0 4px; display: flex; align-items: center; gap: 4px; }
.mine .bubble-time { justify-content: flex-end; }
.chat-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 60px 0; color: #bbb; font-size: 13px; }

.msg-input-bar { border-top: 1px solid #f0f0f0; background: #fff; display: flex; flex-direction: column; }
.input-toolbar { display: flex; gap: 8px; padding: 8px 16px 0; }
.file-upload-btn { cursor: pointer; color: #909399; display: flex; align-items: center; transition: color .15s; }
.file-upload-btn:hover { color: #409eff; }
.input-main { padding: 4px 16px; }
.input-main .el-textarea__inner { min-height: auto !important; padding: 8px 12px; line-height: 1.4; resize: none; border-radius: 10px; border: 1px solid #e0e0e0; }
.input-main .el-textarea__inner:focus { border-color: #409eff; }
.input-footer { display: flex; justify-content: flex-end; padding: 0 16px 10px; }

.no-selection { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: #999; }
.no-selection h2 { font-size: 20px; color: #666; margin: 0; }
.no-selection p { font-size: 14px; color: #999; margin: 0; }
.quick-actions { display: flex; gap: 12px; margin-top: 16px; }

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

/* ===== 群成员列表 ===== */
.group-members-list { max-height: 400px; overflow-y: auto; }
.group-member-item { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.group-member-item:last-child { border-bottom: none; }
.member-info { flex: 1; display: flex; align-items: center; gap: 8px; }
.member-info .member-name { font-size: 14px; color: #333; }

/* ===== 拖拽上传 ===== */
.msg-list { position: relative; }
.drag-overlay {
  position: absolute; inset: 0; z-index: 10;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  background: rgba(64,158,255,0.92); color: #fff; border-radius: 8px;
}
.drag-overlay span { font-size: 18px; font-weight: 600; }
.drag-overlay small { font-size: 13px; opacity: .85; }

.upload-progress-bar {
  position: absolute; bottom: 0; left: 0; right: 0; height: 4px;
  background: rgba(0,0,0,0.06); z-index: 10;
}
.upload-progress-inner {
  height: 100%; background: #409eff; transition: width .3s;
  border-radius: 0 2px 2px 0;
}
.upload-progress-bar span {
  position: absolute; top: -22px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: #409eff; white-space: nowrap;
}

/* ===== 文件/图片消息 ===== */
.bubble-image {
  max-width: 260px; cursor: pointer; border-radius: 12px;
  overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.1);
}
.bubble-image img {
  width: 100%; height: auto; display: block;
  transition: transform .2s;
}
.bubble-image:hover img { transform: scale(1.03); }

.bubble-file {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: 12px; cursor: pointer;
  min-width: 200px;
}
.mine .bubble-file { background: linear-gradient(135deg, #409eff, #337ecc); color: #fff; border-bottom-right-radius: 4px; }
.theirs .bubble-file { background: #fff; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.bubble-file-info { flex: 1; min-width: 0; }
.bubble-file-name {
  font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  display: block;
}
.bubble-file-info small { font-size: 11px; opacity: .7; }

/* ===== 图片预览 ===== */
.image-preview-overlay {
  position: fixed; inset: 0; z-index: 3000;
  background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center;
  cursor: zoom-out;
}
.image-preview-overlay img {
  max-width: 90vw; max-height: 90vh; border-radius: 8px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.4);
}

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

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