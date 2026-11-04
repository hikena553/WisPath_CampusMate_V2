/**
 * 聊天消息里的「附件消息」解析。
 *
 * 附件不另建表：一条附件消息就是一条普通文本消息，content 里存 JSON ——
 *
 *   {"type":"image"|"voice"|"file", "text":"文件名", "url":"/api/files/root/xx", "duration":3}
 *
 * 好处是历史接口、会话列表、文件页、教师端 / 学生端都不用改协议；
 * 代价是**任何按人展示 content 的地方都必须先解析**，否则界面上会冒出
 * `{"type":"image","url":...}` 这种字符串。
 * 后端对应口径：backend/app/utils/message_attach.py（会话摘要的 [图片] / [语音 3″]）。
 */

export type AttachmentType = 'file' | 'image' | 'voice'

export interface MessageAttachment {
  type: AttachmentType
  /** 文件名 / 展示名；语音消息为空 */
  text: string
  url: string
  /** 语音时长（秒），其它类型为 0 */
  duration: number
}

const ATTACHMENT_TYPES: AttachmentType[] = ['file', 'image', 'voice']

/** 安全阀：只接受站内相对地址，挡掉 javascript: / data: 之类的伪协议 */
function isSafeUrl(url: string): boolean {
  return url.startsWith('/') && !url.startsWith('//')
}

/** 解析附件消息；普通文本 / 坏 JSON 一律返回 null（按文本渲染） */
export function parseAttachment(content: string | null | undefined): MessageAttachment | null {
  if (!content || !content.startsWith('{')) return null
  try {
    const data = JSON.parse(content)
    if (!data || typeof data !== 'object') return null
    if (!ATTACHMENT_TYPES.includes(data.type)) return null
    if (typeof data.url !== 'string' || !isSafeUrl(data.url)) return null
    return {
      type: data.type as AttachmentType,
      text: typeof data.text === 'string' ? data.text : '',
      url: data.url,
      duration: Number(data.duration) || 0,
    }
  } catch {
    return null
  }
}

/** 会话列表里的一句话预览（与服务端预览口径一致，用于 WS 直推的本地行） */
export function attachmentPreview(content: string | null | undefined): string {
  const attach = parseAttachment(content)
  if (!attach) return content || ''
  if (attach.type === 'image') return '[图片]'
  if (attach.type === 'voice') return `[语音 ${formatVoiceDuration(attach.duration)}]`
  return `[文件] ${attach.text}`.trim()
}

/** 语音时长：`3″` / `1′05″` */
export function formatVoiceDuration(seconds: number): string {
  const s = Math.max(0, Math.round(Number(seconds) || 0))
  if (s < 60) return `${s}″`
  return `${Math.floor(s / 60)}′${String(s % 60).padStart(2, '0')}″`
}

/**
 * 语音条宽度随时长递增（微信 / QQ 的语音条手感）：
 * 1 秒也至少能看清，长语音封顶 180px，避免一条语音把气泡撑满整屏。
 */
export function voiceBubbleWidth(seconds: number): string {
  const s = Math.max(1, Number(seconds) || 1)
  return `${Math.min(180, 84 + s * 8)}px`
}

/**
 * 录音落盘的文件名与扩展名。
 * Chrome / Android 出 webm，Safari 只出 mp4 容器（存成 .m4a，后端按音频返回 media type）。
 */
export function recordFileExt(mime: string): string {
  if (mime.includes('mp4')) return 'm4a'
  if (mime.includes('ogg')) return 'ogg'
  return 'webm'
}
