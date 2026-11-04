import { getToken } from '@/utils/token'

/** 聊天文件单文件上限：5GB（服务端只保留 7 天，到期自动删除） */
export const MAX_CHAT_FILE_SIZE = 5 * 1024 * 1024 * 1024

export async function uploadFile(file: File): Promise<{ url: string; filename: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const token = getToken()
  const resp = await fetch('/api/upload', {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  })
  if (!resp.ok) throw new Error('上传失败')
  return resp.json()
}

/**
 * 聊天文件上传（裸 body 流式发送）：支持最大 5GB，不经过 FormData，
 * 避免大文件在浏览器/服务端临时目录里多占一份空间。
 */
export function uploadChatFile(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<{ url: string; filename: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const token = getToken()
    xhr.open('POST', `/api/upload/chat-file?filename=${encodeURIComponent(file.name)}`)
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('上传失败'))
        }
        return
      }
      let detail = '上传失败'
      try {
        detail = JSON.parse(xhr.responseText)?.detail || detail
      } catch { /* 非 JSON 响应走默认文案 */ }
      reject(new Error(detail))
    }
    xhr.onerror = () => reject(new Error('上传失败'))
    xhr.send(file)
  })
}