import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { setToken, setUser, getToken, getUser, removeToken } from '@/utils/token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref<UserInfo | null>(getUser())

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role)
  const userName = computed(() => user.value?.name)

  function login(t: string, u: UserInfo) {
    token.value = t
    user.value = u
    setToken(t)
    setUser(u)
  }

  function updateUser(u: UserInfo) {
    user.value = u
    setUser(u)
  }

  function logout() {
    token.value = null
    user.value = null
    removeToken()
  }

  return { token, user, isLoggedIn, role, userName, login, updateUser, logout }
})
