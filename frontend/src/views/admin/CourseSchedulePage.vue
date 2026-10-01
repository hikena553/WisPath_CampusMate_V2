<template>
  <div class="page-container">
    <!-- ══════════ 顶级工具栏：单行，标题 + 统计 + 操作 ══════════ -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2>课程表管理</h2>
        <span v-if="!loadingSummary" class="toolbar-summary">
          共 <b>{{ totalSchedules }}</b> 个课程表 · <b>{{ totalCourses }}</b> 门课程
        </span>
      </div>
      <div class="toolbar-actions">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索班级"
          clearable
          :prefix-icon="Search"
          class="search-input"
        />
        <el-select v-model="filterCollegeId" placeholder="学院" clearable style="width: 120px" @change="onCollegeChange">
          <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filterMajorId" placeholder="专业" clearable style="width: 130px" @change="onMajorChange" :disabled="!filterCollegeId">
          <el-option v-for="m in filteredMajors" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-button type="primary" plain @click="showImportDialog">导入课程表</el-button>
        <el-button type="success" plain :icon="Connection" @click="showXiqueDialog">喜鹊儿同步</el-button>
        <el-button type="warning" plain :icon="Setting" @click="showSemesterDialog">学期管理</el-button>
      </div>
    </div>

    <!-- ══════════ 总览模式：学期分页 + 课程表卡片 ══════════ -->
    <template v-if="!activeClassId">
      <div v-if="semesterTabs.length" class="semester-tabs">
        <button
          v-for="t in semesterTabs"
          :key="t.value"
          class="sem-tab"
          :class="{ active: filterSemester === t.value }"
          @click="onSemesterChange(t.value)"
        >
          {{ t.label }}
          <span class="sem-count">{{ t.schedule_count }}</span>
        </button>
      </div>

      <div v-if="loadingSummary && !schedules.length" class="card-skeleton">
        <el-skeleton :rows="6" animated />
      </div>

      <template v-else>
        <!-- 已编排课程表 -->
        <section v-if="scheduledList.length" class="schedule-section">
          <div class="section-head">
            <span class="section-title">已编排课程表</span>
            <span class="section-count">{{ scheduledList.length }}</span>
          </div>
          <div class="card-grid">
            <div
              v-for="s in scheduledList"
              :key="s.class_group_id"
              class="schedule-card"
              @click="openSchedule(s)"
            >
              <div class="card-top">
                <span class="class-name">{{ s.class_name }}</span>
                <span class="course-badge">{{ s.course_count }} 门课</span>
              </div>
              <div class="card-meta">
                {{ s.college_name }}<template v-if="s.major_name"> · {{ s.major_name }}</template>
              </div>
              <div class="card-progress">
                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: progressPct(s) + '%' }"></div>
                </div>
                <span class="progress-text">{{ s.filled_slots }}/{{ s.total_slots }} 节次已占用</span>
              </div>
              <div class="card-foot">
                <span>{{ s.grade }} 级</span>
                <span v-if="s.student_count">{{ s.student_count }} 人</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 未编排班级 -->
        <section v-if="unscheduledList.length" class="schedule-section">
          <div class="section-head">
            <span class="section-title">未编排班级</span>
            <span class="section-count muted">{{ unscheduledList.length }}</span>
          </div>
          <div class="unscheduled-list">
            <div v-for="s in unscheduledList" :key="s.class_group_id" class="unscheduled-item">
              <span class="u-name">{{ s.class_name }}</span>
              <span class="u-meta">{{ s.college_name }} · {{ s.major_name }} · {{ s.grade }} 级</span>
              <el-button size="small" type="primary" plain @click="openSchedule(s)">去编排</el-button>
            </div>
          </div>
        </section>

        <!-- 无任何数据 -->
        <div v-if="!scheduledList.length && !unscheduledList.length" class="empty-wrap">
          <el-empty description="还没有任何课程表数据">
            <el-button type="primary" @click="showImportDialog">导入课程表</el-button>
            <el-button type="success" plain @click="showXiqueDialog">喜鹊儿同步</el-button>
          </el-empty>
        </div>
      </template>
    </template>

    <!-- ══════════ 详情模式：单个班级课程表网格 ══════════ -->
    <template v-else>
      <div class="detail-bar">
        <el-button text :icon="ArrowLeft" @click="backToList">返回</el-button>
        <div class="detail-title">
          <span class="detail-class">{{ currentClassName }}</span>
          <span class="detail-sem">
            {{ semesterLabel }} · <b>{{ courses.length }}</b> 门课程
          </span>
        </div>
        <div class="detail-actions">
          <el-select v-model="activeClassId" style="width: 150px" @change="loadCourses">
            <el-option v-for="s in schedules" :key="s.class_group_id" :label="s.class_name" :value="s.class_group_id" />
          </el-select>
          <el-button type="primary" :icon="Plus" @click="showAddDialog()">添加课程</el-button>
        </div>
      </div>

      <div class="grid-card" v-loading="loadingCourses">
        <div v-if="!courses.length" class="grid-hint">
          该班级本学期暂无课程，点击下方空白格子或右上角「添加课程」开始编排
        </div>

        <div class="schedule-grid">
          <!-- 表头 -->
          <div class="grid-row header">
            <div class="cell period-header">节次</div>
            <div class="cell day-header" v-for="d in 7" :key="d">周{{ ['一','二','三','四','五','六','日'][d-1] }}</div>
          </div>
          <!-- 课表行 -->
          <div class="grid-row" v-for="p in periods" :key="p">
            <div class="cell period-cell">{{ p }}-{{ p+1 }}</div>
            <div
              class="cell day-cell"
              v-for="d in 7" :key="d"
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
      </div>
    </template>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingCourse ? '编辑课程' : '新增课程'" width="620px">
      <div class="form-scroll-x">
      <el-form :model="courseForm" label-width="100px">
        <el-form-item label="课程名称" required><el-input v-model="courseForm.name" placeholder="如：高等数学" /></el-form-item>
        <el-form-item label="授课教师" required><el-input v-model="courseForm.teacher" placeholder="如：张老师" /></el-form-item>
        <el-form-item label="上课地点" required><el-input v-model="courseForm.location" placeholder="如：教学楼A-301" /></el-form-item>
        <el-form-item label="星期" required>
          <el-select v-model="courseForm.day_of_week" placeholder="请选择星期" style="width: 100%">
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
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入弹窗 -->
    <el-dialog v-model="importDialogVisible" title="导入课程表" width="640px">
      <el-form label-width="100px">
        <el-form-item label="目标学院" required>
          <el-select v-model="importCollegeId" placeholder="选择学院" style="width: 100%">
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学期" required>
          <el-select v-model="importSemester" placeholder="选择学期" style="width: 100%">
            <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="上传文件" required>
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

    <!-- 喜鹊儿同步弹窗 -->
    <el-dialog v-model="xiqueDialogVisible" title="喜鹊儿课表同步" width="660px">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
        title="从喜鹊儿（青果教务）账号一键拉取课表，自动匹配学号对应的班级并写入课程表"
      />
      <el-form :model="xiqueForm" label-width="100px">
        <el-form-item label="教务地址" required>
          <el-input v-model="xiqueForm.root_url" placeholder="如：https://jwgl.mycc.edu.cn" />
        </el-form-item>
        <el-form-item label="学号" required>
          <el-input v-model="xiqueForm.username" placeholder="喜鹊儿登录学号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="xiqueForm.password"
            type="password"
            show-password
            :placeholder="xiquePasswordSet ? '已设置密码，留空则保持不变' : '喜鹊儿登录密码'"
          />
        </el-form-item>
        <el-form-item label="学年" required>
          <el-input-number v-model="xiqueForm.school_year" :min="2000" :max="2100" style="width: 160px" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px">起始年份，如 2024 表示 2024-2025 学年</span>
        </el-form-item>
        <el-form-item label="学期">
          <el-radio-group v-model="xiqueForm.term">
            <el-radio :value="0">第一学期</el-radio>
            <el-radio :value="1">第二学期</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="xiqueSemester" label="目标学期">
          <el-tag type="success" effect="light">{{ xiqueSemester }}</el-tag>
        </el-form-item>
      </el-form>

      <!-- 同步结果 -->
      <div v-if="xiqueResult" style="margin-top: 4px">
        <el-alert :type="xiqueResult.success ? 'success' : 'error'" :closable="false" show-icon>
          <template #title>
            <div style="white-space: pre-line">{{ xiqueResult.message || xiqueResult.error }}</div>
          </template>
        </el-alert>
        <div v-if="xiqueResult.success && xiqueResult.total" style="margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap">
          <el-tag type="primary">共 {{ xiqueResult.total }} 条</el-tag>
          <el-tag type="success">新增 {{ xiqueResult.created }}</el-tag>
          <el-tag type="warning">更新 {{ xiqueResult.updated }}</el-tag>
          <el-tag type="info">跳过 {{ xiqueResult.skipped }}</el-tag>
        </div>
      </div>

      <template #footer>
        <el-button @click="xiqueDialogVisible = false">关闭</el-button>
        <el-button type="success" plain @click="handleSaveXiqueConfig" :loading="xiqueSaving">保存配置</el-button>
        <el-button type="primary" :loading="xiqueSyncing" @click="handleSyncXique">一键同步</el-button>
      </template>
    </el-dialog>

    <!-- 学期管理弹窗 -->
    <el-dialog v-model="semesterDialogVisible" title="学期管理" width="720px">
      <div class="sem-manage-tip">
        手工配置的学期（含无课程数据）会显示在课程表总览中；已有课程数据的学期自动纳入管理，删除前需先移除其中课程
      </div>

      <!-- 新增表单 -->
      <div class="sem-add-row">
        <el-input v-model="semForm.year" placeholder="学年，如 2026-2027" style="width: 150px" />
        <el-select v-model="semForm.term" style="width: 120px">
          <el-option label="第一学期" :value="1" />
          <el-option label="第二学期" :value="2" />
        </el-select>
        <el-input v-model="semForm.label" placeholder="显示名称（可选，默认自动生成）" style="flex: 1" />
        <el-button type="primary" :loading="semSaving" @click="handleCreateSemester">新增学期</el-button>
      </div>

      <!-- 学期列表 -->
      <el-table v-loading="semLoading" :data="managedSemesters" size="small" class="sem-table">
        <el-table-column label="学期" min-width="120">
          <template #default="{ row }">
            <b>{{ row.value }}</b>
          </template>
        </el-table-column>
        <el-table-column label="显示名称" min-width="180">
          <template #default="{ row }">
            <el-input
              v-if="editingSemId === row.id"
              v-model="semEditLabel"
              size="small"
              style="width: 160px"
            />
            <span v-else>{{ row.label }}</span>
          </template>
        </el-table-column>
        <el-table-column label="课程数" width="86" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.course_count" type="primary" size="small">{{ row.course_count }} 门</el-tag>
            <span v-else style="color: #c0c4cc">—</span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="104" align="center">
          <template #default="{ row }">
            <el-tag :type="row.managed ? 'success' : 'info'" size="small" effect="plain">
              {{ row.managed ? '手工配置' : '课程数据' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="right">
          <template #default="{ row }">
            <template v-if="editingSemId === row.id">
              <el-button link type="primary" size="small" @click="handleUpdateSemester(row)">保存</el-button>
              <el-button link size="small" @click="cancelEditSemester">取消</el-button>
            </template>
            <template v-else>
              <el-button v-if="row.managed" link type="primary" size="small" @click="startEditSemester(row)">编辑</el-button>
              <el-button v-if="row.managed" link type="danger" size="small" @click="handleDeleteSemester(row)">删除</el-button>
              <span v-else style="color: #c0c4cc; font-size: 12px">自动</span>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, UploadFilled, Connection, Search, ArrowLeft, Plus, Setting } from '@element-plus/icons-vue'
import type { College, Major, Course } from '@/types'
import type { UploadFile, UploadInstance } from 'element-plus'
import { getColleges, getMajors } from '@/api/organization'
import {
  adminGetCourses, adminCreateCourse, adminUpdateCourse, adminDeleteCourse,
  adminGetSemesters, adminImportCourses, adminGetCoursesSummary,
  adminGetXiqueConfig, adminSaveXiqueConfig, adminSyncXique,
  adminGetManagedSemesters, adminCreateSemester, adminUpdateSemester, adminDeleteSemester,
  type ScheduleSummaryItem, type ManagedSemester,
} from '@/api/academic'

// ─── 组织数据 ─────────────────────────────────────────────
const colleges = ref<College[]>([])
const majors = ref<Major[]>([])
const semesters = ref<{ value: string; label: string }[]>([])

// ─── 筛选与总览 ───────────────────────────────────────────
const filterCollegeId = ref<number | null>(null)
const filterMajorId = ref<number | null>(null)
const filterSemester = ref('')
const searchKeyword = ref('')

const semesterTabs = ref<{ value: string; label: string; schedule_count: number; course_count: number }[]>([])
const schedules = ref<ScheduleSummaryItem[]>([])
const loadingSummary = ref(false)

// ─── 详情模式 ─────────────────────────────────────────────
const activeClassId = ref<number | null>(null)
const courses = ref<Course[]>([])
const loadingCourses = ref(false)

const periods = [1, 3, 5, 7, 9]

const filteredMajors = computed(() =>
  filterCollegeId.value ? majors.value.filter(m => m.college_id === filterCollegeId.value) : majors.value
)

const keyword = computed(() => searchKeyword.value.trim().toLowerCase())
const matchKeyword = (s: ScheduleSummaryItem) => {
  if (!keyword.value) return true
  const text = `${s.class_name} ${s.college_name || ''} ${s.major_name || ''}`.toLowerCase()
  return text.includes(keyword.value)
}

const scheduledList = computed(() => schedules.value.filter(s => s.course_count > 0 && matchKeyword(s)))
const unscheduledList = computed(() => schedules.value.filter(s => s.course_count === 0 && matchKeyword(s)))
const totalSchedules = computed(() => schedules.value.filter(s => s.course_count > 0).length)
const totalCourses = computed(() => schedules.value.reduce((sum, s) => sum + s.course_count, 0))

const currentClassName = computed(() =>
  schedules.value.find(s => s.class_group_id === activeClassId.value)?.class_name || ''
)
const semesterLabel = computed(() => {
  const t = semesterTabs.value.find(t => t.value === filterSemester.value)
  return t ? t.label : filterSemester.value
})

function progressPct(s: ScheduleSummaryItem) {
  return Math.round((s.filled_slots / Math.max(s.total_slots, 1)) * 100)
}

// ─── 总览交互 ─────────────────────────────────────────────
async function loadSummary() {
  loadingSummary.value = true
  try {
    const data = await adminGetCoursesSummary({
      semester: filterSemester.value || undefined,
      college_id: filterCollegeId.value || undefined,
      major_id: filterMajorId.value || undefined,
    })
    semesterTabs.value = data.semesters
    schedules.value = data.schedules
    if (data.semesters.length) {
      // 选中的学期不在已有列表中时，跳到最新的一个有数据的学期
      if (!filterSemester.value || !data.semesters.some(t => t.value === filterSemester.value)) {
        filterSemester.value = data.semesters[0].value
        loadingSummary.value = false
        await loadSummary()
        return
      }
    }
  } finally {
    loadingSummary.value = false
  }
}

function onSemesterChange(v: string) {
  if (v === filterSemester.value) return
  filterSemester.value = v
  activeClassId.value = null
  loadSummary()
}

function onCollegeChange() {
  filterMajorId.value = null
  activeClassId.value = null
  loadSummary()
}

function onMajorChange() {
  activeClassId.value = null
  loadSummary()
}

function openSchedule(s: ScheduleSummaryItem) {
  activeClassId.value = s.class_group_id
  courses.value = []
  loadCourses()
}

function backToList() {
  activeClassId.value = null
  loadSummary()
}

// ─── 课表网格 ─────────────────────────────────────────────
function getCourseAt(day: number, period: number) {
  return courses.value.find(c => c.day_of_week === day && c.start_period <= period && c.end_period >= period)
}

async function loadCourses() {
  if (!activeClassId.value || !filterSemester.value) { courses.value = []; return }
  loadingCourses.value = true
  try {
    const data = await adminGetCourses({ class_group_id: activeClassId.value, semester: filterSemester.value })
    courses.value = data as any
  } finally {
    loadingCourses.value = false
  }
}

// ─── 新增/编辑 ─────────────────────────────────────────────
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
  if (!activeClassId.value) return
  const data = {
    ...courseForm.value,
    class_group_id: activeClassId.value,
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
    loadSummary()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确认删除该课程？', '提示', { type: 'warning' })
    await adminDeleteCourse(id)
    ElMessage.success('删除成功')
    loadCourses()
    loadSummary()
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
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
    loadSummary()
    if (filterSemester.value && activeClassId.value) {
      loadCourses()
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importLoading.value = false
  }
}

// ─── 喜鹊儿同步 ─────────────────────────────────────
const xiqueDialogVisible = ref(false)
const xiqueSaving = ref(false)
const xiqueSyncing = ref(false)
const xiquePasswordSet = ref(false)
const xiqueSemester = ref('')
const xiqueResult = ref<{ success: boolean; message?: string; error?: string; total?: number; created?: number; updated?: number; skipped?: number } | null>(null)
const xiqueForm = ref({
  root_url: '',
  username: '',
  password: '',
  school_year: new Date().getFullYear(),
  term: new Date().getMonth() >= 7 ? 1 : 0,
})

async function showXiqueDialog() {
  xiqueResult.value = null
  xiqueForm.value.password = ''
  try {
    const cfg = await adminGetXiqueConfig()
    xiqueForm.value.root_url = cfg.root_url
    xiqueForm.value.username = cfg.username
    xiquePasswordSet.value = cfg.password_set
    xiqueSemester.value = cfg.semester
    if (cfg.school_year >= 2000) xiqueForm.value.school_year = cfg.school_year
    if (cfg.term === 0 || cfg.term === 1) xiqueForm.value.term = cfg.term
    if (cfg.hint && !cfg.root_url) ElMessage.info(cfg.hint)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '读取配置失败')
  }
  xiqueDialogVisible.value = true
}

