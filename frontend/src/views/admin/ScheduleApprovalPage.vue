<template>
  <div class="page-container sc-page">
    <div class="sc-toolbar">
      <div class="sc-toolbar-left">
        <h2>调课 / 增课审批</h2>
        <span class="sc-toolbar-sum">
          待审 <b>{{ pending.length }}</b> 条 · 台账 <b>{{ all.length }}</b> 条
        </span>
      </div>
      <div class="sc-toolbar-actions">
        <el-select v-model="kindFilter" clearable placeholder="全部类型" style="width: 110px" @change="load">
          <el-option label="调课" value="swap" />
          <el-option label="增课" value="add" />
        </el-select>
        <el-select v-model="semesterFilter" clearable placeholder="全部学期" style="width: 150px" @change="load">
          <el-option v-for="s in semesterOptions" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button :icon="RefreshCw" :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <el-skeleton v-if="loading && !pending.length && !all.length" :rows="6" animated />

    <template v-else>
      <!-- 待审批 -->
      <section class="sc-section">
        <div class="sc-section-hd">
          <span class="sc-section-t">待审批</span>
          <span class="sc-section-n">{{ pending.length }}</span>
        </div>
        <el-empty v-if="!pending.length" description="没有待审批的申请" :image-size="70" />
        <div v-else class="sc-cards">
          <article v-for="r in pending" :key="r.id" class="sc-card">
            <header class="sc-card-hd">
              <span class="sc-kind" :class="`is-${r.kind}`">{{ r.kind_label }}</span>
              <b class="sc-name">{{ r.course_name }}</b>
              <span class="sc-class">{{ r.class_name }}</span>
              <span class="sc-time">{{ fmt(r.created_at) }}</span>
            </header>

            <div class="sc-compare">
              <div v-if="r.kind === 'swap'" class="sc-side is-origin">
                <span class="sc-side-lb">原排课</span>
                <span class="sc-side-v">
                  第{{ r.origin_week_no || r.origin_week_start }}周
                  {{ weekdayText(r.origin_day_of_week) }} 第{{ r.origin_start_period }}-{{ r.origin_end_period }}节
                  <em v-if="r.origin_location">{{ r.origin_location }}</em>
                </span>
              </div>
              <span v-if="r.kind === 'swap'" class="sc-arrow">→</span>
              <div class="sc-side is-target">
                <span class="sc-side-lb">{{ r.kind === 'swap' ? '调整为' : '上课时间' }}</span>
                <span class="sc-side-v">
                  第{{ r.week_start }}周
                  {{ weekdayText(r.day_of_week) }} 第{{ r.start_period }}-{{ r.end_period }}节
                  <em v-if="r.location">{{ r.location }}</em>
                </span>
              </div>
              <div class="sc-side">
                <span class="sc-side-lb">周次</span>
                <span class="sc-side-v">
                  {{ r.kind === 'swap'
                    ? `第 ${r.origin_week_no || r.origin_week_start} 周 → 第 ${r.week_start} 周（单次）`
                    : `第 ${r.week_start}-${r.week_end} 周` }}
                </span>
              </div>
              <div class="sc-side">
                <span class="sc-side-lb">申请人</span>
                <span class="sc-side-v">{{ r.applicant_name }}</span>
              </div>
            </div>

            <p v-if="r.reason" class="sc-reason">理由：{{ r.reason }}</p>
            <div v-if="r.conflicts.length" class="sc-conflict">
              <b>存在冲突，无法通过：</b>
              <span v-for="(c, i) in r.conflicts" :key="i">{{ c }}</span>
            </div>

            <footer class="sc-card-ft">
              <el-button size="small" @click="openReject(r)">驳回</el-button>
              <el-button size="small" type="primary" :disabled="r.conflicts.length > 0" @click="approve(r)">
                通过并写入课表
              </el-button>
            </footer>
          </article>
        </div>
      </section>

      <!-- 台账 -->
      <section class="sc-section">
        <div class="sc-section-hd">
          <span class="sc-section-t">申请台账</span>
          <el-segmented v-model="statusFilter" :options="STATUS_TABS" size="small" @change="load" />
        </div>
        <el-table :data="all" size="small" empty-text="暂无申请记录">
          <el-table-column label="类型" width="70">
            <template #default="{ row }">
              <span class="sc-kind" :class="`is-${row.kind}`">{{ row.kind_label }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="course_name" label="课程" min-width="120" show-overflow-tooltip />
          <el-table-column prop="class_name" label="班级" min-width="140" show-overflow-tooltip />
          <el-table-column label="调整" min-width="210">
            <template #default="{ row }">
              <span v-if="row.kind === 'swap'" class="sc-cell-origin">
                第{{ row.origin_week_no || row.origin_week_start }}周
                {{ weekdayText(row.origin_day_of_week) }} 第{{ row.origin_start_period }}-{{ row.origin_end_period }}节 →
              </span>
              第{{ row.week_start }}周 {{ weekdayText(row.day_of_week) }} 第{{ row.start_period }}-{{ row.end_period }}节
            </template>
          </el-table-column>
          <el-table-column prop="applicant_name" label="申请人" width="90" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" effect="light" :type="statusType(row.status)">{{ row.status_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="审批" min-width="150">
            <template #default="{ row }">
              <span v-if="row.approver_name">{{ row.approver_name }}<em v-if="row.reject_reason" class="sc-reject-note">：{{ row.reject_reason }}</em></span>
              <span v-else class="sc-quiet">—</span>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" width="120">
            <template #default="{ row }">{{ fmt(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <!-- 驳回弹窗 -->
    <el-dialog v-model="rejectVisible" title="驳回申请" width="440px">
      <p class="sc-dialog-tip">
        {{ rejectTarget?.class_name }}《{{ rejectTarget?.course_name }}》— {{ rejectTarget?.applicant_name }}
      </p>
      <el-input
        v-model="rejectReason"
        type="textarea"
        :rows="3"
        maxlength="300"
        show-word-limit
        placeholder="请填写驳回原因，会通知申请人"
      />
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="confirmReject">驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshCw } from 'lucide-vue-next'
import {
  getAllScheduleChanges, getPendingScheduleChanges, reviewScheduleChange,
  WEEKDAY_LABELS, type ScheduleChangeItem,
} from '@/api/scheduleChange'

