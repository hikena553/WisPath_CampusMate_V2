<template>
  <div class="cr-panel">
    <!-- 顶部操作 -->
    <div class="cr-toolbar">
      <div class="cr-toolbar-title">
        工作记录
        <span v-if="records.length" class="cr-count">{{ records.length }} 条</span>
      </div>
      <el-button type="primary" size="small" round :icon="Plus" @click="openCreate">新增记录</el-button>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="cr-empty">加载中…</div>

    <!-- 空态 -->
    <div v-else-if="!records.length" class="cr-empty">
      <el-icon :size="34" color="#d0d5dd"><Notebook /></el-icon>
      <p>还没有工作记录，点击「新增记录」开始沉淀</p>
    </div>

    <!-- 记录时间线 -->
    <div v-else class="cr-timeline">
      <div v-for="r in records" :key="r.id" class="cr-item" :class="`cr-${r.record_type}`">
        <div class="cr-dot"></div>
        <div class="cr-body">
          <div class="cr-head">
            <span class="cr-type" :class="`t-${r.record_type}`">{{ CARE_TYPE_LABEL[r.record_type] }}</span>
            <span v-if="r.is_private" class="cr-private">
              <el-icon :size="11"><Lock /></el-icon>仅我可见
            </span>
            <span class="cr-time">{{ formatTime(r.created_at) }}</span>
          </div>
          <div class="cr-content">{{ r.content }}</div>
          <div class="cr-actions">
            <button class="cr-link" @click="openEdit(r)">编辑</button>
            <button class="cr-link cr-link-danger" @click="handleDelete(r)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <CareRecordDialog
      v-model="dialogVisible"
      :student-id="studentId"
      :student-name="studentName"
      :record="editing"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Lock, Notebook, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CARE_TYPE_LABEL,
  deleteCareRecord,
  getCareRecords,
  type CareRecord,
} from '@/api/careRecord'
import CareRecordDialog from './CareRecordDialog.vue'

const props = defineProps<{
  studentId: number
  studentName?: string
}>()

const emit = defineEmits<{ changed: [] }>()

const records = ref<CareRecord[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref<CareRecord | null>(null)

async function load() {
  if (!props.studentId) return
  loading.value = true
  try {
    records.value = await getCareRecords({ student_id: props.studentId })
  } catch {
    ElMessage.error('工作记录加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  dialogVisible.value = true
}

function openEdit(r: CareRecord) {
  editing.value = r
  dialogVisible.value = true
}

function onSaved() {
  load()
  emit('changed')
}

async function handleDelete(r: CareRecord) {
  try {
    await ElMessageBox.confirm('确定删除这条工作记录？删除后不再计入工作量统计。', '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteCareRecord(r.id)
    ElMessage.success('已删除')
    load()
    emit('changed')
  } catch {
    ElMessage.error('删除失败')
  }
}

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

watch(() => props.studentId, load)
onMounted(load)

defineExpose({ reload: load })
</script>

<style scoped>
.cr-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cr-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cr-toolbar-title {
  font-size: 14px;
  font-weight: 600;
  color: #101828;
}
.cr-count {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 400;
  color: #98a2b3;
}

.cr-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 34px 0;
  color: #98a2b3;
  font-size: 13px;
}
.cr-empty p { margin: 0; }

.cr-timeline {
  display: flex;
  flex-direction: column;
}

.cr-item {
  position: relative;
  display: flex;
  gap: 12px;
  padding-bottom: 16px;
}
.cr-item:last-child { padding-bottom: 0; }
/* 时间线竖线 */
.cr-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 16px;
  bottom: 0;
  width: 1px;
  background: #eaecf0;
}

.cr-dot {
  flex-shrink: 0;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  margin-top: 4px;
  background: #f04438;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #eaecf0;
  z-index: 1;
}
.cr-talk .cr-dot { background: #7c3aed; }
.cr-comment .cr-dot { background: #2563eb; }

.cr-body {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 10px;
  padding: 11px 13px;
}

.cr-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.cr-type {
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fef3f2;
  color: #d92d20;
}
.cr-type.t-talk { background: #f4f3ff; color: #6941c6; }
.cr-type.t-comment { background: #eff4ff; color: #2563eb; }

.cr-private {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: #98a2b3;
}
.cr-time {
  margin-left: auto;
  font-size: 11.5px;
  color: #98a2b3;
}

.cr-content {
  font-size: 13px;
  color: #344054;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.cr-actions {
  display: flex;
  gap: 14px;
  margin-top: 8px;
}
.cr-link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: #2563eb;
  cursor: pointer;
  font-family: inherit;
}
.cr-link-danger { color: #d92d20; }
</style>
