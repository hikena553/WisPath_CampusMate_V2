/**
 * Token 存储管理（F3 安全加固后）
 *
 * 安全说明：
 * - 登录凭证已改为 httpOnly Cookie 通道（`campus_token`），JS 不可读，用户信息仍缓存于 localStorage 用于首屏渲染；
 * - 本模块保留「内存态 token」用于 WebSocket 握手等显式传参场景：新登录仅写内存；
 * - 旧版本 localStorage 中的 token（`campus_token`）在首次读取时自动迁移进内存并删除，完成升级清理；
 * - 刷新页面后内存态为空：API 请求凭 Cookie 自动认证，路由守卫会调用 /api/auth/me 探活与回填。
 */

const TOKEN_KEY = 'campus_token'
const USER_KEY = 'campus_user'

let memoryToken: string | null = null

/**
 * 退出登录进行中标记。
 * 服务端撤销 httpOnly Cookie 是异步的，而退出后紧接着跳转 /login 会触发路由守卫；
 * 若此时 Cookie 尚未失效，守卫调 /auth/me 会把登录态重新「复活」并跳回角色首页。
 * 浏览器内无对应 API 查后端状态，故用该标记让守卫在退出期间不做探活。
 */
let loggingOut = false

/** 已主动退出登录的持久标记（sessionStorage：刷新后仍有效） */
const FORCED_LOGOUT_KEY = 'mian02_forced_logout'

export function markLoggingOut(value: boolean) {
  loggingOut = value
}

export function isLoggingOut() {
  return loggingOut
}

/**
 * 记录「用户已主动退出」。
 * 若服务端撤销凭证失败（断网/超时），httpOnly Cookie 可能仍留在浏览器里，
 * 刷新后守卫的 /auth/me 会把用户重新登录回来。该标记让守卫在用户下次登录前
 * 一律按未登录处理，保证退出在刷新后依然生效。
 */
export function markForcedLogout() {
  try {
    sessionStorage.setItem(FORCED_LOGOUT_KEY, '1')
  } catch {
    // 隐私模式等 sessionStorage 不可用：忽略，仍有内存标记兜底
  }
}

export function isForcedLogout() {
  try {
    return sessionStorage.getItem(FORCED_LOGOUT_KEY) === '1'
  } catch {
    return false
  }
}

/** 重新登录成功后清除强制退出标记 */
export function clearForcedLogout() {
  try {
    sessionStorage.removeItem(FORCED_LOGOUT_KEY)
  } catch {
    // 忽略不可用场景
  }
}

/** 升级迁移：首次读取时把旧版 localStorage token 移入内存并删除，避免 XSS 窃取面残留 */
function migrateLegacyToken(force = false): string | null {
  if (memoryToken) return memoryToken
  const legacy = localStorage.getItem(TOKEN_KEY)
  if (legacy) {
    memoryToken = legacy
    if (!force) {
      localStorage.removeItem(TOKEN_KEY)
    }
  }
  return memoryToken
}

export function getToken(): string | null {
  return migrateLegacyToken()
}

export function setToken(token: string) {
  memoryToken = token
  // 不写入 localStorage：凭证只走 httpOnly Cookie（服务端登录时下发）与内存态
}

export function removeToken() {
  memoryToken = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getUser(): Record<string, unknown> | null {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? (JSON.parse(raw) as Record<string, unknown>) : null
}

/** 当前登录用户 id（用于按用户分区的本地存储 key），未登录返回 null */
export function getUserId(): number | null {
  const user = getUser()
  return user && typeof user.id === 'number' ? user.id : null
}

export function setUser(user: Record<string, unknown>) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}