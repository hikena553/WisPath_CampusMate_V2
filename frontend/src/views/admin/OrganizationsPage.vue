<template>
  <div class="page-container">
    <div class="page-header">
      <h2>院系班级管理</h2>
    </div>

    <!-- 学院管理 -->
    <el-card shadow="never" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span>学院管理</span>
          <el-button type="primary" @click="showCollegeDialog()">新增学院</el-button>
        </div>
      </template>
      <el-table :data="colleges" stripe border>
        <el-table-column prop="code" label="学院代码" width="120" />
        <el-table-column prop="name" label="学院名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="showCollegeDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该学院？" @confirm="handleDeleteCollege(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 专业管理 -->
    <el-card shadow="never" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span>专业管理</span>
          <div>
            <el-select v-model="majorFilterCollege" placeholder="按学院筛选" clearable style="margin-right: 10px; width: 180px">
              <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-button type="primary" @click="showMajorDialog()">新增专业</el-button>
          </div>
        </div>
      </template>
      <el-table :data="filteredMajors" stripe border>
        <el-table-column prop="college_name" label="所属学院" width="140" />
        <el-table-column prop="code" label="专业代码" width="120" />
        <el-table-column prop="name" label="专业名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="showMajorDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该专业？" @confirm="handleDeleteMajor(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 班级管理 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>班级管理</span>
          <div>
            <el-select v-model="cgFilterMajor" placeholder="按专业筛选" clearable style="margin-right: 10px; width: 200px">
              <el-option v-for="m in majors" :key="m.id" :label="`${m.college_name} - ${m.name}`" :value="m.id" />
            </el-select>
            <el-button type="primary" @click="showClassGroupDialog()">新增班级</el-button>
          </div>
        </div>
      </template>
      <el-table :data="filteredClassGroups" stripe border>
        <el-table-column prop="college_name" label="学院" width="140" />
        <el-table-column prop="major_name" label="专业" width="160" />
        <el-table-column prop="grade" label="年级" width="80" />
        <el-table-column prop="name" label="班级名称" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="showClassGroupDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该班级？" @confirm="handleDeleteClassGroup(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学院弹窗 -->
    <el-dialog v-model="collegeDialogVisible" :title="editingCollege ? '编辑学院' : '新增学院'" width="450px">
      <el-form :model="collegeForm" label-width="80px">
        <el-form-item label="学院名称"><el-input v-model="collegeForm.name" /></el-form-item>
        <el-form-item label="学院代码"><el-input v-model="collegeForm.code" placeholder="如 SE、DS" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="collegeForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="collegeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCollege">保存</el-button>
      </template>
    </el-dialog>

    <!-- 专业弹窗 -->
    <el-dialog v-model="majorDialogVisible" :title="editingMajor ? '编辑专业' : '新增专业'" width="450px">
      <el-form :model="majorForm" label-width="80px">
        <el-form-item label="所属学院">
          <el-select v-model="majorForm.college_id" placeholder="请选择">
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="专业名称"><el-input v-model="majorForm.name" /></el-form-item>
        <el-form-item label="专业代码"><el-input v-model="majorForm.code" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="majorForm.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="majorDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveMajor">保存</el-button>
      </template>
    </el-dialog>

    <!-- 班级弹窗 -->
    <el-dialog v-model="classGroupDialogVisible" :title="editingClassGroup ? '编辑班级' : '新增班级'" width="450px">
      <el-form :model="classGroupForm" label-width="80px">
        <el-form-item label="所属专业">
          <el-select v-model="classGroupForm.major_id" placeholder="请选择">
            <el-option v-for="m in majors" :key="m.id" :label="`${m.college_name} - ${m.name}`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="年级"><el-input-number v-model="classGroupForm.grade" :min="2020" :max="2030" /></el-form-item>
        <el-form-item label="班级名称"><el-input v-model="classGroupForm.name" placeholder="如 2024级软件工程1班" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="classGroupDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveClassGroup">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { College, Major, ClassGroup } from '@/types'
import {
  getColleges, createCollege, updateCollege, deleteCollege,
  getMajors, createMajor, updateMajor, deleteMajor,
  getClassGroups, createClassGroup, updateClassGroup, deleteClassGroup,
} from '@/api/organization'

const colleges = ref<College[]>([])
const majors = ref<Major[]>([])
const classGroups = ref<ClassGroup[]>([])

const majorFilterCollege = ref<number | null>(null)
const cgFilterMajor = ref<number | null>(null)

const filteredMajors = computed(() =>
  majorFilterCollege.value ? majors.value.filter(m => m.college_id === majorFilterCollege.value) : majors.value
)
const filteredClassGroups = computed(() =>
  cgFilterMajor.value ? classGroups.value.filter(cg => cg.major_id === cgFilterMajor.value) : classGroups.value
)

// ─── 学院弹窗 ─────────────────────────────────────────
const collegeDialogVisible = ref(false)
const editingCollege = ref<College | null>(null)
const collegeForm = ref({ name: '', code: '', description: '' })

function showCollegeDialog(row?: College) {
  editingCollege.value = row || null
  collegeForm.value = row ? { name: row.name, code: row.code, description: row.description || '' } : { name: '', code: '', description: '' }
  collegeDialogVisible.value = true
}

async function handleSaveCollege() {
  try {
    if (editingCollege.value) {
      await updateCollege(editingCollege.value.id, collegeForm.value)
      ElMessage.success('修改成功')
    } else {
      await createCollege(collegeForm.value)
      ElMessage.success('新增成功')
    }
    collegeDialogVisible.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDeleteCollege(id: number) {
  await deleteCollege(id)
  ElMessage.success('删除成功')
  loadData()
}

// ─── 专业弹窗 ─────────────────────────────────────────
const majorDialogVisible = ref(false)
const editingMajor = ref<Major | null>(null)
const majorForm = ref({ college_id: 0, name: '', code: '', description: '' })

function showMajorDialog(row?: Major) {
  editingMajor.value = row || null
  majorForm.value = row
    ? { college_id: row.college_id, name: row.name, code: row.code, description: row.description || '' }
    : { college_id: majorFilterCollege.value || (colleges.value[0]?.id ?? 0), name: '', code: '', description: '' }
  majorDialogVisible.value = true
}

async function handleSaveMajor() {
  try {
    if (editingMajor.value) {
      await updateMajor(editingMajor.value.id, majorForm.value)
      ElMessage.success('修改成功')
    } else {
      await createMajor(majorForm.value)
      ElMessage.success('新增成功')
    }
    majorDialogVisible.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDeleteMajor(id: number) {
  await deleteMajor(id)
  ElMessage.success('删除成功')
  loadData()
}

// ─── 班级弹窗 ─────────────────────────────────────────
const classGroupDialogVisible = ref(false)
const editingClassGroup = ref<ClassGroup | null>(null)
const classGroupForm = ref({ major_id: 0, name: '', grade: 2024 })

function showClassGroupDialog(row?: ClassGroup) {
  editingClassGroup.value = row || null
  classGroupForm.value = row
    ? { major_id: row.major_id, name: row.name, grade: row.grade }
    : { major_id: cgFilterMajor.value || (majors.value[0]?.id ?? 0), name: '', grade: 2024 }
  classGroupDialogVisible.value = true
}

async function handleSaveClassGroup() {
  try {
    if (editingClassGroup.value) {
      await updateClassGroup(editingClassGroup.value.id, classGroupForm.value)
      ElMessage.success('修改成功')
    } else {
      await createClassGroup(classGroupForm.value)
      ElMessage.success('新增成功')
    }
    classGroupDialogVisible.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDeleteClassGroup(id: number) {
  await deleteClassGroup(id)
  ElMessage.success('删除成功')
  loadData()
}

// ─── 加载数据 ─────────────────────────────────────────
async function loadData() {
  const [c, m, cg] = await Promise.all([getColleges(), getMajors(), getClassGroups()])
  colleges.value = c as any
  majors.value = m as any
  classGroups.value = cg as any
}

onMounted(loadData)
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
