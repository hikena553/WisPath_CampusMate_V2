<template>
  <!-- 首页只呈现关键数据：两条指标 + 一句高危提示，明细统一收进「智能提示」子页面，
       避免把完整清单铺在首页造成重复与冗长。 -->
  <section class="ai-card">
    <header class="ai-head">
      <span class="tui-mascot tui-mascot-sm">
        <img :src="siteMascot" :alt="siteName" />
      </span>
      <div class="ai-head-text">
        <div class="ai-title">{{ siteName }} · 智能助手</div>
        <div class="ai-sub" :class="{ 'is-alert': highCount > 0 }">{{ highText }}</div>
      </div>
      <div class="ai-head-ops">
        <button class="ai-go" type="button" @click="goInsights">
          查看详情<el-icon :size="12"><ArrowRight /></el-icon>
        </button>
      </div>
    </header>

    <div class="ai-metrics">
      <button class="ai-metric" type="button" @click="goInsights">
        <span class="ai-num" :class="{ danger: highCount > 0 }">{{ proactiveActions.length }}</span>
        <span class="ai-lb">主动发现</span>
      </button>
      <button class="ai-metric" type="button" @click="goInsights">
        <span class="ai-num">{{ contactSuggestions.length }}</span>
        <span class="ai-lb">建议联系</span>
      </button>
    </div>

    <button class="ai-chat" type="button" @click="router.push('/teacher/agent')">
      <el-icon :size="14"><ChatDotRound /></el-icon>
      和{{ siteName }}聊聊
      <el-icon class="ai-chat-arrow" :size="12"><ArrowRight /></el-icon>
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ChatDotRound } from '@element-plus/icons-vue'
import type { ProactiveAction } from '@/api/agent'
import type { ContactSuggestion } from '@/api/teacher'
import { useSiteConfig } from '@/composables/useSiteConfig'

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName } = useSiteConfig()

const props = defineProps<{
  proactiveActions: ProactiveAction[]
  contactSuggestions: ContactSuggestion[]
  aiLoading?: boolean
}>()

const router = useRouter()

/** 高危口径：主动发现 priority≥80 或推荐联系 priority=high */
const highCount = computed(() => {
  const a = props.proactiveActions.filter((x) => x.priority >= 80).length
  const c = props.contactSuggestions.filter((x) => x.priority === 'high').length
  return a + c
})

const highText = computed(() =>
  highCount.value > 0 ? `${highCount.value} 条高危提示待处置` : '暂无高危提示',
)

function goInsights() {
  router.push('/teacher/ai')
}
</script>

<style scoped>
.ai-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
  padding: 16px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border-strong);
  border-radius: var(--tui-radius);
  box-shadow: none;
}

/* ===== 头部 ===== */
.ai-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ai-head-text {
  flex: 1;
  min-width: 0;
}
.ai-title {
  font-size: 14px;
  font-weight: 600;
  color: #2b3245;
}
.ai-sub {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-sub.is-alert { color: #b54708; font-weight: 500; }
.ai-head-ops {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.ai-go {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: none;
  background: none;
  padding: 0;
  font-size: 11.5px;
  font-family: inherit;
  color: var(--tui-text-quiet);
  cursor: pointer;
}
.ai-go:hover { color: var(--tui-brand); }

/* ===== 关键数据 ===== */
.ai-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.ai-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 9px 12px;
  border: none;
  border-radius: 10px;
  background: #f9fafb;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.ai-metric:hover { background: #f2f4f7; }
.ai-num {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.15;
  color: #101828;
}
.ai-num.danger { color: #d92d20; }
.ai-lb {
  font-size: 11.5px;
  color: #98a2b3;
}

/* ===== 和智能助手对话 ===== */
.ai-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #cfdcf3;
  border-radius: 10px;
  background: #fff;
  color: #1d4ed8;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
}
.ai-chat:hover { background: #eff4ff; }
.ai-chat-arrow { margin-left: auto; color: #98a2b3; }
</style>