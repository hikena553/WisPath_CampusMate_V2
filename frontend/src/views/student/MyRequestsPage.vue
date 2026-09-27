<template>
  <div class="my-req-page">
    <!-- 吸顶头 -->
    <div class="topbar">
      <div class="back" @click="goBack"><el-icon :size="18"><ArrowLeft /></el-icon></div>
      <div class="topbar-title">我的申请</div>
      <div class="topbar-right"></div>
    </div>

    <el-tabs v-model="activeTab" class="req-tabs" @tab-change="() => load()">
      <el-tab-pane label="请假申请" name="leave" />
      <el-tab-pane label="办事工单" name="ticket" />
    </el-tabs>

    <!-- 请假 -->
    <div v-if="activeTab === 'leave'" class="group">
      <div v-if="leaves.length" class="req-list">
        <div v-for="r in leaves" :key="r.id" class="req-card">
          <div class="req-head">
            <span class="req-title">{{ r.leave_type ? typeLabel(r.leave_type) : '请假' }}</span>
            <el-tag :type="statusType(r.status)" size="small" effect="plain">{{ statusLabel(r.status) }}</el-tag>
          </div>
          <div class="req-row"><span class="lab">时间</span><span>{{ r.start_date }} ~ {{ r.end_date }}</span></div>
          <div class="req-row" v-if="r.reason"><span class="lab">原因</span><span class="val">{{ r.reason }}</span></div>
          <div class="req-row" v-if="r.reject_reason"><span class="lab">驳回原因</span><span class="val danger">{{ r.reject_reason }}</span></div>
          <div class="req-foot">
            <span class="time">{{ r.created_at ? r.created_at.slice(0, 16) : '' }}</span>
            <el-button v-if="r.status === 'pending'" type="danger" size="small" plain @click="revokeLeave(r)">
              <el-icon><Delete /></el-icon> 撤销
            </el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无请假申请" :image-size="90" />
    </div>

    <!-- 工单（证明 / 项目） -->
    <div v-else class="group">
      <div v-if="tickets.length" class="req-list">
        <div v-for="t in tickets" :key="t.id" class="req-card">
          <div class="req-head">
            <span class="req-title">{{ t.title }}</span>
            <el-tag :type="statusType(t.status)" size="small" effect="plain">{{ statusLabel(t.status) }}</el-tag>
          </div>
          <div class="req-row"><span class="lab">类型</span><span>{{ ticketTypeLabel(t.type) }}</span></div>
          <div class="req-row" v-if="t.content"><span class="lab">内容</span><span class="val">{{ t.content }}</span></div>
          <div class="req-foot">
            <span class="time">{{ t.created_at ? t.created_at.slice(0, 16) : '' }}</span>
            <el-button v-if="t.status === 'pending'" type="danger" size="small" plain @click="revokeTicket(t)">
              <el-icon><Delete /></el-icon> 撤销
            </el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无办事工单" :image-size="90" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete } from '@element-plus/icons-vue'
import { getMyLeaves, deleteLeave } from '@/api/leave'
import { getTickets, cancelTicket } from '@/api/service'
import type { LeaveRequestOut, ServiceTicket } from '@/types'

const router = useRouter()
const route = useRoute()
const activeTab = ref((route.query.tab === 'ticket' ? 'ticket' : 'leave'))
const leaves = ref<LeaveRequestOut[]>([])
const tickets = ref<ServiceTicket[]>([])

const typeLabels: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
const typeLabel = (t: string) => typeLabels[t] || t
const ticketTypeLabel = (t: string) => {
  const map: Record<string, string> = { certificate: '证明申请', project: '项目申请', leave: '请假' }
  return map[t] || t
}
const statusLabel = (s: string) => ({ pending: '待审批', approved: '已通过', rejected: '已驳回' }[s] || s)
const statusType = (s: string) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info') as any

async function load() {
  if (activeTab.value === 'leave') {
    try { leaves.value = await getMyLeaves() } catch { leaves.value = [] }
  } else {
    try { tickets.value = (await getTickets()).filter((t) => t.type !== 'leave') } catch { tickets.value = [] }
  }
}

async function revokeLeave(r: LeaveRequestOut) {
  try { await ElMessageBox.confirm('确定撤销这条请假申请吗？', '撤销申请', { type: 'warning' }) } catch { return }
  try { await deleteLeave(r.id); ElMessage.success('已撤销'); load() } catch { ElMessage.error('撤销失败') }
}

async function revokeTicket(t: ServiceTicket) {
  try { await ElMessageBox.confirm('确定撤销这条工单吗？', '撤销工单', { type: 'warning' }) } catch { return }
  try { await cancelTicket(t.id); ElMessage.success('已撤销'); load() } catch { ElMessage.error('撤销失败') }
}

function goBack() { router.back() }
onMounted(load)
</script>

<style scoped>
.my-req-page { max-width: 480px; margin: 0 auto; min-height: 100%; background: #f5f7fb; padding-bottom: 40px; }
.topbar {
  position: sticky; top: 0; z-index: 20;
  display: flex; align-items: center; justify-content: space-between;
  height: 52px; padding: 0 14px; background: #fff; box-shadow: 0 1px 6px rgba(0,0,0,.04);
}
.back { display: flex; align-items: center; width: 32px; cursor: pointer; color: #1a1a2e; }
.topbar-title { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.topbar-right { width: 32px; }
.req-tabs { padding: 0 12px; background: #fff; }
.req-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
.group { padding: 12px 12px 0; }
.req-list { display: flex; flex-direction: column; gap: 10px; }
.req-card {
  background: #fff; border-radius: 12px; padding: 12px 14px;
  box-shadow: 0 1px 5px rgba(0,0,0,.04); border: 1px solid rgba(0,0,0,.03);
}
.req-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.req-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.req-row { display: flex; gap: 8px; font-size: 13px; line-height: 1.6; color: #333; }
.req-row .lab { flex-shrink: 0; width: 64px; color: #909399; }
.req-row .val { flex: 1; word-break: break-all; }
.req-row .val.danger { color: #f56c6c; }
.req-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(0,0,0,.05); }
.req-foot .time { font-size: 12px; color: #a0a6b5; }
</style>