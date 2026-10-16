import request from '@/utils/request'

export interface MessageOut {
  id: number
  sender_id: number
  receiver_id: number
  content: string
  read: boolean
  created_at: string
}

export interface ConversationOut {
  user_id: number
  user_name: string
  user_avatar: string | null
  last_message: string
  last_message_time: string | null
  unread_count: number
}

export function getConversations() {
  return request.get<ConversationOut[]>('/messages/conversations')
}

export function getMessages(userId: number) {
  return request.get<MessageOut[]>(`/messages/${userId}`)
}

export function sendMessage(receiverId: number, content: string) {
  return request.post<{ id: number; created_at: string }>('/messages/send', { receiver_id: receiverId, content })
}

export function markRead(userId: number) {
  return request.put(`/messages/read/${userId}`)
}

/** 置顶的会话 key 列表（g-<groupId> / s-<userId>），服务端持久化 */
export function getSessionPins() {
  return request.get<{ keys: string[] }>('/messages/pins')
}

/** 置顶 / 取消置顶某个会话（幂等） */
export function setSessionPin(sessionKey: string, pinned: boolean) {
  return request.put<{ key: string; pinned: boolean }>('/messages/pins', { session_key: sessionKey, pinned })
}

/**
 * 删除会话条目（服务端按用户级隐藏记录，跨端同步）。
 * 只从本人列表移除：聊天记录保留、对方不受影响，之后收到新消息会自动恢复展示。
 */
export function deleteSession(sessionKey: string) {
  return request.delete<{ session_key: string; hidden_upto_id: number }>(`/messages/sessions/${sessionKey}`)
}

export interface UnreadSummary {
  chat: number
  group: number
  notification: number
  total: number
}

/** 全局未读汇总：单聊 + 群聊 + 站内通知，导航红点一次取齐 */
export function getUnreadSummary() {
  return request.get<UnreadSummary>('/messages/unread-summary')
}

/** 清除未读提示：单聊与群聊全部置已读（站内通知走 /notifications/read-all） */
export function clearAllUnread() {
  return request.put<{ message: string; chat: number; group: number }>('/messages/read-all')
}
