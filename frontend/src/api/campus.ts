import request from '@/utils/request'
import type { CampusScenery, Announcement, ImpressionItem } from '@/types'

export function getSceneries(area?: string) {
  return request.get<CampusScenery[]>('/campus/sceneries', { params: { area } })
}

export function getAnnouncements() {
  return request.get<Announcement[]>('/campus/announcements')
}

export function getGallery() {
  return request.get<GalleryImage[]>('/campus/gallery')
}

export function getImpression() {
  return request.get<ImpressionItem[]>('/campus/impression')
}

/** 站内阅读器数据：文章正文或列表页链接清单 */
export interface CampusArticleLink {
  title: string
  url: string
  date: string | null
}

/** 正文之外的附件下载项（校站的「附件【xxx】」区块） */
export interface CampusArticleAttachment {
  name: string
  url: string
}

export interface CampusArticle {
  /**
   * article = 正文；links = 列表页链接清单；
   * error = 后端抓取失败（校站超时/改版）—— 详情子页仍会返回，正文区改为「暂不可用」，
   * 互动与评论照常可用，所以不顺延成 HTTP 502 把整页打死。
   */
  kind: 'article' | 'links' | 'error'
  title: string
  date: string | null
  content_html: string | null
  links: CampusArticleLink[]
  /** 正文之外的附件下载项：正文只有「附件：xxx」文字，链接在此单独返回 */
  attachments?: CampusArticleAttachment[]
  source_url: string
  /**
   * 该页面能否用「原页渲染」（反代 iframe）打开。
   * 后端对超星系 SPA（lib.mycc.edu.cn 等）返回 false —— 其正文由脚本注入，
   * 而不透明源 iframe 会中断这些脚本，原页必然白屏。
   * 老后端不返回该字段时按 true 处理（保持既有行为）。
   */
  supports_original?: boolean
}

/** 站内阅读：后端代理抓取校内页面并提取正文，避免跳出应用 */
export function readCampusArticle(url: string) {
  return request.get<CampusArticle>('/campus/reader', { params: { url } })
}

/**
 * 原页渲染地址：后端反代后的校内页面，供 iframe 嵌入（保留原版排版）。
 * 走同源 /api 代理是安全的：iframe 必须带 sandbox（不含 allow-same-origin），
 * 不透明源下学校页面的脚本拿不到应用的 localStorage / Cookie。
 */
export function campusEmbedUrl(url: string) {
  return `/api/campus/embed?url=${encodeURIComponent(url)}`
}

export interface GalleryImage {
  title: string
  image_url: string
  campus: string
}

/* ==================== 资讯互动：评论 / 点赞 / 转发 ==================== */

/**
 * 单篇资讯的互动状态。资讯来自校站爬虫、没有内部 id，
 * 所以 url 就是这篇资讯的 id（与后端 campus_article_socials.url 一致）。
 */
export interface CampusArticleInteract {
  url: string
  title: string
  source: string
  image_url: string | null
  like_count: number
  comment_count: number
  repost_count: number
  view_count: number
  liked: boolean
  updated_at: string | null
}

export interface CampusArticleDetail {
  article: CampusArticle
  social: CampusArticleInteract
}

export interface CampusArticleComment {
  id: number
  article_url: string
  user_id: number
  content: string
  created_at: string | null
  author_name: string | null
  author_avatar: string | null
  /** 是否本人发表：后端算好，前端不必再比对当前用户 id */
  mine: boolean
}

/** 详情子页：正文 + 互动状态（同时浏览数 +1） */
export function getArticleDetail(url: string) {
  return request.get<CampusArticleDetail>('/campus/articles/detail', { params: { url } })
}

/** 资讯流批量取互动状态：一次请求补齐整屏计数，返回 { url: 互动状态 } */
export function getArticleInteractions(urls: string[]) {
  return request.get<Record<string, CampusArticleInteract>>('/campus/interactions', {
    params: { urls: urls.join(',') },
  })
}

export function getArticleComments(url: string) {
  return request.get<CampusArticleComment[]>('/campus/articles/comments', { params: { url } })
}

/** 点赞 / 取消点赞（同一接口切换），返回最新状态与总数 */
export function toggleArticleLike(url: string) {
  return request.post<{ liked: boolean; count: number }>('/campus/articles/like', { url })
}

export function createArticleComment(url: string, content: string) {
  return request.post<CampusArticleComment>('/campus/articles/comments', { url, content })
}

export function deleteArticleComment(commentId: number) {
  return request.delete<{ ok: boolean }>(`/campus/articles/comments/${commentId}`)
}

/** 转发资讯：content 为可选附言，返回转发后的总次数 */
export function repostArticle(url: string, content = '') {
  return request.post<{ ok: boolean; count: number }>('/campus/articles/repost', { url, content })
}
