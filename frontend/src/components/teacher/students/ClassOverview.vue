<template>
  <div class="cls-page">
    <!-- 工具条：搜索（跨班搜人，命中直接进详情）+ 排序 -->
    <div class="cls-toolbar">
      <el-input
        :model-value="search"
        class="cls-search"
        placeholder="搜索姓名 / 学号（可跨班级）"
        clearable
        @update:model-value="(v: string) => emit('update:search', v)"
      >
        <template #prefix><el-icon :size="15"><Search /></el-icon></template>
      </el-input>
      <el-dropdown trigger="click" placement="bottom-end" @command="(c: string) => emit('update:sort', c)">
        <button class="cls-sort" type="button" :title="`排序：${sortLabel}`">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <path d="M7 4v15M4 16l3 3 3-3" />
            <path d="M14 7h7M14 12h5M14 17h3" />
          </svg>
          {{ sortLabel }}
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="o in sortOptions" :key="o.value" :command="o.value">
              {{ o.label }}
              <el-icon v-if="sort === o.value" :size="14" style="margin-left:6px"><Check /></el-icon>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!--
      跨班搜索结果：搜索的意图是「找到那个人」，不是浏览班级，
      所以命中后直接平铺成学生行，点一条就进详情，不绕道班级。
    -->
    <template v-if="isSearching">
      <div v-if="!searchHits.length && loaded" class="cls-empty">
        <img :src="siteMascot" :alt="siteName" class="cls-empty-mascot" />
        <p class="cls-empty-text">没有符合条件的学生</p>
      </div>
      <div v-else class="cls-hits">
        <button
          v-for="s in searchHits"
          :key="s.id"
          type="button"
          class="cls-hit"
          :data-risk="s.crisis_level || 'calm'"
          @click="emit('open', s)"
        >
          <el-avatar :size="34" :src="s.avatar || undefined" class="cls-hit-avatar">{{ s.name[0] }}</el-avatar>
          <span class="cls-hit-main">
            <span class="cls-hit-name">
              {{ s.name }}
              <em v-if="s.crisis_level" class="cls-hit-tag" :class="`is-${s.crisis_level}`">{{ crisisLabel(s.crisis_level) }}</em>
            </span>
            <span class="cls-hit-sub">{{ classNameOf(s) }} · {{ s.username }}</span>
          </span>
          <el-icon :size="14" class="cls-hit-arrow"><ArrowRight /></el-icon>
        </button>
        <p class="cls-hits-foot">共 {{ searchHits.length }} 条匹配</p>
      </div>
    </template>

    <!-- 班级卡网格 -->
    <template v-else>
      <div v-if="!classes.length && loaded" class="cls-empty">
        <img :src="siteMascot" :alt="siteName" class="cls-empty-mascot" />
        <p class="cls-empty-text">当前名下暂无学生</p>
      </div>

      <div v-else class="cls-grid">
        <button
          v-for="c in sortedClasses"
          :key="c.id"
          type="button"
          class="cls-card"
          :class="{ 'is-unassigned': c.unassigned, 'has-focus': c.focus > 0 }"
          @click="emit('select', c)"
        >
          <!-- 卡头：班级名 + 学生数 -->
          <div class="cls-card-head">
            <span class="cls-card-name">{{ c.name }}</span>
            <span class="cls-card-total">{{ c.total }} 人</span>
          </div>
          <div class="cls-card-meta">
            {{ c.unassigned ? '未关联班级的学生' : (c.majorName || '') }}
          </div>

          <!--
            重点关注：整张卡最重要的一行。
            不做成「N 人高危 / M 人中度」两个并列数字 —— 教师第一眼要的是
            「这个班到底几个人要盯」，拆开反而要自己加。
          -->
          <div class="cls-card-focus" :class="{ 'is-zero': !c.focus }">
            <template v-if="c.focus > 0">
              <el-icon :size="14" class="cls-focus-ic"><WarningFilled /></el-icon>
              <b>{{ c.focus }}</b> 人需要重点关注
            </template>
            <template v-else>
              <el-icon :size="14" class="cls-focus-ic"><CircleCheckFilled /></el-icon>
              暂无重点关注
            </template>
          </div>

          <!-- 分布条：红橙绿三段，宽度按人数占比，点之前就能看出班级的「风险形状」 -->
          <div class="cls-bar">
            <i
              v-if="c.severe"
              class="cls-bar-seg is-severe"
              :style="{ flexGrow: c.severe }"
              :title="`必须今天处理 ${c.severe} 人`"
            />
            <i
              v-if="c.moderate"
              class="cls-bar-seg is-moderate"
              :style="{ flexGrow: c.moderate }"
              :title="`这周要跟进 ${c.moderate} 人`"
            />
            <i class="cls-bar-seg is-calm" :style="{ flexGrow: c.calm || 1 }" :title="`状态平稳 ${c.calm} 人`" />
          </div>

          <div class="cls-card-foot">
            <span class="cls-foot-item" v-if="c.severe"><i class="cls-dot is-severe"></i>必须今天 {{ c.severe }}</span>
            <span class="cls-foot-item" v-if="c.moderate"><i class="cls-dot is-moderate"></i>本周跟进 {{ c.moderate }}</span>
            <span class="cls-foot-item is-quiet" v-if="!c.severe && !c.moderate">
              <i class="cls-dot is-calm"></i>状态平稳 {{ c.calm }}
            </span>
            <span class="cls-foot-time" v-if="c.latestCrisisTime">最近预警 {{ fromNow(c.latestCrisisTime) }}</span>
          </div>
        </button>
      </div>

      <p v-if="classes.length" class="cls-footnote">
        <b>重点关注口径：</b>最近一次预警为「高危」或「中度」的学生；已闭环的预警仍计入，处置状态请进入班级查看。
      </p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Search, Check, ArrowRight, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import type { StudentSummary } from '@/api/teacher'
