<template>
  <div class="tui-page">
    <SubPageHeader title="心理预警工作台" sub="AI 心理预警闭环处置" fallback="/teacher/more">
      <template #right>
        <el-button text circle aria-label="刷新" :loading="loading" @click="loadAlerts">
          <el-icon :size="19"><Refresh /></el-icon>
        </el-button>
      </template>
    </SubPageHeader>

    <div class="tui-content">
      <!-- 桌面端页头（移动端由 SubPageHeader 承担标题，避免重复） -->
      <header v-if="!isMobile" class="tui-header">
        <div>
          <h2 class="tui-header-title">心理预警工作台</h2>
          <p class="tui-header-sub">AI 心理预警闭环处置：发现 → 干预 → 随访 → 闭环（v3.0 实施文档 §4）</p>
        </div>
        <div class="tui-header-actions">
          <el-button type="primary" round :icon="Refresh" :loading="loading" @click="loadAlerts">刷新</el-button>
        </div>
      </header>

      <!-- 统计总览 -->
      <div class="tui-stat-row cols-4">
        <div class="tui-stat">
          <div class="tui-stat-num">{{ alerts.length }}</div>
          <div class="tui-stat-label">全部预警</div>
        </div>
        <div class="tui-stat">
          <div class="tui-stat-num st-warn">{{ unresolved.length }}</div>
          <div class="tui-stat-label">待处置</div>
        </div>
        <div class="tui-stat">
          <div class="tui-stat-num st-danger">{{ highRisk.length }}</div>
          <div class="tui-stat-label">高危未闭环</div>
        </div>
        <div class="tui-stat">
          <div class="tui-stat-num st-success">{{ intervenedCount }}</div>
          <div class="tui-stat-label">已干预</div>
        </div>
        <div class="tui-stat">
          <div class="tui-stat-num st-purple">{{ followUpDue.length }}</div>
          <div class="tui-stat-label">待随访</div>
        </div>
      </div>

      <!-- 筛选（手写分段控件，保持 filter ref 逻辑不变） -->
      <div class="tui-seg tui-seg-wrap">
        <button type="button" class="tui-seg-item" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
        <button type="button" class="tui-seg-item" :class="{ active: filter === 'unresolved' }" @click="filter = 'unresolved'">待处置</button>
        <button type="button" class="tui-seg-item" :class="{ active: filter === 'follow_up' }" @click="filter = 'follow_up'">待随访</button>
        <button type="button" class="tui-seg-item" :class="{ active: filter === 'resolved' }" @click="filter = 'resolved'">已闭环</button>
      </div>

      <!-- 移动端：卡片列表 -->
      <template v-if="isMobile">
        <div v-if="!filtered.length" class="tui-empty">
          <span class="tui-empty-icon"><el-icon :size="26"><WarningFilled /></el-icon></span>
          <span class="tui-empty-title">暂无预警记录</span>
        </div>

        <div v-else class="tui-stack">
          <article v-for="row in filtered" :key="row.id" class="tui-card">
            <div class="tui-row">
              <span class="stu-avatar">{{ row.student_name.slice(0, 1) }}</span>
              <span class="tui-row-main">
                <span class="tui-row-label">{{ row.student_name }}</span>
                <span class="wb-summary tui-ellipsis-2">{{ row.summary }}</span>
              </span>
              <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
            </div>

            <div class="wb-alert-meta tui-meta">
              <span>{{ formatTime(row.created_at) }}</span>
              <span class="tui-meta-sep">·</span>
              <el-tag :type="row.resolved ? 'success' : 'warning'" size="small" effect="plain">
                {{ row.resolved ? '已闭环' : '待处置' }}
              </el-tag>
              <template v-if="row.follow_up_date">
                <span class="tui-meta-sep">·</span>
                <span :class="{ 'fu-due': isFollowUpDue(row) }">
                  随访 {{ row.follow_up_date }}{{ isFollowUpDue(row) ? ' · 已到期' : '' }}
                </span>
              </template>
            </div>

            <div v-if="row.intervention_type" class="wb-alert-note">
              <el-tag size="small" type="success" effect="light">{{ row.intervention_type }}</el-tag>
              <span class="note-text">{{ row.intervention_note || '未填写备注' }}</span>
            </div>

            <div class="wb-alert-ops">
              <el-button size="small" type="primary" plain round :disabled="row.resolved" @click="openIntervene(row)">
                干预处置
              </el-button>
              <el-button size="small" text type="success" :disabled="row.resolved" @click="handleResolve(row)">标记闭环</el-button>
            </div>
          </article>
        </div>
      </template>

      <!-- 桌面端：表格 -->
      <el-table v-if="!isMobile" v-loading="loading" :data="filtered" class="wb-table" empty-text="暂无预警记录">
        <el-table-column label="学生" min-width="120">
          <template #default="{ row }">
            <div class="stu-cell">
              <span class="stu-avatar">{{ row.student_name.slice(0, 1) }}</span>
              <span class="stu-name">{{ row.student_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="90">
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.level)" size="small" effect="dark">{{ levelText(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="预警时间" width="150">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="风险摘要" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.summary }}</template>
        </el-table-column>
        <el-table-column label="处置记录" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="row.intervention_type">
              <el-tag size="small" type="success" effect="light" style="margin-right:4px">{{ row.intervention_type }}</el-tag>
              <span class="note-text">{{ row.intervention_note || '未填写备注' }}</span>
            </template>
            <span v-else class="note-text muted">尚未干预</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.resolved ? 'success' : 'warning'" size="small" effect="plain">
              {{ row.resolved ? '已闭环' : '待处置' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="随访" width="130">
          <template #default="{ row }">
            <template v-if="row.follow_up_date">
              <span :class="{ 'fu-due': isFollowUpDue(row) }">
                {{ row.follow_up_date }}{{ isFollowUpDue(row) ? ' · 已到期' : '' }}
              </span>
            </template>
            <span v-else class="note-text muted">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain round :disabled="row.resolved" @click="openIntervene(row)">
              干预处置
            </el-button>
            <el-button size="small" text type="success" :disabled="row.resolved" @click="handleResolve(row)">标记闭环</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 干预弹窗 -->
      <el-dialog v-model="dialogVisible" title="预警干预处置" width="480px" destroy-on-close>
        <el-form label-width="90px" v-if="current">
          <el-form-item label="学生">
            <span style="font-weight:600">{{ current.student_name }}</span>
            <el-tag :type="levelTagType(current.level)" size="small" effect="dark" style="margin-left:8px">
              {{ levelText(current.level) }}
            </el-tag>
          </el-form-item>
          <el-form-item label="风险摘要">
            <div class="summary-box">{{ current.summary }}</div>
          </el-form-item>
          <el-form-item label="干预方式">
            <el-radio-group v-model="form.intervention_type">
              <el-radio value="谈话">谈话疏导</el-radio>
              <el-radio value="约谈家长">约谈家长</el-radio>
              <el-radio value="转介心理咨询">转介心理咨询</el-radio>
              <el-radio value="其他">其他</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="处置备注">
            <el-input v-model="form.intervention_note" type="textarea" :rows="3" placeholder="记录本次处置过程，供后续随访参考……" maxlength="300" show-word-limit />
          </el-form-item>
          <el-form-item label="随访日期">
            <el-date-picker v-model="form.follow_up_date" type="date" value-format="YYYY-MM-DD" placeholder="计划跟进时间" style="width:100%" />
          </el-form-item>
          <el-form-item label="处置结果">
            <el-switch v-model="form.resolved" active-text="已闭环" inactive-text="持续跟进" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitIntervene">保存处置</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { getAlerts, resolveAlert, interveneAlert } from '@/api/crisis'
import type { CrisisAlert } from '@/types'

const { isMobile } = useResponsive()

const alerts = ref<CrisisAlert[]>([])
const loading = ref(false)
const filter = ref<'all' | 'unresolved' | 'follow_up' | 'resolved'>('all')

const dialogVisible = ref(false)
const current = ref<CrisisAlert | null>(null)
const submitting = ref(false)
const form = ref({
  intervention_type: '谈话',
  intervention_note: '',
  follow_up_date: '',
  resolved: true,
})

const unresolved = computed(() => alerts.value.filter(a => !a.resolved))
const highRisk = computed(() => alerts.value.filter(a => !a.resolved && a.level === 'severe'))
const intervenedCount = computed(() => alerts.value.filter(a => a.intervention_type).length)

/** 随访日期已到期且未闭环 */
function isFollowUpDue(row: CrisisAlert) {
  if (row.resolved || !row.follow_up_date) return false
  return row.follow_up_date <= new Date().toISOString().slice(0, 10)
}
const followUpDue = computed(() => alerts.value.filter(isFollowUpDue))

const filtered = computed(() => {
  if (filter.value === 'unresolved') return unresolved.value
  if (filter.value === 'follow_up') return followUpDue.value
  if (filter.value === 'resolved') return alerts.value.filter(a => a.resolved)
  return alerts.value
})

function levelText(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度', normal: '正常' }
  return map[level] || level || '未知'
}

function levelTagType(level: string): 'danger' | 'warning' | 'info' | 'success' {
  const map: Record<string, 'danger' | 'warning' | 'info' | 'success'> = {
    severe: 'danger', moderate: 'warning', mild: 'info', normal: 'success',
  }
  return map[level] || 'info'
}

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadAlerts() {
  loading.value = true
  try {
    alerts.value = await getAlerts()
  } catch {
    ElMessage.error('预警加载失败')
  } finally {
    loading.value = false
  }
}

function openIntervene(row: CrisisAlert) {
  current.value = row
  form.value = {
    intervention_type: row.intervention_type || '谈话',
    intervention_note: row.intervention_note || '',
    follow_up_date: row.follow_up_date || '',
    resolved: true,
  }
  dialogVisible.value = true
}

async function submitIntervene() {
  if (!current.value) return
  submitting.value = true
  try {
    await interveneAlert(current.value.id, {
      intervention_type: form.value.intervention_type,
      intervention_note: form.value.intervention_note || undefined,
      follow_up_date: form.value.follow_up_date || undefined,
      resolved: form.value.resolved,
    })
    ElMessage.success('干预记录已保存')
    dialogVisible.value = false
    loadAlerts()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

async function handleResolve(row: CrisisAlert) {
  try {
    await ElMessageBox.confirm(`确认将「${row.student_name}」的预警标记为已闭环？`, '闭环确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await resolveAlert(row.id, true)
    ElMessage.success('已标记闭环')
    loadAlerts()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(loadAlerts)
</script>

<style scoped>
/* 统计卡数值语义色（仅用现有 tui-stat-num，不新增全局类） */
.tui-stat-num.st-warn { color: #b54708; }
.tui-stat-num.st-danger { color: #d92d20; }
.tui-stat-num.st-success { color: #079455; }
.tui-stat-num.st-purple { color: #6941c6; }

/* 桌面端表格 */
.wb-table {
  background: #fff;
  border-radius: var(--tui-radius);
  overflow: hidden;
}

.stu-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 学生首字头像：改为纯色（去除渐变），移动端卡片与桌面表格共用 */
.stu-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tui-brand-strong);
  font-size: 13px;
  font-weight: 600;
  background: var(--tui-brand-soft);
  flex-shrink: 0;
}

.stu-name { font-weight: 600; color: #1f2937; }

.note-text { font-size: 12px; color: #4b5563; }
.note-text.muted { color: #9ca3af; }

.fu-due { color: #b54708; font-weight: 600; }

.summary-box {
  width: 100%;
  background: #f7f9fc;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}

/* 移动端卡片列表 */
.wb-summary {
  font-size: 12.5px;
  color: var(--tui-text-tertiary);
  line-height: 1.5;
}
.wb-alert-meta {
  padding: 9px 16px 0;
}
.wb-alert-note {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px 0;
  font-size: 12px;
  color: var(--tui-text-secondary);
}
.wb-alert-ops {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 10px 12px 12px 16px;
}
</style>