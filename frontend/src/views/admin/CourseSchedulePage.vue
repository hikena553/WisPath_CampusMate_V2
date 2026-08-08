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
        <el-select v-model="filterSemester" placeholder="选择学期" style="width: 200px" @change="loadCourses">
          <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-button type="primary" plain @click="showImportDialog">导入课程表</el-button>
      </div>
    </el-card>

    <!-- 课表网格 -->
    <el-card shadow="never" v-if="filterClassGroupId && filterSemester">
      <template #header>
        <div class="card-header">
          <span>{{ currentClassName }} — {{ semesterLabel }} 课程表</span>
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

    <!-- 导入弹窗 -->
    <el-dialog v-model="importDialogVisible" title="导入课程表" width="550px">
      <el-form label-width="80px">
        <el-form-item label="目标学院">
          <el-select v-model="importCollegeId" placeholder="选择学院" style="width: 100%">
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学期">
          <el-select v-model="importSemester" placeholder="选择学期" style="width: 100%">
            <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="上传文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 Excel 文件到此处 或 <em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip" style="margin-top: 8px">
                支持 .xlsx / .xls 格式。表头需包含：班级名称、课程名称、授课教师、上课地点、星期、开始节次、结束节次、开始周、结束周、学分
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <!-- 导入结果 -->
      <div v-if="importResult" class="import-result">
        <el-alert
          :type="importResult.errors.length > 0 ? 'warning' : 'success'"
          :closable="false"
          show-icon
        >
          <template #title>
            共 {{ importResult.total }} 条，成功 {{ importResult.created }} 条，跳过 {{ importResult.skipped }} 条
            <span v-if="importResult.errors.length">，异常 {{ importResult.errors.length }} 条</span>
          </template>
        </el-alert>
        <div v-if="importResult.unmatched_classes.length" style="margin-top: 8px">
          <span style="color: #e6a23c">未匹配班级：</span>
          <el-tag v-for="cls in importResult.unmatched_classes" :key="cls" size="small" type="warning" style="margin: 2px 4px">{{ cls }}</el-tag>
        </div>
        <div v-if="importResult.errors.length" style="margin-top: 8px; max-height: 150px; overflow-y: auto">
          <div v-for="(err, i) in importResult.errors" :key="i" style="font-size: 12px; color: #f56c6c; margin: 2px 0">
            第{{ err.row }}行: {{ err.msg }}
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleImport" :loading="importLoading">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, UploadFilled } from '@element-plus/icons-vue'
import type { College, Major, ClassGroup, Course } from '@/types'
import type { UploadFile, UploadInstance } from 'element-plus'
import { getColleges, getMajors, getClassGroups } from '@/api/organization'
import {
  adminGetCourses, adminCreateCourse, adminUpdateCourse, adminDeleteCourse,
  adminGetSemesters, adminImportCourses,
} from '@/api/academic'

const colleges = ref<College[]>([])
const majors = ref<Major[]>([])
const classGroups = ref<ClassGroup[]>([])
const courses = ref<Course[]>([])
const semesters = ref<{ value: string; label: string }[]>([])

const filterCollegeId = ref<number | null>(null)
const filterMajorId = ref<number | null>(null)
const filterClassGroupId = ref<number | null>(null)
const filterSemester = ref('')

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
const semesterLabel = computed(() => {
  const s = semesters.value.find(s => s.value === filterSemester.value)
  return s ? s.label : filterSemester.value
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

// ─── 导入 ─────────────────────────────────────────────
const importDialogVisible = ref(false)
const importCollegeId = ref<number | null>(null)
const importSemester = ref('')
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const importResult = ref<any>(null)
const uploadRef = ref<UploadInstance>()

function showImportDialog() {
  importCollegeId.value = filterCollegeId.value
  importSemester.value = filterSemester.value
  importFile.value = null
  importResult.value = null
  uploadRef.value?.clearFiles()
  importDialogVisible.value = true
}

function onFileChange(file: UploadFile) {
  importFile.value = file.raw || null
}

function onFileRemove() {
  importFile.value = null
}

async function handleImport() {
  if (!importCollegeId.value) { ElMessage.warning('请选择目标学院'); return }
  if (!importSemester.value) { ElMessage.warning('请选择学期'); return }
  if (!importFile.value) { ElMessage.warning('请上传课程表文件'); return }

  importLoading.value = true
  importResult.value = null
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    fd.append('college_id', String(importCollegeId.value))
    fd.append('semester', importSemester.value)
    const res = await adminImportCourses(fd)
    importResult.value = res
    ElMessage.success(`导入完成：成功 ${(res as any).created} 条`)
    if (filterClassGroupId.value && filterSemester.value) {
      loadCourses()
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importLoading.value = false
  }
}

// ─── 加载 ─────────────────────────────────────────────
async function loadCourses() {
  if (!filterClassGroupId.value || !filterSemester.value) { courses.value = []; return }
  const data = await adminGetCourses({ class_group_id: filterClassGroupId.value, semester: filterSemester.value })
  courses.value = data as any
}

async function loadSemesters() {
  try {
    const data = await adminGetSemesters()
    semesters.value = data as any
    if (semesters.value.length > 0 && !filterSemester.value) {
      filterSemester.value = semesters.value[0].value
    }
  } catch {
    semesters.value = [
      { value: '2025-2026-1', label: '2025-2026 第一学期' },
      { value: '2025-2026-2', label: '2025-2026 第二学期' },
    ]
    filterSemester.value = semesters.value[0].value
  }
}

onMounted(async () => {
  const [c, m, cg] = await Promise.all([getColleges(), getMajors(), getClassGroups()])
  colleges.value = c as any
  majors.value = m as any
  classGroups.value = cg as any
  loadSemesters()
})
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { margin-bottom: 12px; }
.page-header h2 { margin: 0;   font-size: 18px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

.schedule-grid { border: 1px solid #e4e7ed; border-radius: 4px; overflow: hidden; }
.grid-row { display: flex; }
.grid-row.header { background: #f5f7fa; font-weight: 600; }
.cell { flex: 1; min-height: 40px; display: flex; align-items: center; justify-content: center; border-right: 1px solid #e4e7ed; border-bottom: 1px solid #e4e7ed; padding: 3px; }
.cell:last-child { border-right: none; }
.period-header, .period-cell { width: 64px; flex: none; font-size: 12px; color: #666; }
.day-header { font-size: 13px; }
.day-cell { cursor: pointer; position: relative; min-height: 64px; align-items: stretch; justify-content: stretch; }
.day-cell:hover { background: #f0f9ff; }
.empty-cell { color: #ccc; font-size: 16px; width: 100%; text-align: center; padding-top: 14px; }
.course-card { background: linear-gradient(135deg, #409eff, #66b1ff); color: #fff; border-radius: 4px; padding: 4px 6px; width: 100%; cursor: pointer; position: relative; }
.course-name { font-weight: 600; font-size: 12px; margin-bottom: 1px; }
.course-info { font-size: 10px; opacity: 0.9; }
.course-weeks { font-size: 10px; opacity: 0.7; margin-top: 1px; }
.delete-icon { position: absolute; top: 1px; right: 1px; cursor: pointer; opacity: 0; transition: opacity 0.2s; }
.course-card:hover .delete-icon { opacity: 1; }

.import-result { margin-top: 12px; }
</style>
