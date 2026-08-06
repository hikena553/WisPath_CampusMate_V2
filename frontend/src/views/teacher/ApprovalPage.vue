<template>
  <div class="approval-page">
    <div class="page-header">
      <h2>审批管理</h2>
      <p class="page-sub">共 <strong>{{ totalPending }}</strong> 条待审批事项</p>
    </div>

    <el-tabs v-model="activeTab" @tab-change="loadData" class="approval-tabs">
      <el-tab-pane label="待审批" name="pending">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Document /></el-icon> 请假申请</h3>
            <el-tag v-if="pendingLeaves.length" type="warning" effect="plain" size="small">
              {{ pendingLeaves.length }} 条待批
            </el-tag>
          </div>
          <el-table :data="paginatedPendingLeaves" v-if="pendingLeaves.length" style="width:100%"
            :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="leave_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_date" label="开始日期" width="110" />
            <el-table-column prop="end_date" label="结束日期" width="110" />
            <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
            <el-table-column label="AI 分析" min-width="200">
              <template #default="{ row }">
                <div v-if="analysisMap[row.id]" class="ai-analyze">
                  <el-tag :type="analysisMap[row.id].suggestion === 'approve' ? 'success' : 'danger'" size="small" effect="plain">
                    {{ analysisMap[row.id].suggestion === 'approve' ? '建议通过' : '建议拒绝' }}
                  </el-tag>
                  <el-tooltip placement="top" :show-after="200">
                    <template #content>
                      <div style="max-width:280px;line-height:1.6;font-size:13px">{{ analysisMap[row.id].reason }}</div>
                    </template>
                    <el-icon class="analyze-tip"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
                <el-tag v-else type="info" size="small" effect="plain" class="analyzing-tag">
                  <el-icon class="is-loading"><Loading /></el-icon> 分析中
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleApprove(row)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="showReject(row)">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper" v-if="pendingLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageLeaves"
              v-model:page-size="pageSizeLeaves"
              :page-sizes="[50, 100, 200]"
              :total="pendingLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleLeaveSizeChange"
              @current-change="handleLeaveCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无待批请假" :image-size="80" />
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><Tickets /></el-icon> 办事申请</h3>
            <el-tag v-if="pendingTickets.length" type="warning" effect="plain" size="small">
              {{ pendingTickets.length }} 条待批
            </el-tag>
          </div>
          <el-table :data="paginatedPendingTickets" v-if="pendingTickets.length" style="width:100%"
            :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
            <el-table-column prop="type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.type === 'leave' ? '请假' : '证明' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleTicketApprove(row.id)">
                  <el-icon><Check /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" plain @click="handleTicketReject(row.id)">
                  <el-icon><Close /></el-icon> 拒绝
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper" v-if="pendingTickets.length > 0">
            <el-pagination
              v-model:current-page="currentPageTickets"
              v-model:page-size="pageSizeTickets"
              :page-sizes="[50, 100, 200]"
              :total="pendingTickets.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleTicketSizeChange"
              @current-change="handleTicketCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无待办申请" :image-size="80" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="已通过" name="approved">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleCheck /></el-icon> 已通过请假</h3>
          </div>
          <el-table :data="paginatedApprovedLeaves" v-if="approvedLeaves.length" style="width:100%"
            :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="leave_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_date" label="开始日期" width="110" />
            <el-table-column prop="end_date" label="结束日期" width="110" />
            <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default>
                <el-tag type="success" size="small" effect="dark">已通过</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper" v-if="approvedLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageApprovedLeaves"
              v-model:page-size="pageSizeApprovedLeaves"
              :page-sizes="[50, 100, 200]"
              :total="approvedLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleApprovedLeaveSizeChange"
              @current-change="handleApprovedLeaveCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无已通过请假" :image-size="80" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="已拒绝" name="rejected">
        <div class="section-card">
          <div class="section-header">
            <h3><el-icon><CircleClose /></el-icon> 已拒绝请假</h3>
          </div>
          <el-table :data="paginatedRejectedLeaves" v-if="rejectedLeaves.length" style="width:100%"
            :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="leave_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ typeLabel(row.leave_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_date" label="开始日期" width="110" />
            <el-table-column prop="end_date" label="结束日期" width="110" />
            <el-table-column prop="reason" label="原因" min-width="140" show-overflow-tooltip />
            <el-table-column prop="reject_reason" label="拒绝理由" min-width="140" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default>
                <el-tag type="danger" size="small" effect="dark">已拒绝</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper" v-if="rejectedLeaves.length > 0">
            <el-pagination
              v-model:current-page="currentPageRejectedLeaves"
              v-model:page-size="pageSizeRejectedLeaves"
              :page-sizes="[50, 100, 200]"
              :total="rejectedLeaves.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleRejectedLeaveSizeChange"
              @current-change="handleRejectedLeaveCurrentChange"
            />
          </div>
          <el-empty v-else description="暂无已拒绝请假" :image-size="80" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="rejectVisible" title="拒绝理由" width="420px" :close-on-click-modal="false">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请输入拒绝理由" />
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, Tickets, CircleCheck, CircleClose,
  InfoFilled, Loading, Check, Close
} from '@element-plus/icons-vue'
import { getPendingLeaves, reviewLeave as reviewLeaveApi, getAllLeaves, analyzeLeave } from '@/api/leave'
import { getTickets, approveTicket as approveTicketApi } from '@/api/service'
import type { LeaveRequestOut, ServiceTicket } from '@/types'