async function handleSaveXiqueConfig() {
  if (!xiqueForm.value.root_url.trim()) { ElMessage.warning('请填写教务地址'); return }
  if (!xiqueForm.value.username.trim()) { ElMessage.warning('请填写学号'); return }
  xiqueSaving.value = true
  try {
    const payload: any = {
      root_url: xiqueForm.value.root_url,
      username: xiqueForm.value.username,
      school_year: xiqueForm.value.school_year,
      term: xiqueForm.value.term,
    }
    if (xiqueForm.value.password) payload.password = xiqueForm.value.password
    const cfg = await adminSaveXiqueConfig(payload)
    xiquePasswordSet.value = cfg.password_set
    xiqueSemester.value = cfg.semester
    xiqueForm.value.password = ''
    ElMessage.success('配置已保存')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    xiqueSaving.value = false
  }
}

async function handleSyncXique() {
  if (!xiqueForm.value.root_url.trim()) { ElMessage.warning('请填写教务地址'); return }
  if (!xiqueForm.value.username.trim()) { ElMessage.warning('请填写学号'); return }
  if (!xiquePasswordSet.value && !xiqueForm.value.password) { ElMessage.warning('请填写密码'); return }
  xiqueSyncing.value = true
  xiqueResult.value = null
  try {
    const payload: any = {
      root_url: xiqueForm.value.root_url,
      username: xiqueForm.value.username,
      school_year: xiqueForm.value.school_year,
      term: xiqueForm.value.term,
    }
    if (xiqueForm.value.password) payload.password = xiqueForm.value.password
    const res = await adminSyncXique(payload)
    xiqueResult.value = { success: true, message: res.message, total: res.total, created: res.created, updated: res.updated, skipped: res.skipped }
    xiqueSemester.value = res.semester
    xiquePasswordSet.value = true
    xiqueForm.value.password = ''
    // 同步成功后刷新总览与当前课表
    loadSummary()
    if (filterSemester.value && activeClassId.value) loadCourses()
  } catch (e: any) {
    xiqueResult.value = { success: false, error: e.response?.data?.detail || '同步失败，请检查网络或教务信息' }
  } finally {
    xiqueSyncing.value = false
  }
}

