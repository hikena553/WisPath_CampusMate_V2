﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="tui-page">
    <SubPageHeader title="班级公告" fallback="/teacher" />

    <div class="tui-content">
      <!-- 桌面端特色头部：广播语义色 + 喇叭图标。
           本页下方「触达概览」已用环形呈现触达强度与等级分布，头部不重复挂数字。 -->
      <TuiPageHero
        v-if="!isMobile"
        title="班级公告"
        sub="发布与触达：发布通知 → 标记紧急 → 置顶高优"
        :icon="Promotion"
        tone="cyan"
      />

      <!-- ===================== 桌面端骨架：触达概览横向带 + 公告卡片网格 =====================
           为什么这样改：概览是全局汇总，横向一条带即可读完「整体触达 + 等级构成」；
           公告是并列的同类卡片，双列网格比单列长列表更省纵向空间、也更便于横向扫读。 -->
      <template v-if="!isMobile">
        <!-- ① 触达概览横向带：环形 + 图例 + 三等级迷你条，一行铺开 -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><Promotion /></el-icon>触达概览</h3>
            <div class="tui-section-extra"><span class="an-total">共 {{ items.length }} 条</span></div>
          </div>
          <div class="an-band">
            <!-- 环形：整体触达强度（复用 .tui-ring，--pct = 触达率） -->
            <div class="an-band-ring">
              <span class="tui-ring is-brand" :style="{ '--pct': reachRate / 100 }">
                <span class="tui-ring-num">{{ reachRate }}%</span>
              </span>
              <span class="an-band-cap">整体触达率</span>
            </div>
            <!-- 图例（复用 .an-legend，此处在横向带内改为一行） -->
            <ul class="an-legend">
              <li><i class="dot dot-danger"></i>紧急 {{ dist.urgent }}</li>
              <li><i class="dot dot-warn"></i>重要 {{ dist.important }}</li>
              <li><i class="dot dot-quiet"></i>普通 {{ dist.normal }}</li>
            </ul>
            <!-- 三等级迷你条：各占一条横向进度，长度按占比 -->
            <div class="an-band-bars">
              <div class="an-mini">
                <span class="an-mini-label">紧急</span>
                <div class="an-mini-track"><i class="bar-danger" :style="{ width: barWidth(dist.urgent) }"></i></div>
                <span class="an-mini-num">{{ dist.urgent }}</span>
              </div>
              <div class="an-mini">
                <span class="an-mini-label">重要</span>
                <div class="an-mini-track"><i class="bar-warn" :style="{ width: barWidth(dist.important) }"></i></div>
                <span class="an-mini-num">{{ dist.important }}</span>
              </div>
              <div class="an-mini">
                <span class="an-mini-label">普通</span>
                <div class="an-mini-track"><i class="bar-brand" :style="{ width: barWidth(dist.normal) }"></i></div>
                <span class="an-mini-num">{{ dist.normal }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- ② 公告卡片网格：双列（auto-fill 320px） -->
        <section class="tui-section">
          <div class="tui-section-head">
            <h3><el-icon><Bell /></el-icon>公告流</h3>
            <div class="tui-section-extra">
              <span class="an-total">{{ items.length }} 条</span>
              <el-button class="an-publish" size="small" :icon="Plus" @click="dialogVisible = true">发布公告</el-button>
            </div>
          </div>

          <div v-if="loading" class="tui-empty">
            <span class="tui-empty-title">加载中…</span>
          </div>

          <div v-else-if="!items.length" class="tui-empty">
            <span class="tui-empty-icon"><el-icon :size="26"><Bell /></el-icon></span>
            <span class="tui-empty-title">还没有发布过公告</span>
            <span class="tui-empty-desc">发布第一条通知，让学生第一时间知晓</span>
            <el-button class="an-publish" size="small" @click="dialogVisible = true">发布第一条</el-button>
          </div>

          <div v-else class="an-grid">
            <article v-for="a in paged" :key="a.id" class="tui-card an-card" :class="{ 'is-urgent': a.urgency === 'urgent' }">
              <div class="tui-card-body">
                <div class="an-head">
                  <span v-if="a.urgency === 'urgent'" class="an-pin"><el-icon :size="11"><Top /></el-icon>置顶</span>
                  <span class="tui-chip" :class="urgencyClass(a.urgency)">{{ urgencyLabel(a.urgency) }}</span>
                  <span class="an-date">{{ (a.created_at || '').slice(0, 10) }}</span>
                </div>
                <h3 class="an-title">{{ a.title }}</h3>
                <p class="an-content tui-ellipsis-2">{{ a.content }}</p>
                <div class="an-reachbar">
                  <div class="an-reachbar-head">
                    <span>触达率<em v-if="reachDetail(a)" class="an-reach-detail">{{ reachDetail(a) }}</em></span>
                    <span>{{ reachOf(a) }}%</span>
                  </div>
                  <div class="an-reachbar-track">
                    <i :class="urgencyBarClass(a.urgency)" :style="{ width: reachOf(a) + '%' }"></i>
                  </div>
                </div>
                <!-- 操作沿用现有事件：附件查看 / 删除（无附件时用弱化标记占位） -->
                <div class="an-ops">
                  <a v-if="a.attachment_url" class="an-link" :href="a.attachment_url" target="_blank" rel="noopener noreferrer">查看附件</a>
                  <span v-else class="an-link an-link-muted">无附件</span>
                  <button class="an-link an-link-danger" @click="remove(a)">删除</button>
                </div>
              </div>
            </article>
          </div>

          <div v-if="items.length" class="pagination-wrapper">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50]"
              :total="items.length"
              :pager-count="5"
              small
              background
              layout="total, prev, pager, next"
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
            />
          </div>
        </section>
      </template>

      <!-- ===================== 移动端：完全保留原有纵向结构（类名 / 顺序不变） ===================== -->
      <template v-if="isMobile">

      <!-- ① 触达概览：触达率环形进度 + 等级分布 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Promotion /></el-icon>触达概览</h3>
          <div class="tui-section-extra"><span class="an-total">共 {{ items.length }} 条</span></div>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>触达率 = 已读学生数 ÷ 应读学生数（真实回执）。紧急公告会置顶高亮，且在学生端触发更强的提醒。</span>
        </div>
        <div class="an-reach">
          <span class="ring" :style="reachRingStyle"><span class="ring-mid">{{ reachRate }}%</span></span>
          <div class="an-reach-info">
            <div class="an-reach-cap">整体触达率</div>
            <ul class="an-legend">
              <li><i class="dot dot-danger"></i>紧急 {{ dist.urgent }}</li>
              <li><i class="dot dot-warn"></i>重要 {{ dist.important }}</li>
              <li><i class="dot dot-quiet"></i>普通 {{ dist.normal }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ② 公告流：置顶 / 紧急角标 + 触达进度条 -->
      <section class="tui-section">
        <div class="tui-section-head">
          <h3><el-icon><Bell /></el-icon>公告流</h3>
          <div class="tui-section-extra">
            <span class="an-total">{{ items.length }} 条</span>
            <el-button class="an-publish" size="small" :icon="Plus" @click="dialogVisible = true">发布公告</el-button>
          </div>
        </div>
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>紧急公告会置顶显示并高亮角标；进度条为真实触达率（已读 ÷ 应读）。</span>
        </div>

        <div v-if="loading" class="tui-empty">
          <span class="tui-empty-title">加载中…</span>
        </div>

        <div v-else-if="!items.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="26"><Bell /></el-icon></span>
          <span class="tui-empty-title">还没有发布过公告</span>
          <span class="tui-empty-desc">发布第一条通知，让学生第一时间知晓</span>
          <el-button class="an-publish" size="small" @click="dialogVisible = true">发布第一条</el-button>
        </div>

        <div v-else class="tui-stack">
          <article v-for="a in paged" :key="a.id" class="tui-card an-card" :class="{ 'is-urgent': a.urgency === 'urgent' }">
            <div class="tui-card-body">
              <div class="an-head">
                <span v-if="a.urgency === 'urgent'" class="an-pin"><el-icon :size="11"><Top /></el-icon>置顶</span>
                <span class="tui-chip" :class="urgencyClass(a.urgency)">{{ urgencyLabel(a.urgency) }}</span>
                <span class="an-date">{{ (a.created_at || '').slice(0, 10) }}</span>
              </div>
              <h3 class="an-title">{{ a.title }}</h3>
              <p class="an-content">{{ a.content }}</p>
              <div class="an-reachbar">
                <div class="an-reachbar-head">
                  <span>触达率<em v-if="reachDetail(a)" class="an-reach-detail">{{ reachDetail(a) }}</em></span>
                  <span>{{ reachOf(a) }}%</span>
                </div>
                <div class="an-reachbar-track">
                  <i :class="urgencyBarClass(a.urgency)" :style="{ width: reachOf(a) + '%' }"></i>
                </div>
              </div>
              <div class="an-ops">
                <a v-if="a.attachment_url" class="an-link" :href="a.attachment_url" target="_blank" rel="noopener noreferrer">查看附件</a>
                <button class="an-link an-link-danger" @click="remove(a)">删除</button>
              </div>
            </div>
          </article>
        </div>

        <div v-if="items.length" class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="items.length"
            :pager-count="5"
            small
            background
            layout="total, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </section>
      </template>

      <el-dialog
        v-model="dialogVisible"
        title="发布公告"
        :width="isMobile ? '90%' : '380px'"
        align-center
        :close-on-click-modal="false"
        class="tui-dialog"
        destroy-on-close
      >
        <div class="tui-section-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>发布后即时推送给你名下全体学生；紧急公告会置顶并高亮角标，请确认标题与内容无误。</span>
        </div>
        <div class="an-ctx">
          <span class="an-ctx-item">已发布公告 <b>{{ items.length }}</b> 条</span>
          <span class="an-ctx-item">其中紧急 <b>{{ dist.urgent }}</b> 条</span>
          <span class="an-ctx-item">公告日期 <b>{{ today }}</b></span>
        </div>
        <div class="an-form">
          <div class="an-field">
            <label class="an-label">标题</label>
            <el-input v-model="form.title" maxlength="100" placeholder="一句话说明通知主题，如：关于期中考试安排的通知" />
          </div>
          <div class="an-field">
            <label class="an-label">紧急程度</label>
            <el-select v-model="form.urgency" placeholder="请选择紧急程度" style="width: 100%">
              <el-option v-for="o in urgencyOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </div>
          <AiDraftField
            v-model="form.content"
            label="公告内容"
            required
            :rows="5"
            :maxlength="1000"
            placeholder="写清时间、地点、需要学生做什么，例如：请于周五 16:00 前到教室集中……"
            :draft="aiDraft"
            :points="aiPoints"
          />
        </div>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" :disabled="!valid" @click="submit">发布</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Bell, Plus, InfoFilled, Promotion, Top } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import AiDraftField from '@/components/teacher/ui/AiDraftField.vue'
import { useResponsive } from '@/composables/useResponsive'
import {
  createAnnouncement,
  deleteAnnouncement,
  getAnnouncementReach,
  getTeacherAnnouncements,
  type AnnouncementItem,
  type AnnouncementReachItem,
} from '@/api/announcement'

defineOptions({ name: 'teacher-announcement' })

const { isMobile } = useResponsive()

const items = ref<AnnouncementItem[]>([])
/** 触达回执：announcement_id → { read, total, rate }（真实已读口径） */
const reachMap = ref<Record<number, AnnouncementReachItem>>({})
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const form = reactive({ title: '', content: '', urgency: 'normal' as AnnouncementItem['urgency'] })

const urgencyOptions: { value: AnnouncementItem['urgency']; label: string }[] = [
  { value: 'normal', label: '普通通知' },
  { value: 'important', label: '重要通知' },
  { value: 'urgent', label: '紧急通知' },
]

/** 今日日期（YYYY-MM-DD）：用于上下文与 AI 草稿 */
const today = new Date().toISOString().slice(0, 10)

/** AI 建议要点：随紧急程度变化 */
const aiPoints = computed(() => {
  if (form.urgency === 'urgent') return ['时间节点', '紧急事项', '回复确认', '联系方式']
  if (form.urgency === 'important') return ['事项背景', '时间与地点', '需做的准备', '截止时间']
  return ['通知事项', '时间地点', '注意事项', '反馈方式']
})

/** AI 草稿：结合所选紧急程度 + 日期，写成正式通知口吻 */
const aiDraft = computed(() => {
  if (form.urgency === 'urgent') {
    return `【紧急通知 ${today}】全体同学请注意：接学校临时安排，请立即查看本次通知的具体要求，并务必于今日按规定时间完成确认与回复，逾期将影响正常学习安排。收到请回复“已阅”。如遇特殊情况，请第一时间与我联系。`
  }
  if (form.urgency === 'important') {
    return `【重要通知 ${today}】各位同学：现将近期重要安排通知如下，请大家认真阅读并提前做好准备。请在通知要求的时间节点前完成相应事项，如有疑问及时向我反馈。请相互转告，确保人人知晓。`
  }
  return `【班级通知 ${today}】各位同学：现将近期班级安排告知大家，请留意相关时间与要求，提前做好准备。如有疑问，可在课后或群内与我沟通。感谢大家配合。`
})

const valid = computed(() => form.title.trim().length > 0 && form.content.trim().length > 0)

function urgencyLabel(u: AnnouncementItem['urgency']) {
  return u === 'urgent' ? '紧急' : u === 'important' ? '重要' : '普通'
}
function urgencyClass(u: AnnouncementItem['urgency']) {
  return u === 'urgent' ? 'tui-tag-danger' : u === 'important' ? 'tui-tag-warn' : ''
}
function urgencyBarClass(u: AnnouncementItem['urgency']) {
  return u === 'urgent' ? 'bar-danger' : u === 'important' ? 'bar-warn' : 'bar-brand'
}
/** 触达率（真实口径）：已读学生数 / 应读学生数，来自 /teacher/announcements/reach */
function reachOf(a: AnnouncementItem) {
  return reachMap.value[a.id]?.rate ?? 0
}
/** 触达明细文案：已读 / 应读（无数据时留空） */
function reachDetail(a: AnnouncementItem) {
  const r = reachMap.value[a.id]
  return r ? `${r.read}/${r.total}` : ''
}

/** 迷你分布条宽度：某等级条数占全部公告的比例（无数据时给 0，避免 NaN） */
function barWidth(n: number) {
  const total = items.value.length || 1
  return `${Math.round((n / total) * 100)}%`
}

/** 公告等级分布 */
const dist = computed(() => {
  const urgent = items.value.filter(i => i.urgency === 'urgent').length
  const important = items.value.filter(i => i.urgency === 'important').length
  return { urgent, important, normal: items.value.length - urgent - important }
})

/** 整体触达率（真实口径）：所有公告的「已读 ÷ 应读」加权汇总 */
const reachRate = computed(() => {
  const rows = items.value.map(a => reachMap.value[a.id]).filter(Boolean) as AnnouncementReachItem[]
  const sumTotal = rows.reduce((s, r) => s + r.total, 0)
  if (!sumTotal) return 0
  const sumRead = rows.reduce((s, r) => s + r.read, 0)
  return Math.round((sumRead / sumTotal) * 100)
})
const reachRingStyle = computed(() => ({
  background: `conic-gradient(var(--tui-brand) 0 ${reachRate.value}%, var(--tui-surface-sunken) ${reachRate.value}% 100%)`,
}))

/* 分页（契约第 2 节统一） */
const currentPage = ref(1)
const pageSize = ref(10)
const paged = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return items.value.slice(start, start + pageSize.value)
})
function handleSizeChange() {
  currentPage.value = 1
}
function handlePageChange() {
  /* 页码由 v-model 同步，无需额外处理 */
}
watch(() => items.value.length, () => { currentPage.value = 1 })

