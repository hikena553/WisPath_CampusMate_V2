/**
 * 游客（免费使用）会话标记。
 * 游客只持有本地标记，没有登录凭证：路由守卫据此放开公开页面，
 * 请求层据此避免 401 触发全局跳转。
 */
const GUEST_KEY = 'campus_guest'

export function isGuestMode(): boolean {
  return localStorage.getItem(GUEST_KEY) === '1'
}

export function setGuestMode(on: boolean) {
  if (on) localStorage.setItem(GUEST_KEY, '1')
  else localStorage.removeItem(GUEST_KEY)
}
