import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { ChatMessage } from '@/types'

const STORAGE_KEYS: Record<string, string> = {
  student: 'campus_chat_messages',
  teacher: 'campus_teacher_chat_messages',
}

function loadMessages(storageKey: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function createAgentStore(role: 'student' | 'teacher') {
  const storageKey = STORAGE_KEYS[role]
  const storeId = role === 'teacher' ? 'teacherAgent' : 'agent'

  return defineStore(storeId, () => {
    const messages = ref<ChatMessage[]>(loadMessages(storageKey))
    const loading = ref(false)

    watch(messages, (val) => {
      localStorage.setItem(storageKey, JSON.stringify(val.slice(-100)))
    }, { deep: true })

    function addMessage(msg: ChatMessage) {
      messages.value.push(msg)
    }

    function replaceMessages(msgs: ChatMessage[]) {
      messages.value = msgs
      localStorage.setItem(storageKey, JSON.stringify(msgs.slice(-100)))
    }

    function clearMessages() {
      messages.value = []
      localStorage.removeItem(storageKey)
    }

    return { messages, loading, addMessage, replaceMessages, clearMessages }
  })
}

/** 学生端AI对话消息管理 */
export const useAgentStore = createAgentStore('student')
/** 教师端AI对话消息管理 */
export const useTeacherAgentStore = createAgentStore('teacher')
