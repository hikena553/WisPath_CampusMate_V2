import { getToken } from '@/utils/token'

export async function uploadFile(file: File): Promise<{ url: string; filename: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const token = getToken()
  const resp = await fetch('/api/upload', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (!resp.ok) throw new Error('上传失败')
  return resp.json()
}