// ─── 学期管理 ─────────────────────────────────────
const semesterDialogVisible = ref(false)
const managedSemesters = ref<ManagedSemester[]>([])
const semLoading = ref(false)
const semSaving = ref(false)
const semForm = ref({ year: '', term: 1, label: '' })
const editingSemId = ref(-1)  // -1 表示当前无编辑；null 与课程数据行（id=null）冲突，故不可用
const semEditLabel = ref('')

async function showSemesterDialog() {
  semesterDialogVisible.value = true
  semForm.value = { year: '', term: 1, label: '' }
  editingSemId.value = -1
  await loadManagedSemesters()
}

async function loadManagedSemesters() {
  semLoading.value = true
  try {
    managedSemesters.value = await adminGetManagedSemesters()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载学期列表失败')
  } finally {
    semLoading.value = false
  }
}

async function handleCreateSemester() {
  const year = semForm.value.year.trim()
  if (!/^\d{4}-\d{4}$/.test(year)) { ElMessage.warning('学年格式不正确，示例：2026-2027'); return }
  semSaving.value = true
  try {
    const payload: { year: string; term: number; label?: string } = { year, term: semForm.value.term }
    if (semForm.value.label.trim()) payload.label = semForm.value.label.trim()
    await adminCreateSemester(payload)
    ElMessage.success('新增学期成功')
    semForm.value = { year: '', term: 1, label: '' }
    await loadManagedSemesters()
    loadSummary()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '新增失败')
  } finally {
    semSaving.value = false
  }
}

