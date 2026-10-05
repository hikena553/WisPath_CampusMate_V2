<template>
  <div class="sr-panel">
    <!-- 概览 -->
    <div class="sr-overall">
      <div class="sr-overall-num">
        <template v-if="result.enough_sample && result.overall_average !== null">
          {{ result.overall_average.toFixed(1) }}
        </template>
        <template v-else>—</template>
        <small>/ 5.0</small>
      </div>
      <div class="sr-overall-meta">
        <span class="sr-count">有效样本 {{ result.response_count }} 份</span>
        <el-tag v-if="result.enough_sample" size="small" type="success" effect="plain" round>样本充足</el-tag>
        <el-tag v-else size="small" type="warning" effect="plain" round>样本不足</el-tag>
      </div>
    </div>

    <!-- 匿名保护提示 -->
    <div v-if="!result.enough_sample" class="sr-guard">
      <el-icon><Lock /></el-icon>
      <span>为保证匿名性，样本少于 {{ result.min_sample }} 份时不展示分布与建议</span>
    </div>

    <!-- 维度分布 -->
    <div class="sr-questions">
      <div v-for="q in result.questions" :key="q.key" class="sr-q">
        <div class="sr-q-head">
          <span class="sr-q-label">{{ q.label }}</span>
          <span class="sr-q-avg">
            {{ q.average !== null ? q.average.toFixed(1) : '—' }}
          </span>
        </div>
        <div class="sr-bar">
          <span class="sr-bar-fill" :style="{ width: barWidth(q.average) }"></span>
        </div>
        <div v-if="result.enough_sample && Object.keys(q.distribution).length" class="sr-dist">
          <span v-for="(n, score) in q.distribution" :key="score" class="sr-dist-chip">
            {{ score }} 分 · {{ n }}
          </span>
        </div>
      </div>
    </div>

    <!-- 匿名建议 -->
    <div v-if="result.enough_sample" class="sr-suggest">
      <div class="sr-suggest-title">匿名建议（{{ result.suggestions.length }}）</div>
      <div v-if="!result.suggestions.length" class="sr-suggest-empty">暂无文字建议</div>
      <div v-for="(s, i) in result.suggestions" :key="i" class="sr-suggest-item">
        <span class="sr-quote">“</span>{{ s }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Lock } from '@element-plus/icons-vue'
import type { PeerSurveyResult } from '@/api/peerSurvey'

defineProps<{ result: PeerSurveyResult }>()

function barWidth(avg: number | null) {
  if (avg === null) return '0%'
  return `${Math.max(0, Math.min(100, (avg / 5) * 100))}%`
}
</script>

<style scoped>
.sr-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sr-overall {
  display: flex;
  align-items: center;
  gap: 14px;
  background: #f9fafb;
  border-radius: 12px;
  padding: 12px 16px;
}
.sr-overall-num {
  font-size: 28px;
  font-weight: 700;
  color: #101828;
  line-height: 1;
}
.sr-overall-num small {
  font-size: 12px;
  font-weight: 400;
  color: #98a2b3;
  margin-left: 3px;
}
.sr-overall-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sr-count {
  font-size: 12.5px;
  color: #667085;
}

.sr-guard {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  color: #b54708;
  background: #fffaeb;
  border-radius: 10px;
  padding: 9px 12px;
}

.sr-questions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sr-q-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 5px;
}
.sr-q-label {
  font-size: 13px;
  color: #344054;
}
.sr-q-avg {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
}
.sr-bar {
  height: 8px;
  border-radius: 999px;
  background: #f2f4f7;
  overflow: hidden;
}
.sr-bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #5b8def, #2563eb);
  transition: width 0.4s ease;
}
.sr-dist {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}
.sr-dist-chip {
  font-size: 11px;
  color: #667085;
  background: #f2f4f7;
  border-radius: 999px;
  padding: 2px 8px;
}

.sr-suggest {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sr-suggest-title {
  font-size: 13px;
  font-weight: 600;
  color: #101828;
}
.sr-suggest-empty {
  font-size: 12.5px;
  color: #98a2b3;
}
.sr-suggest-item {
  font-size: 12.5px;
  color: #475467;
  line-height: 1.6;
  background: #fcfcfd;
  border-left: 2px solid #d0d5dd;
  padding: 7px 11px;
  border-radius: 0 8px 8px 0;
}
.sr-quote {
  color: #98a2b3;
  margin-right: 2px;
}
</style>