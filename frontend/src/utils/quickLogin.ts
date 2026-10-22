/**
 * 本设备「一键登录」信息。
 *
 * 只有账号已绑定手机号/QQ 时，后端才会在登录响应里下发 quick_token；
 * 这里把凭证与脱敏后的绑定信息留在本设备，供下次打开登录页直接一键登录。
 * 只保存脱敏后的尾号，不落明文手机号/QQ。
 */
import type { LoginResponse, UserInfo } from '@/types'
import { refreshQuickCredential } from '@/api/auth'

const QUICK_KEY = 'campus_quick_account'

export type QuickChannel = 'phone' | 'qq'

export interface QuickAccount {
  token: string
  username: string
  name: string
  channels: QuickChannel[]
  phoneTail?: string
  qqTail?: string
}

function tail(value?: string | null): string | undefined {
  if (!value) return undefined
  return value.length > 4 ? value.slice(-4) : value
}

export function getQuickAccount(): QuickAccount | null {
  const raw = localStorage.getItem(QUICK_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as QuickAccount
    if (!parsed?.token || !Array.isArray(parsed.channels) || !parsed.channels.length) return null
    return parsed
  } catch {
    return null
  }
}

export function saveQuickAccount(account: QuickAccount) {
  localStorage.setItem(QUICK_KEY, JSON.stringify(account))
}

export function clearQuickAccount() {
  localStorage.removeItem(QUICK_KEY)
}

/** 登录成功后按响应落库（未绑定手机号/QQ 时清空旧凭证） */
export function saveQuickAccountFromLogin(res: LoginResponse) {
  const channels = (res.quick_channels || []) as QuickChannel[]
  if (!res.quick_token || !channels.length) {
    clearQuickAccount()
    return
  }
  const u = res.user
  saveQuickAccount({
    token: res.quick_token,
    username: u.username,
    name: u.name,
    channels,
    phoneTail: tail(u.phone),
    qqTail: tail(u.qq),
  })
}

/** 资料页绑定/解绑手机号或 QQ 后刷新凭证，保证登录页的一键登录与最新绑定一致 */
export async function syncQuickAccount(user: UserInfo): Promise<void> {
  if (!user.phone && !user.qq) {
    clearQuickAccount()
    return
  }
  try {
    const res = await refreshQuickCredential()
    const channels = (res.quick_channels || []) as QuickChannel[]
    if (!res.quick_token || !channels.length) {
      clearQuickAccount()
      return
    }
    saveQuickAccount({
      token: res.quick_token,
      username: user.username,
      name: user.name,
      channels,
      phoneTail: tail(user.phone),
      qqTail: tail(user.qq),
    })
  } catch {
    // 刷新失败不影响资料保存：下次账号密码登录会重新下发凭证
  }
}