const loading = ref(false)
const submitting = ref(false)
const pending = ref<ScheduleChangeItem[]>([])
const all = ref<ScheduleChangeItem[]>([])

const kindFilter = ref<string>('')
const semesterFilter = ref<string>('')
/** 台账状态筛选：空=全部 */
const statusFilter = ref<string>('')
const STATUS_TABS = [
  { label: '全部', value: '' },
  { label: '待审批', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
  { label: '已撤回', value: 'cancelled' },
]

const semesterOptions = computed(() => {
  const set = new Set<string>()
  for (const r of all.value) if (r.semester) set.add(r.semester)
  return Array.from(set).sort().reverse()
})

function weekdayText(d: number | null | undefined) {
  return (d && WEEKDAY_LABELS[d]) || '—'
}

function fmt(s: string) {
  return (s || '').slice(0, 16).replace('T', ' ')
}

function statusType(s: string): 'warning' | 'success' | 'danger' | 'info' {
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'danger'
  if (s === 'pending') return 'warning'
  return 'info'
}

async function load() {
  loading.value = true
  try {
    const [p, a] = await Promise.all([
      getPendingScheduleChanges({ kind: kindFilter.value || undefined, semester: semesterFilter.value || undefined }),
      getAllScheduleChanges({
        kind: kindFilter.value || undefined,
        semester: semesterFilter.value || undefined,
        status: statusFilter.value || undefined,
      }),
    ])
    pending.value = p
    all.value = a
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function approve(r: ScheduleChangeItem) {
  try {
    await ElMessageBox.confirm(
      `通过后将立即写入正式课表，并通知 ${r.class_name} 的学生。\n` +
        `${r.course_name} → ${weekdayText(r.day_of_week)} 第${r.start_period}-${r.end_period}节` +
        (r.location ? ` · ${r.location}` : ''),
      '确认通过',
      { type: 'warning', confirmButtonText: '通过', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    await reviewScheduleChange(r.id, 'approve')
    ElMessage.success('已通过，课表已更新')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '审批失败')
  } finally {
    submitting.value = false
  }
}

const rejectVisible = ref(false)
const rejectTarget = ref<ScheduleChangeItem | null>(null)
const rejectReason = ref('')

function openReject(r: ScheduleChangeItem) {
  rejectTarget.value = r
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject() {
  if (!rejectTarget.value) return
  if (!rejectReason.value.trim()) return ElMessage.warning('请填写驳回原因')
  submitting.value = true
  try {
    await reviewScheduleChange(rejectTarget.value.id, 'reject', rejectReason.value.trim())
    ElMessage.success('已驳回')
    rejectVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.sc-page { display: flex; flex-direction: column; gap: 12px; }

.sc-toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px; padding: 8px 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.sc-toolbar-left { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.sc-toolbar h2 { margin: 0; font-size: 16px; color: #1e293b; white-space: nowrap; }
.sc-toolbar-sum { font-size: 12px; color: #64748b; }
.sc-toolbar-sum b { color: #2563eb; font-weight: 600; }
.sc-toolbar-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.sc-section {
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px; padding: 12px 16px 14px;
}
.sc-section-hd { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.sc-section-t { font-size: 14px; font-weight: 600; color: #1e293b; }
.sc-section-n {
  min-width: 18px; height: 18px; padding: 0 6px; border-radius: 99px;
  background: #eff6ff; color: #2563eb; font-size: 11px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.sc-section-hd :deep(.el-segmented) { margin-left: auto; }

.sc-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 10px; }
.sc-card {
  border: 1px solid #fde3c8; border-radius: 9px; padding: 11px 13px; background: #fffdfa;
  display: flex; flex-direction: column; gap: 8px;
}
.sc-card-hd { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sc-kind {
  font-size: 11px; font-weight: 700; border-radius: 4px; padding: 1px 6px; white-space: nowrap;
  background: #eff6ff; color: #2563eb;
}
.sc-kind.is-add { background: #ecfdf5; color: #059669; }
.sc-name { font-size: 13.5px; color: #1e293b; }
.sc-class { font-size: 12px; color: #64748b; }
.sc-time { margin-left: auto; font-size: 11.5px; color: #94a3b8; }

.sc-compare { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.sc-side { display: flex; flex-direction: column; gap: 2px; }
.sc-side-lb { font-size: 11px; color: #94a3b8; }
.sc-side-v { font-size: 12.5px; color: #334155; }
.sc-side-v em { font-style: normal; color: #64748b; margin-left: 4px; }
.sc-side.is-origin .sc-side-v { color: #94a3b8; text-decoration: line-through; }
.sc-side.is-target .sc-side-v { font-weight: 600; color: #0f172a; }
.sc-arrow { color: #cbd5e1; font-size: 14px; }

.sc-reason { margin: 0; font-size: 12px; color: #475569; line-height: 1.65; }
.sc-conflict {
  display: flex; flex-direction: column; gap: 2px;
  font-size: 12px; color: #b45309; background: #fffbeb;
  border: 1px solid #fde68a; border-radius: 6px; padding: 6px 9px; line-height: 1.6;
}
.sc-card-ft { display: flex; justify-content: flex-end; gap: 8px; }

.sc-cell-origin { color: #94a3b8; text-decoration: line-through; margin-right: 4px; }
.sc-reject-note { font-style: normal; color: #94a3b8; }
.sc-quiet { color: #cbd5e1; }
.sc-dialog-tip { margin: 0 0 10px; font-size: 13px; color: #475569; }

@media (max-width: 767px) {
  .sc-cards { grid-template-columns: 1fr; }
  .sc-toolbar-actions { width: 100%; }
  .sc-toolbar-actions :deep(.el-select) { flex: 1; }
}
</style>
