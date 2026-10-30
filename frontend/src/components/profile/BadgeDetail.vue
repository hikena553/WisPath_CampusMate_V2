<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { Close, ArrowLeft } from '@element-plus/icons-vue'
import BadgeMedal from './BadgeMedal.vue'
import type { BadgeItem, BadgeTier } from '@/api/badge'
import { useResponsive } from '@/composables/useResponsive'

/**
 * 勋章放大查看：点击任何勋章后浮起的独立查看层，
 * 只做「看」这一件事 —— 大尺寸勋章 + 名称 + 说明 + 获得时间/解锁进度。
 * v6 弹窗重设计：桌面端保持居中卡片浮层；移动端改为全屏子页（返回栏 + 内容），不再用遮罩弹窗。
 */
const props = defineProps<{ badge: BadgeItem | null }>()
const emit = defineEmits<{ (e: 'close'): void }>()
const { isMobile } = useResponsive()

const TIER_LABEL: Record<BadgeTier, string> = {
  bronze: '铜质勋章',
  silver: '银质勋章',
  gold: '金质勋章',
  diamond: '钻石勋章',
}

const tierLabel = computed(() => (props.badge ? TIER_LABEL[props.badge.tier] : ''))
const awardedDate = computed(() => {
  const raw = props.badge?.awarded_at
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.badge) emit('close')
}
watch(() => props.badge, (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
}, { immediate: true })
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <!-- 桌面端：居中卡片浮层 -->
    <Transition name="bd-fade">
      <div v-if="badge && !isMobile" class="bd-mask" @click.self="emit('close')">
        <div class="bd-panel" role="dialog" :aria-label="badge.name">
          <button type="button" class="bd-close" aria-label="关闭" @click="emit('close')">
            <el-icon :size="15"><Close /></el-icon>
          </button>

          <div class="bd-stage" :class="[`tier-${badge.tier}`, { 'is-locked': !badge.earned }]">
            <BadgeMedal :icon="badge.icon" :tier="badge.tier" :earned="badge.earned" :size="116" />
          </div>

          <span class="bd-tier">{{ tierLabel }}</span>
          <h3 class="bd-name">{{ badge.name }}</h3>
          <p class="bd-desc">{{ badge.desc }}</p>

          <div v-if="badge.earned" class="bd-status">
            已获得<template v-if="awardedDate"> · {{ awardedDate }}</template>
          </div>
          <div v-else class="bd-progress">
            <div class="bd-progress-head">
              <span>{{ badge.target_label }}</span>
              <b>{{ badge.progress }}%</b>
            </div>
            <div class="bd-track"><i :style="{ width: badge.progress + '%' }"></i></div>
            <p class="bd-tip">继续积累成长值即可点亮这枚勋章</p>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 移动端：全屏子页承接（与 ResponsivePopup 同一交互范式） -->
    <Transition name="bd-sheet">
      <div v-if="badge && isMobile" class="bdm-page" role="dialog" :aria-label="badge.name">
        <header class="bdm-appbar">
          <button type="button" class="bdm-back" aria-label="返回" @click="emit('close')">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <div class="bdm-title">勋章详情</div>
        </header>
        <div class="bdm-body">
          <div class="bd-stage bd-stage-m" :class="[`tier-${badge.tier}`, { 'is-locked': !badge.earned }]">
            <BadgeMedal :icon="badge.icon" :tier="badge.tier" :earned="badge.earned" :size="128" />
          </div>
          <div class="bdm-card">
            <span class="bd-tier">{{ tierLabel }}</span>
            <h3 class="bd-name">{{ badge.name }}</h3>
            <p class="bd-desc">{{ badge.desc }}</p>
            <div v-if="badge.earned" class="bd-status">
              已获得<template v-if="awardedDate"> · {{ awardedDate }}</template>
            </div>
            <div v-else class="bd-progress">
              <div class="bd-progress-head">
                <span>{{ badge.target_label }}</span>
                <b>{{ badge.progress }}%</b>
              </div>
              <div class="bd-track"><i :style="{ width: badge.progress + '%' }"></i></div>
              <p class="bd-tip">继续积累成长值即可点亮这枚勋章</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.bd-mask {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 20, 24, 0.46);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.bd-panel {
  position: relative;
  width: min(84vw, 320px);
  padding: 30px 24px 22px;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(17, 20, 24, 0.24);
  text-align: center;
}
.bd-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 10px;
  background: #f4f5f7;
  color: #6b7280;
  cursor: pointer;
}
.bd-close:active { background: #eceef1; }

.bd-stage {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  margin-bottom: 10px;
  padding: 10px 0 4px;
}
/* 等级光晕：勋章背后一层同色柔光，不做圆形描边，只做氛围 */
.bd-stage::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 190px;
  height: 190px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(circle, var(--stage-glow) 0%, rgba(255, 255, 255, 0) 68%);
  pointer-events: none;
}
.bd-stage.is-locked::before { display: none; }
.bd-stage.tier-bronze { --stage-glow: rgba(217, 154, 85, 0.2); }
.bd-stage.tier-silver { --stage-glow: rgba(160, 176, 192, 0.22); }
.bd-stage.tier-gold { --stage-glow: rgba(247, 210, 97, 0.26); }
.bd-stage.tier-diamond { --stage-glow: rgba(117, 205, 235, 0.26); }
.bd-tier {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  background: #f4f5f7;
  color: #7b8492;
  font-size: 10.5px;
  letter-spacing: 0.3px;
}
.bd-name {
  margin: 8px 0 6px;
  font-size: 19px;
  font-weight: 700;
  color: #1f2430;
}
.bd-desc {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #667085;
}
.bd-status {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
  font-size: 11.5px;
  color: #8b929e;
  font-variant-numeric: tabular-nums;
}
.bd-progress { margin-top: 16px; }
.bd-progress-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 11.5px;
  color: #667085;
}
.bd-progress-head b { font-size: 12px; color: #1f2430; font-variant-numeric: tabular-nums; }
.bd-track {
  height: 5px;
  margin-top: 7px;
  border-radius: 999px;
  background: #f0f2f5;
  overflow: hidden;
}
.bd-track i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #9aa4b2;
  transition: width 0.4s ease;
}
.bd-tip {
  margin: 9px 0 0;
  font-size: 10.5px;
  color: #98a2b3;
}

