/** 忘记密码等待状态：登录页与找回页共用，刷新/重开浏览器后仍可提醒 */
export interface PendingPasswordReset {
  id: number
  username: string
  submittedAt: string
  etaHours: number
}

const STORAGE_KEY = 'mian02_password_reset'
/** 超过该时长（小时）的旧记录不再提示，避免长期打扰 */
const MAX_AGE_HOURS = 72

export function loadPendingPasswordReset(): PendingPasswordReset | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as PendingPasswordReset
    if (!data?.id || !data?.username || !data?.submittedAt) return null
    const ageHours = (Date.now() - new Date(data.submittedAt).getTime()) / 3_600_000
    if (!Number.isFinite(ageHours) || ageHours > MAX_AGE_HOURS) {
      localStorage.removeItem(STORAGE_KEY)
      return null
    }
    return data
  } catch {
    return null
  }
}

export function savePendingPasswordReset(data: PendingPasswordReset): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    // 隐私模式下写入失败不影响主流程
  }
}

export function clearPendingPasswordReset(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // 忽略
  }
}

/** 距离管理员承诺的处理时限还剩多少小时（向上取整，最小 0） */
export function remainingHours(data: PendingPasswordReset): number {
  const elapsed = (Date.now() - new Date(data.submittedAt).getTime()) / 3_600_000
  return Math.max(0, Math.ceil(data.etaHours - elapsed))
}
