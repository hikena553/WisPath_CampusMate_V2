import request from '@/utils/request'
import type { LoginRequest, LoginResponse } from '@/types'

export function loginApi(data: LoginRequest) {
  return request.post<LoginResponse>('/auth/login', data)
}

export interface CurrentIdentity extends Record<string, any> {
  id: number
  username: string
  name: string
  role: string
  password_needs_change?: boolean
}

/** SSO 统一身份信息：校验 token 并获取当前登录者身份 */
export function getCurrentIdentity() {
  return request.get<CurrentIdentity>('/auth/me')
}
