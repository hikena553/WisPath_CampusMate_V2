/**
 * QQ 互联移动端授权（Android 壳内可用）。
 *
 * 链路：原生 QQAuthPlugin（官方 OpenSDK）拉起手机 QQ 授权 → 返回
 * access_token + openid → 交后端 /api/auth/qq/mobile/* 核验（见 api/auth.ts）。
 *
 * 浏览器环境恒不可用：调用方先用 qqNativeAuthAvailable() 分流，
 * 非原生环境保持既有 Web 行为（网站应用资质下来前的回退链路不变）。
 */
import { Capacitor, registerPlugin } from '@capacitor/core'

export interface QqNativeSession {
  openId: string
  accessToken: string
  /** 有效期（秒），QQ 一般下发 90 天；本链路用后即弃不落库 */
  expiresIn: number
}

interface QQAuthPluginInterface {
  isQQInstalled(): Promise<{ installed: boolean }>
  login(options?: { scope?: string }): Promise<QqNativeSession>
  logout(): Promise<void>
}

const QQAuth = registerPlugin<QQAuthPluginInterface>('QQAuth')

/** 是否具备原生 QQ 授权条件（App 壳内且启用了移动端 QQ 开关） */
export function qqNativeAuthAvailable(): boolean {
  return Capacitor.isNativePlatform()
}

/**
 * 拉起手机 QQ 授权。
 * 拒绝码：QQ_NOT_CONFIGURED / QQ_NOT_INSTALLED / QQ_LOGIN_BUSY / USER_CANCEL / QQ_ERROR / NOT_AVAILABLE
 */
export async function qqNativeLogin(scope = 'all'): Promise<QqNativeSession> {
  if (!qqNativeAuthAvailable()) {
    throw new Error('NOT_AVAILABLE')
  }
  return QQAuth.login({ scope })
}

/** 设备上是否安装了手机 QQ（不可用环境一律返回 false） */
export async function qqNativeIsInstalled(): Promise<boolean> {
  if (!qqNativeAuthAvailable()) return false
  try {
    return (await QQAuth.isQQInstalled()).installed
  } catch {
    return false
  }
}
