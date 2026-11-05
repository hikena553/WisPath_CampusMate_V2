import request from '@/utils/request'

/** 关注关系结果：三项标记 + 目标用户的关注/粉丝/好友计数 */
export interface RelationState {
  is_following: boolean
  is_follower: boolean
  is_friend: boolean
  following: number
  followers: number
  friends: number
}

export interface ContactUser {
  id: number
  name: string
  username: string
  avatar: string | null
  role: string
  college: string | null
  class_name: string | null
  signature: string | null
  is_following: boolean
  is_follower: boolean
  is_friend: boolean
}

export interface SuggestUser {
  id: number
  name: string
  username: string
  avatar: string | null
  role: string
  college: string | null
  class_name: string | null
  signature: string | null
}

/** 论坛互动类型：赞 / 收藏 / 评论 / 新粉丝 */
export type ForumKind = 'like' | 'favorite' | 'comment' | 'follow'

export interface ForumMessageOut {
  id: number
  kind: ForumKind
  actor_id: number
  actor_name: string
  actor_avatar: string | null
  post_id: number | null
  post_title: string | null
  /** 帖子首图（无配图 / 帖子已删为 null） */
  post_cover: string | null
  content: string | null
  is_read: boolean
  created_at: string
}

/** 双方关系（好友 = 互相关注），供个人主页关注按钮与计数使用 */
export function getRelation(userId: number) {
  return request.get<RelationState>(`/social/relation/${userId}`)
}

export function followUser(userId: number) {
  return request.post<RelationState>(`/social/follow/${userId}`)
}

export function unfollowUser(userId: number) {
  return request.delete<RelationState>(`/social/follow/${userId}`)
}

/** 通讯录：following=我关注的 followers=关注我的 friends=互关好友 */
export function getContacts(params: { tab: 'following' | 'followers' | 'friends'; keyword?: string; limit?: number }) {
  return request.get<ContactUser[]>('/social/contacts', { params })
}

/** 推荐关注（同学院优先，排除已关注） */
export function getSuggestions(limit = 10) {
  return request.get<SuggestUser[]>('/social/suggestions', { params: { limit } })
}

/** 论坛互动消息（赞 / 收藏 / 评论 / 新粉丝），与聊天会话分开 */
export function getForumMessages(params?: { kind?: ForumKind; unread_only?: boolean; limit?: number; offset?: number }) {
  return request.get<ForumMessageOut[]>('/social/forum-messages', { params })
}

/** 标记互动消息已读；不传 ids 表示全部已读 */
export function markForumRead(ids?: number[]) {
  return request.put<{ updated: number }>('/social/forum-messages/read', { ids: ids ?? null })
}

export function getForumUnreadCount() {
  return request.get<{ count: number }>('/social/forum-messages/unread-count')
}

/* ==================== 好友设置（个人主页「设置」页） ====================
   备注 / 特别关心 / 免打扰 / 黑名单 / 动态权限 / 亲密关系 都存在服务端，
   换设备也跟着走；字段含义与后端 models.social.FriendSetting 一一对应。 */

export interface FriendSetting {
  peer_id: number
  /** 备注：只有自己看得见的称呼 */
  remark: string
  /** 特别关心：消息列表挂「特别」标、主页封面挂金标 */
  care: boolean
  mute: boolean
  blocked: boolean
  /** 动态权限·不看 TA 的动态 */
  hide_peer_posts: boolean
  /** 动态权限·不让 TA 看我的动态 */
  hide_my_posts: boolean
  /** 亲密关系标识：'' = 未设置，其余见 INTIMACY_OPTIONS */
  intimacy: string
}

/** 一次拿到两份：我设的（mine）+ 对方设的（peer），亲密关系展示两份取其一 */
export interface FriendSettingState {
  mine: FriendSetting
  peer: FriendSetting
}

export type FriendSettingPatch = Partial<Omit<FriendSetting, 'peer_id'>>

/** 我设过的全部联系人（消息列表按 care 挂标） */
export function getFriendSettings() {
  return request.get<FriendSetting[]>('/social/friend-settings')
}

export function getFriendSetting(peerId: number) {
  return request.get<FriendSettingState>(`/social/friend-settings/${peerId}`)
}

export function updateFriendSetting(peerId: number, patch: FriendSettingPatch) {
  return request.put<FriendSettingState>(`/social/friend-settings/${peerId}`, patch)
}