function startEditSemester(row: ManagedSemester) {
  editingSemId.value = row.id!
  semEditLabel.value = row.label
}

function cancelEditSemester() {
  editingSemId.value = -1
}

async function handleUpdateSemester(row: ManagedSemester) {
  if (!semEditLabel.value.trim()) { ElMessage.warning('显示名称不能为空'); return }
  try {
    await adminUpdateSemester(row.id!, { label: semEditLabel.value.trim() })
    ElMessage.success('保存成功')
    editingSemId.value = -1
    await loadManagedSemesters()
    loadSummary()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function handleDeleteSemester(row: ManagedSemester) {
  try {
    await ElMessageBox.confirm(
      `确认删除学期「${row.value}」？删除后其将不再出现在课程表总览的学期列表中。`,
      '提示', { type: 'warning' }
    )
    await adminDeleteSemester(row.id!)
    ElMessage.success('删除成功')
    await loadManagedSemesters()
    loadSummary()
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// ─── 加载 ─────────────────────────────────────────────
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
  const [c, m] = await Promise.all([getColleges(), getMajors()])
  colleges.value = c as any
  majors.value = m as any
  loadSemesters()
  loadSummary()
})
</script>

<style scoped>
/* ══════════ 顶级工具栏：紧凑单行 ══════════ */
.toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px;
  padding: 6px 16px; margin-bottom: 0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.toolbar-left { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.toolbar h2 { margin: 0; font-size: 16px; color: #1e293b; white-space: nowrap; }
.toolbar-summary { font-size: 12px; color: #64748b; white-space: nowrap; }
.toolbar-summary b { color: #2563eb; font-weight: 600; }
.toolbar-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.search-input { width: 170px; }

/* ══════════ 学期分页 ══════════ */
.semester-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }
.sem-tab {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 999px;
  border: 1px solid #e2e8f0; background: #fff;
  color: #475569; font-size: 13px; cursor: pointer;
  transition: all 0.15s ease;
}
.sem-tab:hover { border-color: #bfdbfe; color: #2563eb; }
.sem-tab.active { background: #2563eb; border-color: #2563eb; color: #fff; font-weight: 600; }
.sem-count {
  font-size: 11px; line-height: 1; padding: 3px 6px; border-radius: 999px;
  background: #eef2f7; color: #64748b;
}
.sem-tab.active .sem-count { background: rgba(255, 255, 255, 0.22); color: #fff; }

/* ══════════ 总览区块 ══════════ */
.schedule-section { margin-bottom: 18px; }
.section-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.section-title { font-size: 14px; font-weight: 600; color: #334155; }
.section-count {
  font-size: 12px; font-weight: 600; color: #2563eb;
  background: #eff6ff; border: 1px solid #dbeafe;
  padding: 0 8px; border-radius: 999px;
}
.section-count.muted { color: #64748b; background: #f1f5f9; border-color: #e2e8f0; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
.schedule-card {
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px;
  padding: 14px 16px; cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: all 0.18s ease;
}
.schedule-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.09);
  border-color: #bfdbfe;
}
.card-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.class-name { font-size: 15px; font-weight: 700; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.course-badge {
  font-size: 12px; font-weight: 600; color: #2563eb;
  background: #eff6ff; border: 1px solid #dbeafe;
  padding: 1px 8px; border-radius: 999px; flex-shrink: 0;
}
.card-meta {
  font-size: 12px; color: #64748b; margin-top: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card-progress { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.progress-track { flex: 1; height: 6px; border-radius: 3px; background: #eef2f7; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #3b82f6, #60a5fa); transition: width 0.3s ease; }
.progress-text { font-size: 11px; color: #94a3b8; flex-shrink: 0; }
.card-foot { display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: #94a3b8; }

/* 未编排班级 */
.unscheduled-list {
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px; overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.unscheduled-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; border-bottom: 1px solid #f1f5f9;
}
.unscheduled-item:last-child { border-bottom: none; }
.u-name { font-size: 13px; font-weight: 600; color: #334155; min-width: 110px; flex-shrink: 0; }
.u-meta {
  flex: 1; font-size: 12px; color: #94a3b8;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.card-skeleton, .empty-wrap {
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px;
  padding: 20px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

/* ══════════ 详情模式 ══════════ */
.detail-bar {
  display: flex; align-items: center; gap: 4px;
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px;
  padding: 8px 14px; margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.detail-title { display: flex; align-items: baseline; gap: 10px; flex: 1; min-width: 0; margin-left: 4px; }
.detail-class { font-size: 16px; font-weight: 700; color: #1e293b; white-space: nowrap; }
.detail-sem { font-size: 12px; color: #64748b; white-space: nowrap; }
.detail-sem b { color: #2563eb; }
.detail-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.grid-card {
  background: #fff; border: 1px solid #eef2f7; border-radius: 10px;
  padding: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.grid-hint {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #94a3b8; margin-bottom: 12px;
}
.grid-hint::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #93c5fd; flex-shrink: 0; }

/* 课表网格 */
.schedule-grid { border: 1px solid #e4e7ed; border-radius: 8px; overflow: hidden; }
.grid-row { display: flex; }
.grid-row.header { background: #f5f7fa; font-weight: 600; }
.cell {
  flex: 1; min-height: 40px;
  display: flex; align-items: center; justify-content: center;
  border-right: 1px solid #e4e7ed; border-bottom: 1px solid #e4e7ed; padding: 3px;
}
.cell:last-child { border-right: none; }
.period-header, .period-cell { width: 64px; flex: none; font-size: 12px; color: #666; }
.day-header { font-size: 13px; }
.day-cell { cursor: pointer; position: relative; min-height: 64px; align-items: stretch; justify-content: stretch; }
.day-cell:hover { background: #f0f9ff; }
.empty-cell { color: #cbd5e1; font-size: 16px; width: 100%; text-align: center; padding-top: 14px; }
.course-card {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: #fff; border-radius: 4px; padding: 4px 6px;
  width: 100%; cursor: pointer; position: relative;
}
.course-name { font-weight: 600; font-size: 12px; margin-bottom: 1px; }
.course-info { font-size: 10px; opacity: 0.9; }
.course-weeks { font-size: 10px; opacity: 0.7; margin-top: 1px; }
.delete-icon { position: absolute; top: 1px; right: 1px; cursor: pointer; opacity: 0; transition: opacity 0.2s; }
.course-card:hover .delete-icon { opacity: 1; }

.import-result { margin-top: 12px; }

/* ══════════ 学期管理弹窗 ══════════ */
.sem-manage-tip {
  font-size: 12px; color: #64748b; background: #f8fafc;
  border: 1px solid #eef2f7; border-radius: 8px;
  padding: 8px 12px; margin-bottom: 12px;
}
.sem-add-row {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  background: #f8fafc; border: 1px solid #eef2f7; border-radius: 8px;
  padding: 10px 12px;
}
.sem-table { margin-top: 12px; }

/* ══════════ 响应式 ══════════ */
@media (max-width: 768px) {
  .toolbar { padding: 10px 12px; }
  .toolbar-summary { display: none; }
  .search-input { width: 120px; }
  .detail-title { flex-direction: column; align-items: flex-start; gap: 2px; }
  .detail-actions { flex-direction: column; align-items: stretch; }
}
</style>