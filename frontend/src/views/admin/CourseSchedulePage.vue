<template>
  <div class="page-container">
    <div class="page-header">
      <h2>课程表管理</h2>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" style="margin-bottom: 20px">
      <div class="filter-bar">
        <el-select v-model="filterCollegeId" placeholder="选择学院" clearable @change="onCollegeChange" style="width: 160px">
          <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filterMajorId" placeholder="选择专业" clearable @change="onMajorChange" style="width: 180px">
          <el-option v-for="m in filteredMajors" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-select v-model="filterClassGroupId" placeholder="选择班级" clearable @change="loadCourses" style="width: 200px">
          <el-option v-for="cg in filteredClassGroups" :key="cg.id" :label="cg.name" :value="cg.id" />
        </el-select>
        <el-select v-model="filterSemester" placeholder="选择学期" style="width: 160px" @change="loadCourses">
          <el-option label="2024-2025-1" value="2024-2025-1" />
          <el-option label="2024-2025-2" value="2024-2025-2" />
          <el-option label="2025-2026-1" value="2025-2026-1" />
        </el-select>
      </div>
    </el-card>

    <!-- 课表网格 -->
    <el-card shadow="never" v-if="filterClassGroupId && filterSemester">
      <template #header>
        <div class="card-header">
          <span>{{ currentClassName }} — {{ filterSemester }} 课程表</span>
          <el-button type="primary" @click="showAddDialog()">添加课程</el-button>
        </div>
      </template>

      <div class="schedule-grid">
        <!-- 表头 -->
        <div class="grid-row header">
          <div class="cell period-header">节次</div>
          <div class="cell day-header" v-for="d in 5" :key="d">周{{ ['一','二','三','四','五'][d-1] }}</div>
        </div>
        <!-- 课表行 -->
        <div class="grid-row" v-for="p in periods" :key="p">
          <div class="cell period-cell">{{ p }}-{{ p+1 }}</div>
          <div
            class="cell day-cell"
            v-for="d in 5" :key="d"
            @click="onCellClick(d, p)"
          >
            <div v-if="getCourseAt(d, p)" class="course-card" @click.stop="showEditDialog(getCourseAt(d, p)!)">
              <div class="course-name">{{ getCourseAt(d, p)!.name }}</div>
              <div class="course-info">{{ getCourseAt(d, p)!.teacher }} | {{ getCourseAt(d, p)!.location }}</div>
              <div class="course-weeks">第{{ getCourseAt(d, p)!.week_start }}-{{ getCourseAt(d, p)!.week_end }}周</div>
              <el-icon class="delete-icon" @click.stop="handleDelete(getCourseAt(d, p)!.id)"><Delete /></el-icon>
            </div>
            <div v-else class="empty-cell">+</div>
          </div>
        </div>
      </div>
    </el-card>

    <el-empty v-else description="请选择班级和学期以查看课程表" />

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingCourse ? '编辑课程' : '新增课程'" width="500px">
      <el-form :model="courseForm" label-width="80px">
        <el-form-item label="课程名称"><el-input v-model="courseForm.name" /></el-form-item>
        <el-form-item label="授课教师"><el-input v-model="courseForm.teacher" /></el-form-item>
        <el-form-item label="上课地点"><el-input v-model="courseForm.location" /></el-form-item>
        <el-form-item label="星期">
          <el-select v-model="courseForm.day_of_week" style="width: 100%">
            <el-option v-for="d in 5" :key="d" :label="'周' + ['一','二','三','四','五'][d-1]" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="节次">
          <el-select v-model="courseForm.start_period" placeholder="开始节次" style="width: 45%; margin-right: 5%">
            <el-option v-for="p in 10" :key="p" :label="`第${p}节`" :value="p" />
          </el-select>
          <span style="line-height: 32px">~</span>
          <el-select v-model="courseForm.end_period" placeholder="结束节次" style="width: 45%">
            <el-option v-for="p in 10" :key="p" :label="`第${p}节`" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="周数范围">
          <el-input-number v-model="courseForm.week_start" :min="1" :max="20" style="width: 45%; margin-right: 5%" />
          <span style="line-height: 32px">~</span>
          <el-input-number v-model="courseForm.week_end" :min="1" :max="20" style="width: 45%" />
        </el-form-item>
        <el-form-item label="学分"><el-input-number v-model="courseForm.credit" :min="0" :max="10" :step="0.5" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import type { College, Major, ClassGroup, Course } from '@/types'
import { getColleges, getMajors, getClassGroups } from '@/api/organization'
import { adminGetCourses, adminCreateCourse, adminUpdateCourse, adminDeleteCourse } from '@/api/academic'

const colleges = ref<College[]>([])
const majors = ref<Major[]>([])
const classGroups = ref<ClassGroup[]>([])
const courses = ref<Course[]>([])

