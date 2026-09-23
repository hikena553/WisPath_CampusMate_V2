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
  liked: boolean
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

export const COMMUNITY_CATEGORIES = ['技术', '提问', '分享', '求助']

export function getPosts(params?: { category?: string; q?: string; page?: number; page_size?: number; sort?: string }) {
  return request.get<CommunityPost[]>('/community/posts', { params })
}

export function getPost(id: number) {
  return request.get<CommunityPost>(`/community/posts/${id}`)
}

export function createPost(data: { category: string; title: string; content: string }) {
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