<template>
  <div class="growth-dashboard">
    <!-- 卡1：成长指数概览 -->
    <section class="gd-card" v-loading="loadingOverview">
      <div class="gd-head">
        <div class="gd-title-block">
          <div class="gd-title">
            <span class="gd-logo"><el-icon :size="15"><TrendCharts /></el-icon></span>
            <span>AI 成长驾驶舱</span>
          </div>
          <div class="gd-sub">看看我现在处于什么阶段</div>
        </div>
        <span class="gd-chip"><span class="ai-dot"></span> AI 为你服务</span>
      </div>

      <div class="gd-body">
        <!-- 成长指数环形 -->
        <div class="growth-ring-wrap">
          <svg class="growth-ring" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="#eef2f8" stroke-width="12" />
            <circle
              cx="60" cy="60" r="52" fill="none"
              stroke="url(#gdGrad)" stroke-width="12" stroke-linecap="round"
              :stroke-dasharray="`${(score / 100) * 326.7} 326.7`"
              transform="rotate(-90 60 60)"
            />
            <defs>
              <linearGradient id="gdGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#4f8cff" />
                <stop offset="100%" stop-color="#22d3ac" />
              </linearGradient>
            </defs>
          </svg>
          <div class="growth-ring-center">
            <div class="growth-score">{{ score }}</div>
            <div class="growth-score-label">成长指数</div>
          </div>
        </div>

        <!-- 五维 -->
        <div class="growth-radar">
          <div class="radar-item" v-for="d in radarDims" :key="d.name">
            <div class="radar-row">
              <span class="radar-name">{{ d.name }}</span>
              <span class="radar-val">{{ Math.round(d.value) }}</span>
            </div>
            <div class="radar-track"><div class="radar-fill" :style="{ width: d.value + '%', background: d.color }"></div></div>
          </div>
        </div>
      </div>

      <!-- 成长统计 -->
      <div class="growth-stats">
        <div class="stat-cell" @click="go('/student/workbench')">
          <b>{{ profile?.total_records ?? 0 }}</b><span>成长记录</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-cell" @click="go('/student/workbench')">
          <b>{{ profile?.total_skills ?? 0 }}</b><span>技能素养</span>
        </div>
      </div>
    </section>

    <!-- 卡2：我的学业（驾驶舱内置功能区：课程表 / 成绩分析 / 成长轨迹） -->
    <section class="gd-card">
      <div class="gd-section-head">
        <span class="gd-section-dot"></span>
        <span>我的学业</span>
        <span class="gd-section-sub">学习数据 · 一键直达</span>
      </div>
      <div class="gd-academic-list">
        <div class="gd-academic-item" @click="emit('open', 'schedule')">
          <div class="gd-academic-icon" style="background:#eaf3ff;color:#409eff"><el-icon :size="18"><Calendar /></el-icon></div>
          <div class="gd-academic-info">
            <b>课程表</b><span>本周教学安排 · 节次与教室</span>
          </div>
          <el-icon class="gd-academic-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="gd-academic-item" @click="emit('open', 'grades')">
          <div class="gd-academic-icon" style="background:#eaf7e8;color:#67c23a"><el-icon :size="18"><DataLine /></el-icon></div>
          <div class="gd-academic-info">
            <b>成绩分析</b><span>绩点趋势 · 课程画像 · 学期明细</span>
          </div>
          <el-icon class="gd-academic-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="gd-academic-item" @click="emit('open', 'growth')">
          <div class="gd-academic-icon" style="background:#f1edff;color:#7c5cff"><el-icon :size="18"><TrendCharts /></el-icon></div>
          <div class="gd-academic-info">
            <b>成长轨迹</b><span>成长档案 · 综合评分 · 项目经历</span>
          </div>
          <el-icon class="gd-academic-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </section>

    <!-- 卡3：快捷空间 -->
    <section class="gd-card">
      <div class="gd-section-head">
        <span class="gd-section-dot"></span>
        <span>快捷空间</span>
        <span class="gd-section-sub">常用服务 · 快速进入</span>
      </div>
      <div class="space-grid">
        <div class="space-card" @click="go('/student/plan')">
          <el-icon class="space-icon space-icon-blue"><Calendar /></el-icon>
          <div><b>学习计划</b><span>阶段目标 · 任务打卡</span></div>
        </div>
        <div class="space-card" @click="go('/student/portfolio')">
          <el-icon class="space-icon space-icon-green"><Collection /></el-icon>
          <div><b>我的作品集</b><span>项目 · 证书 · 简历</span></div>
        </div>
        <div class="space-card" @click="go('/student/growth')">
          <el-icon class="space-icon space-icon-violet"><TrendCharts /></el-icon>
          <div><b>成长档案</b><span>综合评分 · 成长记录</span></div>
        </div>
        <div class="space-card" @click="go('/student/agent')">
          <el-icon class="space-icon space-icon-orange"><ChatDotRound /></el-icon>
          <div><b>AI 导师</b><span>学习 / 成长答疑</span></div>
        </div>
      </div>
    </section>

    <!-- 卡4：AI 主动发现 -->
    <section class="gd-card">
      <div class="ai-discover-header">
        <span class="ai-discover-title">
          <el-icon class="ai-discover-icon"><MagicStick /></el-icon>
          AI 主动发现
        </span>
        <el-button size="small" text circle :loading="discoverLoading" @click="loadDiscover">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
      <div v-if="!discoverLoading && proactiveActions.length === 0" class="ai-discover-empty">
        <el-icon class="ai-empty-icon"><CircleCheckFilled /></el-icon>
        <span>状态良好，AI 持续守护你的成长</span>
      </div>
      <div v-for="act in proactiveActions" :key="act.trigger + '-' + act.student_id" class="ai-action-item">
        <el-tag :type="actionTag(act.priority)" size="small" effect="dark" class="ai-action-tag">
          {{ actionLabel(act.priority) }}
        </el-tag>
        <div class="ai-action-body">
          <div class="ai-action-title">{{ act.title }}</div>
          <div class="ai-action-content">{{ act.content }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  TrendCharts, Collection, ChatDotRound, MagicStick, Refresh,
  CircleCheckFilled, Calendar, DataLine, ArrowRight
} from '@element-plus/icons-vue'
import { getGrowthProfile, type GrowthProfile } from '@/api/growth'
import { fetchProactiveActions, type ProactiveAction } from '@/api/agent'

