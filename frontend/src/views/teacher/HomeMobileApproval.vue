<template>
  <!-- 审批管理子页面 -->
  <!-- transition removed -->
  <div class="sub-page">
    <div class="sub-page-header">
      <el-button text circle @click="emit('close')"><el-icon :size="20"><ArrowLeft /></el-icon></el-button>
      <span class="sub-page-title">审批管理</span>
      <div style="width:36px"></div>
    </div>
    <div class="sub-page-body" style="padding:12px 16px">
      <!-- Tabs: 待审批 / 已通过 / 已拒绝 -->
      <el-tabs v-model="approvalActiveTab" @tab-change="loadApprovalData">
        <el-tab-pane label="待审批" name="pending">
          <!-- 请假申请列表 -->
          <div class="mobile-section-card" style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
              <span style="font-weight:600;font-size:14px">请假申请</span>
              <el-tag v-if="approvalPendingLeaves.length" type="warning" size="small" effect="plain">{{ approvalPendingLeaves.length }} 条待批</el-tag>
            </div>
            <div v-if="approvalPendingLeaves.length === 0" class="empty-tip-small">暂无待批请假</div>
            <div v-for="row in approvalPaginatedPendingLeaves" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:600;font-size:14px">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ approvalTypeLabel(row.leave_type) }}</el-tag>
              </div>
              <div style="font-size:13px;color:#666;margin-bottom:4px">{{ row.start_date }} ~ {{ row.end_date }}</div>
              <div v-if="row.reason" style="font-size:13px;color:#999;margin-bottom:8px;line-height:1.4">{{ row.reason }}</div>
              <div v-if="approvalAnalysisMap[row.id]" style="margin-bottom:8px">
                <el-tag :type="approvalAnalysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                  {{ approvalAnalysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                </el-tag>
                <span style="font-size:12px;color:#999;margin-left:6px">{{ approvalAnalysisMap[row.id].reason }}</span>
              </div>
              <div v-else style="margin-bottom:8px">
                <el-tag type="info" size="small" effect="plain"><el-icon class="is-loading"><Loading /></el-icon> 分析中</el-tag>
              </div>
              <div style="display:flex;gap:8px">
                <el-button type="success" size="small" @click="approvalHandleApprove(row)"><el-icon><Check /></el-icon> 通过</el-button>
                <el-button type="danger" size="small" plain @click="approvalShowReject(row)"><el-icon><Close /></el-icon> 拒绝</el-button>
              </div>
            </div>
            <el-pagination v-if="approvalPendingLeaves.length > 0"
              v-model:current-page="approvalCurrentPageLeaves"
              :page-size="10" :total="approvalPendingLeaves.length"
              layout="prev, pager, next" small style="margin-top:8px" />
          </div>

          <!-- 办事申请列表 -->
          <div class="mobile-section-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
              <span style="font-weight:600;font-size:14px">办事申请</span>
              <el-tag v-if="approvalPendingTickets.length" type="warning" size="small" effect="plain">{{ approvalPendingTickets.length }} 条待批</el-tag>
            </div>
            <div v-if="approvalPendingTickets.length === 0" class="empty-tip-small">暂无待办申请</div>
            <div v-for="row in approvalPaginatedPendingTickets" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:600;font-size:14px">{{ row.title }}</span>
                <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
              </div>
              <div v-if="row.content" style="font-size:13px;color:#999;margin-bottom:8px;line-height:1.4">{{ row.content }}</div>
              <div style="display:flex;gap:8px">
                <el-button type="success" size="small" @click="approvalHandleTicketApprove(row)"><el-icon><Check /></el-icon> 通过</el-button>
                <el-button type="danger" size="small" plain @click="approvalHandleTicketReject(row)"><el-icon><Close /></el-icon> 拒绝</el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="已通过" name="approved">
          <div class="mobile-section-card">
            <div v-if="approvalApprovedLeaves.length === 0" class="empty-tip-small">暂无已通过请假</div>
            <div v-for="row in approvalPaginatedApprovedLeaves" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span style="font-weight:600;font-size:14px">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ approvalTypeLabel(row.leave_type) }}</el-tag>
              </div>
              <div style="font-size:13px;color:#666">{{ row.start_date }} ~ {{ row.end_date }}</div>
              <div style="margin-top:6px"><el-tag type="success" size="small" effect="dark">已通过</el-tag></div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="已拒绝" name="rejected">
          <div class="mobile-section-card">
            <div v-if="approvalRejectedLeaves.length === 0" class="empty-tip-small">暂无已拒绝请假</div>
            <div v-for="row in approvalPaginatedRejectedLeaves" :key="row.id" class="mobile-card" style="margin-bottom:8px;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,0.04)">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span style="font-weight:600;font-size:14px">{{ row.student_name }}</span>
                <el-tag size="small" effect="plain">{{ approvalTypeLabel(row.leave_type) }}</el-tag>
              </div>
              <div style="font-size:13px;color:#666">{{ row.start_date }} ~ {{ row.end_date }}</div>
              <div v-if="row.reject_reason" style="font-size:13px;color:#f56c6c;margin-top:4px">拒绝理由：{{ row.reject_reason }}</div>
              <div style="margin-top:6px"><el-tag type="danger" size="small" effect="dark">已拒绝</el-tag></div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 拒绝对话框 -->
    <el-dialog v-model="approvalRejectVisible" title="拒绝理由" width="90%" :close-on-click-modal="false">
      <el-input v-model="approvalRejectReason" type="textarea" :rows="3" placeholder="请填写拒绝理由" maxlength="200" show-word-limit />
      <template #footer>
        <el-button @click="approvalRejectVisible = false">取消</el-button>
        <el-button type="danger" @click="approvalConfirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>

    <!-- 工单审批对话框 -->
    <el-dialog :title="approvalTicketAction === 'approve' ? '通过申请' : '拒绝申请'" v-model="approvalTicketVisible" width="90%" :close-on-click-modal="false">
      <el-input v-model="approvalTicketComment" type="textarea" :rows="3" :placeholder="approvalTicketAction === 'approve' ? '审批意见（选填）' : '拒绝意见（必填），如：材料不全，请补充后重新提交'" maxlength="500" show-word-limit />
      <template #footer>
        <el-button @click="approvalTicketVisible = false">取消</el-button>
        <el-button :type="approvalTicketAction === 'approve' ? 'success' : 'danger'" @click="approvalConfirmTicketReview">
          {{ approvalTicketAction === 'approve' ? '确认通过' : '确认拒绝' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
  <!-- /transition removed -->
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft, Loading, Check, Close } from '@element-plus/icons-vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave } from '@/api/leave'
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
const approvalAnalysisMap = ref<Record<number, { suggestion: string; reason: string }>>({})
const approvalRejectVisible = ref(false)
const approvalRejectTarget = ref<LeaveRequestOut | null>(null)
const approvalRejectReason = ref('')
// 工单审批弹窗状态
const approvalTicketVisible = ref(false)
const approvalTicketTarget = ref<ServiceTicket | null>(null)
const approvalTicketAction = ref<'approve' | 'reject'>('approve')
const approvalTicketComment = ref('')
const approvalCurrentPageLeaves = ref(1)
const approvalCurrentPageTickets = ref(1)
const approvalCurrentPageApprovedLeaves = ref(1)
const approvalCurrentPageRejectedLeaves = ref(1)

const approvalPaginatedPendingLeaves = computed(() => {
  const start = (approvalCurrentPageLeaves.value - 1) * 10
  return approvalPendingLeaves.value.slice(start, start + 10)
})
const approvalPaginatedPendingTickets = computed(() => {
  const start = (approvalCurrentPageTickets.value - 1) * 10
  return approvalPendingTickets.value.slice(start, start + 10)
})
const approvalPaginatedApprovedLeaves = computed(() => {
  const start = (approvalCurrentPageApprovedLeaves.value - 1) * 10
  return approvalApprovedLeaves.value.slice(start, start + 10)
})
const approvalPaginatedRejectedLeaves = computed(() => {
  const start = (approvalCurrentPageRejectedLeaves.value - 1) * 10
  return approvalRejectedLeaves.value.slice(start, start + 10)
})

function approvalTypeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

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
  }
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
.empty-tip-small {
  text-align: center;
  color: #bbb;
  padding: 14px 0;
  font-size: 12px;
}

/* 子页面 */
.sub-page {
  position: fixed; inset: 0; background: #f5f7fa;
  z-index: 100; display: flex; flex-direction: column;
}
.sub-page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fff;
  border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
}
.sub-page-title {
  font-size: 16px; font-weight: 600; color: #1a1a1a;
}
.sub-page-body {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}

/* 移动端区块卡片 */
.mobile-section-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 1px 6px rgba(0,0,0,0.03);
}
</style>