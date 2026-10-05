<template>
  <div class="gp-page">
    <header class="gp-header">
      <div class="gp-header-left">
        <h2>家校沟通</h2>
        <p class="gp-sub">家长零账号可完整留痕：短信提示 · 报告导出 · 只读链接</p>
      </div>
      <el-select v-model="studentId" filterable placeholder="选择学生" style="width: 200px" @change="onStudentChange">
        <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
    </header>

    <div v-if="!studentId" class="gp-empty">
      <el-icon :size="40" color="#d0d5dd"><User /></el-icon>
      <p>请先选择一名学生</p>
    </div>

    <template v-else>
      <!-- 联系人 -->
      <section class="gp-section">
        <div class="gp-section-head">
          <span class="gp-section-title">家长联系人</span>
          <el-button size="small" round type="primary" :icon="Plus" @click="openGuardianCreate">新增联系人</el-button>
        </div>
        <div v-if="!guardians.length" class="gp-empty-small">暂无联系人，先建档才能发短信 / 留痕</div>
        <div class="gp-guardians">
          <div v-for="g in guardians" :key="g.id" class="gp-guardian">
            <div class="gp-guardian-main">
              <span class="gp-guardian-name">{{ g.name }}</span>
              <el-tag size="small" effect="plain" round>{{ g.relation }}</el-tag>
              <el-tag v-if="g.is_primary" size="small" type="success" effect="plain" round>主要</el-tag>
              <span class="gp-guardian-phone">{{ g.phone_masked || '未填手机号' }}</span>
            </div>
            <div class="gp-guardian-ops">
              <button class="gp-link" @click="openGuardianEdit(g)">编辑</button>
              <button class="gp-link gp-link-danger" @click="removeGuardian(g)">删除</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 沟通台账 -->
      <section class="gp-section">
        <div class="gp-section-head">
          <span class="gp-section-title">沟通台账（{{ logs.length }}）</span>
          <el-button size="small" round type="primary" :icon="Plus" @click="logVisible = true">记录沟通</el-button>
        </div>
        <div v-if="!logs.length" class="gp-empty-small">暂无沟通记录</div>
        <div v-for="l in logs" :key="l.id" class="gp-log">
          <div class="gp-log-head">
            <el-tag size="small" effect="light" round>{{ GUARDIAN_SCENE_LABEL[l.scene] }}</el-tag>
            <el-tag size="small" effect="plain" round>{{ GUARDIAN_CHANNEL_LABEL[l.channel] }}</el-tag>
            <el-tag size="small" :type="statusTag(l.status)" effect="plain" round>
              {{ GUARDIAN_STATUS_LABEL[l.status] }}
            </el-tag>
            <span v-if="l.guardian_name" class="gp-log-who">对象：{{ l.guardian_name }}</span>
            <span class="gp-log-date">{{ (l.created_at || '').slice(0, 10) }}</span>
          </div>
          <div class="gp-log-body">{{ l.content_summary }}</div>
          <div class="gp-log-ops">
            <template v-if="links[l.id] && !links[l.id].revoked">
              <span class="gp-link-valid">链接有效至 {{ (links[l.id].expires_at || '').slice(0, 10) }} · 访问 {{ links[l.id].view_count }} 次</span>
              <button class="gp-link" @click="copyLink(links[l.id])">复制链接</button>
              <button class="gp-link gp-link-danger" @click="revoke(links[l.id])">撤销链接</button>
            </template>
            <template v-else-if="l.scene !== 'crisis'">
              <button class="gp-link" @click="makeLink(l)">生成只读链接</button>
            </template>
            <span v-else class="gp-link-locked">
              <el-icon :size="11"><Lock /></el-icon>危机记录不生成链接
            </span>
            <button class="gp-link gp-link-danger" @click="removeLog(l)">删除</button>
          </div>
        </div>
      </section>
    </template>

    <GuardianDialog v-model="guardianVisible" :student-id="studentId || 0" :guardian="editingGuardian" @saved="loadAll" />
    <ContactLogDialog v-model="logVisible" :student-id="studentId || 0" :guardians="guardians" @saved="loadAll" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Lock, Plus, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getStudents, type StudentSummary } from '@/api/teacher'
import {
  createShareLink, deleteContactLog, deleteGuardian, getContactLogs, getGuardians,
  getLogShareLink, revokeShareLink, GUARDIAN_CHANNEL_LABEL, GUARDIAN_SCENE_LABEL,
  GUARDIAN_STATUS_LABEL,
  type ContactLog, type Guardian, type GuardianContactStatus, type ShareLink,
} from '@/api/guardian'
import GuardianDialog from '@/components/teacher/guardian/GuardianDialog.vue'
import ContactLogDialog from '@/components/teacher/guardian/ContactLogDialog.vue'

defineOptions({ name: 'teacher-guardian' })

const students = ref<StudentSummary[]>([])
const studentId = ref<number | undefined>(undefined)
const guardians = ref<Guardian[]>([])
const logs = ref<ContactLog[]>([])
const links = ref<Record<number, ShareLink>>({})

