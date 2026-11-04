import request from '@/utils/request'

export interface CommunityPost {
  id: number
  student_id: number
  category: string
  title: string
  content: string
  view_count: number
  like_count: number
  comment_count: number
  created_at: string | null
  author_name: string | null
  author_avatar: string | null
  author_is_following: boolean
  liked: boolean
  /** 配图 URL 数组（最多 9 张），后端出参恒为数组 */
  images: string[]
}

export interface CommunityComment {
  id: number
  post_id: number
  student_id: number
  content: string
  created_at: string | null
  author_name: string | null
  author_avatar: string | null
}

export const COMMUNITY_CATEGORIES = ['技术', '提问', '分享', '求助', '资讯']

export function getPosts(params?: { category?: string; q?: string; page?: number; page_size?: number; sort?: string }) {
  return request.get<CommunityPost[]>('/community/posts', { params })
}

export function getPost(id: number) {
  return request.get<CommunityPost>(`/community/posts/${id}`)
}

/** 我发布的帖子（个人中心「我发布的」） */
export function getMyPosts() {
  return request.get<CommunityPost[]>('/community/posts/mine')
}

/**
 * 某个用户发布的帖子（个人主页「TA 的动态」）。
 * 游标分页：翻下一页时传手上最后一条的 id，比 page 分页更抗「翻页期间有人发新帖」。
 */
export function getUserPosts(userId: number, params?: { limit?: number; before_id?: number }) {
  return request.get<CommunityPost[]>(`/community/users/${userId}/posts`, { params })
}

/**
 * 关注流：我关注的人发的帖子（校园资讯「关注」页签）。
 * 与 getPosts 的区别只有作者集合：只收我关注的人，不收自己，也不做推荐加权。
 */
export function getFollowingPosts(params?: { page?: number; page_size?: number }) {
  return request.get<CommunityPost[]>('/community/following', { params })
}

export function createPost(data: { category: string; title: string; content: string; images?: string[] }) {
  return request.post<CommunityPost>('/community/posts', data)
}

export function updatePost(id: number, data: Partial<CommunityPost>) {
  return request.put<CommunityPost>(`/community/posts/${id}`, data)
}

export function deletePost(id: number) {
  return request.delete(`/community/posts/${id}`)
}

export function toggleLike(postId: number) {
  return request.post<{ liked: boolean; count: number }>(`/community/posts/${postId}/like`)
}

export function getComments(postId: number) {
  return request.get<CommunityComment[]>(`/community/posts/${postId}/comments`)
}

export function createComment(postId: number, content: string) {
  return request.post<CommunityComment>(`/community/posts/${postId}/comments`, { content })
}

export function deleteComment(commentId: number) {
  return request.delete(`/community/comments/${commentId}`)
}

export function getHotPosts(limit = 5) {
  return request.get<CommunityPost[]>('/community/hot', { params: { limit } })
}

/**
 * 推荐流候选：后端按「新鲜度 × 热度 × 兴趣画像」排好序的帖子，供校园资讯「推荐」页穿插。
 * 与 /posts 的区别是不含自己发的、剔除与资讯重名的、且限制资讯站账号的占比。
 */
export function getRecommendedPosts(limit = 12) {
  return request.get<CommunityPost[]>('/community/recommend', { params: { limit } })
}