async function load() {
  loading.value = true
  try {
    // 公告列表与触达回执并发拉取；触达接口失败不影响列表展示
    const [list, reach] = await Promise.all([
      getTeacherAnnouncements(),
      getAnnouncementReach().catch(() => null),
    ])
    items.value = list
    const map: Record<number, AnnouncementReachItem> = {}
    for (const r of reach?.items || []) map[r.announcement_id] = r
    reachMap.value = map
  } catch {
    ElMessage.error('公告加载失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!valid.value) return
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.title.trim())
    fd.append('content', form.content.trim())
    fd.append('urgency', form.urgency)
    await createAnnouncement(fd)
    ElMessage.success('公告已发布')
    dialogVisible.value = false
    form.title = ''
    form.content = ''
    form.urgency = 'normal'
    load()
  } catch {
    ElMessage.error('发布失败')
  } finally {
    saving.value = false
  }
}

async function remove(a: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确定删除公告「${a.title}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteAnnouncement(a.id)
    ElMessage.success('已删除')
    load()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.an-total { font-size: 11.5px; color: var(--tui-text-quiet); }
/* 触达明细（已读/应读）：弱化小字，跟在「触达率」后 */
.an-reach-detail { margin-left: 5px; font-style: normal; font-size: 10.5px; color: var(--tui-text-quiet); }

/* ===== 桌面端 触达概览横向带：环形 + 图例 + 三条迷你分布条，横向一行铺开 ===== */
.an-band {
  display: flex;
  align-items: center;
  gap: 22px;
}
.an-band-ring {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}
.an-band-cap { font-size: 10.5px; color: var(--tui-text-quiet); white-space: nowrap; }
/* 图例在横向带内改为一行，避免三行竖排把带子撑高 */
.an-band .an-legend { flex-direction: row; gap: 16px; flex: 0 0 auto; }
.an-band-bars {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.an-mini { display: flex; align-items: center; gap: 10px; }
.an-mini-label { flex: 0 0 30px; font-size: 11.5px; color: var(--tui-text-secondary); }
.an-mini-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.an-mini-track > i { display: block; height: 100%; border-radius: 999px; }
.an-mini-num {
  flex: 0 0 22px;
  text-align: right;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}

/* ===== 桌面端 公告卡片网格：双列自适应（窄屏自动回退单列） ===== */
.an-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
  align-items: start;
}
/* 网格内正文改用常规换行，配合 .tui-ellipsis-2 正常截断（移动端单列仍保持 pre-wrap） */
.an-grid .an-content { white-space: normal; }
/* 无附件时的弱化标记，占位于「查看附件」同一行 */
.an-link-muted { color: var(--tui-text-quiet); cursor: default; }

/* 发布公告入口：放在「公告流」分区头部（紧邻它要写入的列表），
   采用中性描边小按钮，不再使用蓝色实心，保持简约。 */
.an-publish {
  height: 28px;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 8px;
  border-color: var(--tui-border-strong);
  background: #fff;
  color: var(--tui-text-secondary);
  font-size: 12.5px;
  font-weight: 500;
}
.an-publish:hover,
.an-publish:focus {
  background: var(--tui-surface-muted);
  border-color: #d6dbe3;
  color: var(--tui-text);
}
.an-publish :deep(.el-icon) {
  font-size: 13px;
}

/* ===== 发布弹窗：上下文信息条 ===== */
.an-ctx {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 9px;
  background: var(--tui-surface-muted);
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
.an-ctx-item b { color: var(--tui-text); font-weight: 600; }

/* ===== 触达概览：环形进度 ===== */
.an-reach {
  display: flex;
  align-items: center;
  gap: 16px;
}
.ring {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}
.ring::after {
  content: '';
  position: absolute;
  inset: 9px;
  border-radius: 50%;
  background: var(--tui-surface);
}
.ring-mid {
  position: relative;
  z-index: 1;
  font-size: 17px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--tui-text);
}
.an-reach-info { display: flex; flex-direction: column; gap: 6px; }
.an-reach-cap { font-size: 12px; font-weight: 600; color: var(--tui-text-secondary); }
.an-legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.an-legend li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--tui-text-secondary);
}
.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-danger { background: var(--tui-danger); }
.dot-warn { background: var(--tui-warn); }
.dot-quiet { background: var(--tui-border-strong); }

