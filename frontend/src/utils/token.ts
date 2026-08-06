/**
 * Token 存储管理
 * 
 * 安全说明：
 * - 当前使用 localStorage 存储 JWT，存在 XSS 风险
 * - 生产环境建议改用 httpOnly Cookie + CSRF Token
 * - 或使用 short-lived access_token + refresh_token 模式
 */

const TOKEN_KEY = 'campus_token'
const USER_KEY = 'campus_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getUser(): Record<string, unknown> | null {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setUser(user: Record<string, unknown>) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}
