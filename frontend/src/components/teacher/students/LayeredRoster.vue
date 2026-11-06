<template>
  <div class="lr-wrap">
    <!--
      三档折叠队列：必须今天处理 / 这周要跟进 / 状态平稳。
      每档单独可折叠，档头左侧的色条是唯一的「档位标识」——
      不再给每行额外贴重复的等级标签，一屏能少掉几十个红黄小方块。
    -->
    <div
      v-for="g in groups"
      :key="g.key"
      class="lr-group"
      :style="{ '--lr-c': g.color, '--lr-soft': g.soft }"
    >
      <button class="lr-hd" type="button" :aria-expanded="open.has(g.key)" @click="toggle(g.key)">
        <span class="lr-hd-t">{{ g.title }}</span>
        <span class="lr-hd-n">{{ g.items.length }} 人</span>
        <span class="lr-hd-hint">{{ g.hint }}</span>
        <el-icon :size="13" class="lr-hd-ic" :class="{ 'is-open': open.has(g.key) }">
          <ArrowRight />
        </el-icon>
      </button>

      <div v-if="open.has(g.key)" class="lr-body">
        <!-- 桌面端：紧凑行，信息密度高 -->
        <template v-if="!isMobile">
          <div
            v-for="s in g.items"
            :key="s.id"
            class="lr-row"
            role="button"
            tabindex="0"
            @click="emit('open', s)"
            @keydown.enter="emit('open', s)"
          >
            <el-avatar :size="32" :src="s.avatar || undefined" class="lr-avatar">{{ s.name[0] }}</el-avatar>
            <div class="lr-main">
              <div class="lr-name-row">
                <strong class="lr-name">{{ s.name }}</strong>
                <span class="lr-id">{{ s.username }}</span>
                <span v-if="s.crisis_level" class="lr-tag" :class="`is-${s.crisis_level}`">{{ crisisLabel(s.crisis_level) }}</span>
              </div>
              <div class="lr-sub">
                {{ s.college || '未分配' }}
                <template v-if="lastSeenOf(s)"> · {{ lastSeenOf(s) }}</template>
              </div>
              <div v-if="s.latest_crisis_summary" class="lr-note">{{ s.latest_crisis_summary }}</div>
            </div>
            <div class="lr-facts">
              <span :class="{ 'is-zero': !s.growth_count }"><b>{{ s.growth_count ?? 0 }}</b> 成果</span>
              <span class="lr-fact-sep" aria-hidden="true"></span>
              <span :class="{ 'is-zero': !s.leave_count }"><b>{{ s.leave_count ?? 0 }}</b> 请假</span>
              <span class="lr-fact-sep" aria-hidden="true"></span>
              <span :class="s.score !== undefined ? scoreClass(s.score) : 'is-zero'"><b>{{ s.score ?? '—' }}</b> 综合分</span>
            </div>
            <div class="lr-ops" @click.stop>
              <button class="lr-op is-primary" type="button" @click="emit('open', s)">详情</button>
              <button class="lr-op" type="button" @click="emit('contact', s)">联系</button>
            </div>
          </div>
        </template>

        <!-- 移动端：两行式，点整行进详情 -->
        <template v-else>
          <button
            v-for="s in g.items"
            :key="s.id"
            type="button"
            class="lr-mrow"
            @click="emit('open', s)"
          >
            <el-avatar :size="38" :src="s.avatar || undefined" class="lr-avatar">{{ s.name[0] }}</el-avatar>
            <span class="lr-mmain">
              <span class="lr-mname">
                {{ s.name }}
                <em v-if="s.crisis_level" class="lr-tag" :class="`is-${s.crisis_level}`">{{ crisisLabel(s.crisis_level) }}</em>
              </span>
              <span class="lr-msub">
                {{ s.college || '未分配' }}<template v-if="lastSeenOf(s)"> · {{ lastSeenOf(s) }}</template>
              </span>
              <span v-if="s.latest_crisis_summary" class="lr-mnote">{{ s.latest_crisis_summary }}</span>
            </span>
            <span class="lr-mnum">
              <b>{{ s.growth_count ?? 0 }}</b><i>成果</i>
              <b>{{ s.leave_count ?? 0 }}</b><i>请假</i>
            </span>
          </button>
        </template>

        <div v-if="!g.items.length" class="lr-empty">这一档现在是空的</div>
      </div>
    </div>

    <p class="lr-foot">
      <b>分档依据：</b>学生最近一次危机预警的等级。高危 → 必须今天处理；中度 → 这周要跟进；
      轻度或无预警 → 状态平稳。档内按「最近预警时间」新→旧排列。
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import type { StudentSummary } from '@/api/teacher'
import { triageOf, type TriageKey } from '@/composables/useClassSummaries'

