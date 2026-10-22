<template>
  <div class="care-page">
    <SubPageHeader title="我的关怀" fallback="/student" />

    <!-- 顶部概览 -->
    <div class="care-hero">
      <div class="hero-top">
        <div class="hero-kicker">CARE · 我的关怀</div>
        <h2 class="hero-title">老师的关心，都在这里</h2>
        <p class="hero-sub">激励、关怀记录与家访，都是你成长路上被看见的痕迹</p>
      </div>
      <div class="hero-stats">
        <div class="hs-item">
          <span class="hs-num">{{ summary.praises }}</span>
          <span class="hs-label">正向激励</span>
        </div>
        <div class="hs-sep"></div>
        <div class="hs-item">
          <span class="hs-num">{{ summary.visits }}</span>
          <span class="hs-label">家访记录</span>
        </div>
        <div class="hs-sep"></div>
        <div class="hs-item">
          <span class="hs-num">{{ summary.records }}</span>
          <span class="hs-label">关怀记录</span>
        </div>
      </div>
    </div>

    <!-- 激励徽章墙 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">我的激励</span>
        <span class="head-sub">表扬与徽章</span>
      </div>
      <div v-if="praises.length" class="badge-grid">
        <div
          v-for="p in praises"
          :key="p.id"
          class="badge-item"
          :class="{ 'is-badge': p.praise_type === 'badge' }"
        >
          <div class="badge-icon">{{ p.praise_type === 'badge' ? '🏅' : '⭐' }}</div>
          <div class="badge-name">{{ p.praise_type === 'badge' ? (p.badge_name || '徽章') : '表扬' }}</div>
          <div class="badge-reason">{{ p.reason }}</div>
          <div class="badge-meta">
            <span>{{ p.teacher_name || '老师' }}</span>
            <span>{{ fmt(p.occurred_on) }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else description="还没有收到激励，继续加油" />
    </div>

    <!-- 关怀记录时间轴 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">关怀记录</span>
        <span class="head-sub">老师记录下的点滴</span>
      </div>
      <div v-if="records.length" class="tl">
        <div v-for="r in records" :key="r.id" class="tl-item">
          <span class="tl-node"></span>
          <div class="tl-body">
            <div class="tl-top">
              <span class="tl-type">{{ RECORD_TYPE_LABEL[r.record_type] }}</span>
              <span class="tl-time">{{ fmtTime(r.created_at) }}</span>
            </div>
            <div class="tl-content">{{ r.content }}</div>
            <div class="tl-teacher">{{ r.teacher_name || '老师' }}</div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无关怀记录" />
    </div>

    <!-- 家访记录 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">家访记录</span>
        <span class="head-sub">老师与家长沟通的留痕</span>
      </div>
      <div v-if="visits.length" class="visit-list">
        <div v-for="v in visits" :key="v.id" class="visit-item">
          <div class="visit-top">
            <span class="visit-method">{{ VISIT_METHOD_LABEL[v.method] }}</span>
            <span class="visit-date">{{ fmt(v.visit_date) }}</span>
            <span class="visit-status" :class="v.follow_up_status === 'done' ? 'is-done' : 'is-pending'">
              <i class="visit-dot" />{{ FOLLOW_UP_STATUS_LABEL[v.follow_up_status] }}
            </span>
          </div>
          <div class="visit-content">{{ v.content }}</div>
          <div v-if="v.follow_up" class="visit-follow">后续安排：{{ v.follow_up }}</div>
          <div class="visit-teacher">{{ v.teacher_name || '老师' }}</div>
        </div>
      </div>
      <el-empty v-else description="暂无家访记录" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import {
  getMyCarePraises, getMyCareRecords, getMyCareSummary, getMyCareVisits,
  type MyCarePraise, type MyCareRecord, type MyCareSummary, type MyCareVisit,
} from '@/api/careStudent'
import { FOLLOW_UP_STATUS_LABEL, VISIT_METHOD_LABEL } from '@/api/careCenter'

const RECORD_TYPE_LABEL: Record<MyCareRecord['record_type'], string> = {
  care: '关怀记录',
  talk: '谈心谈话',
  comment: '评语',
}

const summary = ref<MyCareSummary>({ praises: 0, visits: 0, records: 0 })
const praises = ref<MyCarePraise[]>([])
const records = ref<MyCareRecord[]>([])
const visits = ref<MyCareVisit[]>([])

function fmt(d: string | null) {
  return d ? d.slice(0, 10) : ''
}
function fmtTime(d: string) {
  return d ? d.slice(0, 16).replace('T', ' ') : ''
}

onMounted(async () => {
  const [s, p, r, v] = await Promise.allSettled([
    getMyCareSummary(),
    getMyCarePraises(),
    getMyCareRecords(),
    getMyCareVisits(),
  ])
  if (s.status === 'fulfilled') summary.value = s.value
  if (p.status === 'fulfilled') praises.value = p.value
  if (r.status === 'fulfilled') records.value = r.value
  if (v.status === 'fulfilled') visits.value = v.value
})
</script>

<style scoped>
.care-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 4px 0 24px;
  height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
  scrollbar-width: none;
}
.care-page::-webkit-scrollbar { display: none; }

