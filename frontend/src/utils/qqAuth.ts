/**
 * QQ 互联移动端授权（Android 壳内可用）。
 *
 * 链路：原生 QQAuthPlugin（官方 OpenSDK）拉起手机 QQ 授权 → 返回
 * access_token + openid → 交后端 /api/auth/qq/mobile/* 核验（见 api/auth.ts）。
 *
 * 插件是否真的进包，取决于 android/app/libs/ 下有没有官方 open_sdk_*.aar：
 * - aar 就位：Gradle 编译 QQAuthPlugin，MainActivity 注册插件；
 * - aar 缺失：插件源码被 sourceSets 剔除、不注册，调用会抛
 *   `QQAuth.login()` is not implemented on android（Capacitor UNIMPLEMENTED）。
 * 所以「能不能用」不能只看 Capacitor.isNativePlatform()，必须同时探测插件注册情况，
 * 否则登录页会露出一个点了必然失败的 QQ 入口，并弹出误导性的「QQ 登录失败」。
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

/** 原生插件拒绝码 + 前端补充码 */
export type QqNativeErrorCode =
  | 'USER_CANCEL'
  | 'QQ_NOT_INSTALLED'
  | 'QQ_NOT_CONFIGURED'
  | 'QQ_LOGIN_BUSY'
  | 'QQ_ERROR'
  | 'NOT_AVAILABLE'
  | 'QQ_PLUGIN_MISSING'
  | 'UNKNOWN'

const PLUGIN_ERROR_CODES = new Set<QqNativeErrorCode>([
  'USER_CANCEL',
  'QQ_NOT_INSTALLED',
  'QQ_NOT_CONFIGURED',
  'QQ_LOGIN_BUSY',
  'QQ_ERROR',
  'NOT_AVAILABLE',
])

/** 带拒绝码的原生授权异常：调用方按 code 分别提示，不再靠比较 message 字符串 */
export class QqNativeError extends Error {
  readonly code: QqNativeErrorCode

  constructor(code: QqNativeErrorCode, message?: string) {
    super(message || code)
    this.name = 'QqNativeError'
    this.code = code
  }
}

/** 是否运行在 Capacitor 原生壳内（浏览器恒 false） */
export function qqNativePlatform(): boolean {
  try {
    return Capacitor.isNativePlatform()
  } catch {
    return false
  }
}

/** 原生壳内是否真的注册了 QQ 授权插件（缺 OpenSDK aar 时为 false） */
export function qqNativePluginReady(): boolean {
  if (!qqNativePlatform()) return false
  try {
    return Capacitor.isPluginAvailable('QQAuth')
  } catch {
    return false
  }
}

let missingPluginWarned = false

/**
 * 是否具备原生 QQ 授权条件：原生壳 + 插件已注册。
 *
 * 登录页、注册页、个人中心都靠这个函数决定是否展示 QQ 入口：
 * aar 没放进 android/app/libs/ 时这里返回 false，入口直接隐藏，
 * 不会再出现「点了 QQ → QQ 登录失败，请使用账号密码登录」的死路。
 */
export function qqNativeAuthAvailable(): boolean {
  const ready = qqNativePluginReady()
  if (!ready && qqNativePlatform() && !missingPluginWarned) {
    missingPluginWarned = true
    console.warn(
      '[QQ] 当前安装包未注册 QQAuth 插件（android/app/libs 缺少官方 open_sdk_*.aar），App 内 QQ 登录入口不展示'
    )
  }
  return ready
}

function errorText(error: unknown): string {
  const err = error as { message?: unknown } | null | undefined
  return typeof err?.message === 'string' ? err.message : ''
}

/** Capacitor 未注册插件时抛 UNIMPLEMENTED，消息形如 `QQAuth.login()` is not implemented on android */
function isUnimplemented(error: unknown): boolean {
  const code = (error as { code?: unknown } | null | undefined)?.code
  if (typeof code === 'string' && code.toUpperCase() === 'UNIMPLEMENTED') return true
  return /not implemented|plugin not found/i.test(errorText(error))
}

/** 把原生 / 桥接异常归一成带 code 的 QqNativeError */
export function normalizeQqNativeError(error: unknown): QqNativeError {
  if (error instanceof QqNativeError) return error
  if (isUnimplemented(error)) {
    return new QqNativeError('QQ_PLUGIN_MISSING', '当前安装包未集成 QQ 登录组件')
  }
  const rawCode = (error as { code?: unknown } | null | undefined)?.code
  const code = typeof rawCode === 'string' ? rawCode.trim().toUpperCase() : ''
  if (PLUGIN_ERROR_CODES.has(code as QqNativeErrorCode)) {
    return new QqNativeError(code as QqNativeErrorCode, errorText(error) || code)
  }
  return new QqNativeError('UNKNOWN', errorText(error) || 'QQ 授权失败')
}

/** 取归一后的错误码：调用方不必自己判断 e.code / e.message 的差异 */
export function qqNativeErrorCode(error: unknown): QqNativeErrorCode {
  if (error instanceof QqNativeError) return error.code
  return normalizeQqNativeError(error).code
}

/** 错误码 → 用户可读提示（USER_CANCEL 返回空串，由调用方静默处理） */
export function qqNativeErrorMessage(error: unknown, fallback = 'QQ 授权失败，请稍后重试'): string {
  const code = qqNativeErrorCode(error)
  switch (code) {
    case 'USER_CANCEL':
      return ''
    case 'QQ_NOT_INSTALLED':
      return '未检测到手机 QQ，请安装后重试'
    case 'QQ_NOT_CONFIGURED':
      return '当前安装包未配置 QQ AppID，暂时无法使用 QQ 登录'
    case 'QQ_LOGIN_BUSY':
      return '上一次 QQ 授权尚未完成，请稍后重试'
    case 'QQ_PLUGIN_MISSING':
    case 'NOT_AVAILABLE':
      return '当前安装包未集成 QQ 登录组件，请使用账号密码登录'
    default:
      return fallback
  }
}

/**
 * 拉起手机 QQ 授权。
 * 失败统一抛 QqNativeError（code 见 QqNativeErrorCode），调用方按 code 分流提示。
 */
export async function qqNativeLogin(scope = 'all'): Promise<QqNativeSession> {
  if (!qqNativePlatform()) {
    throw new QqNativeError('NOT_AVAILABLE', '当前环境不支持 QQ 授权')
  }
  if (!qqNativePluginReady()) {
    throw new QqNativeError('QQ_PLUGIN_MISSING', '当前安装包未集成 QQ 登录组件')
  }
  try {
    return await QQAuth.login({ scope })
  } catch (error) {
    throw normalizeQqNativeError(error)
  }
}

/** 设备上是否安装了手机 QQ（不可用环境一律返回 false） */
export async function qqNativeIsInstalled(): Promise<boolean> {
  if (!qqNativePluginReady()) return false
  try {
    return (await QQAuth.isQQInstalled()).installed
  } catch {
    return false
  }
}