const filterCollegeId = ref<number | null>(null)
const filterMajorId = ref<number | null>(null)
const filterClassGroupId = ref<number | null>(null)
const filterSemester = ref('2024-2025-2')

const periods = [1, 3, 5, 7, 9]

const filteredMajors = computed(() =>
  filterCollegeId.value ? majors.value.filter(m => m.college_id === filterCollegeId.value) : majors.value
)
const filteredClassGroups = computed(() =>
  filterMajorId.value ? classGroups.value.filter(cg => cg.major_id === filterMajorId.value) : classGroups.value
)
const currentClassName = computed(() => {
  const cg = classGroups.value.find(c => c.id === filterClassGroupId.value)
  return cg ? cg.name : ''
})

function onCollegeChange() {
  filterMajorId.value = null
  filterClassGroupId.value = null
  courses.value = []
}
function onMajorChange() {
  filterClassGroupId.value = null
  courses.value = []
}

function getCourseAt(day: number, period: number) {
  return courses.value.find(c => c.day_of_week === day && c.start_period <= period && c.end_period >= period)
}

// ─── 弹窗 ─────────────────────────────────────────────
const dialogVisible = ref(false)
const editingCourse = ref<Course | null>(null)
const courseForm = ref({
  name: '', teacher: '', location: '',
  day_of_week: 1, start_period: 1, end_period: 2,
  week_start: 1, week_end: 16, credit: 2,
})

function showAddDialog(day?: number, period?: number) {
  editingCourse.value = null
  courseForm.value = {
    name: '', teacher: '', location: '',
    day_of_week: day || 1, start_period: period || 1, end_period: (period || 1) + 1,
    week_start: 1, week_end: 16, credit: 2,
  }
  dialogVisible.value = true
}

function showEditDialog(course: Course) {
  editingCourse.value = course
  courseForm.value = {
    name: course.name, teacher: course.teacher, location: course.location,
    day_of_week: course.day_of_week, start_period: course.start_period, end_period: course.end_period,
    week_start: course.week_start, week_end: course.week_end, credit: course.credit || 2,
  }
  dialogVisible.value = true
}

function onCellClick(day: number, period: number) {
  if (!getCourseAt(day, period)) {
    showAddDialog(day, period)
  }
}

async function handleSave() {
  const data = {
    ...courseForm.value,
    class_group_id: filterClassGroupId.value!,
    semester: filterSemester.value,
  }
  try {
    if (editingCourse.value) {
      await adminUpdateCourse(editingCourse.value.id, data)
      ElMessage.success('修改成功')
    } else {
      await adminCreateCourse(data)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadCourses()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(id: number) {
  await ElMessageBox.confirm('确认删除该课程？', '提示', { type: 'warning' })
  await adminDeleteCourse(id)
  ElMessage.success('删除成功')
  loadCourses()
}

// ─── 加载 ─────────────────────────────────────────────
async function loadCourses() {
  if (!filterClassGroupId.value || !filterSemester.value) { courses.value = []; return }
  const data = await adminGetCourses({ class_group_id: filterClassGroupId.value, semester: filterSemester.value })
  courses.value = data as any
}

onMounted(async () => {
  const [c, m, cg] = await Promise.all([getColleges(), getMajors(), getClassGroups()])
  colleges.value = c as any
  majors.value = m as any
  classGroups.value = cg as any
})
</script>

<style scoped>
.page-container { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; }

.schedule-grid { border: 1px solid #e4e7ed; border-radius: 4px; overflow: hidden; }
.grid-row { display: flex; }
.grid-row.header { background: #f5f7fa; font-weight: 600; }
.cell { flex: 1; min-height: 48px; display: flex; align-items: center; justify-content: center; border-right: 1px solid #e4e7ed; border-bottom: 1px solid #e4e7ed; padding: 4px; }
.cell:last-child { border-right: none; }
.period-header, .period-cell { width: 80px; flex: none; font-size: 13px; color: #666; }
.day-header { font-size: 14px; }
.day-cell { cursor: pointer; position: relative; min-height: 80px; align-items: stretch; justify-content: stretch; }
.day-cell:hover { background: #f0f9ff; }
.empty-cell { color: #ccc; font-size: 20px; width: 100%; text-align: center; padding-top: 20px; }
.course-card { background: linear-gradient(135deg, #409eff, #66b1ff); color: #fff; border-radius: 6px; padding: 6px 8px; width: 100%; cursor: pointer; position: relative; }
.course-name { font-weight: 600; font-size: 13px; margin-bottom: 2px; }
.course-info { font-size: 11px; opacity: 0.9; }
.course-weeks { font-size: 10px; opacity: 0.7; margin-top: 2px; }
.delete-icon { position: absolute; top: 2px; right: 2px; cursor: pointer; opacity: 0; transition: opacity 0.2s; }
.course-card:hover .delete-icon { opacity: 1; }
</style>
