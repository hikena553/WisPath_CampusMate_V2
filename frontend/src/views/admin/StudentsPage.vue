<template>
  <div class="students-page">
    <div class="page-header">
      <h2>学生管理</h2>
      <div class="header-actions">
        <el-upload
          :show-file-list="false"
          :before-upload="handleImport"
          accept=".xlsx,.xls"
        >
          <el-button type="success" plain :loading="importing">导入学生</el-button>
        </el-upload>
      </div>
    </div>

    <div class="stats-cards">
      <div class="stat-card total">
        <span class="stat-label">学生总数</span>
        <span class="stat-value">{{ stats?.total ?? 0 }}</span>
      </div>
      <div class="stat-card college" v-for="cs in (stats?.college_stats ?? [])" :key="cs.college">
        <span class="stat-label">{{ cs.college }}</span>
        <span class="stat-value">{{ cs.count }}</span>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-box">
        <h4>学院分布</h4>
        <VChart v-if="collegePieOptions" :option="collegePieOptions" autoresize style="height:260px" />
      </div>
      <div class="chart-box">
        <h4>危机等级分布</h4>
        <VChart v-if="crisisPieOptions" :option="crisisPieOptions" autoresize style="height:260px" />
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchText" placeholder="搜索学号或姓名" clearable style="width:220px">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="collegeFilter" placeholder="学院" clearable style="width:150px">
        <el-option v-for="c in collegeList" :key="c" :label="c" :value="c" />
      </el-select>
      <el-select v-model="classFilter" placeholder="班级" clearable style="width:150px">
        <el-option v-for="c in classList" :key="c" :label="c" :value="c" />
      </el-select>
    </div>

    <el-table :data="paginatedStudents" style="width:100%" border v-loading="loading">
      <el-table-column prop="username" label="学号" width="120" />
      <el-table-column prop="name" label="姓名" width="120">
        <template #default="{ row }">
          <div class="student-name-cell">
            <el-avatar :size="32" :src="row.avatar || ''">{{ row.name?.[0] }}</el-avatar>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="college" label="学院" min-width="140" />
      <el-table-column prop="class_name" label="班级" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.class_name" size="small" effect="plain">{{ row.class_name }}</el-tag>
          <span v-else class="text-muted">--</span>
        </template>
      </el-table-column>
      <el-table-column prop="score" label="综合评分" width="100" align="center" />
      <el-table-column prop="crisis_level" label="危机等级" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.crisis_level" :type="row.crisis_level === 'severe' ? 'danger' : row.crisis_level === 'moderate' ? 'warning' : 'info'" size="small">
            {{ row.crisis_level === 'severe' ? '严重' : row.crisis_level === 'moderate' ? '中等' : '轻微' }}
          </el-tag>
          <span v-else class="text-muted">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <div style="display: inline-flex; align-items: center; gap: 12px;">
            <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
            <ActionButtons :user-id="row.id" :user-name="row.name" @reset-success="loadStudents" />
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[50, 100, 200]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-dialog v-model="editVisible" title="编辑学生信息" width="500px">
      <el-form v-if="editForm" :model="editForm" label-width="90px" size="small">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="学号"><el-input v-model="editForm.username" disabled /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名"><el-input v-model="editForm.name" disabled /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="学院"><el-input v-model="editForm.college" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="班级"><el-input v-model="editForm.class_name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="辅导员">
              <el-select v-model="editForm.tutor_id" placeholder="选择辅导员" filterable clearable style="width:100%">
                <el-option v-for="t in teachers" :key="t.id" :label="`${t.name}`" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="性别">
              <el-select v-model="editForm.gender" placeholder="请选择" style="width:100%">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="年龄">
              <el-input-number v-model="editForm.age" :min="1" :max="120" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="联系电话"><el-input v-model="editForm.phone" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="籍贯"><el-input v-model="editForm.hometown" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getStudentList, getStudentStats, updateStudent, importData, type StudentBrief, type StudentStats } from '@/api/admin'
import { getTeachers } from '@/api/user'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import ActionButtons from './components/ActionButtons.vue'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const loading = ref(false)
const students = ref<StudentBrief[]>([])
const searchText = ref('')
const collegeFilter = ref('')
const classFilter = ref('')
const importing = ref(false)
const editVisible = ref(false)
const saving = ref(false)
const editForm = ref<any>(null)
const teachers = ref<any[]>([])

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