/**
 * 危机分层名单：桌面端与移动端共用一套分档逻辑，只切换行样式。
 *
 * 为什么要提取成组件：原来这套分诊队列只长在移动端模板里，
 * 桌面端完全没有；而分层与否和「哪个端」无关，是教师自己的查看偏好。
 * 现在数据源换成「当前班级的学生」，渲染逻辑两端复用，口径只有一处。
 */

const props = defineProps<{
  students: (StudentSummary & { class_group_id?: number | null })[]
  isMobile: boolean
  /** 最近互动时间文案（由页面统一计算，避免两处实现不一致） */
  lastSeenOf: (s: StudentSummary) => string
}>()

const emit = defineEmits<{
  (e: 'open', s: StudentSummary): void
  (e: 'contact', s: StudentSummary): void
}>()

const GROUPS: { key: TriageKey; title: string; hint: string; color: string; soft: string }[] = [
  { key: 'severe', title: '必须今天处理', hint: '高危预警', color: '#d92d20', soft: '#fef3f2' },
  { key: 'moderate', title: '这周要跟进', hint: '中度预警', color: '#e99a1a', soft: '#fffaeb' },
  { key: 'calm', title: '状态平稳', hint: '轻度 / 无预警', color: '#0f8e6b', soft: '#ecfdf3' },
]

const byKey = computed(() => {
  const map: Record<TriageKey, StudentSummary[]> = { severe: [], moderate: [], calm: [] }
  for (const s of props.students) map[triageOf(s)].push(s)
  // 档内按最近预警时间新→旧，其次按综合分低→高（有问题且分数低的更该先看）
  const sortItems = (list: StudentSummary[]) =>
    list.sort((a, b) => {
      const ta = a.latest_crisis_time || ''
      const tb = b.latest_crisis_time || ''
      if (ta !== tb) return tb.localeCompare(ta)
      return (a.score ?? 0) - (b.score ?? 0)
    })
  return {
    severe: sortItems(map.severe),
    moderate: sortItems(map.moderate),
    calm: sortItems(map.calm),
  }
})

const groups = computed(() =>
  GROUPS.map(g => ({ ...g, items: byKey.value[g.key] })),
)

const open = ref<Set<TriageKey>>(new Set())
/** 用户是否手动折叠/展开过：手动之后不再自动改默认展开档 */
const touched = ref(false)