/* 顶部概览 */
.care-hero {
  padding: 18px 20px;
  margin-bottom: 16px;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background: var(--gradient-card);
  animation: fadeInUp 0.35s ease-out;
}
.hero-kicker { font-size: 11px; letter-spacing: 1px; color: var(--accent-blue); font-weight: 700; }
.hero-title { font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 6px 0 4px; }
.hero-sub { font-size: 12.5px; color: var(--text-muted); margin: 0; }
.hero-stats { display: flex; align-items: center; gap: 20px; margin-top: 16px; }
.hs-item { display: flex; flex-direction: column; align-items: center; min-width: 56px; }
.hs-num { font-size: 22px; font-weight: 700; color: var(--accent-blue); line-height: 1.1; }
.hs-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.hs-sep { width: 1px; height: 26px; background: var(--border-color); }

/* 通用卡片 */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
  margin-bottom: 16px;
  animation: fadeInUp 0.35s ease-out;
}
.card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.head-bar { width: 4px; height: 15px; border-radius: 2px; background: linear-gradient(180deg, var(--accent-blue), var(--accent-green)); flex-shrink: 0; }
.head-title { font-size: 14px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.head-sub { font-size: 11.5px; color: var(--text-muted); line-height: 1; }

/* 徽章墙 */
.badge-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
.badge-item {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 12px 10px;
  background: var(--hover-bg);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.badge-item:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.badge-item.is-badge { background: linear-gradient(180deg, rgba(230, 162, 60, 0.12), rgba(230, 162, 60, 0.02)); border-color: rgba(230, 162, 60, 0.35); }
.badge-icon { font-size: 22px; line-height: 1; }
.badge-name { font-size: 13px; font-weight: 700; color: var(--text-primary); margin-top: 6px; }
.badge-reason { font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin-top: 4px; word-break: break-word; }
.badge-meta { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; font-size: 11px; color: var(--text-muted); }

/* 时间轴 */
.tl { position: relative; padding-left: 18px; }
.tl::before { content: ''; position: absolute; left: 5px; top: 4px; bottom: 4px; width: 2px; background: var(--border-color); }
.tl-item { position: relative; margin-bottom: 12px; }
.tl-item:last-child { margin-bottom: 0; }
.tl-node {
  position: absolute; left: -18px; top: 4px; width: 10px; height: 10px; border-radius: 50%;
  background: var(--bg-card); box-shadow: inset 0 0 0 2px var(--accent-blue);
}
.tl-body { border: 1px solid var(--border-color); border-radius: 12px; padding: 10px 12px; background: var(--hover-bg); }
.tl-top { display: flex; align-items: center; gap: 10px; }
.tl-type { font-size: 11.5px; font-weight: 600; color: var(--accent-blue); background: rgba(64, 158, 255, 0.1); border-radius: 999px; padding: 2px 9px; }
.tl-time { margin-left: auto; font-size: 11px; color: var(--text-muted); }
.tl-content { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-top: 6px; white-space: pre-wrap; word-break: break-word; }
.tl-teacher { font-size: 11px; color: var(--text-muted); margin-top: 6px; }

/* 家访 */
.visit-list { display: flex; flex-direction: column; gap: 10px; }
.visit-item { border: 1px solid var(--border-color); border-left: 3px solid var(--accent-blue); border-radius: 12px; padding: 11px 13px; background: var(--hover-bg); }
.visit-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.visit-method { font-size: 11.5px; font-weight: 600; color: var(--accent-blue); background: rgba(64, 158, 255, 0.1); border-radius: 999px; padding: 2px 9px; }
.visit-date { font-size: 11.5px; color: var(--text-muted); }
.visit-status { margin-left: auto; display: inline-flex; align-items: center; gap: 4px; font-size: 11.5px; font-weight: 600; }
.visit-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.visit-status.is-pending { color: #e6a23c; }
.visit-status.is-done { color: #67c23a; }
.visit-content { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-top: 7px; white-space: pre-wrap; word-break: break-word; }
.visit-follow {
  font-size: 12px; color: #8a6d3b; background: #fffaf0; border: 1px solid rgba(230, 162, 60, 0.25);
  border-radius: 8px; padding: 6px 9px; margin-top: 8px;
}
.visit-teacher { font-size: 11px; color: var(--text-muted); margin-top: 7px; }

@media (max-width: 767px) {
  .care-page { padding: 8px 12px 24px; }
  .care-hero { padding: 16px; }
  .hero-stats { gap: 12px; }
  .hs-num { font-size: 19px; }
  .badge-grid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
}
</style>