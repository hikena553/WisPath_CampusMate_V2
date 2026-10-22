<template>
  <div class="badge-wall">
    <!-- ===== 等级头：白底细线信息条（等级 / 进度 / 稀有度），不用深色渐变与发光 ==== -->
    <div class="mw-hero">
      <div class="mw-hero-top">
        <span class="mw-lv">Lv.{{ level.level }}</span>
        <span class="mw-hero-name">{{ level.name }}</span>
        <span class="mw-hero-count">{{ earned.length }} / {{ earned.length + locked.length }} 枚</span>
      </div>
      <div class="mw-hero-bar">
        <i :style="{ width: level.progress + '%' }"></i>
      </div>
      <div class="mw-hero-foot">
        <span>{{ level.next_points === null
          ? '已达最高等级'
          : `距 Lv.${level.level + 1} 还需 ${level.next_points - level.points} 成长值` }}</span>
        <span class="mw-hero-points">{{ level.points }} 成长值</span>
      </div>
      <!-- 稀有度统计：只用小圆点区分，不做彩色徽章堆叠 -->
      <div class="mw-rarity">
        <span v-for="t in rarity" :key="t.key" class="mw-rarity-item" :class="`tier-${t.key}`">
          <i class="mw-dot"></i>{{ t.label }} {{ t.earned }}<em>/{{ t.total }}</em>
        </span>
      </div>
    </div>

    <!-- ===== 勋章陈列：按类别分组，发丝分割，不做卡片堆叠 ===== -->
    <div class="mw-panel">
      <section v-for="g in groups" :key="g.name" class="mw-group">
        <div class="mw-group-head">
          <span class="mw-group-name">{{ g.name }}</span>
          <span class="mw-group-count">{{ g.earned }}/{{ g.items.length }}</span>
        </div>
        <div class="mw-grid">
          <div
            v-for="b in g.items"
            :key="b.code"
            class="mw-item"
            :class="[`tier-${b.tier}`, { 'is-locked': !b.earned }]"
            :title="b.earned ? `${b.name} · ${b.desc}` : `${b.name} · ${b.target_label}（${b.progress}%）`"
          >
            <span class="mw-disc">
              <span class="mw-inner"><i class="mw-emoji">{{ b.icon }}</i></span>
              <span v-if="!b.earned" class="mw-lock"><el-icon :size="9"><Lock /></el-icon></span>
            </span>
            <span class="mw-name">{{ b.name }}</span>
            <span v-if="!b.earned" class="mw-progress">
              <i :style="{ width: b.progress + '%' }"></i>
            </span>
            <span class="mw-meta">{{ b.earned ? '已获得' : b.progress + '%' }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { BadgeItem, BadgeTier, LevelInfo } from '@/api/badge'
import { Lock } from '@element-plus/icons-vue'

const props = defineProps<{
  earned: BadgeItem[]
  locked: BadgeItem[]
  level: LevelInfo
}>()

const TIER_META: { key: BadgeTier; label: string }[] = [
  { key: 'bronze', label: '铜' },
  { key: 'silver', label: '银' },
  { key: 'gold', label: '金' },
  { key: 'diamond', label: '钻' },
]

/** 稀有度统计：按铜/银/金/钻统计已点亮数与总数 */
const rarity = computed(() =>
  TIER_META.map((t) => ({
    ...t,
    earned: props.earned.filter((b) => b.tier === t.key).length,
    total: [...props.earned, ...props.locked].filter((b) => b.tier === t.key).length,
  })).filter((t) => t.total > 0)
)

/**
 * 按类别分组：已点亮的排在同组前面，未点亮的按进度倒序（离解锁最近的先出现）。
 * 分组顺序取首次出现顺序，避免为了排序再把勋章目录搬到前端。
 */
const groups = computed(() => {
  const order: string[] = []
  const bucket = new Map<string, BadgeItem[]>()
  const push = (b: BadgeItem) => {
    if (!bucket.has(b.category)) {
      bucket.set(b.category, [])
      order.push(b.category)
    }
    bucket.get(b.category)!.push(b)
  }
  props.earned.forEach(push)
  ;[...props.locked].sort((a, b) => b.progress - a.progress).forEach(push)
  return order.map((name) => {
    const items = bucket.get(name)!
    return { name, items, earned: items.filter((i) => i.earned).length }
  })
})
</script>

<style scoped>
.badge-wall { display: flex; flex-direction: column; gap: 10px; }

/* ===== 等级头：白底 + 发丝边框，信息靠字重与留白分层 ===== */
.mw-hero {
  padding: 14px 16px;
  border: 1px solid var(--tui-border, #eef0f3);
  border-radius: 14px;
  background: var(--tui-surface, #fff);
}
.mw-hero-top { display: flex; align-items: baseline; gap: 8px; }
.mw-lv {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 6px;
  background: var(--tui-surface-sunken, #f4f5f7);
  color: var(--tui-text-secondary, #667085);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2px;
  font-variant-numeric: tabular-nums;
}
.mw-hero-name {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--tui-text, #1f2430);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mw-hero-count {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--tui-text-quiet, #98a2b3);
  font-variant-numeric: tabular-nums;
}

/* 细进度条：中性轨道 + 品牌色填充，不用发光 */
.mw-hero-bar {
  height: 4px;
  margin-top: 10px;
  border-radius: 999px;
  background: var(--tui-surface-sunken, #f0f2f5);
  overflow: hidden;
}
.mw-hero-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--tui-brand, #5b5bd6);
  transition: width 0.5s ease;
}
.mw-hero-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 7px;
  font-size: 11px;
  color: var(--tui-text-tertiary, #8b929e);
}
.mw-hero-points { flex-shrink: 0; font-variant-numeric: tabular-nums; }

/* 稀有度：小圆点 + 计数，弱化存在感 */
.mw-rarity {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--tui-border, #eef0f3);
}
.mw-rarity-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--tui-text-secondary, #667085);
  font-variant-numeric: tabular-nums;
}
.mw-rarity-item em { font-style: normal; color: var(--tui-text-quiet, #98a2b3); }
.mw-dot { width: 6px; height: 6px; border-radius: 50%; }
.tier-bronze .mw-dot { background: #b4763e; }
.tier-silver .mw-dot { background: #8f9bab; }
.tier-gold .mw-dot { background: #c79a1f; }
.tier-diamond .mw-dot { background: #3f92b8; }

/* ===== 陈列面板 ===== */
.mw-panel {
  padding: 2px 16px 14px;
  border: 1px solid var(--tui-border, #eef0f3);
  border-radius: 14px;
  background: var(--tui-surface, #fff);
}

.mw-group + .mw-group { border-top: 1px solid var(--tui-border, #eef0f3); }
.mw-group-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 11px 0 9px;
}
.mw-group-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-secondary, #667085);
  letter-spacing: 0.3px;
}
.mw-group-count { font-size: 11px; color: var(--tui-text-quiet, #98a2b3); font-variant-numeric: tabular-nums; }

.mw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(68px, 1fr));
  gap: 14px 8px;
}

/* ===== 单枚勋章：扁平圆盘，层级靠底色深浅与描边区分 ===== */
.mw-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  min-width: 0;
}
.mw-disc {
  position: relative;
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--disc-bg);
  box-shadow: inset 0 0 0 1px var(--disc-ring);
}
.mw-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mw-emoji { font-style: normal; font-size: 24px; line-height: 1; }

/* 未点亮：中性灰底、降饱和徽记，右下角小锁 */
.mw-item.is-locked .mw-disc {
  background: var(--tui-surface-sunken, #f5f6f8);
  box-shadow: inset 0 0 0 1px var(--tui-border, #eaecf0);
}
.mw-item.is-locked .mw-emoji { filter: grayscale(1); opacity: 0.32; }
.mw-lock {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: #a6adb8;
  box-shadow: inset 0 0 0 1px var(--tui-border, #e4e7ec);
}

/* 分级配色：极浅底色 + 同色 1px 内描边，克制但有区分 */
.tier-bronze { --disc-bg: #fbf3ec; --disc-ring: #ecd6c2; }
.tier-silver { --disc-bg: #f6f7f9; --disc-ring: #dfe4ea; }
.tier-gold { --disc-bg: #fdf7e8; --disc-ring: #efdfb6; }
.tier-diamond { --disc-bg: #eef7fb; --disc-ring: #cfe6f0; }

.mw-name {
  max-width: 100%;
  font-size: 11px;
  line-height: 1.2;
  color: var(--tui-text, #344054);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mw-item.is-locked .mw-name { color: var(--tui-text-quiet, #98a2b3); }
.mw-progress {
  width: 40px;
  height: 3px;
  border-radius: 999px;
  background: var(--tui-surface-sunken, #eef0f3);
  overflow: hidden;
}
.mw-progress i { display: block; height: 100%; border-radius: 999px; background: #b6bfcc; }
.mw-meta {
  font-size: 10px;
  color: var(--tui-text-quiet, #98a2b3);
  font-variant-numeric: tabular-nums;
}
.mw-item:not(.is-locked) .mw-meta { color: var(--tui-text-tertiary, #8b929e); }

@media (max-width: 380px) {
  .mw-grid { grid-template-columns: repeat(auto-fill, minmax(62px, 1fr)); gap: 14px 6px; }
  .mw-disc { width: 50px; height: 50px; }
  .mw-emoji { font-size: 21px; }
}
</style>
