import { ref } from 'vue'

import { getUserHomepage, type UserHomepage } from '@/api/badge'

/**
 * 个人主页浮层的全局单例状态。
 *
 * 挂载点放在布局层（StudentLayout / TeacherLayout），任何页面只要调用
 * ``openUserHomepage(userId)`` 就能拉起同一个主页浮层 —— 这样消息页、通讯录、
 * 社区等入口的接入成本都只有一行，不必各自维护一份主页组件与数据请求。
 */
const visible = ref(false)
const loading = ref(false)
const data = ref<UserHomepage | null>(null)
const error = ref('')
const currentUserId = ref<number | null>(null)

export async function openUserHomepage(userId: number) {
  if (!userId) return
  currentUserId.value = userId
  visible.value = true
  loading.value = true
  error.value = ''
  data.value = null
  try {
    data.value = await getUserHomepage(userId)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '主页加载失败'
  } finally {
    loading.value = false
  }
}

export function closeUserHomepage() {
  visible.value = false
  data.value = null
  error.value = ''
  currentUserId.value = null
}

export function useUserHomepage() {
  return { visible, loading, data, error, currentUserId, open: openUserHomepage, close: closeUserHomepage }
}