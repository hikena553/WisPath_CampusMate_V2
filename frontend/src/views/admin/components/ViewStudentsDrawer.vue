<template>
  <el-drawer v-model="visible" :title="`${teacher?.name} - 学生列表`" size="600px">
    <div v-if="loading" class="loading-wrap">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>
    <template v-else>
      <div v-if="students.length === 0" class="empty-tip">暂无学生</div>
      <div v-else class="student-list">
        <div v-for="student in students" :key="student.id" class="student-card">
          <el-avatar :size="40" :src="student.avatar || ''">{{ student.name?.[0] }}</el-avatar>
          <div class="student-info">
            <span class="student-name">{{ student.name }}</span>
            <span class="student-detail">{{ student.username }} · {{ student.college || '未分配' }}</span>
            <span v-if="student.class_name" class="student-class">班级: {{ student.class_name }}</span>
          </div>
          <div class="student-meta">
            <span class="student-score">综合评分: {{ student.score }}</span>
            <el-tag v-if="student.crisis_level" :type="student.crisis_level === 'severe' ? 'danger' : 'warning'" size="small">
              {{ student.crisis_level === 'severe' ? '严重' : student.crisis_level === 'moderate' ? '中等' : '轻微' }}
            </el-tag>
            <el-button type="primary" link size="small" @click="openEdit(student)">编辑</el-button>
          </div>
        </div>
      </div>
    </template>

    <el-dialog v-model="editVisible" title="编辑学生信息" width="500px" append-to-body>
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
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getTeacherStudents, updateStudent, type TeacherInfo, type StudentBrief } from '@/api/admin'
import { getTeachers } from '@/api/user'

const props = defineProps<{
  teacher: TeacherInfo | null
}>()

const visible = defineModel<boolean>({ default: false })

const students = ref<StudentBrief[]>([])
const loading = ref(false)
const editVisible = ref(false)
const saving = ref(false)
const editForm = ref<any>(null)
const teachers = ref<any[]>([])

function openEdit(student: StudentBrief) {
  editForm.value = { ...student, tutor_id: null }
  editVisible.value = true
}

async function handleSaveEdit() {
  saving.value = true
  try {
    const payload: any = {}
    if (editForm.value.college !== undefined) payload.college = editForm.value.college || null
    if (editForm.value.class_name !== undefined) payload.class_name = editForm.value.class_name || null
    if (editForm.value.tutor_id !== null && editForm.value.tutor_id !== undefined) payload.tutor_id = editForm.value.tutor_id
    await updateStudent(editForm.value.id, payload)
    ElMessage.success('保存成功')
    editVisible.value = false
    students.value = await getTeacherStudents(props.teacher!.id)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

watch(visible, async (val) => {
  if (val && props.teacher) {
    loading.value = true
    try {
      students.value = await getTeacherStudents(props.teacher.id)
      teachers.value = await getTeachers()
    } catch {
      ElMessage.error('加载学生列表失败')
    } finally {
      loading.value = false
    }
  }
})
</script>

<style scoped>
.loading-wrap {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-tip {
  text-align: center;
  color: #999;
  padding: 40px;
}

.student-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.student-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 8px;
  transition: background 0.2s;
}

.student-card:hover {
  background: #f5f7fa;
}

.student-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.student-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.student-detail {
  font-size: 12px;
  color: #999;
}

.student-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.student-class {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.student-score {
  font-size: 12px;
  color: #666;
}
</style>
