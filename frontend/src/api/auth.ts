import request from '@/utils/request'
import type { LoginRequest, LoginResponse, UserInfo } from '@/types'

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

/** 发送短信验证码：purpose=login 登录用，purpose=bind 已登录换绑用 */
export interface SmsCodeResponse {
  provider: string
  configured: boolean
  expires_in: number
  cooldown: number
  /** 仅开发环境未配置短信服务商时返回，便于本地联调 */
  debug_code?: string | null
}

export function sendSmsCode(phone: string, purpose: 'login' | 'bind' = 'login') {
  return request.post<SmsCodeResponse>('/auth/sms/send', { phone, purpose })
}

/** 手机号 + 短信验证码登录 */
export function phoneLoginApi(phone: string, code: string) {
  return request.post<LoginResponse>('/auth/phone-login', { phone, code })
}

/** 已登录账号校验验证码后绑定手机号 */
export function bindPhoneApi(phone: string, code: string) {
  return request.post<UserInfo>('/auth/phone/bind', { phone, code })
}

/** 获取 QQ 互联授权地址（mode=login 登录 / bind 绑定到当前账号 / register 注册） */
export function getQqAuthorizeUrl(mode: 'login' | 'bind' | 'register' = 'login') {
  return request.get<{ url: string }>('/auth/qq/authorize', { params: { mode } })
}

/** QQ 回跳票据换取正式登录态 */
export function exchangeQqTicket(ticket: string) {
  return request.post<LoginResponse>('/auth/qq/exchange', { ticket })
}

/** 解除 QQ 互联授权绑定 */
export function unbindQqApi() {
  return request.post<UserInfo>('/auth/qq/unbind')
}

// ─── 学生自助注册 ───────────────────────────────────────
export interface RegisterOptions {
  colleges: { id: number; name: string }[]
  majors: { id: number; college_id: number; name: string }[]
  tutors: { id: number; name: string; college: string | null; title: string | null }[]
}

export function getRegisterOptions() {
  return request.get<RegisterOptions>('/auth/register/options')
}

export interface RegisterPayload {
  /** 注册身份：student 学生 / teacher 教师 */
  role: 'student' | 'teacher'
  student_no: string
  password: string
  name: string
  college_id: number
  major_id: number
  tutor_id: number
  phone?: string | null
  qq?: string | null
  phone_ticket?: string | null
  qq_ticket?: string | null
  /** 未走短信/QQ 验证通道时（资质申请期间）必填，用于注册防刷 */
  captcha_id?: string
  captcha_code?: string
}

export function sendRegisterSms(phone: string, captchaId: string, captchaCode: string) {
  return request.post<SmsCodeResponse>('/auth/register/sms/send', {
    phone,
    captcha_id: captchaId,
    captcha_code: captchaCode,
  })
}

export function verifyRegisterPhone(phone: string, code: string) {
  return request.post<{ phone: string; phone_ticket: string }>('/auth/register/phone/verify', { phone, code })
}

export function registerApi(data: RegisterPayload) {
  return request.post<LoginResponse>('/auth/register', data)
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

/** 退出登录：服务端撤销当前 token（Bearer 或 httpOnly Cookie）并清除 Cookie。
 * 设置超时：退出流程需要等服务端撤销 Cookie 后再跳转，避免请求挂起导致无法退出。 */
export function logoutApi() {
  return request.post<{ message: string }>('/auth/logout', undefined, { timeout: 5000 })
}
