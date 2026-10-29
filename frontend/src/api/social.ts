/**
 * 社交关系：关注 / 粉丝 / 好友（互关）/ 论坛互动消息
 *
 * 口径（2026-10 改版）：关注是单向的，互相关注即好友——
 * 前端不再维护「好友」独立列表，一切都从 is_following / is_follower / is_friend 推导。
 * 论坛互动消息（评论 / 点赞 / 新粉丝）与聊天消息分属两套接口与两个页签，互不混排。
 */
import request from '@/utils/request'

export interface SocialUser {
  id: number
  name: string
  username: string
  avatar: string | null
  role: string
  college: string | null
  class_name: string | null
  title: string | null
  signature: string | null
  is_following: boolean
  is_follower: boolean
  is_friend: boolean
  followed_at: string | null
}

export interface FollowState {
  /** 计数属于 user_id 指向的人（/stats 时是自己） */
  user_id: number
  is_following: boolean
  is_follower: boolean
  is_friend: boolean
  following: number
  followers: number
  friends: number
}

export type ForumMessageKind = 'comment' | 'like' | 'favorite' | 'follow'

export interface ForumMessageItem {
  id: number
  kind: ForumMessageKind
  actor_id: number
  actor_name: string
  actor_avatar: string | null
  post_id: number | null
  post_title: string
  content: string
  is_read: boolean
  created_at: string
}

export interface ForumUnread {
  total: number
  comment: number
  like: number
  favorite: number
  follow: number
}

/** 我关注的人 */
export function getFollowing() {
  return request.get<SocialUser[]>('/social/following')
}

/** 关注我的人（粉丝） */
export function getFollowers() {
  return request.get<SocialUser[]>('/social/followers')
}

/** 互关好友 */
export function getFriends() {
  return request.get<SocialUser[]>('/social/friends')
}

/** 我的关注 / 粉丝 / 好友计数 */
export function getSocialStats() {
  return request.get<FollowState>('/social/stats')
}

/** 关注某人（幂等） */
export function followUser(userId: number) {
  return request.post<FollowState>(`/social/follow/${userId}`)
}

/** 取消关注（幂等） */
export function unfollowUser(userId: number) {
  return request.delete<FollowState>(`/social/follow/${userId}`)
}

/** 查询与某人的关系 */
export function getRelation(userId: number) {
  return request.get<FollowState>(`/social/relation/${userId}`)
}

/** 按姓名 / 学工号搜索 */
export function searchSocialUsers(keyword: string, limit = 20) {
  return request.get<SocialUser[]>('/social/users/search', { params: { keyword, limit } })
}

/** 可能认识的人（同班 / 同学院优先） */
export function getFollowSuggestions(limit = 10) {
  return request.get<SocialUser[]>('/social/suggestions', { params: { limit } })
}

/** 论坛互动消息（与聊天隔离） */
export function getForumMessages(params?: { kind?: ForumMessageKind; page?: number; page_size?: number }) {
  return request.get<ForumMessageItem[]>('/social/forum-messages', { params })
}

/** 互动未读（按类型拆分） */
export function getForumUnread() {
  return request.get<ForumUnread>('/social/forum-messages/unread')
}

/** 单条已读 */
export function readForumMessage(id: number) {
  return request.post(`/social/forum-messages/${id}/read`)
}

/** 全部已读（可按类型） */
export function readAllForumMessages(kind?: ForumMessageKind) {
  return request.post<{ message: string; count: number }>('/social/forum-messages/read-all', null, {
    params: kind ? { kind } : undefined,
  })
}