.bd-fade-enter-active, .bd-fade-leave-active { transition: opacity 0.2s ease; }
.bd-fade-enter-active .bd-panel, .bd-fade-leave-active .bd-panel { transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1); }
.bd-fade-enter-from, .bd-fade-leave-to { opacity: 0; }
.bd-fade-enter-from .bd-panel, .bd-fade-leave-to .bd-panel { transform: scale(0.94) translateY(6px); }

/* ===== 移动端：全屏子页 ===== */
.bdm-page {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  background: #f7f8fa;
  overflow: hidden;
}
.bdm-appbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 48px;
  min-height: 48px;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid #e9ebee;
}
.bdm-back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  margin-left: -4px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #1f2430;
}
.bdm-back:active { background: rgba(20, 23, 26, 0.06); }
.bdm-title { font-size: 15px; font-weight: 600; color: #1f2430; }
.bdm-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 28px 16px 32px;
}
/* 移动端舞台：白卡内呈现，光晕随卡片走 */
.bd-stage-m {
  background: #fff;
  border-radius: 20px;
  padding: 26px 0 10px;
  border: 1px solid #eef0f4;
}
.bdm-card {
  margin-top: 12px;
  background: #fff;
  border-radius: 20px;
  border: 1px solid #eef0f4;
  padding: 20px 18px 18px;
  text-align: center;
}
.bdm-card .bd-name { margin-top: 10px; }
.bdm-card .bd-status { margin-top: 16px; }

.bd-sheet-enter-active, .bd-sheet-leave-active { transition: transform 0.3s cubic-bezier(0.32, 0.72, 0.32, 1); }
.bd-sheet-enter-from, .bd-sheet-leave-to { transform: translateY(100%); }
</style>
