import request from '@/utils/request'

export interface GroupCreate {
  name: string
  member_ids: number[]
}

export interface GroupOut {
  id: number
  name: string
  avatar: string | null
  creator_id: number
  announcement: string | null
  is_dismissed: boolean
  member_count: number
  last_message: string
  last_message_time: string | null
  unread_count: number
}

export interface GroupMemberOut {
  user_id: number
  user_name: string
  user_avatar: string | null
  role: string
  joined_at: string
}

export interface GroupMessageOut {
  id: number
  group_id: number
  sender_id: number
  sender_name: string
  sender_avatar: string | null
  content: string
  created_at: string
}

export interface UserSearchResult {
  id: number
  name: string
  username: string
  avatar: string | null
  role: string
}

export function createGroup(data: GroupCreate) {
  return request.post<{ id: number; name: string }>('/groups/create', data)
}

export function getGroups() {
  return request.get<GroupOut[]>('/groups')
}

export function getGroup(groupId: number) {
  return request.get<GroupOut>(`/groups/${groupId}`)
}

export function getGroupMembers(groupId: number) {
  return request.get<GroupMemberOut[]>(`/groups/${groupId}/members`)
}

export function addGroupMembers(groupId: number, userIds: number[]) {
  return request.post(`/groups/${groupId}/members`, { user_ids: userIds })
}

export function removeGroupMember(groupId: number, userId: number) {
  return request.delete(`/groups/${groupId}/members/${userId}`)
}

export function sendGroupMessage(groupId: number, content: string) {
  return request.post<{ id: number; created_at: string }>(`/groups/${groupId}/send`, { content })
}

export function getGroupMessages(groupId: number) {
  return request.get<GroupMessageOut[]>(`/groups/${groupId}/messages`)
}

export function searchUsers(keyword: string) {
  return request.get<UserSearchResult[]>('/groups/search/users', { params: { keyword } })
}

export function updateGroupAnnouncement(groupId: number, announcement: string) {
  return request.put<{ message: string; announcement: string | null }>(`/groups/${groupId}/announcement`, { announcement })
}

export function leaveGroup(groupId: number) {
  return request.post<{ message: string }>(`/groups/${groupId}/leave`)
}

export function disbandGroup(groupId: number) {
  return request.delete<{ message: string }>(`/groups/${groupId}`)
}

export function markGroupRead(groupId: number) {
  return request.post<{ message: string }>(`/groups/${groupId}/read`)
}