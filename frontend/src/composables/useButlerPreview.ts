/**
 * 小绵管家会话的「动态预览」组合式。
 *
 * 消息列表 / 消息中心中的小绵管家入口需要展示真实、动态的摘要，
 * 而不是写死的文案：这里统一拉取一次资讯简报，取最新一条资讯标题作为会话摘要，
 * 教师端与学生端共用同一份缓存，避免重复请求。
 */
import { computed, ref } from 'vue'
import { getButlerBriefing } from '@/api/butler'

const PREVIEW_FALLBACK = '自动推送最新资讯 · 一键总结对话'

const newsTitle = ref('')
const generatedAt = ref('')
/** 管家会话的最后一条消息：有聊天记录时优先展示它，做到「外面看到的就是最后一条」 */
const lastMessage = ref('')
let inflight: Promise<void> | null = null

/** 会话摘要文本：最后一条消息 > 资讯标题 > 默认文案 */
const butlerPreview = computed(() => lastMessage.value || newsTitle.value || PREVIEW_FALLBACK)

/** 由管家会话在消息变化时回写：让它成为摘要的第一优先级 */
function setButlerPreview(text: string) {
  lastMessage.value = (text || '').replace(/\s+/g, ' ').trim()
}

/** 拉取（并发去重）最新资讯摘要 */
function refresh() {
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const data = await getButlerBriefing(1)
      const first = data.items?.[0]
      newsTitle.value = first?.title || ''
      generatedAt.value = data.generated_at
    } catch {
      // 接口异常时保持默认文案，不影响入口展示
    } finally {
      inflight = null
    }
  })()
  return inflight
}

export function useButlerPreview() {
  return { butlerPreview, generatedAt, refreshButlerPreview: refresh, setButlerPreview }
}