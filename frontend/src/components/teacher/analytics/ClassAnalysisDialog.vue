<template>
  <el-dialog
    v-model="visibleModel"
    class="mascot-analysis-dialog"
    :append-to-body="true"
    destroy-on-close
  >
    <template #header>
      <div class="dialog-header">
        <img :src="siteMascot" :alt="siteName" class="dialog-header-mascot" />
        <div class="dialog-header-text">
          <div class="dialog-title">班级情况分析</div>
          <div class="dialog-sub">{{ siteName }}基于班级图表与学生成长数据智能生成</div>
        </div>
      </div>
    </template>
    <div class="dialog-content">
      <div v-if="analysisLoading" class="dialog-loading">
        <img :src="siteMascot" :alt="siteName" class="dialog-loading-mascot" />
        <p class="dialog-loading-text">{{ analysisLoadingText }}</p>
      </div>
      <div v-else-if="analysisResult" class="analysis-report markdown-body" v-html="renderedAnalysisHtml"></div>
      <div v-else class="dialog-empty">
        <el-icon class="dialog-empty-icon"><MagicStick /></el-icon>
        <p>点击下方按钮，{{ siteName }}将为您生成班级分析报告</p>
      </div>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button round @click="visibleModel = false">关闭</el-button>
        <el-button round type="primary" :loading="analysisLoading" @click="startMascotAnalysis">
          <el-icon><Refresh /></el-icon> 重新分析
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { MagicStick, Refresh } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'
import { useSiteConfig } from '@/composables/useSiteConfig'

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName, agentName } = useSiteConfig()

// 桌宠分析弹窗：AI 状态（loading/result）由父级 useAiAnalysis 实例持有（桌面分析图表区共用），
// 分析编排依赖（analyze/loadProfiles/buildPrompt）通过 props 注入，保证与父级同一份数据状态
const props = defineProps<{
  visible: boolean
  analysisResult: string
  analysisLoading: boolean
  analyze: (prompt: string, options?: { skipCache?: boolean; onStream?: (chunk: string) => void }) => Promise<void>
  loadProfiles: () => Promise<void>
  buildPrompt: () => string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const visibleModel = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})

const analysisLoadingText = ref(`${agentName.value}正在深度分析班级情况...`)

const renderedAnalysisHtml = computed(() => renderMarkdown(props.analysisResult))

// 首次打开时自动触发分析（与父级原 openMascotAnalysis 行为一致）
watch(() => props.visible, (open) => {
  if (open && !props.analysisResult && !props.analysisLoading) {
    startMascotAnalysis()
  }
})

/** 重新/开始分析 */
async function startMascotAnalysis() {
  if (props.analysisLoading) return
  analysisLoadingText.value = `${agentName.value}正在收集班级数据与学生成长记录...`
  await props.loadProfiles()
  analysisLoadingText.value = `${agentName.value}正在深度分析班级情况...`
  await props.analyze(props.buildPrompt(), { skipCache: true })
}
</script>

<style scoped>
/* 桌宠分析弹窗（自父级迁移） */
@keyframes mascot-pet-bounce {
  0%, 100% { transform: translateY(0) scale(1); }
  30% { transform: translateY(-8px) scale(1.04); }
  55% { transform: translateY(0) scale(1); }
  75% { transform: translateY(-4px) scale(1.02); }
}
.dialog-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dialog-header-mascot {
  width: 40px; height: 40px;
  object-fit: contain;
  filter: drop-shadow(0 2px 6px rgba(139, 92, 246, 0.35));
}
.dialog-header-text { display: flex; flex-direction: column; }
.dialog-title { font-size: 16px; font-weight: 700; color: #4c1d95; }
.dialog-sub { font-size: 11px; color: #7c3aed; margin-top: 2px; }
.dialog-content { min-height: 200px; }
.dialog-loading {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 36px 12px; gap: 14px;
}
.dialog-loading-mascot {
  width: 72px; height: 72px; object-fit: contain;
  animation: mascot-pet-bounce 1.4s ease-in-out infinite !important;
}
.dialog-loading-text { font-size: 13px; color: #7c3aed; margin: 0; }
.dialog-empty {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 36px 12px; gap: 10px;
  color: #9ca3af; font-size: 13px; margin: 0;
}
.dialog-empty-icon { font-size: 32px; color: #c4b5fd; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }

:deep(.mascot-analysis-dialog) {
  border-radius: 16px !important;
  background: linear-gradient(180deg, #faf7ff 0%, #ffffff 42%) !important;
}
:deep(.mascot-analysis-dialog .el-dialog__header) {
  padding-bottom: 6px;
  margin-right: 0;
}
:deep(.mascot-analysis-dialog .el-dialog__body) {
  padding-top: 4px;
}
:deep(.markdown-body) {
  font-size: 13px;
  line-height: 1.75;
  color: #374151;
}
:deep(.markdown-body .md-h2),
:deep(.markdown-body .md-h3) {
  font-size: 14px;
  color: #4c1d95;
  margin: 14px 0 6px;
  padding-left: 8px;
  border-left: 3px solid #8b5cf6;
}
:deep(.markdown-body .md-ul) {
  padding-left: 18px;
  margin: 6px 0;
}
:deep(.markdown-body .md-li) { margin: 3px 0; }
:deep(.markdown-body strong) { color: #4c1d95; }

:deep(.el-dialog) {
  width: 92vw !important;
  max-height: 80vh;
  margin: 0 auto !important;
  border-radius: 16px 16px 0 0 !important;
  position: fixed !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  top: auto !important;
}

:deep(.el-dialog__body) {
  max-height: 60vh;
  overflow-y: auto;
}
</style>