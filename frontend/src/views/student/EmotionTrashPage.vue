<template>
  <div
    class="emotion-page"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="情绪树洞" fallback="/student" />
    <!-- 移动端下拉刷新：指示器放在吸顶头之后，头部保持不动 -->
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <!-- 头部主视觉 -->
    <div class="emotion-hero">
      <div class="hero-glow g1"></div>
      <div class="hero-top">
        <div class="hero-title-wrap">
          <div class="hero-kicker">MOOD · 情绪树洞</div>
          <h2 class="hero-title">把情绪说出来，轻轻放下</h2>
          <p class="hero-sub">这里存放着你通话中流露的情绪，也可以向辅导员求助</p>
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
      <!-- 求助辅导员：学生有问题 / 求助 → 辅导员一对一查看并帮扶 -->
      <div class="card help-card">
        <div class="card-head">
          <span class="head-bar help-bar"></span>
          <span class="head-title">求助辅导员</span>
          <span class="head-sub">有困难，找老师</span>
          <el-button size="small" text type="primary" class="help-add" @click="openHelp">
            <el-icon style="margin-right:2px"><ChatDotRound /></el-icon>发起求助
          </el-button>
        </div>
        <p class="help-tip">把困扰写下来，你的辅导员会一对一查看并回复；可匿名提交，也可留下身份方便老师找到你。</p>
        <div v-if="helpList.length" class="help-list">
          <div v-for="h in helpList" :key="h.id" class="help-item">
            <div class="help-top">
              <span class="help-cat">{{ HELP_CATEGORY_LABEL[h.category] }}</span>
              <span class="help-status" :class="`st-${h.status}`">{{ HELP_STATUS_LABEL[h.status] }}</span>
              <span class="help-time">{{ timeStr(h.created_at) }}</span>
            </div>
            <div class="help-content">{{ h.content }}</div>
            <div v-if="h.reply" class="help-reply">
              <span class="help-reply-label">{{ h.teacher_name || '辅导员' }}回复</span>
              <span class="help-reply-text">{{ h.reply }}</span>
            </div>
            <div v-else class="help-wait">等待辅导员查看…</div>
          </div>
        </div>
        <div v-else class="help-empty">还没有发起过求助。遇到学业、生活或情绪上的难题，都可以告诉辅导员。</div>
      </div>

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
          <div class="empty-msg">还没有情绪记录<br />去语音通话并开启摄像头，{{ agentName }}会帮你收集今天的情绪</div>
        </div>
      </div>

      <!-- 情绪时间线 -->
      <div class="card">
        <div class="card-head">
          <span class="head-bar"></span>
          <span class="head-title">情绪流水</span>
          <el-button size="small" text type="danger" :disabled="!history.length" @click="handleClear">
            <el-icon style="margin-right:2px"><Delete /></el-icon>清空
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

    <!-- 发起求助弹窗 -->
    <!-- 求助辅导员（2 字段：移动端=底部动作面板） -->
    <ActionSheet
      v-model="helpVisible"
      title="求助辅导员"
      width="440px"
      class="help-dialog"
    >
      <div class="help-form">
        <div class="help-field">
          <span class="help-label">求助类型</span>
          <div class="help-cats">
            <button
              v-for="c in HELP_CATEGORIES"
              :key="c.value"
              type="button"
              class="help-cat-btn"
              :class="{ on: helpForm.category === c.value }"
              @click="helpForm.category = c.value"
            >{{ c.label }}</button>
          </div>
        </div>
        <div class="help-field">
          <span class="help-label">求助内容<span class="req">*</span></span>
          <el-input
            v-model="helpForm.content"
            type="textarea"
            :rows="5"
            maxlength="1000"
            show-word-limit
            placeholder="说说你遇到的困难，或需要老师帮忙的地方……"
          />
        </div>
        <div class="help-field help-anon">
          <div class="help-anon-info">
            <span class="help-label">匿名提交</span>
            <p class="help-anon-tip">开启后老师看不到你的姓名，但仍可回复你</p>
          </div>
          <el-switch v-model="helpForm.anonymous" />
        </div>
      </div>
      <template #footer>
        <el-button @click="helpVisible = false">取消</el-button>
        <el-button type="primary" :loading="helpSaving" :disabled="!helpForm.content.trim()" @click="submitHelp">提交求助</el-button>
      </template>
    </ActionSheet>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
// v6.1 弹窗减负：求助小表单与清空确认走底部动作面板
import ActionSheet from '@/components/common/ActionSheet.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { ElMessage } from 'element-plus'
import { Delete, ChatDotRound } from '@element-plus/icons-vue'
import { fetchEmotionStats, fetchEmotionHistory, clearEmotions, type EmotionStats, type EmotionRecordItem } from '@/api/emotion'
import {
  createHelpRequest, fetchMyHelpRequests,
  HELP_CATEGORY_LABEL, HELP_STATUS_LABEL,
  type HelpRequest, type HelpCategory,
} from '@/api/helpRequest'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useResponsive } from '@/composables/useResponsive'
import { usePullRefresh } from '@/composables/usePullRefresh'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'

// AI 助手称谓取自站点配置（管理端「自我称谓」）
const { agentName } = useSiteConfig()

const stats = ref<EmotionStats>({ total: 0, breakdown: [], trending: [] })
const history = ref<EmotionRecordItem[]>([])

