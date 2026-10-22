import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { setToken, setUser, getToken, getUser, removeToken } from '@/utils/token'
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
    // 本地清理必须最先同步执行：调用方（各退出入口）随后会立即 router.push，
    // 若此时凭证仍在，路由守卫会判定为「已登录」并把 /login 重定向回角色首页，
    // 表现为「先跳回某个页面、等接口 401 后才真正退出」。
    // 先清理当前用户分区（此时 user 信息尚在），再清除凭证
    useAgentStore().clearMessages()
    useTeacherAgentStore().clearMessages()
    token.value = null
    user.value = null
    guest.value = false
    setGuestMode(false)
    removeToken()
    // 再通知服务端撤销 token（Bearer 或 httpOnly Cookie，Cookie 此时仍随请求发出），
    // 失败不阻断本地登出
    try {
      await logoutApi()
    } catch {
      // 网络异常/凭证已失效：本地已清理，无需处理
    }
  }

  return { token, user, guest, isLoggedIn, role, userName, login, updateUser, enterGuest, exitGuest, logout }
})