const guardianVisible = ref(false)
const editingGuardian = ref<Guardian | null>(null)
const logVisible = ref(false)

function statusTag(status: GuardianContactStatus) {
  return status === 'sent' ? 'success' : status === 'pending' ? 'warning' : status === 'failed' ? 'danger' : 'info'
}

async function loadStudents() {
  try {
    students.value = await getStudents()
    if (!studentId.value && students.value.length) {
      studentId.value = students.value[0].id
      await loadAll()
    }
  } catch {
    students.value = []
  }
}

async function loadAll() {
  if (!studentId.value) return
  const [g, l] = await Promise.allSettled([
    getGuardians(studentId.value),
    getContactLogs(studentId.value),
  ])
  guardians.value = g.status === 'fulfilled' ? g.value : []
  logs.value = l.status === 'fulfilled' ? l.value : []

  // 回显已有分享链接
  const map: Record<number, ShareLink> = {}
  await Promise.all(
    logs.value.map(async (log) => {
      try {
        const link = await getLogShareLink(log.id)
        if (link) map[log.id] = link
      } catch {
        /* 忽略单个失败 */
      }
    })
  )
  links.value = map
}

function onStudentChange() {
  guardianVisible.value = false
  logVisible.value = false
  loadAll()
}

function openGuardianCreate() {
  editingGuardian.value = null
  guardianVisible.value = true
}

function openGuardianEdit(g: Guardian) {
  editingGuardian.value = g
  guardianVisible.value = true
}

async function removeGuardian(g: Guardian) {
  try {
    await ElMessageBox.confirm(`确定删除联系人「${g.name}」？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteGuardian(g.id)
  ElMessage.success('已删除')
  loadAll()
}

async function makeLink(log: ContactLog) {
  try {
    const link = await createShareLink(log.id)
    links.value = { ...links.value, [log.id]: link }
    ElMessage.success('已生成，7 天内有效')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '生成失败')
  }
}

async function copyLink(link: ShareLink) {
  const url = `${window.location.origin}${link.path}`
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.info(url)
  }
}

async function revoke(link: ShareLink) {
  try {
    await ElMessageBox.confirm('撤销后家长将无法再打开该链接，确定撤销？', '撤销确认', { type: 'warning' })
  } catch {
    return
  }
  const updated = await revokeShareLink(link.id)
  links.value = { ...links.value, [updated.log_id]: updated }
  ElMessage.success('已撤销')
}

async function removeLog(log: ContactLog) {
  try {
    await ElMessageBox.confirm('确定删除这条沟通记录？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteContactLog(log.id)
  ElMessage.success('已删除')
  loadAll()
}

onMounted(loadStudents)
</script>

<style scoped>
.gp-page { height: 100%; overflow-y: auto; padding: 8px 4px 24px; }

.gp-header {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 12px;
  padding: 0 4px; margin-bottom: 14px;
}
.gp-header-left h2 { margin: 0; font-size: 18px; font-weight: 700; color: #1a1a2e; }
.gp-sub { margin: 3px 0 0; font-size: 12px; color: #888; }

.gp-empty, .gp-empty-small {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 40px 0; color: #98a2b3; font-size: 13px;
}
.gp-empty-small { padding: 16px 0; align-items: flex-start; }
.gp-empty p { margin: 0; }

.gp-section { margin-bottom: 20px; }
.gp-section-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; padding: 0 4px;
}
.gp-section-title { font-size: 14px; font-weight: 600; color: #101828; }

.gp-guardians { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.gp-guardian {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  border: 1px solid #f0f1f3; border-radius: 12px; padding: 11px 13px; background: #fff;
}
.gp-guardian-main { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.gp-guardian-name { font-size: 13.5px; font-weight: 600; color: #101828; }
.gp-guardian-phone { font-size: 12px; color: #98a2b3; }
.gp-guardian-ops { display: flex; gap: 12px; flex-shrink: 0; }

.gp-log { border: 1px solid #f0f1f3; border-radius: 12px; padding: 12px 14px; background: #fff; margin-bottom: 10px; }
.gp-log-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 7px; }
.gp-log-who { font-size: 11.5px; color: #98a2b3; }
.gp-log-date { margin-left: auto; font-size: 11.5px; color: #98a2b3; }
.gp-log-body { font-size: 13px; color: #475467; line-height: 1.65; white-space: pre-wrap; }
.gp-log-ops { display: flex; align-items: center; gap: 14px; margin-top: 9px; flex-wrap: wrap; }
.gp-link-valid { font-size: 11.5px; color: #079455; }

.gp-link { border: none; background: none; padding: 0; font-size: 12px; color: #2563eb; cursor: pointer; font-family: inherit; }
.gp-link-danger { color: #d92d20; }
.gp-link-locked { display: inline-flex; align-items: center; gap: 3px; font-size: 11.5px; color: #98a2b3; }

@media (max-width: 767px) {
  .gp-header { flex-direction: column; align-items: stretch; }
  .gp-guardians { grid-template-columns: 1fr; }
}
</style>