function toggle(key: TriageKey) {
  touched.value = true
  const next = new Set(open.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  open.value = next
}

/**
 * 默认展开「第一个有人的档」。
 * 不写死 severe：如果这个班没有高危，硬展开一个空档会让教师以为「没数据」。
 * 用户手动折过之后就不再自动改，避免数据刷新把用户的操作冲掉。
 */
watch(
  () => groups.value,
  (gs) => {
    if (touched.value) return
    const nonEmpty = gs.filter(g => g.items.length)
    if (!nonEmpty.length) return
    if (open.value.size && nonEmpty.some(g => open.value.has(g.key))) return
    open.value = new Set([nonEmpty[0].key])
  },
  { immediate: true },
)

function crisisLabel(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度', normal: '正常' }
  return map[level] || level
}

function scoreClass(score: number) {
  if (score >= 80) return 'score-excellent'
  if (score >= 65) return 'score-good'
  if (score >= 50) return 'score-average'
  return 'score-poor'
}
</script>

<style scoped>
.lr-wrap { display: flex; flex-direction: column; gap: 7px; }

.lr-group {
  background: #fff;
  border: 1px solid #ebedf0;
  border-radius: 10px;
  overflow: hidden;
}

/* 档头：色条 + 标题 + 人数 + 一句口径 */
.lr-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 11px;
  border: none;
  border-left: 3px solid var(--lr-c);
  background: #fff;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}
.lr-hd:hover { background: #fbfcfe; }
.lr-hd-t {
  font-size: 13px;
  font-weight: 700;
  color: #16233a;
  letter-spacing: -0.1px;
}
.lr-hd-n {
  padding: 1px 7px;
  border-radius: 6px;
  background: var(--lr-soft);
  color: var(--lr-c);
  font-size: 11.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.lr-hd-hint {
  font-size: 11.5px;
  color: #98a2b3;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lr-hd-ic {
  margin-left: auto;
  color: #98a2b3;
  flex-shrink: 0;
  transition: transform 0.18s ease;
}
.lr-hd-ic.is-open { transform: rotate(90deg); }

.lr-body { padding: 0 7px 7px; display: flex; flex-direction: column; gap: 5px; }

/* ===== 桌面行 ===== */
.lr-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid #f0f2f5;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.lr-row:hover {
  border-color: #cfdcf3;
  background: #fbfcfe;
  box-shadow: 0 1px 4px rgba(16, 24, 40, 0.05);
}
.lr-row:focus-visible { outline: 2px solid #2563eb; outline-offset: 1px; }
.lr-avatar { flex-shrink: 0; background: #f2f4f7; color: #5b6472; font-size: 12.5px; font-weight: 600; }

.lr-main { flex: 1; min-width: 0; }
.lr-name-row { display: flex; align-items: center; gap: 6px; min-width: 0; }
.lr-name { font-size: 13.5px; font-weight: 650; color: #101828; }
.lr-id {
  font-size: 11px;
  color: #b0b7c3;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.lr-sub {
  margin-top: 1px;
  font-size: 11.5px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 预警摘要：只给一行，行本身就是「有事」的人，多给一行会撑高整行 */
.lr-note {
  margin-top: 3px;
  font-size: 11.5px;
  line-height: 1.45;
  color: #b42318;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lr-tag {
  font-style: normal;
  flex-shrink: 0;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  line-height: 1.5;
}
.lr-tag.is-severe { background: #fef3f2; color: #d92d20; }
.lr-tag.is-moderate { background: #fffaeb; color: #b54708; }
.lr-tag.is-mild { background: #f1f4f9; color: #78849a; }

.lr-facts {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  font-size: 11.5px;
  color: #667085;
}
.lr-facts b { font-size: 12.5px; font-weight: 700; color: #101828; margin-right: 1px; }
.lr-facts .is-zero { color: #c3c9d3; }
.lr-facts .is-zero b { color: #c3c9d3; font-weight: 600; }
.lr-facts .score-excellent b { color: #079455; }
.lr-facts .score-good b { color: #2563eb; }
.lr-facts .score-average b { color: #b54708; }
.lr-facts .score-poor b { color: #d92d20; }
.lr-fact-sep { width: 3px; height: 3px; border-radius: 50%; background: #e4e7ec; }

.lr-ops { display: flex; gap: 5px; flex-shrink: 0; }
.lr-op {
  padding: 4px 10px;
  border: 1px solid #ebedf0;
  border-radius: 7px;
  background: #fff;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  color: #475467;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.lr-op:hover { border-color: #2563eb; color: #2563eb; background: #eff4ff; }
.lr-op.is-primary {
  border-color: transparent;
  background: #2563eb;
  color: #fff;
}
.lr-op.is-primary:hover { background: #1d4ed8; color: #fff; }

/* ===== 移动行 ===== */
.lr-mrow {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 1px solid #f0f2f5;
  border-radius: 9px;
  background: #fff;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.lr-mrow:active { background: #f7f9fd; }
.lr-mmain { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.lr-mname {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  font-weight: 650;
  color: #101828;
}
.lr-msub {
  font-size: 11.5px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lr-mnote {
  font-size: 11.5px;
  line-height: 1.4;
  color: #b42318;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lr-mnum {
  flex-shrink: 0;
  display: flex;
  align-items: baseline;
  gap: 1px;
}
.lr-mnum b {
  font-size: 13.5px;
  font-weight: 700;
  color: #101828;
  font-variant-numeric: tabular-nums;
}
.lr-mnum i {
  font-style: normal;
  font-size: 10.5px;
  color: #98a2b3;
  margin: 0 5px 0 1px;
}
.lr-mnum i:last-child { margin-right: 0; }

.lr-empty {
  padding: 14px 8px;
  text-align: center;
  font-size: 12px;
  color: #b0b7c3;
  border: 1px dashed #e7eaf0;
  border-radius: 8px;
}

.lr-foot {
  margin: 3px 0 0;
  padding: 8px 11px;
  border-radius: 8px;
  background: #f7f9fc;
  font-size: 11.5px;
  line-height: 1.6;
  color: #98a2b3;
}
.lr-foot b { color: #667085; font-weight: 600; }
</style>
