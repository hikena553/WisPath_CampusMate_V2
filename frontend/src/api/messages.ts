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
