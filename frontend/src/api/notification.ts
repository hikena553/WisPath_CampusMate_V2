import request from '@/utils/request'

export interface Notification {
  id: number
  title: string
  content: string
  type: string
  is_read: boolean
  link?: string
  related_id?: number
  sender_name?: string
  created_at: string
}

export interface NotificationCount {
  total: number
  unread: number
}

// 获取通知列表
export function getNotifications(params?: {
  is_read?: boolean
  type?: string
  page?: number
  page_size?: number
}) {
  return request.get<Notification[]>('/notifications', { params })
}

// 获取通知数量
export function getNotificationCount() {
  return request.get<NotificationCount>('/notifications/count')
}

// 标记通知为已读
export function markNotificationsRead(notificationIds?: number[]) {
  return request.put('/notifications/read', { notification_ids: notificationIds || [] })
}

// 标记所有通知为已读
export function markAllNotificationsRead() {
  return request.put('/notifications/read-all')
}

// 删除通知
export function deleteNotification(id: number) {
  return request.delete(`/notifications/${id}`)
}
