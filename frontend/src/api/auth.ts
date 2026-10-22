import request from '@/utils/request'
import type { LoginRequest, LoginResponse } from '@/types'

export function loginApi(data: LoginRequest) {
  return request.post<LoginResponse>('/auth/login', data)
}

/** 本设备一键登录：凭长期凭证登录已绑定手机号/QQ 的账号 */
export function quickLoginApi(quick_token: string, channel?: 'phone' | 'qq') {
  return request.post<LoginResponse>('/auth/quick-login', { quick_token, channel })
}

/** 忘记密码：身份核验通过后自动通知管理员 */
export interface ForgotPasswordPayload {
  username: string
  name: string
  contact: string
  reason?: string
  captcha_id: string
  captcha: string
}

export interface CaptchaChallenge {
  captcha_id: string
  /** data:image/svg+xml;base64,... 可直接用于 img */
  image: string
  expires_in: number
}

export function getCaptcha() {
  return request.get<CaptchaChallenge>('/auth/captcha')
}

export interface ForgotPasswordStatus {
  id: number
  status: 'pending' | 'reset' | 'rejected'
  submitted_at: string
  eta_hours: number
  message: string
}

export function forgotPasswordApi(data: ForgotPasswordPayload) {
  return request.post<ForgotPasswordStatus>('/auth/forgot-password', data)
}

export function getForgotPasswordStatus(id: number, username: string) {
  return request.get<ForgotPasswordStatus>(`/auth/forgot-password/${id}`, { params: { username } })
}

/** 资料页绑定手机号/QQ 后刷新本设备一键登录凭证 */
export function refreshQuickCredential() {
  return request.post<{ quick_token: string | null; quick_channels: string[] }>('/auth/quick-credential')
}

export interface CurrentIdentity extends Record<string, any> {
  id: number
  username: string
  name: string
  role: string
  password_needs_change?: boolean
}

/** SSO 统一身份信息：校验 token 并获取当前登录者身份。
 * 探活由路由守卫统一处理，401 时不触发全局硬跳转，
 * 否则 /welcome、/forgot-password 等公开页会被瞬间踢回登录页。 */
export function getCurrentIdentity() {
  return request.get<CurrentIdentity>('/auth/me', { skipAuthRedirect: true })
}

/** 退出登录：服务端撤销当前 token（Bearer 或 httpOnly Cookie）并清除 Cookie */
export function logoutApi() {
  return request.post<{ message: string }>('/auth/logout')
}
