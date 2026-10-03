import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import request from '@/utils/request'

export interface Conversation {
  id: number
  title: string
  type: 'normal' | 'project'
  project_template?: string | null
  project_stage?: string | null
  /** @deprecated 后端历史字段，业务不再使用（见 pinned / archived） */
  is_active: boolean
  pinned: boolean
  archived: boolean
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
  offset: number
  limit: number
  has_more: boolean
  archived: boolean
}

/** 批量操作类型，与后端 /agent/conversations/batch 的 action 对应 */
export type BatchAction = 'delete' | 'restore' | 'pin' | 'unpin' | 'archive' | 'unarchive'

/** 标题长度上限，与后端 TITLE_MAX_LEN 保持一致 */
export const TITLE_MAX_LEN = 200

/** 普通翻页步长；搜索时一次多取一些，避免结果被分页切断 */
const PAGE_SIZE = 30
const SEARCH_LIMIT = 100

const SIDEBAR_KEYS: Record<string, string> = {
  student: 'sidebar_collapsed',
  teacher: 'teacher_sidebar_collapsed',
}

function createConversationStore(role: 'student' | 'teacher') {
  const storeId = role === 'teacher' ? 'teacherConversation' : 'conversation'
  const sidebarKey = SIDEBAR_KEYS[role]

  return defineStore(storeId, () => {
    const list = ref<Conversation[]>([])
    const total = ref(0)
    const hasMore = ref(false)
    const loading = ref(false)
    /** 服务端搜索词：非空时由后端过滤（覆盖全部会话，而非仅已加载部分） */
    const query = ref('')
    const showArchived = ref(false)
    const activeId = ref<number | null>(null)
    const messages = ref<ConversationMessage[]>([])
    const sidebarCollapsed = ref(localStorage.getItem(sidebarKey) === 'true')

    watch(sidebarCollapsed, (v) => {
      localStorage.setItem(sidebarKey, v ? 'true' : 'false')
    })

    function listParams(offset: number) {
      const params: Record<string, unknown> = {
        offset,
        limit: query.value.trim() ? SEARCH_LIMIT : PAGE_SIZE,
      }
      if (query.value.trim()) params.q = query.value.trim()
      if (showArchived.value) params.archived = true
      return params
    }

    /** reset=true 重拉第一页；reset=false 追加下一页 */
    async function fetchList(opts: { reset?: boolean } = {}) {
      const reset = opts.reset !== false
      if (reset) loading.value = true
      try {
        const raw = await request.get<ConversationListResponse | Conversation[]>('/agent/conversations', {
          params: listParams(reset ? 0 : list.value.length),
        })
        // 兼容旧版后端（直接返回数组）：便于前端与后端分批上线/重启
        const res: ConversationListResponse = Array.isArray(raw)
          ? { items: raw, total: raw.length, offset: 0, limit: raw.length, has_more: false, archived: showArchived.value }
          : raw
        const items = res?.items ?? []
        if (reset) {
          list.value = items
        } else {
          const seen = new Set(list.value.map(c => c.id))
          list.value = [...list.value, ...items.filter(c => !seen.has(c.id))]
        }
        total.value = res?.total ?? list.value.length
        hasMore.value = !!res?.has_more
      } catch (e) {
        console.error('获取对话列表失败', e)
        if (reset) {
          list.value = []
          total.value = 0
          hasMore.value = false
        }
      } finally {
        loading.value = false
      }
    }

    async function loadMore() {
      if (!hasMore.value || loading.value) return
      await fetchList({ reset: false })
    }

    /** 切换搜索词：由后端在全部会话中检索 */
    async function setQuery(q: string) {
      if (query.value === q) return
      query.value = q
      await fetchList({ reset: true })
    }

    /** 切换「已归档」视图 */
    async function setShowArchived(v: boolean) {
      if (showArchived.value === v) return
      showArchived.value = v
      await fetchList({ reset: true })
    }

    /** 本地合并：用于 SSE 回传的新标题、置顶/归档开关等无需整表重拉的场景 */
    function patchConversation(id: number, patch: Partial<Conversation>) {
      const idx = list.value.findIndex(c => c.id === id)
      if (idx < 0) return
      Object.assign(list.value[idx], patch)
      // 带着新的 updated_at 回来（例如刚完成一轮对话）时同步重排：
      // 置顶优先，其余按最近更新倒序，避免侧边栏顺序与后端不一致
      if (patch.updated_at) {
        list.value = [...list.value].sort((a, b) => {
          if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        })
      }
    }

    async function createConversation(type: 'normal' | 'project' = 'normal', template?: string, title?: string): Promise<Conversation | null> {
      try {
        const conv: Conversation = await request.post('/agent/conversations', { type, project_template: template, title })
        list.value.unshift(conv)
        total.value += 1
        return conv
      } catch (e) {
        console.error('创建对话失败', e)
        return null
      }
    }

    /** 更新并回填；失败会抛出，调用方负责提示 */
    async function updateConversation(id: number, data: Partial<Conversation>): Promise<Conversation> {
      const updated = await request.put<Conversation>(`/agent/conversations/${id}`, data)
      patchConversation(id, updated)
      return updated
    }

    async function togglePinned(c: Conversation): Promise<Conversation> {
      return updateConversation(c.id, { pinned: !c.pinned })
    }

    /** 归档状态会改变列表归属，交给调用方决定是否刷新列表 */
    async function toggleArchived(c: Conversation): Promise<Conversation> {
      return updateConversation(c.id, { archived: !c.archived })
    }

    /** 软删除：成功即从本地列表移除，可调用 restoreConversation 撤销 */
    async function deleteConversation(id: number) {
      await request.delete(`/agent/conversations/${id}`)
      const idx = list.value.findIndex(c => c.id === id)
      if (idx >= 0) list.value.splice(idx, 1)
      total.value = Math.max(0, total.value - 1)
      if (activeId.value === id) activeId.value = null
    }

    /** 撤销删除：恢复后重拉当前视图，保证排序与归属正确 */
    async function restoreConversation(id: number): Promise<Conversation | null> {
      const res = await request.post<{ conversation?: Conversation }>(`/agent/conversations/${id}/restore`)
      await fetchList({ reset: true })
      return res?.conversation ?? null
    }

    /** 批量操作：单请求单事务，返回后端实际更新的条数 */
    async function batchAction(ids: number[], action: BatchAction): Promise<number> {
      const res = await request.post<{ updated: number }>('/agent/conversations/batch', { ids, action })
      return res?.updated ?? 0
    }

    async function fetchMessages(convId: number) {
      try {
        const msgs: ConversationMessage[] = await request.get(`/agent/conversations/${convId}/messages`)
        messages.value = msgs
      } catch (e) {
        console.error('获取消息失败', e)
        messages.value = []
      }
    }

    function setActive(convId: number | null) {
      activeId.value = convId
    }

    return {
      list, total, hasMore, loading, query, showArchived,
      activeId, messages, sidebarCollapsed,
      fetchList, loadMore, setQuery, setShowArchived, patchConversation,
      createConversation, updateConversation, togglePinned, toggleArchived,
      deleteConversation, restoreConversation, batchAction,
      fetchMessages, setActive,
    }
  })
}

/** 学生端对话列表管理 */
export const useConversationStore = createConversationStore('student')
/** 教师端对话列表管理 */
export const useTeacherConversationStore = createConversationStore('teacher')