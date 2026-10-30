import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import {
  setToken,
  setUser,
  getToken,
  getUser,
  removeToken,
  clearForcedLogout,
} from '@/utils/token'
import { isGuestMode, setGuestMode } from '@/utils/guest'
import { logoutApi } from '@/api/auth'
import { useAgentStore, useTeacherAgentStore } from './agent'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<UserInfo | null>(getUser() as UserInfo | null)
  /** 免费使用（游客）会话：只有前端标记，没有登录凭证 */
  const guest = ref(isGuestMode() && !user.value)

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
    guest.value = false
    setGuestMode(false)
    setToken(t)
    setUser(u as unknown as Record<string, unknown>)
    // 重新登录成功：解除「已主动退出」的强制标记
    clearForcedLogout()
    resetUserState()
  }

  /** 进入免费使用：清掉可能残留的登录态，仅保留游客标记 */
  function enterGuest() {
    token.value = null
    user.value = null
    removeToken()
    guest.value = true
    setGuestMode(true)
  }

  function exitGuest() {
    guest.value = false
    setGuestMode(false)
  }

  function updateUser(u: UserInfo) {
    user.value = u
    setUser(u as unknown as Record<string, unknown>)
  }

  async function logout() {
    // 1) 先撤销服务端凭证并等它真正完成：httpOnly Cookie 只有随响应删除后，
    //    后续 /auth/me 探活才会失败。若不等就跳转，守卫会用仍有效的 Cookie 把登录态复活。
    try {
      await logoutApi()
    } catch {
      // 服务端撤销失败（断网/超时）：本地仍照常清理，退出标记由调用方统一设置
    }
    // 2) 清理本地登录态。业务 store 清理即便异常，也必须保证凭证与用户缓存被移除
    try {
      useAgentStore().clearMessages()
      useTeacherAgentStore().clearMessages()
    } finally {
      token.value = null
      user.value = null
      guest.value = false
      setGuestMode(false)
      removeToken()
    }
  }

  return { token, user, guest, isLoggedIn, role, userName, login, updateUser, enterGuest, exitGuest, logout }
})