import type { ClassSummary } from '@/composables/useClassSummaries'

/** L1 班级总览：本组件只负责渲染与事件上抛，排序/取数留在页面（与名单共享同一份数据） */

const props = defineProps<{
  classes: ClassSummary[]
  students: (StudentSummary & { class_group_id?: number | null })[]
  search: string
  sort: string
  loaded: boolean
}>()

const emit = defineEmits<{
  (e: 'select', c: ClassSummary): void
  (e: 'open', s: StudentSummary): void
  (e: 'update:search', v: string): void
  (e: 'update:sort', v: string): void
}>()

// 站点资源：与名单页共用同一套吉祥物，空态不另造图
import { useSiteConfig } from '@/composables/useSiteConfig'
const { siteMascot, siteName } = useSiteConfig()

const sortOptions = [
  { label: '重点关注优先', value: 'focus' },
  { label: '按人数', value: 'size' },
  { label: '按班级名', value: 'name' },
]
const sortLabel = computed(() => sortOptions.find(o => o.value === props.sort)?.label || '重点关注优先')

const isSearching = computed(() => props.search.trim() !== '')

const searchHits = computed(() => {
  const kw = props.search.trim().toLowerCase()
  if (!kw) return []
  return props.students
    .filter(s => `${s.name}${s.username}${s.class_name || ''}`.toLowerCase().includes(kw))
    .slice(0, 50)
})

/**
 * 班级排序：默认重点关注倒序。未分班卡与普通班级一样参与排序，
 * 有重点关注的未分班学生会按规则浮到对应位置，不再强制置底。
 */
const sortedClasses = computed(() => {
  const list = [...props.classes]
  return list.sort((a, b) => {
    if (props.sort === 'name') return a.name.localeCompare(b.name, 'zh-Hans-CN')
    if (props.sort === 'size') {
      if (b.total !== a.total) return b.total - a.total
      return b.focus - a.focus
    }
    if (b.focus !== a.focus) return b.focus - a.focus
    if (b.total !== a.total) return b.total - a.total
    return a.name.localeCompare(b.name, 'zh-Hans-CN')
  })
})

function classNameOf(s: StudentSummary & { class_group_id?: number | null }) {
  return s.class_name || '未分班'
}

function crisisLabel(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度', normal: '正常' }
  return map[level] || level
}

