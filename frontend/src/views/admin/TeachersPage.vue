<template>
  <div class="teachers-page">
    <div class="page-header">
      <h2>教师管理</h2>
      <div class="header-actions">
        <el-button v-if="!deleteMode" type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新增教师
        </el-button>
        <el-button v-if="!deleteMode" type="danger" plain @click="enterDeleteMode">
          <el-icon><Delete /></el-icon> 删除
        </el-button>
        <el-input v-model="searchText" placeholder="搜索教师" clearable style="width: 200px">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <div v-if="deleteMode" class="batch-bar">
      <span class="batch-info">
        已选 <strong>{{ selectedIds.length }}</strong> 项
      </span>
      <el-button size="small" @click="exitDeleteMode">取消</el-button>
      <el-popconfirm
        title="确认删除所选教师？其名下学生的辅导员将被清空。"
        @confirm="handleBatchDelete"
      >
        <template #reference>
          <el-button type="danger" size="small" :disabled="selectedIds.length === 0" :loading="deleting">
            批量删除
          </el-button>
        </template>
      </el-popconfirm>
    </div>

    <el-table
      :data="paginatedTeachers"
      style="width: 100%" border
      @selection-change="onSelectionChange"
      @row-click="handleRowClick"
    >
      <el-table-column v-if="deleteMode" type="selection" width="40" />
      <el-table-column prop="username" label="工号" min-width="100" />
      <el-table-column prop="name" label="姓名" min-width="100">
        <template #default="{ row }">
          <div class="teacher-name-cell">
            <el-avatar :size="32" :src="row.avatar || ''">{{ row.name?.[0] }}</el-avatar>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="college" label="学院" min-width="140" />
      <el-table-column prop="title" label="职称" min-width="90" />
      <el-table-column prop="department" label="所属单位" min-width="130" />
      <el-table-column prop="student_count" label="学生数量" width="100" align="center">
        <template #default="{ row }">
          <el-tag type="primary">{{ row.student_count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <ActionButtons
              :user-id="row.id"
              :user-name="row.name"
              :show-view-students="true"
              @view-students="openDrawer(row)"
              @reset-success="loadTeachers"
            />
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

    <ViewStudentsDrawer v-model="drawerVisible" :teacher="selectedTeacher" />

    <el-dialog v-model="createVisible" title="新增教师" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="createForm" label-width="80px" size="small">
        <el-form-item label="工号" prop="username" :rules="[{ required: true, message: '请输入工号' }]">
          <el-input v-model="createForm.username" placeholder="教师工号" />
        </el-form-item>
        <el-form-item label="姓名" prop="name" :rules="[{ required: true, message: '请输入姓名' }]">
          <el-input v-model="createForm.name" placeholder="教师姓名" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="学院" prop="college">
              <el-input v-model="createForm.college" placeholder="所属学院" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="职称" prop="title">
              <el-input v-model="createForm.title" placeholder="职称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="所属单位" prop="department">
              <el-input v-model="createForm.department" placeholder="所属单位" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别" prop="gender">
              <el-select v-model="createForm.gender" placeholder="性别" clearable style="width:100%">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="createForm.phone" placeholder="联系电话" />
        </el-form-item>
        <p style="color:#999;font-size:12px;margin:0">默认密码为 123456，创建后可重置</p>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { Search, Delete, Plus } from '@element-plus/icons-vue'
import { getTeacherList, batchDeleteTeachers, createTeacher, type TeacherInfo } from '@/api/admin'
import ViewStudentsDrawer from './components/ViewStudentsDrawer.vue'
import ActionButtons from './components/ActionButtons.vue'

const teachers = ref<TeacherInfo[]>([])
const searchText = ref('')
const drawerVisible = ref(false)
const selectedTeacher = ref<TeacherInfo | null>(null)
const selectedIds = ref<number[]>([])
const deleting = ref(false)
const deleteMode = ref(false)

// 新增教师
const createVisible = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()
const createForm = ref({
  username: '',
  name: '',
  college: '',
  title: '',
  department: '',
  gender: '',
  phone: '',
})

// 分页相关状态
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

// 从后端返回的数据中提取当前页的教师列表
const paginatedTeachers = computed(() => teachers.value)

// 当搜索条件变化时，重置到第一页并重新加载
watch(searchText, () => {
  currentPage.value = 1
  loadTeachers()
})

// 当页码或每页条数变化时，重新加载
watch([currentPage, pageSize], () => {
  loadTeachers()
})

function openCreateDialog() {
  createForm.value = { username: '', name: '', college: '', title: '', department: '', gender: '', phone: '' }
  createVisible.value = true
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await createTeacher({
      username: createForm.value.username,
      name: createForm.value.name,
      college: createForm.value.college || undefined,
      title: createForm.value.title || undefined,
      department: createForm.value.department || undefined,
      gender: createForm.value.gender || undefined,
      phone: createForm.value.phone || undefined,
    })
    ElMessage.success('新增教师成功')
    createVisible.value = false
    await loadTeachers()
  } catch (error) {
    console.error('新增教师失败:', error)
    ElMessage.error('新增教师失败')
  } finally {
    creating.value = false
  }
}

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 页码变化时自动更新表格数据（通过 watch 自动响应）
}

async function loadTeachers() {
  try {
    const response = await getTeacherList({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchText.value || undefined,
    })
    teachers.value = response.items
    total.value = response.total
  } catch (error) {
    console.error('加载教师列表失败:', error)
    ElMessage.error('加载教师列表失败')
  }
}

function handleRowClick(row: TeacherInfo) {
  openDrawer(row)
}

function openDrawer(teacher: TeacherInfo) {
  selectedTeacher.value = teacher
  drawerVisible.value = true
}

function enterDeleteMode() {
  selectedIds.value = []
  deleteMode.value = true
}

function exitDeleteMode() {
  deleteMode.value = false
  selectedIds.value = []
}

function onSelectionChange(rows: TeacherInfo[]) {
  selectedIds.value = rows.map(r => r.id)
}

async function handleBatchDelete() {
  deleting.value = true
  try {
    const res = await batchDeleteTeachers(selectedIds.value)
    ElMessage.success(res.message)
    exitDeleteMode()
    await loadTeachers()
  } catch (error) {
    console.error('批量删除失败:', error)
    ElMessage.error('批量删除失败')
  } finally {
    deleting.value = false
  }
}

onMounted(loadTeachers)
</script>

<style scoped>
.teachers-page {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.teacher-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f8faff;
  border-radius: 6px;
}

.batch-info {
  font-size: 13px;
  color: #666;
}
.batch-info strong {
  color: #409eff;
  font-size: 15px;
}

.action-cell :deep(.action-buttons) {
  flex-direction: column;
  align-items: flex-start;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 12px 0;
}
</style>
