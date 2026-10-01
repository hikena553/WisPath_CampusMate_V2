import request from '@/utils/request'

export interface Setting {
  id: number
  key: string
  value?: string
  description?: string
}

// 获取所有设置
export function getSettings() {
  return request.get<Setting[]>('/settings')
}

// 获取单个设置
export function getSetting(key: string) {
  return request.get<Setting>(`/settings/${key}`)
}

// 更新设置
export function updateSetting(key: string, value: string) {
  return request.put<Setting>(`/settings/${key}`, { value })
}

// 批量更新设置
export function batchUpdateSettings(settings: Record<string, string>) {
  return request.put('/settings', { settings })
}

// AI 生成 Logo/吉祥物图片（提示词 → 多张候选图）
export function generateBrandingImages(prompt: string, count = 4) {
  return request.post<{ images: string[]; model: string }>('/settings/branding/generate', {
    prompt,
    count,
    size: '1024*1024',
  })
}

// 上传自定义 Logo/吉祥物图片
export function uploadBrandingImage(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request
    .post<{ url: string; filename: string }>('/settings/branding/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
}

// ===== 语音与 TTS =====

export interface VoicePipelineInfo {
  stt: { model: string; url: string }
  tts: { model: string; url: string }
  voice: string
  voice_prompt: string
  llm_model: string
}

// 获取语音链路信息（STT/TTS 模型、当前生效音色与播报提示词）
export function getVoicePipelineInfo() {
  return request.get<VoicePipelineInfo>('/settings/voice/info')
}

// TTS 试听：按指定音色（缺省当前生效音色）合成示例语音
export function testTtsPreview(payload: { text: string; voice?: string }) {
  return request.post<{ audio_base64: string; voice: string; model: string; chars: number }>('/settings/tts/test', payload)
}
