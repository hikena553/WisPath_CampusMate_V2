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
