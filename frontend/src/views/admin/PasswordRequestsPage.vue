<template>
  <div class="pr-page">
    <header class="page-header">
      <div>
        <h2>密码重置</h2>
        <p>学生 / 教师忘记密码后提交的申请，审核通过即重置为初始密码 123456</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </header>

    <div class="summary">
      <div class="summary-card">
        <span class="summary-label">待处理</span>
        <strong class="summary-value">{{ pendingCount }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">全部申请</span>
        <strong class="summary-value">{{ total }}</strong>
      </div>
    </div>

    <div class="toolbar">
      <el-radio-group v-model="filter" @change="load">
        <el-radio-button value="pending">待处理</el-radio-button>
        <el-radio-button value="reset">已重置</el-radio-button>
        <el-radio-button value="rejected">已驳回</el-radio-button>
        <el-radio-button value="">全部</el-radio-button>
      </el-radio-group>
    </div>

    <el-table v-loading="loading" :data="items" class="table" empty-text="暂无密码重置申请">
      <el-table-column label="申请人" min-width="150">
        <template #default="{ row }">
          <div class="person">
            <strong>{{ row.name }}</strong>
            <span>{{ row.username }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="contact" label="联系方式" width="160" />
      <el-table-column label="说明" min-width="200">
        <template #default="{ row }">
          <span class="reason">{{ row.reason || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" effect="light" size="small">
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="150">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="处理时间" width="150">
        <template #default="{ row }">{{ formatTime(row.handled_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button type="primary" link size="small" @click="approve(row)">通过</el-button>
            <el-button type="danger" link size="small" @click="reject(row)">驳回</el-button>
          </template>
          <span v-else class="handled">{{ row.admin_note || '已处理' }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  approvePasswordReset,
  getPasswordResetRequests,
  rejectPasswordReset,
  type PasswordResetRequestItem,
} from '@/api/admin'

const loading = ref(false)
const items = ref<PasswordResetRequestItem[]>([])
const total = ref(0)
const pendingCount = ref(0)
const filter = ref('pending')

const statusMap: Record<string, string> = { pending: '待处理', reset: '已重置', rejected: '已驳回' }
const statusTypeMap: Record<string, 'warning' | 'success' | 'info'> = {
  pending: 'warning',
  reset: 'success',
  rejected: 'info',
}

function statusText(status: string) {
  return statusMap[status] || status
}
function statusType(status: string) {
  return statusTypeMap[status] || 'info'
}

function formatTime(value: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  if (!Number.isFinite(d.getTime())) return '—'
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

async function load() {
  loading.value = true
  try {
    const res = await getPasswordResetRequests({
      status: filter.value || undefined,
      page_size: 100,
    })
    items.value = res.items
    total.value = res.total
    pendingCount.value = res.pending
  } catch {
    ElMessage.error('加载密码重置申请失败')
  } finally {
    loading.value = false
  }
}

async function approve(row: PasswordResetRequestItem) {
  try {
    await ElMessageBox.confirm(
      `确认通过 ${row.name}（${row.username}）的申请？通过后密码将重置为初始密码 123456，用户需登录后立即修改。`,
      '通过申请',
      { confirmButtonText: '通过并重置', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    const res = await approvePasswordReset(row.id)
    await ElMessageBox.alert(
      `${res.message}。请提醒用户使用初始密码 ${res.initial_password} 登录，并在登录后立即修改。`,
      '已重置',
      { confirmButtonText: '我知道了' }
    )
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function reject(row: PasswordResetRequestItem) {
  let note = ''
  try {
    const result = await ElMessageBox.prompt('请填写驳回原因，申请人会收到站内消息通知', '驳回申请', {
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：身份信息核验未通过',
      inputValidator: (value) => (value && value.trim() ? true : '请填写驳回原因'),
    })
    note = result.value.trim()
  } catch {
    return
  }
  try {
    await rejectPasswordReset(row.id, note)
    ElMessage.success('已驳回该申请')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

onMounted(load)
</script>

<style scoped>
.pr-page {
  padding: 20px 24px 32px;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2328;
}
.page-header p {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: #8b949e;
}

.summary {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.summary-card {
  min-width: 130px;
  padding: 14px 16px;
  border: 1px solid #eaeef2;
  border-radius: 10px;
  background: #fff;
}
.summary-label {
  display: block;
  font-size: 12px;
  color: #8b949e;
}
.summary-value {
  display: block;
  margin-top: 4px;
  font-size: 22px;
  font-weight: 600;
  color: #1f2328;
}

.toolbar {
  margin-top: 18px;
}

.table {
  margin-top: 12px;
  border: 1px solid #eaeef2;
  border-radius: 10px;
}

.person {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}
.person strong {
  font-size: 13px;
  font-weight: 600;
  color: #1f2328;
}
.person span {
  font-size: 11.5px;
  color: #8b949e;
}

.reason {
  font-size: 12.5px;
  color: #57606a;
}

.handled {
  font-size: 11.5px;
  color: #8b949e;
}
</style>
