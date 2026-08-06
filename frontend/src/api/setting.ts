import request from '@/utils/request'

export interface Setting {
  id: number
  key: string
  value?: string
  description?: string
}

// 获取所有设置
export function getSettings() {
  return request.get<Setting[]>('/settings')
}

// 获取单个设置
export function getSetting(key: string) {
  return request.get<Setting>(`/settings/${key}`)
}

// 更新设置
export function updateSetting(key: string, value: string) {
  return request.put<Setting>(`/settings/${key}`, { value })
}

// 批量更新设置
export function batchUpdateSettings(settings: Record<string, string>) {
  return request.put('/settings', { settings })
}
