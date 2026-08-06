import request from '@/utils/request'

export interface GradeStats {
  total_courses: number
  total_credits: number
  avg_score: number
  avg_gpa: number
  highest_gpa: number
  lowest_gpa: number
  pass_rate: number
}

export interface SemesterGPA {
  semester: string
  gpa: number
  credits: number
  course_count: number
}

export interface CourseTypeStats {
  type: string
  count: number
  avg_score: number
  avg_gpa: number
}

export interface ScoreDistribution {
  range: string
  count: number
  percentage: number
}

export interface GradeAnalysis {
  stats: GradeStats
  semester_gpa: SemesterGPA[]
  course_type_stats: CourseTypeStats[]
  score_distribution: ScoreDistribution[]
  top_courses: any[]
  weak_courses: any[]
}

export interface ClassGradeAnalysis {
  students: {
    student_id: number
    student_name: string
    avg_gpa: number
    total_credits: number
    course_count: number
  }[]
  stats: {
    total_students: number
    class_avg_gpa: number
    highest_gpa: number
    lowest_gpa: number
  }
}

// 获取学生成绩分析
export function getGradeAnalysis(studentId: number) {
  return request.get<GradeAnalysis>(`/academic/analysis/${studentId}`)
}

// 获取班级成绩分析
export function getClassGradeAnalysis(classId: number) {
  return request.get<ClassGradeAnalysis>(`/academic/analysis/class/${classId}`)
}