const emit = defineEmits<{ (e: 'open', tab: 'schedule' | 'grades' | 'growth'): void }>()
const router = useRouter()
const loadingOverview = ref(false)
const discoverLoading = ref(false)
const profile = ref<GrowthProfile | null>(null)
const proactiveActions = ref<ProactiveAction[]>([])

const score = computed(() => profile.value?.total_score ?? 0)
const radarDims = computed(() => {
  const src = profile.value?.radar ?? []
  const palette = ['#4f8cff', '#22d3ac', '#a78bfa', '#f59e0b', '#f472b6']
  return src.map((d, i) => ({ name: d.name, value: d.value, color: palette[i % palette.length] }))
})

function go(p: string) { router.push(p) }
function actionTag(p: number) { return p >= 80 ? 'danger' : p >= 60 ? 'warning' : 'primary' }
function actionLabel(p: number) { return p >= 80 ? '重点关注' : p >= 60 ? '值得关注' : '温馨提醒' }

async function loadOverview() {
  loadingOverview.value = true
  try { profile.value = await getGrowthProfile() } catch { /* ignore */ }
  finally { loadingOverview.value = false }
}

async function loadDiscover() {
  discoverLoading.value = true
  try {
    const all = await fetchProactiveActions()
    proactiveActions.value = all.filter(a => a.target_role === 'student')
  } catch { proactiveActions.value = [] }
  finally { discoverLoading.value = false }
}

onMounted(() => { loadOverview(); loadDiscover() })
</script>

<style scoped>
.growth-dashboard {
  width: 100%;
  display: flex; flex-direction: column; gap: 14px;
}

