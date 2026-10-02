import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { setToken, setUser, getToken, getUser, removeToken } from '@/utils/token'
import { logoutApi } from '@/api/auth'
import { useAgentStore, useTeacherAgentStore } from './agent'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<UserInfo | null>(getUser() as UserInfo | null)

  // F3 双通道：内存 token 刷新后为空，但 user 缓存与 httpOnly Cookie 仍在，
  // 故以「user 缓存或内存 token 任一存在」判定登录态，避免刷新后被误判为未登录
  const isLoggedIn = computed(() => !!(token.value || user.value))
  const role = computed(() => user.value?.role)
  const userName = computed(() => user.value?.name)

  /** 切换账号后重置各业务 store，避免上一个用户的会话残留 */
  function resetUserState() {
    useAgentStore().resetForUser()
    useTeacherAgentStore().resetForUser()
  }

  function login(t: string, u: UserInfo) {
    token.value = t
    user.value = u
    setToken(t)
    setUser(u as unknown as Record<string, unknown>)
    resetUserState()
  }

  function updateUser(u: UserInfo) {
    user.value = u
    setUser(u as unknown as Record<string, unknown>)
  }

  async function logout() {
    // 先通知服务端撤销 token（Bearer 或 httpOnly Cookie），失败不阻断本地登出
    try {
      await logoutApi()
    } catch {
      // 网络异常/凭证已失效：继续本地清理
    }
    // 再清理当前用户分区（此时 user 信息尚在），最后清除凭证
    useAgentStore().clearMessages()
    useTeacherAgentStore().clearMessages()
    token.value = null
    user.value = null
    removeToken()
  }

  return { token, user, isLoggedIn, role, userName, login, updateUser, logout }
})
