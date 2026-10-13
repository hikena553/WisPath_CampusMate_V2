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

const title = ref('')
const generatedAt = ref('')
let inflight: Promise<void> | null = null

/** 会话摘要文本：拿到资讯标题后展示标题，否则回退默认文案 */
const butlerPreview = computed(() => title.value || PREVIEW_FALLBACK)

/** 拉取（并发去重）最新资讯摘要 */
function refresh() {
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const data = await getButlerBriefing(1)
      const first = data.items?.[0]
      title.value = first?.title || ''
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
  return { butlerPreview, generatedAt, refreshButlerPreview: refresh }
}