/** 相对时间：班级卡上只需要「多久没动」，精确到分钟没有意义 */
function fromNow(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const diff = Date.now() - t
  const day = 86400000
  if (diff < 0) return '刚刚'
  if (diff < 3600000) return `${Math.max(1, Math.floor(diff / 60000))} 分钟前`
  if (diff < day) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < day * 30) return `${Math.floor(diff / day)} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.cls-page {
  --cls-line: #ebedf0;
  --cls-line-strong: #e4e7ec;
  --cls-ink: #101828;
  --cls-ink2: #475467;
  --cls-ink3: #98a2b3;
  --cls-bad: #d92d20;
  --cls-bad-soft: #fef3f2;
  --cls-warn: #b54708;
  --cls-warn-soft: #fffaeb;
  --cls-ok: #079455;
  --cls-ok-soft: #ecfdf3;
}

/* ===== 工具条 ===== */
.cls-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0 10px;
  flex-wrap: wrap;
}
.cls-search { max-width: 320px; }
.cls-search :deep(.el-input__wrapper) {
  height: 34px;
  border-radius: 9px;
  padding: 0 11px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--cls-line) inset;
  transition: box-shadow 0.15s ease;
}
.cls-search :deep(.el-input__wrapper:hover) { box-shadow: 0 0 0 1px #d9dee7 inset; }
.cls-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.cls-search :deep(.el-input__inner) { height: 34px; font-size: 13px; color: var(--cls-ink); }
.cls-search :deep(.el-input__prefix) { color: #9aa4b2; }

.cls-sort {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border: 1px solid var(--cls-line);
  border-radius: 8px;
  background: #fff;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--cls-ink2);
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.cls-sort:hover { border-color: #2563eb; color: #2563eb; background: #eff4ff; }

/* ===== 班级卡网格 ===== */
.cls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
  gap: 8px;
}
.cls-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 11px 12px 10px;
  text-align: left;
  background: #fff;
  border: 1px solid var(--cls-line);
  border-radius: 10px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
}
.cls-card:hover {
  border-color: #cfdcf3;
  box-shadow: 0 2px 10px rgba(16, 24, 40, 0.07);
}
.cls-card:active { transform: scale(0.995); }
/* 有重点关注的班级左侧加一条红：一屏扫过去就知道先看哪几张 */
.cls-card.has-focus { border-left: 3px solid var(--cls-bad); }
.cls-card.is-unassigned {
  background: #fbfcfd;
  border-style: dashed;
  border-left-width: 1px;
}

.cls-card-head { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.cls-card-name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--cls-ink);
  letter-spacing: -0.2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cls-card-total {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--cls-ink3);
  font-variant-numeric: tabular-nums;
}
.cls-card-meta {
  font-size: 11.5px;
  color: var(--cls-ink3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 重点关注行：整卡唯一的彩色强调块 */
.cls-card-focus {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 2px;
  padding: 6px 9px;
  border-radius: 7px;
  background: var(--cls-bad-soft);
  font-size: 12px;
  color: #b42318;
  font-weight: 600;
}
.cls-card-focus b {
  font-size: 16px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}
.cls-card-focus.is-zero {
  background: var(--cls-ok-soft);
  color: var(--cls-ok);
  font-weight: 600;
}
.cls-focus-ic { flex-shrink: 0; }

/* 分布条 */
.cls-bar {
  display: flex;
  gap: 2px;
  height: 5px;
  margin: 1px 0 2px;
  border-radius: 999px;
  overflow: hidden;
  background: #f2f4f7;
}
.cls-bar-seg { display: block; min-width: 4px; border-radius: 999px; }
.cls-bar-seg.is-severe { background: var(--cls-bad); }
.cls-bar-seg.is-moderate { background: #e99a1a; }
.cls-bar-seg.is-calm { background: #6fd3af; }

.cls-card-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--cls-ink2);
}
.cls-foot-item { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.cls-foot-item.is-quiet { color: var(--cls-ink3); }
.cls-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.cls-dot.is-severe { background: var(--cls-bad); }
.cls-dot.is-moderate { background: #e99a1a; }
.cls-dot.is-calm { background: #6fd3af; }
.cls-foot-time { margin-left: auto; color: var(--cls-ink3); white-space: nowrap; }

/* ===== 搜索命中列表 ===== */
.cls-hits { display: flex; flex-direction: column; gap: 6px; }
.cls-hit {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 11px;
  background: #fff;
  border: 1px solid var(--cls-line);
  border-radius: 10px;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  position: relative;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.cls-hit::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: transparent;
}
.cls-hit[data-risk='severe']::before { background: var(--cls-bad); }
.cls-hit[data-risk='moderate']::before { background: #e99a1a; }
.cls-hit:hover { border-color: #cfdcf3; background: #fbfcfe; }
.cls-hit-avatar { flex-shrink: 0; background: #f2f4f7; color: #5b6472; font-size: 13px; font-weight: 600; }
.cls-hit-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cls-hit-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--cls-ink);
}
.cls-hit-tag {
  font-style: normal;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  line-height: 1.5;
}
.cls-hit-tag.is-severe { background: var(--cls-bad-soft); color: var(--cls-bad); }
.cls-hit-tag.is-moderate { background: var(--cls-warn-soft); color: var(--cls-warn); }
.cls-hit-tag.is-mild { background: #f1f4f9; color: #78849a; }
.cls-hit-sub {
  font-size: 11.5px;
  color: var(--cls-ink3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cls-hit-arrow { color: #c0c4cc; flex-shrink: 0; }
.cls-hits-foot {
  margin: 2px 0 0;
  padding: 0 2px;
  font-size: 11.5px;
  color: var(--cls-ink3);
}

/* ===== 空态与脚注 ===== */
.cls-empty { padding: 36px 0 30px; text-align: center; }
.cls-empty-mascot { width: 88px; height: 88px; object-fit: contain; opacity: 0.9; margin: 0 auto; }
.cls-empty-text { margin: 8px 0 0; font-size: 13px; color: var(--cls-ink3); }

.cls-footnote {
  margin: 10px 0 0;
  padding: 8px 11px;
  border-radius: 8px;
  background: #f7f9fc;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--cls-ink3);
}
.cls-footnote b { color: var(--cls-ink2); font-weight: 600; }

/* ===== 移动端：单列卡片，卡片更紧凑 ===== */
@media (max-width: 767px) {
  .cls-grid { grid-template-columns: 1fr; }
  .cls-toolbar { padding: 8px 0 10px; }
  .cls-search { max-width: none; flex: 1; }
  .cls-sort { padding: 7px 10px; }
  .cls-card { padding: 11px 12px 11px; }
  .cls-card-name { font-size: 14.5px; }
}
</style>
