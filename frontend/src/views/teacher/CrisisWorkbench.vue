<template>
  <div class="crisis-workbench">
    <!-- 页头 -->
    <div class="wb-header">
      <div class="wb-header-left">
        <h2 class="wb-title">心理预警工作台</h2>
        <p class="wb-sub">AI 心理预警闭环处置：发现 → 干预 → 随访 → 闭环（v3.0 实施文档 §4）</p>
      </div>
      <el-button type="primary" round :icon="Refresh" :loading="loading" @click="loadAlerts">刷新</el-button>
    </div>

    <!-- 统计总览 -->
    <div class="wb-stats">
      <div class="wb-stat">
        <div class="wb-stat-value">{{ alerts.length }}</div>
        <div class="wb-stat-label">全部预警</div>
      </div>
      <div class="wb-stat">
        <div class="wb-stat-value warn">{{ unresolved.length }}</div>
        <div class="wb-stat-label">待处置</div>
      </div>
      <div class="wb-stat">
        <div class="wb-stat-value danger">{{ highRisk.length }}</div>
        <div class="wb-stat-label">高危未闭环</div>
      </div>
      <div class="wb-stat">
        <div class="wb-stat-value success">{{ intervenedCount }}</div>
        <div class="wb-stat-label">已干预</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="wb-filter">
      <el-radio-group v-model="filter" size="small">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="unresolved">待处置</el-radio-button>
        <el-radio-button value="resolved">已闭环</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 预警列表 -->
    <el-table v-loading="loading" :data="filtered" class="wb-table" empty-text="暂无预警记录">
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
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAlerts, resolveAlert, interveneAlert } from '@/api/crisis'
import type { CrisisAlert } from '@/types'

const alerts = ref<CrisisAlert[]>([])
const loading = ref(false)
const filter = ref<'all' | 'unresolved' | 'resolved'>('all')

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

const filtered = computed(() => {
  if (filter.value === 'unresolved') return unresolved.value
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
.crisis-workbench {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.wb-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.wb-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}

.wb-sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: #8a94a6;
}

.wb-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.wb-stat {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 14px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 4px 16px rgba(31, 41, 55, 0.04);
}

.wb-stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2937;
}

.wb-stat-value.warn { color: #e6a23c; }
.wb-stat-value.danger { color: #f56c6c; }
.wb-stat-value.success { color: #67c23a; }

.wb-stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #8a94a6;
}

.wb-filter {
  margin-bottom: 14px;
}

.wb-table {
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
}

.stu-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stu-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  background: linear-gradient(135deg, #5b8def, #8ab4ff);
  flex-shrink: 0;
}

.stu-name { font-weight: 600; color: #1f2937; }

.note-text { font-size: 12px; color: #4b5563; }
.note-text.muted { color: #9ca3af; }

.summary-box {
  width: 100%;
  background: #f7f9fc;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .crisis-workbench { padding: 12px; }
  .wb-stats { grid-template-columns: repeat(2, 1fr); }
  .wb-header { flex-direction: column; gap: 10px; }
}
</style>