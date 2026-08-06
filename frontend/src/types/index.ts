export type UserRole = 'student' | 'teacher' | 'admin'

export interface UserInfo {
  id: number
  username: string
  name: string
  role: UserRole
  college?: string
  avatar?: string
  skills_json?: { skills: { name: string; context: string }[]; interests: string[] }
  tutor_id?: number | null
  gender?: string | null
  age?: number | null
  political_status?: string | null
  title?: string | null
  hometown?: string | null
  phone?: string | null
  department?: string | null
  class_name?: string | null
  password_changed?: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  suggestions?: Suggestion[]
  leaveData?: LeaveRequestOut
  timestamp: string
}

export interface Suggestion {
  text: string
  link?: string
  action?: string
}

export interface LeaveRequestCreate {
  start_date: string
  end_date: string
  reason: string
  leave_type: string
}

export interface LeaveRequestOut {
  id: number
  student_id: number
  student_name: string
  start_date: string
  end_date: string
  reason: string
  leave_type: string
  status: string
  reject_reason: string | null
  created_at: string
}

export interface CrisisAlert {
  id: number
  student_id: number
  student_name: string
  summary: string
  level: string
  keywords_matched: string | null
  resolved: boolean
  created_at: string
}

export interface GrowthRecord {
  id: number
  student_id: number
  type: 'honor' | 'competition' | 'practice' | 'paper' | 'achievement'
  title: string
  description: string | null
  date: string
  attachment_url?: string | null
  honor_level?: string | null
  organizer?: string | null
  competition_level?: string | null
  practice_type?: string | null
  practice_certificate?: string | null
  paper_type?: string | null
  paper_name?: string | null
  first_author?: string | null
  second_author?: string | null
  third_author?: string | null
  achievement_type?: string | null
  achievement_name?: string | null
}

export interface CampusFigure {
  id: number
  name: string
  title: string
  avatar: string
  description: string
  category: 'student' | 'teacher' | 'alumni'
  proofs?: string | null
}

export interface CampusScenery {
  id: number
  title: string
  image_url: string
  description: string
  location: string
  area: string
}

export interface Announcement {
  title: string
  date: string | null
  url: string | null
}

export interface Course {
  id: number
  name: string
  teacher: string
  location: string
  day_of_week: number
  start_period: number
  end_period: number
  week_start: number
  week_end: number
  semester: string
  credit: number | null
  class_group_id: number
}

export interface College {
  id: number
  name: string
  code: string
  description: string | null
}

export interface Major {
  id: number
  college_id: number
  name: string
  code: string
  description: string | null
  college_name: string | null
}

export interface ClassGroup {
  id: number
  major_id: number
  name: string
  grade: number
  student_count: number | null
  major_name: string | null
  college_name: string | null
}

export interface Grade {
  id: number
  course_name: string
  score: number
  credit: number
  gpa: number
  semester: string
}

export interface Exam {
  id: number
  course_name: string
  exam_date: string
  start_time: string
  end_time: string
  location: string
}

export interface ServiceTicket {
  id: number
  type: string
  title: string
  content: string
  status: string
  created_at: string
  applicant_name: string
  applicant_no: string
  applicant_college: string
  form_data: Record<string, any> | null
  attachments: string[] | null
}
