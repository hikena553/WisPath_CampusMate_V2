import request from '@/utils/request'

/** 勋章外观分级：铜 / 银 / 金 / 钻 */
export type BadgeTier = 'bronze' | 'silver' | 'gold' | 'diamond'

export interface BadgeItem {
  code: string
  name: string
  desc: string
  icon: string
  tier: BadgeTier
  category: string
  /** 是否已获得；false 为轮廓态，progress 表示解锁进度 */
  earned: boolean
  awarded_at: string | null
  progress: number
  target_label: string
}

export interface LevelInfo {
  level: number
  name: string
  desc: string
  points: number
  next_points: number | null
  progress: number
}

export interface BadgeWall {
  level: LevelInfo
  earned: BadgeItem[]
  locked: BadgeItem[]
  earned_count: number
  total_count: number
}

export interface HomepageStat {
  key: string
  label: string
  value: number
  icon: string
}

export interface HomepageHighlight {
  title: string
  subtitle: string
  date: string
  icon: string
}

export interface HomepageMutual {
  same_college: boolean
  common_groups: number
  is_my_tutor: boolean
  is_my_student: boolean
  /** 是否已建立单聊关系（聊过天） */
  has_conversation: boolean
  /** 我有没有关注对方：本站「好友 = 我关注的」，主页的联系人菜单据此显示 */
  is_following: boolean
  /** 对方有没有关注我 */
  is_follower: boolean
}

export interface UserHomepage {
  id: number
  name: string
  role: string
  username: string
  avatar: string | null
  signature: string | null
  college: string | null
  class_name: string | null
  title: string | null
  department: string | null
  level: LevelInfo
  badges: BadgeItem[]
  earned_count: number
  total_count: number
  stats: HomepageStat[]
  highlights: HomepageHighlight[]
  mutual: HomepageMutual
}

/** 我的勋章墙（等级 + 已获得 + 未获得进度） */
export function getMyBadgeWall() {
  return request.get<BadgeWall>('/badges/me')
}

/** 结算勋章：返回本次新解锁（含历史待播）的勋章，用于播放奖励动画 */
export function syncBadges() {
  return request.post<{ new: BadgeItem[] }>('/badges/sync')
}

/** 奖励动画播放完毕：清空待播队列，避免重复播放 */
export function markBadgesSeen() {
  return request.post<{ message: string; count: number }>('/badges/seen')
}

/** 保存个性签名 */
export function updateSignature(signature: string) {
  return request.put<{ signature: string }>('/badges/signature', { signature })
}

/** 他人勋章墙 */
export function getUserBadgeWall(userId: number) {
  return request.get<BadgeWall>(`/badges/user/${userId}`)
}

/** 个人主页：签名 / 等级 / 勋章 / 角色化数据 / 近期亮点 / 双方关系 */
export function getUserHomepage(userId: number) {
  return request.get<UserHomepage>(`/badges/user/${userId}/homepage`)
}