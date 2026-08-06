import request from '@/utils/request'
import type { LoginRequest, LoginResponse } from '@/types'

export function loginApi(data: LoginRequest) {
  return request.post<LoginResponse>('/auth/login', data)
}
