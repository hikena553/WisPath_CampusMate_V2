<template>
  <div class="admin-home">
    <!-- Welcome banner -->
    <div class="welcome-banner">
      <div class="welcome-text">
        <h1>管理员控制台</h1>
        <p>欢迎回来，<strong>{{ auth.userName }}</strong> · {{ dateStr }}</p>
      </div>
      <div class="welcome-badge">
        <el-tag size="large" effect="dark" color="#409eff">管理员</el-tag>
      </div>
    </div>

    <!-- Stats row -->
    <div class="stats-row">
      <div v-for="(stat, _i) in stats" :key="stat.label"
        class="stat-card hover-lift"
      >
        <div class="stat-icon" :style="{ background: stat.bg, color: stat.color }">
          <el-icon :size="22"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
        <div class="stat-trend" :style="{ color: stat.color }">
          {{ stat.trend }}
        </div>
      </div>
    </div>

    <!-- ===== 数据管理 ===== -->
    <el-row :gutter="24" style="margin-top:28px">
      <el-col :span="12">
        <el-card>
          <template #header><span>数据导出</span></template>
          <p class="card-desc">导出用户数据为 Excel 文件</p>
          <div class="export-actions">
            <el-button type="primary" @click="handleExport('student')" :loading="exporting" class="hover-lift">导出学生数据</el-button>
            <el-button type="success" @click="handleExport('teacher')" :loading="exporting" class="hover-lift">导出教师数据</el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>数据导入</span></template>
          <p class="card-desc">从 Excel 文件导入用户数据（重复学号/工号将跳过）</p>
          <el-radio-group v-model="importRole" style="margin-bottom:16px">
            <el-radio value="student">导入学生</el-radio>
            <el-radio value="teacher">导入教师</el-radio>
          </el-radio-group>
          <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls">
            <el-button type="warning" :loading="importing" class="hover-lift">选择文件导入</el-button>
          </el-upload>
          <div v-if="importResult" class="import-result">
            <el-alert
              :title="`导入完成：新增 ${importResult.created} 条，跳过 ${importResult.skipped} 条`"
              :type="importResult.errors.length > 0 ? 'warning' : 'success'"
              show-icon :closable="false"
            />
            <div v-if="importResult.errors.length > 0" class="error-list">
              <p>错误信息：</p>
              <ul><li v-for="(err, i) in importResult.errors" :key="i">{{ err }}</li></ul>
            </div>
          </div>
          <el-collapse style="margin-top:12px">
            <el-collapse-item title="导入模板格式说明" name="1">
              <h4>学生：</h4>
              <p>学号 | 姓名 | 学院 | 班级 | 性别 | 年龄 | 联系电话 | 籍贯</p>
              <h4>教师：</h4>
              <p>工号 | 姓名 | 学院 | 性别 | 年龄 | 职称 | 所属单位 | 联系电话</p>
              <p style="color:#999;font-size:12px">第一行为表头，重复学号/工号自动跳过，默认密码 123456</p>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getTeacherList, getStudentList, getKnowledgeList, exportData, importData, type ImportResult } from '@/api/admin'
import {
  User, UserFilled, Document
} from '@element-plus/icons-vue'

const auth = useAuthStore()

const dateStr = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
})

const stats = ref([
  { label: '教师总数', value: 0, icon: User, color: '#409eff', bg: '#e8f4ff', trend: '人' },
  { label: '学生总数', value: 0, icon: UserFilled, color: '#67c23a', bg: '#edf7ed', trend: '人' },
  { label: '知识库', value: 0, icon: Document, color: '#e6a23c', bg: '#fef5e8', trend: '条' },
])

const exporting = ref(false)
const importing = ref(false)
const importRole = ref<'student' | 'teacher'>('student')
const importResult = ref<ImportResult | null>(null)

async function handleExport(role: 'student' | 'teacher') {
  exporting.value = true
  try {
    const data = await exportData(role)
    let blob: Blob
    if (data instanceof Blob) {
      blob = data
    } else if (data instanceof ArrayBuffer) {
      blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    } else {
      const text = typeof data === 'string' ? data : JSON.stringify(data)
      if (text.includes('detail') || text.includes('error')) throw new Error(text)
      blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    }
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = role === 'student' ? '学生数据.xlsx' : '教师数据.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '导出失败'
    ElMessage.error(msg)
  } finally {
    exporting.value = false
  }
}

async function handleImport(file: File) {
  importing.value = true
  importResult.value = null
  try {
    const result = await importData(importRole.value, file)
    importResult.value = result
    ElMessage.success('导入完成')
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
  return false
}

onMounted(async () => {
  try {
    const [teachers, students, knowledge] = await Promise.all([
      getTeacherList(),
      getStudentList(),
      getKnowledgeList()
    ])
    stats.value[0].value = teachers.total
    stats.value[1].value = students.total
    stats.value[2].value = knowledge.total
  } catch {}
})
</script>

<style scoped>
.admin-home {
  padding: 28px 32px;
  overflow-y: auto;
  height: 100%;
}

/* ===== Welcome Banner ===== */
.welcome-banner {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #e8f4ff 0%, #f0f8ff 50%, #e8f4ff 100%);
  border-radius: 16px; padding: 24px 28px; margin-bottom: 28px;
  border: 1px solid rgba(64,158,255,0.1);
}
.welcome-text h1 {
  font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0 0 6px;
}
.welcome-text p {
  font-size: 14px; color: #666; margin: 0;
}
.welcome-text p strong { color: #409eff; }

/* ===== Stats Row ===== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-card {
  display: flex; align-items: center; gap: 16px;
  background: #fff; border-radius: 14px; padding: 20px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}

.stat-icon {
  width: 48px; height: 48px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  display: flex; flex-direction: column; flex: 1;
}
.stat-value {
  font-size: 28px; font-weight: 700; color: #1a1a2e; line-height: 1.2;
}
.stat-label {
  font-size: 13px; color: #999; margin-top: 2px;
}
.stat-trend {
  font-size: 13px; font-weight: 500; opacity: 0.7;
}

.hover-lift {
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.hover-lift:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.08);
}

.card-desc { color: #666; font-size: 14px; margin: 0 0 16px; }
.export-actions { display: flex; gap: 12px; }
.import-result { margin-top: 16px; }
.error-list { margin-top: 8px; font-size: 13px; color: #e6a23c; }
.error-list ul { margin: 4px 0 0 16px; padding: 0; }
.error-list h4 { font-size: 14px; color: #333; margin: 12px 0 8px; }
.error-list h4:first-child { margin-top: 0; }
</style>