/* ===== 公告卡：置顶 / 角标 + 触达进度条 ===== */
.an-card.is-urgent { border-color: var(--tui-danger); }
.an-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
}
.an-date { margin-left: auto; font-size: 11px; color: var(--tui-text-quiet); }
.an-pin {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
}
.an-title {
  margin: 0 0 6px;
  font-size: 14.5px;
  font-weight: 600;
  color: var(--tui-text);
  line-height: 1.45;
}
.an-content {
  margin: 0;
  font-size: 13px;
  color: var(--tui-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}
.an-reachbar {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.an-reachbar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.an-reachbar-track {
  height: 6px;
  border-radius: 999px;
  background: var(--tui-surface-sunken);
  overflow: hidden;
}
.an-reachbar-track > i { display: block; height: 100%; border-radius: 999px; }
.bar-danger { background: var(--tui-danger); }
.bar-warn { background: var(--tui-warn); }
.bar-brand { background: var(--tui-brand); }

.an-ops {
  display: flex;
  gap: 14px;
  margin-top: 10px;
}
.an-link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12.5px;
  color: var(--tui-brand);
  text-decoration: none;
  cursor: pointer;
  font-family: inherit;
}
.an-link-danger { color: var(--tui-danger); }

/* ===== 发布弹窗表单 ===== */
.an-form { display: flex; flex-direction: column; gap: 14px; }
.an-label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
}
</style>