import request from '@/utils/request'

/**
 * 教学域 API（后端 app/api/teaching.py）
 *
 * 语义约定：
 * - 「我教的课」严格按 Course.teacher_id 判定；课表页额外的「按任课教师看」是只读的协作视图。
 * - 本文件只保留课表查询相关的接口。
 */

/** 一门课（教学域视角） */
export interface TeachingCourse {
  id: number
  name: string
  class_group_id: number
  class_name: string
  college_name: string
  teacher: string
  teacher_id: number | null
  location: string
  day_of_week: number
  start_period: number
  end_period: number
  week_start: number
  week_end: number
  semester: string
  credit: number | null
  student_count: number
  /** 本学期已点名课次数（后端历史字段，前端课表不再展示） */
  attendance_sessions: number
  /** 被单次调课挪走的教学周：这几周该课不上（补课是另一条记录） */
  skip_weeks?: number[]
  /** 由哪张调课申请补出来的单次补课（普通课为 null） */
  source_change_id?: number | null
}

// ── 课表：我的 / 按任课教师 / 按班级 ─────────────────────────────

export interface ScheduleTeacher {
  teacher_id: number | null
  name: string
  course_count: number
  class_count: number
  student_count: number
  /** 是否为当前登录教师本人 */
  is_me: boolean
}

/** 本学期有课的任课教师清单（课表页筛选器数据源，本人置顶） */
export function getScheduleTeachers(params?: { semester?: string; keyword?: string }) {
  return request.get<ScheduleTeacher[]>('/teaching/teachers', { params })
}

export interface ScheduleClass {
  class_group_id: number
  name: string
  college_name: string | null
  course_count: number
  student_count: number
  /** 是否是我任教的班级（用于置顶，不代表权限） */
  is_mine: boolean
}

/**
 * 本学期有课的班级清单（课表页「按班级」筛选器 / 空选态引导卡片）。
 * 独立接口：不要从「我的授课」里反推，否则本学期没排课的教师会看到空清单。
 */
export function getScheduleClasses(params?: { semester?: string; keyword?: string }) {
  return request.get<ScheduleClass[]>('/teaching/classes', { params })
}

export interface ScheduleView {
  semester: string | null
  semesters: string[]
  scope: 'mine' | 'teacher' | 'class'
  label: string
  courses: TeachingCourse[]
  today_courses: TeachingCourse[]
  today_course_count: number
  week_course_count: number
  /** 当前教学周（周次选择器默认值；学期外为 null） */
  current_week: number | null
  total_student_count: number
}

/**
 * 课表查询（三视图同构，前端一套渲染逻辑）。
 * - 不传 teacher_name / class_group_id → 我的课表
 * - 传 teacher_name → 该任课教师的课表（只读）
 * - 传 class_group_id → 该班级的课表（含所有任课教师）
 */
export function getScheduleView(params?: {
  semester?: string
  teacher_name?: string
  class_group_id?: number
}) {
  return request.get<ScheduleView>('/teaching/schedule', { params })
}