const activeTab = ref('pending')
const pendingLeaves = ref<LeaveRequestOut[]>([])
const pendingTickets = ref<ServiceTicket[]>([])
const approvedLeaves = ref<LeaveRequestOut[]>([])
const rejectedLeaves = ref<LeaveRequestOut[]>([])
const analysisMap = ref<Record<number, { suggestion: string; reason: string }>>({})
const rejectVisible = ref(false)
const rejectReason = ref('')
const rejectTarget = ref<LeaveRequestOut | null>(null)

// 请假分页相关状态
const currentPageLeaves = ref(1)
const pageSizeLeaves = ref(50)

// 工单分页相关状态
const currentPageTickets = ref(1)
const pageSizeTickets = ref(50)

// 已通过请假分页相关状态
const currentPageApprovedLeaves = ref(1)
const pageSizeApprovedLeaves = ref(50)

// 已拒绝请假分页相关状态
const currentPageRejectedLeaves = ref(1)
const pageSizeRejectedLeaves = ref(50)

const totalPending = computed(() => pendingLeaves.value.length + pendingTickets.value.length)

const paginatedPendingLeaves = computed(() => {
  const start = (currentPageLeaves.value - 1) * pageSizeLeaves.value
  const end = start + pageSizeLeaves.value
  return pendingLeaves.value.slice(start, end)
})

const paginatedPendingTickets = computed(() => {
  const start = (currentPageTickets.value - 1) * pageSizeTickets.value
  const end = start + pageSizeTickets.value
  return pendingTickets.value.slice(start, end)
})

const paginatedApprovedLeaves = computed(() => {
  const start = (currentPageApprovedLeaves.value - 1) * pageSizeApprovedLeaves.value
  const end = start + pageSizeApprovedLeaves.value
  return approvedLeaves.value.slice(start, end)
})

const paginatedRejectedLeaves = computed(() => {
  const start = (currentPageRejectedLeaves.value - 1) * pageSizeRejectedLeaves.value
  const end = start + pageSizeRejectedLeaves.value
  return rejectedLeaves.value.slice(start, end)
})

function handleLeaveSizeChange() {
  currentPageLeaves.value = 1
}

function handleLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleTicketSizeChange() {
  currentPageTickets.value = 1
}

function handleTicketCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleApprovedLeaveSizeChange() {
  currentPageApprovedLeaves.value = 1
}

function handleApprovedLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function handleRejectedLeaveSizeChange() {
  currentPageRejectedLeaves.value = 1
}

function handleRejectedLeaveCurrentChange() {
  // 页码变化时自动更新表格数据
}

function typeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

async function loadData() {
  if (activeTab.value === 'pending') {
    try {
      pendingLeaves.value = await getPendingLeaves()
      loadAnalysis()
    } catch {}
    try { pendingTickets.value = (await getTickets()).filter((t: ServiceTicket) => t.status === 'pending') } catch {}
  } else if (activeTab.value === 'approved') {
    try { approvedLeaves.value = await getAllLeaves('approved') } catch {}
  } else if (activeTab.value === 'rejected') {
    try { rejectedLeaves.value = await getAllLeaves('rejected') } catch {}
  }
}

async function loadAnalysis() {
  for (const leave of pendingLeaves.value) {
    if (!analysisMap.value[leave.id]) {
      analysisMap.value[leave.id] = { suggestion: 'approve', reason: '分析中...' }
      try {
        const result = await analyzeLeave(leave.id)
        console.log('[AI分析]', leave.id, result)
        analysisMap.value[leave.id] = result
      } catch (e) {
        console.error('[AI分析失败]', leave.id, e)
        analysisMap.value[leave.id] = { suggestion: 'approve', reason: 'AI分析暂时不可用' }
      }
    }
  }
}

async function handleApprove(row: LeaveRequestOut) {
  try {
    await reviewLeaveApi(row.id, 'approve')
    ElMessage.success('已通过')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

function showReject(row: LeaveRequestOut) {
  rejectTarget.value = row
  rejectReason.value = ''
  rejectVisible.value = true
}

async function confirmReject() {
  if (!rejectTarget.value) return
  try {
    await reviewLeaveApi(rejectTarget.value.id, 'reject', rejectReason.value || undefined)
    ElMessage.success('已拒绝')
    rejectVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

async function handleTicketApprove(id: number) {
  try {
    await approveTicketApi(id, 'approve')
    ElMessage.success('已通过')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

async function handleTicketReject(id: number) {
  try {
    await approveTicketApi(id, 'reject')
    ElMessage.success('已拒绝')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

onMounted(loadData)
</script>

<style scoped>
.approval-page { height: 100%; overflow-y: auto; overflow-x: hidden; padding: 8px 4px; }

.page-header {
  display: flex; align-items: baseline; gap: 12px;
  margin-bottom: 20px; padding: 0 4px;
}
.page-header h2 {
  font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0;
}
.page-sub { font-size: 14px; color: #888; margin: 0; }
.page-sub strong { color: #e6a23c; }

.approval-tabs { --el-tabs-header-height: 44px; }
.approval-tabs :deep(.el-tabs__header) { margin-bottom: 20px; }
.approval-tabs :deep(.el-tabs__item) { font-size: 14px; font-weight: 500; }
.approval-tabs :deep(.el-tabs__item.is-active) { font-weight: 600; }

.section-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 20px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}

.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.section-header h3 {
  font-size: 16px; font-weight: 600; color: #1a1a2e; margin: 0;
  display: flex; align-items: center; gap: 6px;
}

.ai-analyze { display: flex; align-items: center; gap: 6px; }
.analyze-tip { cursor: pointer; color: #909399; font-size: 16px; }
.analyze-tip:hover { color: #409eff; }
.analyzing-tag { display: inline-flex; align-items: center; gap: 4px; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 12px 0;
}
</style>
