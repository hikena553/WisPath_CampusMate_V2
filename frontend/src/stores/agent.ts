import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { ChatMessage } from '@/types'
import { getUserId } from '@/utils/token'

const STORAGE_KEYS: Record<string, string> = {
  student: 'campus_chat_messages',
  teacher: 'campus_teacher_chat_messages',
}

/**
 * 按登录用户分区存储：`{baseKey}_{userId}`。
 * 换账号登录后各用户消息互不串扰；未登录（异常态）退回基础 key。
 */
function partitionKey(baseKey: string): string {
  const uid = getUserId()
  return uid ? `${baseKey}_${uid}` : baseKey
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
  const baseKey = STORAGE_KEYS[role]
  const storeId = role === 'teacher' ? 'teacherAgent' : 'agent'

  return defineStore(storeId, () => {
    const messages = ref<ChatMessage[]>([])
    const loading = ref(false)

    /** 加载当前用户分区的历史消息（含旧版本全局 key 的一次性迁移） */
    function loadCurrentPartition() {
      const current = partitionKey(baseKey)
      if (getUserId()) {
        const legacyRaw = localStorage.getItem(baseKey)
        const hasPartition = localStorage.getItem(current) !== null
        if (!hasPartition && legacyRaw !== null) {
          // 老版本按角色全局存储 → 迁移到当前用户分区，避免升级丢历史
          localStorage.setItem(current, legacyRaw)
          localStorage.removeItem(baseKey)
        }
      }
      messages.value = loadMessages(current)
    }

    loadCurrentPartition()

    let saveTimer: ReturnType<typeof setTimeout> | null = null
    watch(messages, (val) => {
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => {
        localStorage.setItem(partitionKey(baseKey), JSON.stringify(val.slice(-100)))
      }, 300)
    }, { deep: true })

    /** 换账号 / 登录成功后调用：切到当前用户分区 */
    function resetForUser() {
      loadCurrentPartition()
    }

    function addMessage(msg: ChatMessage) {
      messages.value.push(msg)
    }

    function updateMessage(id: string, patch: Partial<ChatMessage>) {
      const msg = messages.value.find(m => m.id === id)
      if (msg) {
        Object.assign(msg, patch)
      }
    }

    function replaceMessages(msgs: ChatMessage[]) {
      messages.value = msgs
      localStorage.setItem(partitionKey(baseKey), JSON.stringify(msgs.slice(-100)))
    }

    function clearMessages() {
      messages.value = []
      localStorage.removeItem(partitionKey(baseKey))
    }

    return { messages, loading, addMessage, updateMessage, replaceMessages, clearMessages, resetForUser }
  })
}

/** 学生端AI对话消息管理 */
export const useAgentStore = createAgentStore('student')
/** 教师端AI对话消息管理 */
export const useTeacherAgentStore = createAgentStore('teacher')
