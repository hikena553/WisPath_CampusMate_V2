<template>
  <!-- 审批管理子页面 -->
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="18"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">审批管理</span>
      <div class="sub-page-head-spacer"></div>
    </div>
    <div class="sub-page-body">
      <!-- Tabs: 待审批 / 已通过 / 已拒绝 / 统计 -->
      <el-tabs v-model="approvalActiveTab" @tab-change="loadApprovalData">
        <el-tab-pane label="待审批" name="pending">
          <!-- 请假申请列表 -->
          <section class="tui-section">
            <div class="tui-section-head">
              <h3><el-icon><Document /></el-icon>请假申请</h3>
              <div class="tui-section-extra">
                <span v-if="approvalPendingLeaves.length" class="tui-tag tui-tag-warn">{{ approvalPendingLeaves.length }} 条待批</span>
              </div>
            </div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>AI 已给出初步建议，仅供参考；通过后学生将收到通知，拒绝需填写理由。</span>
            </div>
            <div v-if="approvalPendingLeaves.length === 0" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><Document /></el-icon></span>
              <span class="tui-empty-title">暂无待批请假</span>
              <span class="tui-empty-desc">新的请假申请提交后会实时出现在这里</span>
            </div>
            <div v-for="row in approvalPaginatedPendingLeaves" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-title">{{ row.student_name }}</span>
                <span class="tui-tag">{{ approvalTypeLabel(row.leave_type) }}</span>
              </div>
              <div class="ap-card-meta">{{ row.start_date }} ~ {{ row.end_date }}</div>
              <div v-if="row.reason" class="ap-card-desc">{{ row.reason }}</div>
              <div v-if="approvalAnalysisMap[row.id]" class="ap-analysis">
                <span class="tui-tag" :class="approvalAnalysisMap[row.id].suggestion === 'approve' ? 'tui-tag-success' : 'tui-tag-danger'">
                  {{ approvalAnalysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                </span>
                <span class="ap-analysis-reason">{{ approvalAnalysisMap[row.id].reason }}</span>
              </div>
              <div v-else class="ap-analysis">
                <span class="tui-tag"><el-icon class="is-loading"><Loading /></el-icon> 分析中</span>
              </div>
              <div class="ap-actions">
                <el-button type="success" size="small" @click="approvalHandleApprove(row)"><el-icon><Check /></el-icon> 通过</el-button>
                <el-button type="danger" size="small" plain @click="approvalShowReject(row)"><el-icon><Close /></el-icon> 拒绝</el-button>
              </div>
            </div>
            <div v-if="approvalPendingLeaves.length > approvalPageSize" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="approvalCurrentPageLeaves"
                v-model:page-size="approvalPageSize"
                :page-sizes="[10, 20, 50]"
                :total="approvalPendingLeaves.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="approvalOnSizeChange"
                @current-change="approvalOnCurrentChange"
              />
            </div>
          </section>

          <!-- 办事申请列表 -->
          <section class="tui-section">
            <div class="tui-section-head">
              <h3><el-icon><Document /></el-icon>办事申请</h3>
              <div class="tui-section-extra">
                <span v-if="approvalPendingTickets.length" class="tui-tag tui-tag-warn">{{ approvalPendingTickets.length }} 条待批</span>
              </div>
            </div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>办事申请来自学生端提交，通过或拒绝都会即时反馈给学生。</span>
            </div>
            <div v-if="approvalPendingTickets.length === 0" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><Document /></el-icon></span>
              <span class="tui-empty-title">暂无待办申请</span>
              <span class="tui-empty-desc">学生提交证明等办事申请后会出现在这里</span>
            </div>
            <div v-for="row in approvalPaginatedPendingTickets" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-title">{{ row.title }}</span>
                <span class="tui-tag">{{ row.type === 'leave' ? '请假' : '证明' }}</span>
              </div>
              <div v-if="row.content" class="ap-card-desc">{{ row.content }}</div>
              <div class="ap-actions">
                <el-button type="success" size="small" @click="approvalHandleTicketApprove(row)"><el-icon><Check /></el-icon> 通过</el-button>
                <el-button type="danger" size="small" plain @click="approvalHandleTicketReject(row)"><el-icon><Close /></el-icon> 拒绝</el-button>
              </div>
            </div>
            <div v-if="approvalPendingTickets.length > approvalPageSize" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="approvalCurrentPageTickets"
                v-model:page-size="approvalPageSize"
                :page-sizes="[10, 20, 50]"
                :total="approvalPendingTickets.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="approvalOnSizeChange"
                @current-change="approvalOnCurrentChange"
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="已通过" name="approved">
          <section class="tui-section">
            <div class="tui-section-head">
              <h3><el-icon><CircleCheck /></el-icon>已通过请假</h3>
            </div>
            <div class="tui-section-hint success">
              <el-icon><InfoFilled /></el-icon>
              <span>已通过的请假需在返校后确认销假，闭环后才算完成。</span>
            </div>
            <div v-if="approvalApprovedLeaves.length === 0" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><CircleCheck /></el-icon></span>
              <span class="tui-empty-title">暂无已通过请假</span>
              <span class="tui-empty-desc">审批通过的请假记录会在此留痕，便于核对销假</span>
            </div>
            <div v-for="row in approvalPaginatedApprovedLeaves" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-title">{{ row.student_name }}</span>
                <span class="tui-tag">{{ approvalTypeLabel(row.leave_type) }}</span>
              </div>
              <div class="ap-card-meta">{{ row.start_date }} ~ {{ row.end_date }}</div>
              <div class="ap-card-foot">
                <span class="tui-tag" :class="row.return_confirmed ? 'tui-tag-success' : 'tui-tag-warn'">
                  {{ row.return_confirmed ? '已销假' : '待销假' }}
                </span>
                <el-button v-if="!row.return_confirmed" type="primary" size="small" @click="approvalConfirmReturn(row)">确认返校</el-button>
                <span v-else class="ap-closed">已闭环</span>
              </div>
            </div>
            <div v-if="approvalApprovedLeaves.length > approvalPageSize" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="approvalCurrentPageApprovedLeaves"
                v-model:page-size="approvalPageSize"
                :page-sizes="[10, 20, 50]"
                :total="approvalApprovedLeaves.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="approvalOnSizeChange"
                @current-change="approvalOnCurrentChange"
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="已拒绝" name="rejected">
          <section class="tui-section">
            <div class="tui-section-head">
              <h3><el-icon><Close /></el-icon>已拒绝请假</h3>
            </div>
            <div class="tui-section-hint danger">
              <el-icon><InfoFilled /></el-icon>
              <span>被拒申请会保留拒绝理由，便于后续复核与沟通。</span>
            </div>
            <div v-if="approvalRejectedLeaves.length === 0" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><Close /></el-icon></span>
              <span class="tui-empty-title">暂无已拒绝请假</span>
              <span class="tui-empty-desc">被拒绝的请假会连同理由记录在此</span>
            </div>
            <div v-for="row in approvalPaginatedRejectedLeaves" :key="row.id" class="ap-card">
              <div class="ap-card-head">
                <span class="ap-card-title">{{ row.student_name }}</span>
                <span class="tui-tag">{{ approvalTypeLabel(row.leave_type) }}</span>
              </div>
              <div class="ap-card-meta">{{ row.start_date }} ~ {{ row.end_date }}</div>
              <div v-if="row.reject_reason" class="ap-card-reject">拒绝理由：{{ row.reject_reason }}</div>
              <div class="ap-card-foot"><span class="tui-tag tui-tag-danger">已拒绝</span></div>
            </div>
            <div v-if="approvalRejectedLeaves.length > approvalPageSize" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="approvalCurrentPageRejectedLeaves"
                v-model:page-size="approvalPageSize"
                :page-sizes="[10, 20, 50]"
                :total="approvalRejectedLeaves.length"
                :pager-count="5"
                small
                background
                layout="total, prev, pager, next"
                @size-change="approvalOnSizeChange"
                @current-change="approvalOnCurrentChange"
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="统计" name="stats">
          <div class="ms-stat-summary">
            <div class="ms-stat-box"><span class="ms-stat-num">{{ approvalLeaveStats.total }}</span><span class="ms-stat-label">总申请</span></div>
            <div class="ms-stat-box"><span class="ms-stat-num ok">{{ approvalLeaveStats.approved }}</span><span class="ms-stat-label">已通过</span></div>
            <div class="ms-stat-box"><span class="ms-stat-num warn">{{ approvalLeaveStats.pending }}</span><span class="ms-stat-label">待审批</span></div>
            <div class="ms-stat-box"><span class="ms-stat-num danger">{{ approvalLeaveStats.rejected }}</span><span class="ms-stat-label">已拒绝</span></div>
            <div class="ms-stat-box"><span class="ms-stat-num brand">{{ approvalLeaveStats.awaiting_return }}</span><span class="ms-stat-label">待销假</span></div>
          </div>

          <section class="tui-section">
            <div class="tui-section-head"><h3>按请假类型</h3></div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>按类型统计的审批分布，帮助判断请假集中在哪类情形。</span>
            </div>
            <div v-if="approvalLeaveStats.by_type.length === 0" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><Document /></el-icon></span>
              <span class="tui-empty-title">暂无数据</span>
              <span class="tui-empty-desc">有审批记录后会自动生成类型分布</span>
            </div>
            <div v-for="item in approvalLeaveStats.by_type" :key="item.key" class="ms-stat-row">
              <div class="ms-stat-row-head"><span>{{ item.label }}</span><span>{{ item.total }} 条</span></div>
              <div class="ms-stat-bar">
                <div class="ms-seg seg-approved" :style="{ width: approvalPct(item.approved, item.total) }"></div>
                <div class="ms-seg seg-pending" :style="{ width: approvalPct(item.pending, item.total) }"></div>
                <div class="ms-seg seg-rejected" :style="{ width: approvalPct(item.rejected, item.total) }"></div>
              </div>
            </div>
          </section>

          <section class="tui-section">
            <div class="tui-section-head"><h3>按班级分布</h3></div>
            <div class="tui-section-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>按班级统计的审批分布，便于发现集中请假的班级。</span>
            </div>
            <div v-if="approvalLeaveStats.by_class.length === 0" class="tui-empty">
              <span class="tui-empty-icon"><el-icon :size="22"><Document /></el-icon></span>
              <span class="tui-empty-title">暂无数据</span>
              <span class="tui-empty-desc">有审批记录后会自动生成班级分布</span>
            </div>
            <div v-for="item in approvalLeaveStats.by_class" :key="item.key" class="ms-stat-row">
              <div class="ms-stat-row-head"><span>{{ item.label }}</span><span>{{ item.total }} 条</span></div>
              <div class="ms-stat-bar">
                <div class="ms-seg seg-approved" :style="{ width: approvalPct(item.approved, item.total) }"></div>
                <div class="ms-seg seg-pending" :style="{ width: approvalPct(item.pending, item.total) }"></div>
                <div class="ms-seg seg-rejected" :style="{ width: approvalPct(item.rejected, item.total) }"></div>
              </div>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 拒绝对话框 -->
    <!-- 拒绝理由（1 字段：移动端=底部动作面板） -->
    <ActionSheet
      v-model="approvalRejectVisible"
      title="拒绝理由"
      width="380px"
      align-center
      :close-on-click-modal="false"
      class="tui-dialog"
    >
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>拒绝「{{ approvalRejectTarget?.student_name || '该生' }}」的请假申请，理由将同步给学生。</span>
      </div>
      <el-input v-model="approvalRejectReason" type="textarea" :rows="3" placeholder="请填写拒绝理由" maxlength="200" show-word-limit />
      <template #footer>
        <el-button @click="approvalRejectVisible = false">取消</el-button>
        <el-button type="danger" @click="approvalConfirmReject">确认拒绝</el-button>
      </template>
    </ActionSheet>

    <!-- 工单审批（1 字段：移动端=底部动作面板） -->
    <ActionSheet
      :title="approvalTicketAction === 'approve' ? '通过申请' : '拒绝申请'"
      v-model="approvalTicketVisible"
      width="380px"
      align-center
      :close-on-click-modal="false"
      class="tui-dialog"
    >
      <div class="tui-section-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>{{ approvalTicketAction === 'approve' ? '通过该办事申请后学生将收到通知。' : '拒绝需填写意见，学生将收到拒绝原因。' }}</span>
      </div>
      <el-input v-model="approvalTicketComment" type="textarea" :rows="3" :placeholder="approvalTicketAction === 'approve' ? '审批意见（选填）' : '拒绝意见（必填），如：材料不全，请补充后重新提交'" maxlength="500" show-word-limit />
      <template #footer>
        <el-button @click="approvalTicketVisible = false">取消</el-button>
        <el-button :type="approvalTicketAction === 'approve' ? 'success' : 'danger'" @click="approvalConfirmTicketReview">
          {{ approvalTicketAction === 'approve' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </ActionSheet>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
// v6.1 弹窗减负：单字段审批走底部动作面板
import ActionSheet from '@/components/common/ActionSheet.vue'
import { ArrowLeft, CircleCheck, Close, Document, InfoFilled, Loading } from '@element-plus/icons-vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave, confirmLeaveReturn, getLeaveStats, type LeaveStats } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import type { LeaveRequestOut, ServiceTicket } from '@/types'
import { ElMessage } from 'element-plus'

const emit = defineEmits<{ close: [] }>()

// ===== 审批管理子页面 =====
const approvalActiveTab = ref('pending')
const approvalPendingLeaves = ref<LeaveRequestOut[]>([])
const approvalPendingTickets = ref<ServiceTicket[]>([])
const approvalApprovedLeaves = ref<LeaveRequestOut[]>([])
const approvalRejectedLeaves = ref<LeaveRequestOut[]>([])
const approvalLeaveStats = ref<LeaveStats>({
  total: 0, approved: 0, rejected: 0, pending: 0, awaiting_return: 0,
  by_type: [], by_class: [],
})
const approvalAnalysisMap = ref<Record<number, { suggestion: string; reason: string }>>({})
const approvalRejectVisible = ref(false)
const approvalRejectTarget = ref<LeaveRequestOut | null>(null)
const approvalRejectReason = ref('')
// 工单审批弹窗状态
const approvalTicketVisible = ref(false)
const approvalTicketTarget = ref<ServiceTicket | null>(null)
const approvalTicketAction = ref<'approve' | 'reject'>('approve')
const approvalTicketComment = ref('')
// 分页（按契约第 2 节统一：pageSize 默认 10）
const approvalPageSize = ref(10)
const approvalCurrentPageLeaves = ref(1)
const approvalCurrentPageTickets = ref(1)
const approvalCurrentPageApprovedLeaves = ref(1)
const approvalCurrentPageRejectedLeaves = ref(1)

const approvalPaginatedPendingLeaves = computed(() => {
  const start = (approvalCurrentPageLeaves.value - 1) * approvalPageSize.value
  return approvalPendingLeaves.value.slice(start, start + approvalPageSize.value)
})
const approvalPaginatedPendingTickets = computed(() => {
  const start = (approvalCurrentPageTickets.value - 1) * approvalPageSize.value
  return approvalPendingTickets.value.slice(start, start + approvalPageSize.value)
})
const approvalPaginatedApprovedLeaves = computed(() => {
  const start = (approvalCurrentPageApprovedLeaves.value - 1) * approvalPageSize.value
  return approvalApprovedLeaves.value.slice(start, start + approvalPageSize.value)
})
const approvalPaginatedRejectedLeaves = computed(() => {
  const start = (approvalCurrentPageRejectedLeaves.value - 1) * approvalPageSize.value
  return approvalRejectedLeaves.value.slice(start, start + approvalPageSize.value)
})

function approvalTypeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

function approvalOnSizeChange() {
  approvalCurrentPageLeaves.value = 1
  approvalCurrentPageTickets.value = 1
  approvalCurrentPageApprovedLeaves.value = 1
  approvalCurrentPageRejectedLeaves.value = 1
}
function approvalOnCurrentChange() { /* v-model 已同步当前页 */ }

async function loadApprovalData() {
  if (approvalActiveTab.value === 'pending') {
    try {
      approvalPendingLeaves.value = await getPendingLeaves()
      approvalLoadAnalysis()
    } catch {}
    try { approvalPendingTickets.value = (await getTickets()).filter((t: ServiceTicket) => t.status === 'pending') } catch {}
  } else if (approvalActiveTab.value === 'approved') {
    try { approvalApprovedLeaves.value = await getAllLeaves('approved') } catch {}
  } else if (approvalActiveTab.value === 'rejected') {
    try { approvalRejectedLeaves.value = await getAllLeaves('rejected') } catch {}
  } else if (approvalActiveTab.value === 'stats') {
    try { approvalLeaveStats.value = await getLeaveStats() } catch { /* 统计失败不影响其它 Tab */ }
  }
}

/** 统计条形图分段宽度百分比 */
function approvalPct(part: number, total: number) {
  if (!total) return '0%'
  return `${Math.round((part / total) * 100)}%`
}

async function approvalConfirmReturn(row: LeaveRequestOut) {
  try {
    await confirmLeaveReturn(row.id)
    ElMessage.success('已确认返校')
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

function chunkArray<T>(arr: T[], size: number): T[][] {
  const result: T[][] = []
  for (let i = 0; i < arr.length; i += size) result.push(arr.slice(i, i + size))
  return result
}

async function approvalLoadAnalysis() {
  const todo = approvalPendingLeaves.value.filter((leave) => !approvalAnalysisMap.value[leave.id])
  for (const leave of todo) approvalAnalysisMap.value[leave.id] = { suggestion: 'approve', reason: '分析中...' }
  const batches = chunkArray(todo, 4)
  for (const batch of batches) {
    const results = await Promise.all(batch.map(async (leave) => {
      try { return { id: leave.id, result: await analyzeLeave(leave.id) } }
      catch { return { id: leave.id, result: { suggestion: 'approve', reason: 'AI分析暂时不可用' } } }
    }))
    for (const { id, result } of results) approvalAnalysisMap.value[id] = result
  }
}

async function approvalHandleApprove(row: LeaveRequestOut) {
  try {
    await reviewLeaveApi(row.id, 'approve')
    ElMessage.success('已通过')
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

function approvalShowReject(row: LeaveRequestOut) {
  approvalRejectTarget.value = row
  approvalRejectReason.value = ''
  approvalRejectVisible.value = true
}

async function approvalConfirmReject() {
  if (!approvalRejectReason.value.trim()) { ElMessage.warning('请填写拒绝理由'); return }
  if (!approvalRejectTarget.value) return
  try {
    await reviewLeaveApi(approvalRejectTarget.value.id, 'reject', approvalRejectReason.value)
    ElMessage.success('已拒绝')
    approvalRejectVisible.value = false
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

async function approvalHandleTicketApprove(row: ServiceTicket) {
  approvalTicketTarget.value = row
  approvalTicketAction.value = 'approve'
  approvalTicketComment.value = ''
  approvalTicketVisible.value = true
}

async function approvalHandleTicketReject(row: ServiceTicket) {
  approvalTicketTarget.value = row
  approvalTicketAction.value = 'reject'
  approvalTicketComment.value = ''
  approvalTicketVisible.value = true
}

async function approvalConfirmTicketReview() {
  if (!approvalTicketTarget.value) return
  if (approvalTicketAction.value === 'reject' && !approvalTicketComment.value.trim()) {
    ElMessage.warning('请填写拒绝意见')
    return
  }
  try {
    await approveTicketApi(approvalTicketTarget.value.id, approvalTicketAction.value, approvalTicketComment.value.trim() || undefined)
    ElMessage.success(approvalTicketAction.value === 'approve' ? '已通过' : '已拒绝')
    approvalTicketVisible.value = false
    loadApprovalData()
  } catch { ElMessage.error('操作失败') }
}

// v-if 挂载即加载：每次打开子页面重新挂载时拉取数据
onMounted(() => loadApprovalData())
</script>

<style scoped>
/* 子页面（移动端全屏覆盖层） */
.sub-page {
  position: fixed; inset: 0; background: var(--tui-bg);
  z-index: 100; display: flex; flex-direction: column;
}
.sub-page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: var(--tui-surface);
  border-bottom: 1px solid var(--tui-border); flex-shrink: 0;
}
.sub-page-title {
  font-size: 15px; font-weight: 600; color: var(--tui-text);
}
.sub-page-head-spacer { width: 32px; }
.sub-page-body {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.sub-page-body .tui-empty { padding: 22px 12px; gap: 8px; }
.sub-page-body .tui-empty-icon { width: 46px; height: 46px; }

/* 审批卡片（收紧尺寸） */
.ap-card {
  background: var(--tui-surface-muted);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  padding: 10px;
  margin-bottom: 8px;
}
.ap-card-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-bottom: 5px;
}
.ap-card-title {
  font-size: 13.5px; font-weight: 600; color: var(--tui-text);
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ap-card-meta { font-size: 12px; color: var(--tui-text-secondary); }
.ap-card-desc { margin-top: 3px; font-size: 12px; color: var(--tui-text-tertiary); line-height: 1.45; }
.ap-card-reject { margin-top: 4px; font-size: 12px; color: var(--tui-danger); line-height: 1.45; }
.ap-card-foot {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-top: 8px;
}
.ap-closed { font-size: 12px; color: var(--tui-text-quiet); }

.ap-analysis { display: flex; align-items: center; gap: 6px; margin-top: 6px; min-width: 0; }
.ap-analysis-reason {
  font-size: 11.5px; color: var(--tui-text-quiet);
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ap-actions { display: flex; gap: 8px; margin-top: 8px; }

/* 统计 Tab */
.ms-stat-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.ms-stat-box {
  background: var(--tui-surface);
  border-radius: var(--tui-radius-sm);
  padding: 10px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  border: 1px solid var(--tui-border);
}
.ms-stat-num { font-size: 17px; font-weight: 700; color: var(--tui-text); line-height: 1.2; font-variant-numeric: tabular-nums; }
.ms-stat-num.ok { color: var(--tui-success); }
.ms-stat-num.warn { color: var(--tui-warn); }
.ms-stat-num.danger { color: var(--tui-danger); }
.ms-stat-num.brand { color: var(--tui-brand-strong); }
.ms-stat-label { font-size: 11px; color: var(--tui-text-quiet); }

.ms-stat-row { margin-bottom: 12px; }
.ms-stat-row:last-child { margin-bottom: 0; }
.ms-stat-row-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 6px; font-size: 12.5px; font-weight: 600; color: var(--tui-text-secondary);
}
.ms-stat-row-head span:last-child { font-size: 11.5px; font-weight: 400; color: var(--tui-text-quiet); }
.ms-stat-bar {
  display: flex; height: 8px; border-radius: 999px; overflow: hidden; background: var(--tui-surface-sunken);
}
.ms-seg { height: 100%; }
.ms-seg.seg-approved { background: var(--tui-success); }
.ms-seg.seg-pending { background: var(--tui-warn); }
.ms-seg.seg-rejected { background: var(--tui-danger); }

/* 分页容器（非 .tui-page 环境下的对齐处理） */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 8px;
  padding: 4px 0 0;
}
</style>