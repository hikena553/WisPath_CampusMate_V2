/** 附件消息协议：消息 content 为 JSON 文本，渲染前必须先解析。 */

export interface MessageAttachment {
  type: 'image' | 'voice' | 'file'
  text: string
  url: string
  duration: number
}

/** 解析附件消息，普通文本返回 null */
export function parseAttachment(content?: string | null): MessageAttachment | null {
  if (!content) return null
  const raw = content.trim()
  if (!raw.startsWith('{')) return null
  try {
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    if (!['image', 'voice', 'file'].includes(parsed.type)) return null
    if (typeof parsed.url !== 'string' || !parsed.url) return null
    return {
      type: parsed.type,
      text: typeof parsed.text === 'string' ? parsed.text : '',
      url: parsed.url,
      duration: Number(parsed.duration) || 0,
    }
  } catch {
    return null
  }
}

/** 会话列表最后一条消息的纯文本预览 */
export function attachmentPreview(content?: string | null): string {
  const attach = parseAttachment(content)
  if (!attach) return content || ''
  if (attach.type === 'image') return '[图片]'
  if (attach.type === 'voice') return `[语音] ${formatVoiceDuration(attach.duration)}`
  return `[文件] ${attach.text || '未命名文件'}`
}

/** 语音时长展示（mm:ss） */
export function formatVoiceDuration(seconds?: number | null): string {
  const total = Math.max(0, Math.round(Number(seconds) || 0))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/** 录音 Blob 的 MIME 转文件扩展名 */
export function recordFileExt(mime?: string | null): string {
  const map: Record<string, string> = {
    'audio/webm': 'webm',
    'audio/ogg': 'ogg',
    'audio/mp4': 'm4a',
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'audio/x-wav': 'wav',
  }
  const key = (mime || '').split(';')[0].trim().toLowerCase()
  return map[key] || 'webm'
}

/** 语音气泡宽度随时长递增（QQ 语音条样式） */
export function voiceBubbleWidth(duration?: number | null): string {
  const d = Number(duration) || 1
  return `${Math.min(180, 84 + d * 8)}px`
}
