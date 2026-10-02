import { createRouter, createWebHistory } from 'vue-router'
import { getUser, setUser, removeToken } from '@/utils/token'
import { getCurrentIdentity } from '@/api/auth'

declare module 'vue-router' {
  interface RouteMeta {
    role?: string
    keepAlive?: boolean
    title?: string
  }
}

const publicPaths = ['/login']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: () => import('@/views/login/LoginPage.vue') },

    {
      path: '/student',
      component: () => import('@/components/layout/StudentLayout.vue'),
      meta: { role: 'student' },
      children: [
        { path: '', component: () => import('@/views/student/HomePage.vue') },
        { path: 'agent', component: () => import('@/views/student/AgentPage.vue') },
        { path: 'campus', component: () => import('@/views/student/CampusPage.vue') },
        { path: 'growth', name: 'student-growth', component: () => import('@/views/student/GrowthPage.vue'), meta: { keepAlive: false } },
      { path: 'resources', name: 'student-resources', component: () => import('@/views/student/ResourcesPage.vue'), meta: { keepAlive: false } },
        { path: 'schedule', component: () => import('@/views/student/SchedulePage.vue') },
        { path: 'grade', component: () => import('@/views/student/GradeAnalysisPage.vue') },
        { path: 'grade-analysis', component: () => import('@/views/student/GradeAnalysisPage.vue') },
        { path: 'service', component: () => import('@/views/student/ServicePage.vue') },
        { path: 'workbench', component: () => import('@/views/student/WorkbenchPage.vue') },
        { path: 'plan', name: 'student-plan', component: () => import('@/views/student/PlanView.vue'), meta: { keepAlive: false } },
        { path: 'portfolio', name: 'student-portfolio', component: () => import('@/views/student/PortfolioView.vue'), meta: { keepAlive: false } },
        { path: 'community', name: 'student-community', component: () => import('@/views/student/CommunityView.vue'), meta: { keepAlive: false } },
        { path: 'emotion', name: 'student-emotion', component: () => import('@/views/student/EmotionTrashPage.vue'), meta: { keepAlive: false } },
        { path: 'my-requests', name: 'student-my-requests', component: () => import('@/views/student/MyRequestsPage.vue'), meta: { keepAlive: false } },
        { path: 'materials', name: 'student-materials', component: () => import('@/views/student/MaterialArchivePage.vue'), meta: { keepAlive: false } },
        { path: 'feedback', component: () => import('@/views/student/FeedbackPage.vue') },
        { path: 'profile', component: () => import('@/views/student/ProfilePage.vue') },
      ],
    },
    {
      path: '/teacher',
      component: () => import('@/components/layout/TeacherLayout.vue'),
      meta: { role: 'teacher' },
      children: [
        { path: '', name: 'teacher-home', component: () => import('@/views/teacher/HomePage.vue'), meta: { keepAlive: true } },
        { path: 'agent', name: 'teacher-agent', component: () => import('@/views/teacher/AgentPage.vue'), meta: { keepAlive: false } },
        { path: 'students', name: 'teacher-students', component: () => import('@/views/teacher/StudentsPage.vue'), meta: { keepAlive: true } },
        { path: 'approval', name: 'teacher-approval', component: () => import('@/views/teacher/ApprovalPage.vue'), meta: { keepAlive: false } },
        { path: 'crisis', name: 'teacher-crisis', component: () => import('@/views/teacher/CrisisWorkbench.vue'), meta: { keepAlive: false } },
        { path: 'messages', name: 'teacher-messages', component: () => import('@/views/teacher/MessagesPage.vue'), meta: { keepAlive: false } },
        { path: 'profile', name: 'teacher-profile', component: () => import('@/views/teacher/ProfilePage.vue'), meta: { keepAlive: false } },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/components/layout/AdminLayout.vue'),
      meta: { role: 'admin' },
      children: [
        { path: '', meta: { title: '首页' }, component: () => import('@/views/admin/HomePage.vue') },
        { path: 'knowledge', meta: { title: '知识库' }, component: () => import('@/views/admin/KnowledgePage.vue') },
        { path: 'teachers', meta: { title: '教师管理' }, component: () => import('@/views/admin/TeachersPage.vue') },
        { path: 'students', meta: { title: '学生管理' }, component: () => import('@/views/admin/StudentsPage.vue') },
        { path: 'organizations', meta: { title: '院系班级' }, component: () => import('@/views/admin/OrganizationsPage.vue') },
        { path: 'courses', meta: { title: '课程表管理' }, component: () => import('@/views/admin/CourseSchedulePage.vue') },
        { path: 'crisis', name: 'admin-crisis', meta: { title: '危机预警' }, component: () => import('@/views/admin/CrisisMonitorPage.vue') },
        { path: 'feedbacks', meta: { title: '反馈管理' }, component: () => import('@/views/admin/FeedbackPage.vue') },
        { path: 'settings', meta: { title: '系统设置' }, component: () => import('@/views/admin/SettingPage.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

/**
 * 确保拿到完整的当前用户信息。
 * - 本地缓存命中（含 id）直接返回，避免每次导航都请求；
 * - 缓存缺失（localStorage 被清理/篡改）时调 /api/auth/me 拉取并回填；
 * - 拉取失败（token 失效/网络）返回 null，由守卫统一拒绝。
 */
async function ensureUser(): Promise<Record<string, unknown> | null> {
  const cached = getUser()
  if (cached && cached.id) return cached
  try {
    const identity = await getCurrentIdentity()
    const user = identity as unknown as Record<string, unknown>
    setUser(user)
    return user
  } catch {
    return null
  }
}

router.beforeEach(async (to) => {
  // 会话权威探测：本地缓存命中直接返回；否则调 /api/auth/me 探活并回填。
  // F3 后刷新页面内存态 token 为空，但 httpOnly Cookie 会自动随 /api/auth/me 携带，
  // 因此以「能否拿到 user」为准判断登录态，而非内存 token。
  const user = await ensureUser()

  // 登录页：已登录按角色重定向，未登录放行
  if (publicPaths.includes(to.path)) {
    if (!user) return
    const roleMap: Record<string, string> = { teacher: '/teacher', admin: '/admin' }
    return roleMap[user.role as string] || '/student'
  }

  // 其余路由一律要求已登录
  if (!user) {
    removeToken()
    return '/login'
  }

  // 角色检查：目标路由声明了角色时，必须持有完整 user 信息且角色匹配，
  // 否则一律拒绝（修复 user 缺失时跳过角色检查的旁路）。
  if (to.meta.role) {
    // 管理员可访问所有路由
    if (user.role === 'admin') return

    // 学生不能访问教师端
    if (user.role === 'student' && to.meta.role === 'teacher') return '/student'
    // 学生不能访问管理端
    if (user.role === 'student' && to.meta.role === 'admin') return '/student'

    // 教师不能访问学生端
    if (user.role === 'teacher' && to.meta.role === 'student') return '/teacher'
    // 教师不能访问管理端
    if (user.role === 'teacher' && to.meta.role === 'admin') return '/teacher'

    // 其它角色不匹配情况一律回登录
    if (user.role !== to.meta.role) return '/login'
  }
})

export default router