const stats = ref<StudentStats | null>(null)
const collegePieOptions = computed(() => {
  if (!stats.value?.college_stats.length) return null
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['30%', '70%'],
      data: stats.value.college_stats.map(c => ({ name: c.college, value: c.count })),
      label: { show: true, formatter: '{b}: {c}' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  }
})
const crisisPieOptions = computed(() => {
  if (!stats.value?.crisis_stats.length) return null
  const colorMap: Record<string, string> = { severe: '#f56c6c', moderate: '#e6a23c', mild: '#909399', none: '#67c23a' }
  const labelMap: Record<string, string> = { severe: '严重', moderate: '中等', mild: '轻微', none: '无' }
  return {
    tooltip: { trigger: 'item' },
    color: stats.value.crisis_stats.map(c => colorMap[c.level] || '#909399'),
    series: [{
      type: 'pie',
      radius: ['30%', '70%'],
      data: stats.value.crisis_stats.map(c => ({ name: labelMap[c.level] || c.level, value: c.count })),
      label: { show: true, formatter: '{b}: {c}' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  }
})

// 从后端返回的数据中提取当前页的学生列表
const paginatedStudents = computed(() => students.value)

// 学院和班级列表（从当前页数据中提取，用于筛选）
const collegeList = computed(() => [...new Set(students.value.map(s => s.college).filter(Boolean) as string[])])
const classList = computed(() => [...new Set(students.value.map(s => s.class_name).filter(Boolean) as string[])])

// 当筛选条件变化时，重置到第一页并重新加载
watch([searchText, collegeFilter, classFilter], () => {
  currentPage.value = 1
  loadStudents()
})

// 当页码或每页条数变化时，重新加载
watch([currentPage, pageSize], () => {
  loadStudents()
})

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 页码变化时自动更新表格数据（通过 watch 自动响应）
}

function openEdit(row: StudentBrief) {
  editForm.value = { ...row, tutor_id: null, age: null, gender: '', phone: '', hometown: '' }
  editVisible.value = true
}

async function handleSaveEdit() {
  saving.value = true
  try {
    const payload: any = {}
    for (const key of ['college', 'class_name', 'gender', 'phone', 'hometown']) {
      if (editForm.value[key] !== undefined) payload[key] = editForm.value[key] || null
    }
    if (editForm.value.age !== null && editForm.value.age !== undefined) payload.age = editForm.value.age
    if (editForm.value.tutor_id !== null && editForm.value.tutor_id !== undefined) payload.tutor_id = editForm.value.tutor_id
    await updateStudent(editForm.value.id, payload)
    ElMessage.success('保存成功')
    editVisible.value = false
    await Promise.all([loadStudents(), loadStats()])
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleImport(file: File) {
  importing.value = true
  try {
    const result = await importData('student', file)
    ElMessage.success(`导入完成：新增 ${result.created} 条，跳过 ${result.skipped} 条`)
    if (result.errors.length) {
      ElMessage.warning(`有 ${result.errors.length} 条错误`)
    }
    await Promise.all([loadStudents(), loadStats()])
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
  return false
}

async function loadStats() {
  try {
    stats.value = await getStudentStats()
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

async function loadStudents() {
  loading.value = true
  try {
    const response = await getStudentList({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchText.value || undefined,
      college: collegeFilter.value || undefined,
      class_name: classFilter.value || undefined,
    })
    students.value = response.items
    total.value = response.total
  } catch (error) {
    console.error('加载学生列表失败:', error)
    ElMessage.error('加载学生列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadStudents(), loadStats()])
  try {
    teachers.value = await getTeachers()
  } catch (error) {
    console.error('加载教师列表失败:', error)
  }
})
</script>

<style scoped>
.students-page { padding: 24px; overflow-y: auto; height: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 20px; font-weight: 600; color: #333; margin: 0; }
.header-actions { display: flex; gap: 12px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
.student-name-cell { display: flex; align-items: center; gap: 8px; }
.text-muted { color: #999; font-size: 12px; }

.stats-cards {
  display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;
}
.stat-card {
  flex: 1; min-width: 120px; padding: 16px; border-radius: 10px;
  display: flex; flex-direction: column; gap: 4px;
  cursor: default;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}
.stat-card.total { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; }
.stat-card.college { background: #f0f5ff; color: #333; border: 1px solid #d6e4ff; }
.stat-card.college:hover {
  background: #e8f0ff;
  border-color: #b3cfff;
}
.stat-label { font-size: 13px; opacity: 0.85; }
.stat-value { font-size: 28px; font-weight: 700; }

.charts-row {
  display: flex; gap: 16px; margin-bottom: 20px;
}
.chart-box {
  flex: 1; background: #fff; border-radius: 10px; padding: 16px;
  border: 1px solid #f0f0f0;
}
.chart-box h4 { margin: 0 0 8px; font-size: 14px; color: #333; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 12px 0;
}
</style>