/* ===== 统一卡片 ===== */
.gd-card {
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 16px; padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* ===== 卡1：成长指数概览 ===== */
.gd-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 16px; }
.gd-title { display: flex; align-items: center; gap: 8px; font-size: 15.5px; font-weight: 800; color: #1a1a2e; }
.gd-title-block { min-width: 0; }
.gd-logo {
  width: 28px; height: 28px; border-radius: 9px; background: #eaf3ff;
  display: flex; align-items: center; justify-content: center; color: #409eff;
  flex-shrink: 0;
}
.gd-sub { font-size: 11.5px; color: #999999; margin-top: 5px; }
.gd-chip {
  font-size: 10px; font-weight: 600; background: #f0f6ff; color: #409eff;
  padding: 4px 10px; border-radius: 20px; display: flex; align-items: center; gap: 5px;
  border: 1px solid rgba(64,158,255,0.18); flex-shrink: 0; margin-top: 7px;
}
.ai-dot { width: 6px; height: 6px; border-radius: 50%; background: #10b981; animation: aiPulse 1.6s infinite; }
@keyframes aiPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

.gd-body { display: flex; align-items: center; gap: 18px; margin-bottom: 16px; }
.growth-ring-wrap { position: relative; width: 104px; height: 104px; flex-shrink: 0; }
.growth-ring { width: 104px; height: 104px; }
.growth-ring-center {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.growth-score { font-size: 26px; font-weight: 800; line-height: 1; color: #1a1a2e; }
.growth-score-label { font-size: 10px; color: #999999; margin-top: 3px; }
.growth-radar { flex: 1; min-width: 0; }
.radar-item { margin-bottom: 10px; }
.radar-item:last-child { margin-bottom: 0; }
.radar-row { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; color: #666666; }
.radar-val { color: #1a1a2e; font-weight: 600; }
.radar-track { height: 6px; background: #eef2f8; border-radius: 4px; overflow: hidden; }
.radar-fill { height: 100%; border-radius: 4px; transition: width 0.6s; }

.growth-stats {
  display: flex; align-items: center; background: #f8f9fc;
  border: 1px solid rgba(0,0,0,0.04); border-radius: 12px; padding: 12px 0;
}
.stat-cell { flex: 1; display: flex; flex-direction: column; align-items: center; cursor: pointer; }
.stat-cell b { font-size: 17px; margin-bottom: 2px; color: #1a1a2e; }
.stat-cell span { font-size: 10.5px; color: #999999; }
.stat-divider { width: 1px; height: 22px; background: rgba(0,0,0,0.07); flex-shrink: 0; }

/* ===== 分区标题（我的学业 / 快捷空间） ===== */
.gd-section-head { display: flex; align-items: center; gap: 7px; font-size: 13.5px; font-weight: 700; color: #1a1a2e; margin-bottom: 10px; }
.gd-section-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #34d399); box-shadow: 0 0 6px rgba(64,158,255,0.4);
}
.gd-section-sub { margin-left: auto; font-size: 10px; font-weight: 400; color: #999999; }

/* ===== 卡2：我的学业 ===== */
.gd-academic-list { display: flex; flex-direction: column; }
.gd-academic-item {
  display: flex; align-items: center; gap: 12px; padding: 11px 6px;
  border-bottom: 1px dashed #e5e7ee; cursor: pointer;
  border-radius: 10px; transition: background 0.2s, transform 0.15s;
}
.gd-academic-item:last-child { border-bottom: none; }
.gd-academic-item:active { background: #eef1f6; transform: scale(0.99); }
.gd-academic-icon {
  width: 38px; height: 38px; border-radius: 11px; background: #f0f6ff;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.gd-academic-info { flex: 1; min-width: 0; }
.gd-academic-info b { display: block; font-size: 13.5px; font-weight: 600; color: #1a1a2e; }
.gd-academic-info span {
  display: block; font-size: 10.5px; color: #999999; margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gd-academic-arrow { color: #c0c4cc; flex-shrink: 0; }

/* ===== 卡3：快捷空间 ===== */
.space-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.space-card {
  display: flex; align-items: center; gap: 10px;
  background: #f8f9fc;
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 13px; padding: 12px; cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}
.space-card:active { background: #eef1f6; transform: scale(0.985); }
.space-card b { display: block; font-size: 13px; color: #1a1a2e; }
.space-card span { font-size: 10px; color: #999999; margin-top: 2px; }
.space-icon {
  width: 36px; height: 36px; border-radius: 10px; font-size: 18px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.space-icon-blue { color: #409eff; background: #eaf3ff; }
.space-icon-green { color: #67c23a; background: #eaf7e8; }
.space-icon-violet { color: #7c5cff; background: #f1edff; }
.space-icon-orange { color: #e6a23c; background: #fdf4e5; }

/* ===== 卡4：AI 主动发现 ===== */
.ai-discover-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.ai-discover-title { display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 700; color: #1f2937; }
.ai-discover-icon { color: #7c6af0; font-size: 16px; }
.ai-discover-empty {
  display: flex; align-items: center; gap: 8px; color: #9ca3af; font-size: 12.5px; padding: 8px 0;
}
.ai-empty-icon { color: #34d399; font-size: 18px; }
.ai-action-item {
  display: flex; gap: 10px; padding: 10px 12px; border-radius: 10px; background: #f8faff;
  margin-bottom: 8px; border-left: 3px solid #7c6af0;
}
.ai-action-item:last-child { margin-bottom: 0; }
.ai-action-tag { flex-shrink: 0; margin-top: 1px; }
.ai-action-body { min-width: 0; }
.ai-action-title { font-size: 13px; font-weight: 600; color: #1f2937; }
.ai-action-content { font-size: 11.5px; color: #6b7280; margin-top: 2px; line-height: 1.5; }
</style>