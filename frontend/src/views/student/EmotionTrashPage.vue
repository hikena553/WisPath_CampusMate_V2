<template>
  <div class="emotion-page">
    <SubPageHeader title="情绪垃圾桶" fallback="/student" />
    <!-- 头部主视觉 -->
    <div class="emotion-hero">
      <div class="hero-glow g1"></div>
      <div class="hero-top">
        <div class="hero-title-wrap">
          <div class="hero-kicker">MOOD · 情绪垃圾桶</div>
          <h2 class="hero-title">把情绪倒进来，轻轻放下</h2>
          <p class="hero-sub">这里存放着你通话中流露的每一种情绪</p>
        </div>
      </div>
      <div class="hero-stats">
        <div class="hs-item">
          <span class="hs-num">{{ stats.total || 0 }}</span>
          <span class="hs-label">情绪记录</span>
        </div>
        <div class="hs-sep"></div>
        <div class="hs-item">
          <span class="hs-num">{{ dominantEmotionLabel || '--' }}</span>
          <span class="hs-label">近期主导</span>
        </div>
        <div class="hs-sep"></div>
        <div class="hs-item">
          <span class="hs-num">{{ positivePercent }}%</span>
          <span class="hs-label">正向占比</span>
        </div>
      </div>
    </div>

    <div class="content">
      <!-- 情绪分布 -->
      <div class="card">
        <div class="card-head">
          <span class="head-bar"></span>
          <span class="head-title">情绪画像</span>
          <span class="head-sub">近 30 天情绪构成</span>
        </div>
        <div v-if="stats.breakdown?.length" class="emotion-bars">
          <div v-for="b in breakdownDesc" :key="b.emotion" class="bar-row">
            <span class="bar-emoji">{{ emoji(b.emotion) }}</span>
            <span class="bar-label">{{ b.label }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: b.percent + '%', background: colorOf(b.emotion) }"></div>
            </div>
            <span class="bar-num">{{ b.count }}</span>
          </div>
        </div>
        <div v-else class="empty-block">
          <div class="empty-emoji">🗑️</div>
          <div class="empty-msg">还没有情绪记录<br />去语音通话并开启摄像头，绵小城会帮你收集今天的情绪</div>
        </div>
      </div>

      <!-- 情绪时间线 -->
      <div class="card">
        <div class="card-head">
          <span class="head-bar"></span>
          <span class="head-title">情绪流水</span>
          <el-button size="small" text type="danger" :disabled="!history.length" @click="handleClear">
            <el-icon style="margin-right:2px"><Delete /></el-icon>倒空
          </el-button>
        </div>
        <div v-if="history.length" class="emotion-list">
          <div v-for="r in history" :key="r.id" class="emo-item">
            <span class="emo-ico" :style="{ background: colorOf(r.emotion) + '22' }">{{ emoji(r.emotion) }}</span>
            <div class="emo-info">
              <div class="emo-name">{{ r.label }} <span class="emo-conf">{{ Math.round(r.confidence * 100) }}%</span></div>
              <div class="emo-time">{{ timeStr(r.created_at) }}</div>
            </div>
            <span class="emo-src">{{ r.source === 'voice_call' ? '通话' : '手动' }}</span>
          </div>
        </div>
        <div v-else class="empty-block">
          <div class="empty-emoji">🍃</div>
          <div class="empty-msg">记录为空，一切安好</div>
        </div>
      </div>

      <!-- 情绪周趋势 -->
      <div class="card" v-if="stats.trending?.length">
        <div class="card-head">
          <span class="head-bar"></span>
          <span class="head-title">周趋势</span>
        </div>
        <div class="trend-row">
          <div v-for="(t, i) in stats.trending" :key="i" class="trend-cell">
            <div class="trend-emoji">{{ emoji(t.emotion) }}</div>
            <div class="trend-label">{{ t.label }}</div>
            <div class="trend-week">周{{ weekOf(t.week) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { fetchEmotionStats, fetchEmotionHistory, clearEmotions, type EmotionStats, type EmotionRecordItem } from '@/api/emotion'

const stats = ref<EmotionStats>({ total: 0, breakdown: [], trending: [] })
const history = ref<EmotionRecordItem[]>([])

const emoji = (e: string) =>
  ({ neutral: '😐', happy: '😄', sad: '😢', angry: '😡', fearful: '😨', disgusted: '😖', surprised: '😲' }[e] ?? '🙂')

const colorOf = (e: string) =>
  ({ neutral: '#9aa6b8', happy: '#34b37a', sad: '#5b8def', angry: '#f56c6c', fearful: '#e6a23c', disgusted: '#a78bfa', surprised: '#409eff' }[e] ?? '#9aa6b8')

const POSITIVE = ['happy', 'surprised', 'neutral']

const breakdownDesc = computed(() => [...(stats.value.breakdown ?? [])].sort((a, b) => b.count - a.count))

const dominantEmotionLabel = computed(() => {
  const arr = stats.value.breakdown ?? []
  if (!arr.length) return ''
  return arr.reduce((a, b) => (b.count > a.count ? b : a)).label
})

const positivePercent = computed(() => {
  const arr = stats.value.breakdown ?? []
  const pos = arr.filter((b) => POSITIVE.includes(b.emotion)).reduce((s, b) => s + b.count, 0)
  return stats.value.total ? Math.round((pos / stats.value.total) * 100) : 0
})

function timeStr(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function weekOf(w: string): string {
  const m = w.split('-').map(Number)
  const date = new Date(2026, (m[0] || 1) - 1, m[1] || 1)
  const base = new Date(date.getFullYear(), 0, 1)
  return String(Math.floor((date.valueOf() - base.valueOf()) / 604800000) + 1)
}

async function loadAll() {
  try {
    const [s, h] = await Promise.all([
      fetchEmotionStats(30),
      fetchEmotionHistory(30, 100),
    ])
    stats.value = s
    history.value = h
  } catch {
    /* ignore */
  }
}

async function handleClear() {
  try {
    await ElMessageBox.confirm('确定要倒空情绪垃圾桶吗？历史情绪记录将被删除。', '倒空垃圾桶', {
      confirmButtonText: '确定倒空',
      cancelButtonText: '再想想',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await clearEmotions()
    ElMessage.success('已倒空情绪垃圾桶')
    await loadAll()
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  }
}

onMounted(loadAll)
</script>

<style scoped>
.emotion-page {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  background: #f6f9ff;
}

.emotion-hero {
  position: relative;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(140deg, #e57fe0 0%, #f472b6 40%, #f9709b 75%, #fb7d7d 100%);
  padding: 20px 20px 20px;
  border-radius: 0 0 28px 28px;
  box-shadow: 0 10px 30px rgba(244, 114, 182, 0.25);
}
.hero-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}
.hero-glow.g1 {
  width: 190px; height: 190px;
  background: radial-gradient(circle, rgba(255,255,255,0.2), transparent 62%);
  top: -80px; right: -40px;
}
.hero-top { display: flex; align-items: center; gap: 12px; }
.hero-back {
  width: 36px; height: 36px; border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; flex-shrink: 0;
}
.hero-title-wrap { text-align: left; }
.hero-kicker {
  font-size: 11px; letter-spacing: 1px;
  opacity: 0.85; font-weight: 600;
}
.hero-title { margin: 4px 0 2px; font-size: 20px; font-weight: 700; }
.hero-sub { font-size: 12px; opacity: 0.85; }

.hero-stats {
  display: flex; align-items: center;
  margin-top: 16px;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.24);
  border-radius: 16px;
  padding: 12px 8px;
  backdrop-filter: blur(6px);
}
.hs-item { flex: 1; text-align: center; }
.hs-num { display: block; font-size: 20px; font-weight: 700; line-height: 1.1; }
.hs-label { display: block; font-size: 11px; opacity: 0.85; margin-top: 2px; }
.hs-sep { width: 1px; height: 26px; background: rgba(255,255,255,0.3); }

.content { padding: 16px 16px 28px; }

.card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 2px 12px rgba(91, 120, 200, 0.06);
}
.card-head {
  display: flex; align-items: center;
  margin-bottom: 14px;
}
.head-bar {
  width: 4px; height: 16px; border-radius: 2px;
  background: linear-gradient(180deg, #f472b6, #f9709b);
  margin-right: 8px;
}
.head-title { font-size: 15px; font-weight: 700; color: #303133; }
.head-sub { font-size: 12px; color: #909399; margin-left: 8px; }

/* 情绪条 */
.emotion-bars { display: flex; flex-direction: column; gap: 10px; }
.bar-row { display: flex; align-items: center; gap: 8px; }
.bar-emoji { font-size: 18px; width: 24px; text-align: center; }
.bar-label { font-size: 13px; color: #606266; width: 56px; flex-shrink: 0; }
.bar-track {
  flex: 1; height: 8px; border-radius: 4px;
  background: #f0f2f5; overflow: hidden;
}
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.bar-num { font-size: 13px; color: #909399; width: 24px; text-align: right; }

/* 清单 */
.emotion-list { display: flex; flex-direction: column; gap: 8px; }
.emo-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px;
  border-radius: 12px;
  background: #fafbfe;
}
.emo-ico {
  width: 38px; height: 38px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
}
.emo-info { flex: 1; }
.emo-name { font-size: 14px; font-weight: 600; color: #303133; }
.emo-conf { font-size: 11px; color: #909399; font-weight: 400; }
.emo-time { font-size: 12px; color: #a5adbb; margin-top: 2px; }
.emo-src {
  font-size: 11px; color: #7c5cff;
  background: #f1edff; border-radius: 8px;
  padding: 2px 8px; flex-shrink: 0;
}

/* 趋势 */
.trend-row { display: flex; gap: 8px; padding: 4px 0; }
.trend-cell {
  flex: 1; border-radius: 12px;
  background: #fafbfe; padding: 10px 4px;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
}
.trend-emoji { font-size: 24px; }
.trend-label { font-size: 12px; font-weight: 600; color: #303133; }
.trend-week { font-size: 10px; color: #a5adbb; }

/* 空态 */
.empty-block {
  text-align: center; padding: 30px 0;
}
.empty-emoji { font-size: 42px; margin-bottom: 8px; }
.empty-msg { font-size: 13px; color: #a5adbb; line-height: 1.7; }
</style>