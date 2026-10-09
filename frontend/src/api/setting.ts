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

// ===== 公开展示类设置（免登录）：登录页与各端同步品牌/公告 =====

/** 公开展示类设置键：站点名称 / Logo / 吉祥物 / 系统公告 / 助手称谓 */
export type PublicSettingKey =
  | 'site_name'
  | 'site_logo'
  | 'site_mascot'
  | 'site_announcement'
  | 'agent_name'

export type PublicSettings = Record<PublicSettingKey, string>

// 获取公开展示设置（登录页、教师端、学生端统一走此接口同步管理员下发的品牌信息）
// skipAuthRedirect：公开接口，未登录也可访问，失败不应触发全局 401 登出跳转
export function getPublicSettings() {
  return request.get<PublicSettings>('/settings/public', { skipAuthRedirect: true })
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

export interface VoiceOption {
  voice: string
  label: string
  gender?: string
  tag?: string
  provider: 'edge' | 'tokenplan'
  /** 该 voice 归属的 TTS 模型（后端按 voice 自动选模型） */
  model?: string
  /** 是否在当前账号/套餐下实测可用；false 表示官方支持但需试听确认 */
  verified?: boolean
}

export interface VoiceGroup {
  /** 该分组音色来源：edge（Edge TTS）或 tokenplan（阿里云百炼） */
  provider?: 'edge' | 'tokenplan'
  model: string
  label: string
  voices: VoiceOption[]
}

export interface VoicePipelineInfo {
  stt: { model: string; url: string }
  tts: { model: string; url: string }
  voice: string
  /** 当前 voice 对应的 TTS 模型 */
  voice_model?: string
  voice_prompt: string
  llm_model: string
  voices?: VoiceOption[]
  /** 按模型分组的官方音色清单（含 verified 标记） */
  voice_groups?: VoiceGroup[]
  providers?: string[]
}

// 获取语音链路信息（STT/TTS 模型、当前生效音色与播报提示词）
export function getVoicePipelineInfo() {
  return request.get<VoicePipelineInfo>('/settings/voice/info')
}

// TTS 试听：按指定音色（缺省当前生效音色）合成示例语音
export function testTtsPreview(payload: { text: string; voice?: string }) {
  return request.post<{ audio_base64: string; voice: string; model: string; chars: number }>('/settings/tts/test', payload)
}
