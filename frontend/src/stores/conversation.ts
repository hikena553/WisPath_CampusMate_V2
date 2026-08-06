import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import request from '@/utils/request'

export interface Conversation {
  id: number
  title: string
  type: 'normal' | 'project'
  project_template?: string
  project_stage?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const SIDEBAR_KEYS: Record<string, string> = {
  student: 'sidebar_collapsed',
  teacher: 'teacher_sidebar_collapsed',
}

function createConversationStore(role: 'student' | 'teacher') {
  const storeId = role === 'teacher' ? 'teacherConversation' : 'conversation'
  const sidebarKey = SIDEBAR_KEYS[role]

  return defineStore(storeId, () => {
    const list = ref<Conversation[]>([])
    const activeId = ref<number | null>(null)
    const messages = ref<ConversationMessage[]>([])
    const sidebarCollapsed = ref(localStorage.getItem(sidebarKey) !== 'false')

    watch(sidebarCollapsed, (v) => {
      localStorage.setItem(sidebarKey, v ? 'true' : 'false')
    })

    async function fetchList() {
      try { list.value = await request.get('/agent/conversations') } catch (e) { console.error('获取对话列表失败', e) }
    }

    async function createConversation(type: 'normal' | 'project' = 'normal', template?: string, title?: string): Promise<Conversation | null> {
      try {
        const conv: Conversation = await request.post('/agent/conversations', { type, project_template: template, title })
        list.value.unshift(conv)
        return conv
      } catch (e) { console.error('创建对话失败', e); return null }
    }

    async function updateConversation(id: number, data: Partial<Conversation>) {
      try {
        await request.put(`/agent/conversations/${id}`, data)
        const idx = list.value.findIndex(c => c.id === id)
        if (idx >= 0) Object.assign(list.value[idx], data)
      } catch (e) { console.error('更新对话失败', e) }
    }

    async function deleteConversation(id: number) {
      try {
        await request.delete(`/agent/conversations/${id}`)
        list.value = list.value.filter(c => c.id !== id)
        if (activeId.value === id) activeId.value = null
      } catch (e) { console.error('删除对话失败', e) }
    }

    async function fetchMessages(convId: number) {
      try {
        const msgs: ConversationMessage[] = await request.get(`/agent/conversations/${convId}/messages`)
        messages.value = msgs
      } catch (e) { console.error('获取消息失败', e); messages.value = [] }
    }

    function setActive(convId: number | null) {
      activeId.value = convId
    }

    return {
      list, activeId, messages, sidebarCollapsed,
      fetchList, createConversation, updateConversation, deleteConversation,
      fetchMessages, setActive,
    }
  })
}

/** 学生端对话列表管理 */
export const useConversationStore = createConversationStore('student')
/** 教师端对话列表管理 */
export const useTeacherConversationStore = createConversationStore('teacher')
