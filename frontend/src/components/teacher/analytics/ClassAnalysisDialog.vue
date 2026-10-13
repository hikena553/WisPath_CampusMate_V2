<template>
  <el-dialog
    v-model="visibleModel"
    class="mascot-analysis-dialog tui-dialog"
    :width="isMobile ? '90%' : '400px'"
    align-center
    :append-to-body="true"
    :close-on-click-modal="false"
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
      <!-- 引导提示：让老师知道正在分析谁、会发生什么 -->
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>正在基于班级图表与学生成长数据生成分析，内容由 {{ siteName }} 智能产出，仅供参考。</span>
      </div>
      <div v-if="analysisLoading" class="dialog-loading">
        <img :src="siteMascot" :alt="siteName" class="dialog-loading-mascot" />
        <p class="dialog-loading-text">{{ analysisLoadingText }}</p>
      </div>
      <div v-else-if="analysisResult" class="analysis-report markdown-body" v-html="renderedAnalysisHtml"></div>
      <div v-else class="tui-empty">
        <span class="tui-empty-icon"><el-icon :size="22"><MagicStick /></el-icon></span>
        <span class="tui-empty-title">尚未生成分析</span>
        <span class="tui-empty-desc">点击下方「重新分析」，{{ siteName }}将为您生成班级分析报告</span>
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
import { InfoFilled, MagicStick, Refresh } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useResponsive } from '@/composables/useResponsive'

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName, agentName } = useSiteConfig()
const { isMobile } = useResponsive()

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
  width: 34px; height: 34px;
  object-fit: contain;
}
.dialog-header-text { display: flex; flex-direction: column; }
.dialog-title { font-size: 15px; font-weight: 700; color: var(--tui-text); }
.dialog-sub { font-size: 11px; color: var(--tui-text-tertiary); margin-top: 2px; }
.dialog-content { min-height: 180px; }
.dialog-loading {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 28px 12px; gap: 12px;
}
.dialog-loading-mascot {
  width: 60px; height: 60px; object-fit: contain;
  animation: mascot-pet-bounce 1.4s ease-in-out infinite;
}
.dialog-loading-text { font-size: 12.5px; color: var(--tui-text-secondary); margin: 0; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }

/* 弹窗内空态：收紧尺寸，避免默认大留白 */
.dialog-content .tui-empty { padding: 24px 12px; gap: 8px; }
.dialog-content .tui-empty-icon { width: 46px; height: 46px; }

:deep(.mascot-analysis-dialog) {
  border-radius: var(--tui-radius) !important;
  background: var(--tui-surface) !important;
}
:deep(.mascot-analysis-dialog .el-dialog__header) {
  padding-bottom: 6px;
  margin-right: 0;
}
:deep(.mascot-analysis-dialog .el-dialog__body) {
  padding-top: 4px;
  max-height: 60vh;
  overflow-y: auto;
}
:deep(.markdown-body) {
  font-size: 13px;
  line-height: 1.75;
  color: var(--tui-text-secondary);
}
:deep(.markdown-body .md-h2),
:deep(.markdown-body .md-h3) {
  font-size: 14px;
  color: var(--tui-text);
  margin: 14px 0 6px;
  padding-left: 8px;
  border-left: 3px solid var(--tui-brand);
}
:deep(.markdown-body .md-ul) {
  padding-left: 18px;
  margin: 6px 0;
}
:deep(.markdown-body .md-li) { margin: 3px 0; }
:deep(.markdown-body strong) { color: var(--tui-brand-strong); }
</style>