<!--
  教学育人进度卡（教师端专属 · 趣味进度）
  ---------------------------------------------------------------------------
  设计依据：.trae/documents/教师端桌面卡片设计契约.md §4「趣味教师进度体系」。
  设计意图：把教师本周的真实业务推进（办结 / 闭环 / 成长记录）翻译成
  「等级 → 成长值 → 完成度环 → 成就徽章」的推进叙事，让工作台有推进感与成就感。

  真实性约束（沿用项目 ANTI_FABRICATION）：
  1) 所有数字都来自现有接口字段，不引入任何假数据；
  2) 育人与成长值均为「派生值」，卡片内必须同时展示换算口径（prog-formula）；
  3) 徽章解锁条件全部是真实阈值，未达标即灰化，不做「假装已解锁」。

  数据来源：
  - 任务推进：getTeacherTaskSummary()（done_this_week / pending / overdue）
  - 预警闭环：stats.alert_count / stats.resolved_alert_count（父级首页已拉取）
  - 成长记录：growthTotal（父级首页已拉取）
-->
<template>
  <div class="tui-card is-accent prog-card" :style="{ '--accent': level.c1 }">
    <!-- 卡片头：教师语义标题 + 当前等级徽章 -->
    <div class="tui-card-head">
      <span class="tui-card-head-icon" :style="{ background: level.soft, color: level.c1 }">
        <el-icon :size="14"><TrendCharts /></el-icon>
      </span>
      教学育人进度
      <span class="prog-level">
        <span class="tui-level" :style="{ '--lv-c1': level.c1, '--lv-c2': level.c2 }">
          <span class="tui-level-ic">{{ level.icon }}</span>{{ level.name }}
        </span>
      </span>
    </div>
    <p class="tui-card-desc">
      把本周的办结、闭环与成长留痕折算成成长值 —— 看得见的推进感，数值全部来自真实业务数据。
    </p>

    <div class="tui-card-body">
      <div class="tui-progress-hero">
        <!-- 左：本周推进完成度环 -->
        <div class="prog-ring">
          <span class="tui-ring tui-ring-lg" :style="{ '--pct': weekRatio, '--ring-color': level.c1 }">
            <span class="tui-ring-center">
              <span class="tui-ring-num">{{ weekPercent }}%</span>
              <span class="tui-ring-cap">本周推进</span>
            </span>
          </span>
          <p class="prog-ring-note">
            办结 <b>{{ summary.done_this_week }}</b> · 待处理 <b>{{ summary.pending }}</b>
          </p>
        </div>

        <!-- 右：成长值进度 + 换算口径 -->
        <div class="prog-main">
          <div class="tui-xp" :style="{ '--xp-c1': level.c1, '--xp-c2': level.c2 }">
            <div class="tui-xp-head">
              <span>育人成长值</span>
              <span><b class="tui-xp-val">{{ growthIndex }}</b> 点</span>
            </div>
            <span class="tui-xp-track">
              <span class="tui-xp-fill" :style="{ '--pct': xpRatio }" />
            </span>
            <div class="tui-xp-foot">
              <span>{{ level.name }} · {{ level.min }} 点起</span>
              <span v-if="nextLevel">距「{{ nextLevel.name }}」还差 {{ nextLevel.min - growthIndex }} 点</span>
              <span v-else>已达最高等级，继续深耕</span>
            </div>
          </div>

          <p class="prog-formula">
            换算口径：本周办结 ×2 + 预警闭环 ×3 + 成长记录 ×1
            （当前 {{ summary.done_this_week }} / {{ resolvedAlerts }} / {{ growthTotal }}）
          </p>

          <!-- 三个真实计数器：让「趣味」落在可核对的数字上 -->
          <div class="prog-counters">
            <div class="prog-counter">
              <span class="prog-counter-num">{{ summary.total }}</span>
              <span class="prog-counter-label">名下任务</span>
            </div>
            <div class="prog-counter">
              <span class="prog-counter-num" :class="{ 'is-warn': summary.overdue > 0 }">{{ summary.overdue }}</span>
              <span class="prog-counter-label">已逾期</span>
            </div>
            <div class="prog-counter">
              <span class="prog-counter-num">{{ closeRate }}%</span>
              <span class="prog-counter-label">预警闭环率</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 成就徽章墙：真实阈值解锁 -->
      <div class="prog-badges">
        <div class="prog-badges-head">
          成就徽章
          <span class="prog-badges-count">已解锁 {{ unlockedCount }} / {{ badges.length }}</span>
        </div>
        <div class="tui-badge-wall">
          <div
            v-for="b in badges"
            :key="b.name"
            class="tui-badge"
            :class="{ 'is-locked': !b.unlocked }"
            :style="b.unlocked ? { '--badge-color': b.color, '--badge-soft': b.soft } : undefined"
            :title="b.unlocked ? b.desc : b.lockHint"
          >
            <span class="tui-badge-ic">
              <el-icon :size="18"><component :is="b.icon" /></el-icon>
            </span>
            <span class="tui-badge-name">{{ b.name }}</span>
            <span class="tui-badge-desc">{{ b.unlocked ? b.desc : b.lockHint }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import {
  TrendCharts, Trophy, Medal, Star, CircleCheckFilled, BellFilled, UserFilled,
} from '@element-plus/icons-vue'
import { getTeacherTaskSummary, type TeacherTaskSummary } from '@/api/teacherTask'

const props = defineProps<{
  /** 首页已拉取的仪表盘统计（预警总量 / 已闭环数） */
  alertCount: number
  resolvedAlertCount: number
  /** 首页已拉取的成长记录总数（成长档案统计） */
  growthTotal: number
}>()

const summary = ref<TeacherTaskSummary>({ pending: 0, overdue: 0, today: 0, done_this_week: 0, total: 0 })

// 任务推进数据由卡片自取（与「任务清单」页同源同接口，不新增 API）
onMounted(async () => {
  try {
    summary.value = await getTeacherTaskSummary()
  } catch {
    /* 拉取失败时保持 0，卡片其余部分仍可用 */
  }
})

/** 等级阶梯：阈值与称号为产品约定，成长值口径见卡片内说明 */
interface Level {
  name: string
  icon: string
  min: number
  c1: string
  c2: string
  soft: string
}
const LEVELS: Level[] = [
  { name: '育人学徒', icon: 'Ⅰ', min: 0, c1: '#4093ff', c2: '#2563eb', soft: '#eff4ff' },
  { name: '育人良师', icon: 'Ⅱ', min: 60, c1: '#2563eb', c2: '#6941c6', soft: '#eff4ff' },
  { name: '育人名师', icon: 'Ⅲ', min: 160, c1: '#7f56d9', c2: '#5925dc', soft: '#f4f3ff' },
  { name: '育人先生', icon: 'Ⅳ', min: 320, c1: '#f79009', c2: '#d92d20', soft: '#fffaeb' },
]

/** 育人成长值：完全由真实字段派生的公开口径 */
const growthIndex = computed(() =>
  summary.value.done_this_week * 2 + props.resolvedAlertCount * 3 + props.growthTotal,
)

const levelIndex = computed(() => {
  let idx = 0
  LEVELS.forEach((lv, i) => {
    if (growthIndex.value >= lv.min) idx = i
  })
  return idx
})
const level = computed(() => LEVELS[levelIndex.value])
const nextLevel = computed<Level | null>(() => LEVELS[levelIndex.value + 1] ?? null)

/** 成长值在当前等级区间内的位置（0~1）；满级恒为 1 */
const xpRatio = computed(() => {
  const next = nextLevel.value
  if (!next) return 1
  const span = next.min - level.value.min
  if (span <= 0) return 1
  return Math.min(1, Math.max(0, (growthIndex.value - level.value.min) / span))
})

/** 本周推进 = 本周办结 ÷（本周办结 + 待处理），与「任务清单」页同一口径 */
const weekRatio = computed(() => {
  const denom = summary.value.done_this_week + summary.value.pending
  if (!denom) return 0
  return Math.min(1, summary.value.done_this_week / denom)
})
const weekPercent = computed(() => Math.round(weekRatio.value * 100))

/** 预警闭环率：已闭环 ÷ 预警总量 */
const closeRate = computed(() => {
  if (!props.alertCount) return 0
  return Math.round((props.resolvedAlertCount / props.alertCount) * 100)
})
const resolvedAlerts = computed(() => props.resolvedAlertCount)

/** 成就徽章：解锁条件全部是真实阈值 */
interface Badge {
  name: string
  desc: string
  lockHint: string
  unlocked: boolean
  color: string
  soft: string
  icon: Component
}
const badges = computed<Badge[]>(() => {
  const done = summary.value.done_this_week
  const rate = props.alertCount ? props.resolvedAlertCount / props.alertCount : 0
  return [
    {
      name: '闭环守护', desc: '预警闭环率达标', lockHint: '闭环率 ≥ 80% 解锁',
      unlocked: props.alertCount > 0 && rate >= 0.8, color: '#079455', soft: '#ecfdf3', icon: Trophy,
    },
    {
      name: '周清达人', desc: '本周办结 5 件以上', lockHint: '本周办结 ≥ 5 件解锁',
      unlocked: done >= 5, color: '#2563eb', soft: '#eff4ff', icon: Medal,
    },
    {
      name: '成长见证', desc: `已沉淀 ${props.growthTotal} 条成长记录`, lockHint: '成长记录 ≥ 10 条解锁',
      unlocked: props.growthTotal >= 10, color: '#6941c6', soft: '#f4f3ff', icon: Star,
    },
    {
      name: '待办清零', desc: '名下任务无待处理', lockHint: '名下待处理归零解锁',
      unlocked: summary.value.total > 0 && summary.value.pending === 0, color: '#0891b2', soft: '#ecfeff', icon: CircleCheckFilled,
    },
    {
      name: '预警追踪', desc: '在跟预警有据可查', lockHint: '名下有预警时解锁',
      unlocked: props.alertCount > 0, color: '#d92d20', soft: '#fef3f2', icon: BellFilled,
    },
    {
      name: '带班育人', desc: '带班学生已建档', lockHint: '带班学生 ≥ 1 人解锁',
      unlocked: summary.value.total > 0, color: '#f79009', soft: '#fffaeb', icon: UserFilled,
    },
  ]
})
const unlockedCount = computed(() => badges.value.filter((b) => b.unlocked).length)
</script>

<style scoped>
/* 卡片本体（圆角/描边/阴影/内边距全部来自 teacher-ui.css 的卡片体系） */
.prog-card { display: flex; flex-direction: column; }

.prog-level { margin-left: auto; }

/* 左环 + 右成长值：栅格由 .tui-progress-hero 提供，这里只做局部对齐 */
.prog-ring {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.prog-ring-note {
  margin: 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  white-space: nowrap;
}
.prog-ring-note b {
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}

.prog-main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }

.prog-formula {
  margin: 0;
  padding: 8px 12px;
  border-radius: var(--tui-radius);
  background: var(--tui-surface-muted);
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--tui-text-tertiary);
}

.prog-counters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.prog-counter {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
}
.prog-counter-num {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.prog-counter-num.is-warn { color: var(--tui-danger); }
.prog-counter-label { font-size: 11px; color: var(--tui-text-quiet); }

/* 徽章墙与上方进度区之间留足呼吸（契约 §5 的间距口径） */
.prog-badges { margin-top: 24px; }
.prog-badges-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
  color: #333a4d;
}
.prog-badges-count {
  margin-left: auto;
  font-size: 11.5px;
  font-weight: 400;
  color: var(--tui-text-quiet);
}

@media (max-width: 767px) {
  .prog-counters { grid-template-columns: 1fr; }
  .prog-ring-note { white-space: normal; text-align: center; }
}
</style>