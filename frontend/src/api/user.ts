import request from '@/utils/request'
import type { UserInfo } from '@/types'

export function loginApi(data: { username: string; password: string }) {
  return request.post<{ access_token: string; token_type: string; user: UserInfo }>('/auth/login', data)
}

export function updateProfile(data: Record<string, any>) {
  return request.put<UserInfo>('/auth/profile', data)
}

export function getTeachers() {
  return request.get<UserInfo[]>('/auth/teachers')
}

export function changePassword(old_password: string, new_password: string) {
  return request.put('/auth/change-password', { old_password, new_password })
}