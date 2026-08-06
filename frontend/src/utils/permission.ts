import { useAuthStore } from '@/stores/auth'

// 权限检查函数
export function hasPermission(permission: string): boolean {
  const auth = useAuthStore()
  const user = auth.user
  
  if (!user) return false
  
  // 管理员拥有所有权限
  if (user.role === 'admin') return true
  
  // 角色权限映射
  const rolePermissions: Record<string, string[]> = {
    student: [
      'view_own_profile',
      'edit_own_profile',
      'view_own_growth',
      'manage_own_growth',
      'view_schedule',
      'view_grades',
      'submit_feedback',
      'view_announcements',
      'use_agent',
    ],
    teacher: [
      'view_own_profile',
      'edit_own_profile',
      'view_students',
      'manage_students',
      'view_class_stats',
      'approve_leave',
      'manage_announcements',
      'use_agent',
      'view_messages',
    ],
    admin: [
      'view_all_users',
      'manage_users',
      'manage_knowledge',
      'manage_system',
      'view_logs',
      'manage_feedbacks',
      'manage_settings',
      'export_data',
      'import_data',
    ],
  }
  
  const userPermissions = rolePermissions[user.role] || []
  return userPermissions.includes(permission)
}

// 检查是否是管理员
export function isAdmin(): boolean {
  const auth = useAuthStore()
  return auth.user?.role === 'admin'
}

// 检查是否是教师
export function isTeacher(): boolean {
  const auth = useAuthStore()
  return auth.user?.role === 'teacher'
}

// 检查是否是学生
export function isStudent(): boolean {
  const auth = useAuthStore()
  return auth.user?.role === 'student'
}

// 检查是否是本人或管理员
export function isSelfOrAdmin(userId: number): boolean {
  const auth = useAuthStore()
  const user = auth.user
  
  if (!user) return false
  if (user.role === 'admin') return true
  return user.id === userId
}

// 角色显示名称
export function getRoleName(role: string): string {
  const names: Record<string, string> = {
    student: '学生',
    teacher: '教师',
    admin: '管理员',
  }
  return names[role] || role
}

// 权限显示名称
export function getPermissionName(permission: string): string {
  const names: Record<string, string> = {
    view_own_profile: '查看个人资料',
    edit_own_profile: '编辑个人资料',
    view_own_growth: '查看成长记录',
    manage_own_growth: '管理成长记录',
    view_schedule: '查看课表',
    view_grades: '查看成绩',
    submit_feedback: '提交反馈',
    view_announcements: '查看公告',
    use_agent: '使用AI助手',
    view_students: '查看学生列表',
    manage_students: '管理学生',
    view_class_stats: '查看班级统计',
    approve_leave: '审批请假',
    manage_announcements: '管理公告',
    view_messages: '查看消息',
    view_all_users: '查看所有用户',
    manage_users: '管理用户',
    manage_knowledge: '管理知识库',
    manage_system: '管理系统',
    view_logs: '查看日志',
    manage_feedbacks: '管理反馈',
    manage_settings: '管理设置',
    export_data: '导出数据',
    import_data: '导入数据',
  }
  return names[permission] || permission
}