/* ===== 求助辅导员：学生发起 → 辅导员回复 ===== */
const HELP_CATEGORIES: { value: HelpCategory; label: string }[] = [
  { value: 'academic', label: '学业困扰' },
  { value: 'life', label: '生活困难' },
  { value: 'mental', label: '心理情绪' },
  { value: 'relation', label: '人际关系' },
  { value: 'other', label: '其他' },
]
const helpList = ref<HelpRequest[]>([])
const helpVisible = ref(false)
const helpSaving = ref(false)
const helpForm = ref<{ category: HelpCategory; content: string; anonymous: boolean }>({
  category: 'academic',
  content: '',
  anonymous: false,
})

function openHelp() {
  helpForm.value = { category: 'academic', content: '', anonymous: false }
  helpVisible.value = true
}

async function submitHelp() {
  if (!helpForm.value.content.trim()) return
  helpSaving.value = true
  try {
    await createHelpRequest({
      category: helpForm.value.category,
      content: helpForm.value.content.trim(),
      anonymous: helpForm.value.anonymous,
    })
    ElMessage.success('求助已提交，辅导员会尽快查看')
    helpVisible.value = false
    await loadHelp()
  } catch {
    ElMessage.error('提交失败，请稍后再试')
  } finally {
    helpSaving.value = false
  }
}

async function loadHelp() {
  try {
    helpList.value = await fetchMyHelpRequests()
  } catch {
    /* ignore */
  }
}

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
  await loadHelp()
}

async function handleClear() {
  if (!(await actionConfirm('确定要清空情绪记录吗？历史情绪记录将被删除。', '清空记录', { danger: true, confirmButtonText: '确定清空', cancelButtonText: '再想想' }))) return
  try {
    await clearEmotions()
    ElMessage.success('已清空情绪记录')
    await loadAll()
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  }
}

onMounted(loadAll)

// 下拉刷新（移动端）：复用树洞数据加载，失败静默
async function refreshAll() {
  await loadAll()
}

const { isMobile } = useResponsive()
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })
</script>

<style scoped>
.emotion-page {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  background: #f6f9ff;
  /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
  overscroll-behavior-y: contain;
}

/* 移动端：整屏覆盖子页（与资讯搜索/详情子页同一形式）——
   滑入/滑出时连顶栏与底部导航一起盖住，返回走页面顶部的 SubPageHeader。
   z-index 1500：盖过顶栏(100)/底部导航(1000)，低于 Element Plus 弹层基准(2000+)。 */
@media (max-width: 767px) {
  .emotion-page {
    position: fixed;
    inset: 0;
    z-index: 1500;
  }
  .emotion-page > .tui-appbar {
    position: sticky;
    top: 0;
    z-index: 5;
  }
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

/* ===== 求助辅导员 ===== */
.help-bar { background: linear-gradient(180deg, #5b8def, #7c5cff); }
.help-add { margin-left: auto; font-weight: 600; }
.help-tip { margin: 0 0 12px; font-size: 12px; color: #909399; line-height: 1.6; }
.help-list { display: flex; flex-direction: column; gap: 10px; }
.help-item {
  border: 1px solid #eef1f6;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fafbfe;
}
.help-top { display: flex; align-items: center; gap: 8px; }
.help-cat {
  font-size: 11px; font-weight: 600; color: #5b8def;
  background: #eaf1ff; border-radius: 8px; padding: 2px 8px;
}
.help-status {
  font-size: 11px; font-weight: 600; border-radius: 8px; padding: 2px 8px;
}
.help-status.st-pending { color: #e6a23c; background: #fdf3e2; }
.help-status.st-processing { color: #409eff; background: #e8f3ff; }
.help-status.st-resolved { color: #34b37a; background: #e6f6ee; }
.help-time { margin-left: auto; font-size: 11px; color: #a5adbb; }
.help-content {
  margin-top: 8px; font-size: 13px; color: #303133;
  line-height: 1.6; white-space: pre-wrap; word-break: break-word;
}
.help-reply {
  margin-top: 8px; padding: 8px 10px; border-radius: 10px;
  background: #eef4ff; border-left: 3px solid #5b8def;
}
.help-reply-label { display: block; font-size: 11px; font-weight: 700; color: #5b8def; margin-bottom: 3px; }
.help-reply-text { font-size: 12.5px; color: #4a5568; line-height: 1.6; white-space: pre-wrap; }
.help-wait { margin-top: 8px; font-size: 12px; color: #a5adbb; }
.help-empty {
  text-align: center; font-size: 12.5px; color: #a5adbb;
  line-height: 1.7; padding: 14px 8px;
}

/* 求助弹窗 */
.help-form { display: flex; flex-direction: column; gap: 16px; }
.help-field { display: flex; flex-direction: column; gap: 8px; }
.help-label { font-size: 13px; font-weight: 600; color: #303133; }
.help-label .req { color: #f56c6c; margin-left: 2px; }
.help-cats { display: flex; flex-wrap: wrap; gap: 8px; }
.help-cat-btn {
  font-family: inherit; font-size: 12.5px; color: #606266;
  padding: 6px 14px; border-radius: 999px;
  border: 1px solid #e4e7ed; background: #fff; cursor: pointer;
  transition: all 0.15s ease;
}
.help-cat-btn.on {
  color: #5b8def; border-color: #5b8def;
  background: #eaf1ff; font-weight: 600;
}
.help-anon { flex-direction: row; align-items: center; justify-content: space-between; }
.help-anon-info { display: flex; flex-direction: column; gap: 3px; }
.help-anon-tip { margin: 0; font-size: 11.5px; color: #a5adbb; }
</style>