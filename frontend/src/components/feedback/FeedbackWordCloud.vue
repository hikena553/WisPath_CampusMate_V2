<template>
  <div class="wordcloud-card">
    <div class="wc-header">
      <div class="wc-title-wrap">
        <span class="wc-icon"><el-icon><DataAnalysis /></el-icon></span>
        <div class="wc-title-text">
          <h3>反馈重点词云</h3>
          <span class="wc-sub">基于全部反馈标题与内容统计，词频越高字号越大</span>
        </div>
      </div>
      <div class="wc-tools">
        <span v-if="words.length" class="wc-total">{{ words.length }} 个热点词</span>
        <el-button text size="small" :loading="loading" @click="$emit('refresh')">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <div class="wc-body">
      <!-- 加载中且无数据：骨架屏 -->
      <el-skeleton v-if="loading && !words.length" :rows="3" animated class="wc-skeleton" />

      <!-- 词云主体：数据变化时通过 key 重挂载，重新播放错峰入场动画 -->
      <div v-else-if="words.length" class="wc-cloud" :key="cloudKey">
        <span
          v-for="(w, i) in words"
          :key="w.word"
          class="wc-word"
          :style="wordStyle(w, i)"
          :title="`${w.word}：出现 ${w.count} 次`"
        >{{ w.word }}</span>
      </div>

      <el-empty v-else description="暂无反馈数据，产生反馈后将在此展示热点词" :image-size="64" />
    </div>

    <div v-if="words.length" class="wc-foot">
      <span>最近刷新：{{ refreshedAt }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DataAnalysis, Refresh } from '@element-plus/icons-vue'
import type { FeedbackWord } from '@/api/feedback'

const props = defineProps<{
  words: FeedbackWord[]
  loading?: boolean
}>()

defineEmits<{ (e: 'refresh'): void }>()

const cloudKey = ref(0)
const refreshedAt = ref('')

// 数据刷新时重挂载，重新触发错峰入场动画（“动态”效果）
watch(
  () => props.words,
  (val) => {
    cloudKey.value++
    if (val.length) {
      const d = new Date()
      refreshedAt.value = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
    }
  }
)

const minCount = computed(() => (props.words.length ? Math.min(...props.words.map(w => w.count)) : 0))
const maxCount = computed(() => (props.words.length ? Math.max(...props.words.map(w => w.count)) : 0))

const PALETTE = ['#3b7cff', '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9254de', '#13c2c2', '#eb2f96']

function wordStyle(w: FeedbackWord, i: number) {
  const ratio = maxCount.value === minCount.value ? 0.5 : (w.count - minCount.value) / (maxCount.value - minCount.value)
  const size = Math.round(13 + ratio * 22 + (i % 3))
  return {
    fontSize: `${size}px`,
    color: PALETTE[i % PALETTE.length],
    '--rot': `${((i * 29) % 7) - 3}deg`,
    animationDelay: `${(i % 14) * 45}ms`
  } as Record<string, string>
}
</script>

<style scoped>
.wordcloud-card {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
  margin-bottom: 14px;
  padding: 14px 16px;
  transition: box-shadow 0.25s ease;
}

.wordcloud-card:hover {
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);
}

.wc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.wc-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.wc-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff, #3377ff);
  flex-shrink: 0;
}

.wc-icon .el-icon {
  font-size: 18px;
  color: #fff;
}

.wc-title-text h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #2b3245;
}

.wc-sub {
  font-size: 12px;
  color: #8a91a4;
}

.wc-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.wc-total {
  font-size: 12px;
  color: #8a91a4;
  background: #f4f6fa;
  border-radius: 999px;
  padding: 3px 10px;
  white-space: nowrap;
}

.wc-skeleton {
  padding: 12px 4px;
}

.wc-cloud {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px 12px;
  min-height: 120px;
  padding: 10px 6px;
}

.wc-word {
  --rot: 0deg;
  display: inline-block;
  padding: 4px 8px;
  line-height: 1.2;
  font-weight: 600;
  cursor: default;
  border-radius: 8px;
  opacity: 0;
  transform: scale(0.5);
  animation: wc-pop 0.45s cubic-bezier(0.34, 1.4, 0.64, 1) forwards;
  transition: transform 0.22s ease, box-shadow 0.22s ease, background 0.22s ease;
}

.wc-word:hover {
  transform: translateY(-2px) scale(1.18) rotate(var(--rot));
  box-shadow: 0 6px 16px rgba(16, 24, 40, 0.12);
  background: rgba(16, 24, 40, 0.04);
}

@keyframes wc-pop {
  from { opacity: 0; transform: scale(0.5); }
  to { opacity: 1; transform: scale(1); }
}

.wc-foot {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed #eef0f4;
  font-size: 12px;
  color: #a0a6b4;
  text-align: right;
}

/* 暗色适配 */
html.dark .wordcloud-card {
  background: #1e1e20;
  border-color: rgba(255, 255, 255, 0.08);
}

html.dark .wc-title-text h3 {
  color: #e8e8ea;
}

html.dark .wc-sub {
  color: #a0a0a8;
}

html.dark .wc-total {
  background: rgba(255, 255, 255, 0.06);
  color: #a0a0a8;
}

html.dark .wc-word:hover {
  background: rgba(255, 255, 255, 0.1);
}

html.dark .wc-foot {
  border-top-color: rgba(255, 255, 255, 0.1);
  color: #7c7c84;
}
</style>