import { createRouter, createWebHistory } from 'vue-router'
import { getUser, setUser, removeToken } from '@/utils/token'
import { isGuestMode } from '@/utils/guest'
import { getCurrentIdentity } from '@/api/auth'

declare module 'vue-router' {
  interface RouteMeta {
    role?: string
    keepAlive?: boolean
    title?: string
  }
}

const publicPaths = ['/login', '/welcome', '/forgot-password']

/** 首次打开引导页的本地标记（与 WelcomePage.vue 保持一致） */
const WELCOME_SEEN_KEY = 'mian02_welcome_seen'

/** 免费使用（游客）可访问的对外开放页面：校园资讯为公开内容 */
const guestAllowedPaths = ['/student/campus']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: () => import('@/views/login/LoginPage.vue') },
    // 首次打开的产品介绍页（参考抖音 / 微信引导页），无需登录
    { path: '/welcome', name: 'Welcome', component: () => import('@/views/login/WelcomePage.vue'), meta: { title: '认识绵小城' } },
    // 忘记密码：身份核验后自动通知管理员重置
    { path: '/forgot-password', name: 'ForgotPassword', component: () => import('@/views/login/ForgotPasswordPage.vue'), meta: { title: '找回密码' } },
    // 改密页：可独立访问的改密入口（站内提醒横幅走弹窗，本页供直接跳转/分享链接使用）
    {
      path: '/change-password',
      name: 'ChangePassword',
      component: () => import('@/views/login/ChangePasswordPage.vue'),
      meta: { title: '修改密码' },
    },
    // 家长只读分享页：免登录，凭 token 校验有效性（家校沟通 · 家长观察者）
    {
      path: '/share/guardian/:token',
      name: 'guardian-share',
      component: () => import('@/views/share/GuardianSharePage.vue'),
      meta: { title: '家校沟通' },
    },
    // 群邀请落地页：登录后扫码/打开链接访问，凭邀请码入群（无角色限制）
    {
      path: '/join/group/:code',
      name: 'join-group',
      component: () => import('@/views/share/JoinGroupPage.vue'),
      meta: { title: '加入群聊' },
    },

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
        // 我的关怀：教师端「人文关怀」的学生侧闭环（激励 / 关怀记录 / 家访记录）
        { path: 'care', name: 'student-care', component: () => import('@/views/student/CarePage.vue'), meta: { keepAlive: false } },
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
        { path: 'portfolio', name: 'teacher-portfolio', component: () => import('@/views/teacher/PortfolioPage.vue'), meta: { keepAlive: false } },
        { path: 'survey', name: 'teacher-survey', component: () => import('@/views/teacher/SurveyPage.vue'), meta: { keepAlive: false } },
        { path: 'care-center', name: 'teacher-care-center', component: () => import('@/views/teacher/CareCenterPage.vue'), meta: { keepAlive: false } },
        { path: 'guardian', name: 'teacher-guardian', component: () => import('@/views/teacher/GuardianPage.vue'), meta: { keepAlive: false } },
        { path: 'tasks', name: 'teacher-tasks', component: () => import('@/views/teacher/TasksPage.vue'), meta: { keepAlive: false } },
        { path: 'ai', name: 'teacher-ai-insights', component: () => import('@/views/teacher/AiInsightsPage.vue'), meta: { keepAlive: false } },
        // 功能总览：首页「常用功能」右上角「全部功能」入口下钻至此
        { path: 'features', name: 'teacher-features', component: () => import('@/views/teacher/AllFeaturesPage.vue'), meta: { keepAlive: false } },
        // 原「更多」页签已改名为「消息」；其余功能入口迁至首页宫格，旧链接统一重定向回首页
        { path: 'more', redirect: '/teacher' },
        { path: 'announcement', name: 'teacher-announcement', component: () => import('@/views/teacher/AnnouncementPage.vue'), meta: { keepAlive: false } },
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
        { path: 'feeds', name: 'admin-feeds', meta: { title: '资讯管理' }, component: () => import('@/views/admin/FeedSourcesPage.vue') },
        { path: 'references', name: 'admin-references', meta: { title: '开源参考复用' }, component: () => import('@/views/admin/ReferenceLibraryPage.vue') },
        { path: 'teachers', meta: { title: '教师管理' }, component: () => import('@/views/admin/TeachersPage.vue') },
        { path: 'students', meta: { title: '学生管理' }, component: () => import('@/views/admin/StudentsPage.vue') },
        { path: 'password-requests', name: 'admin-password-requests', meta: { title: '密码重置' }, component: () => import('@/views/admin/PasswordRequestsPage.vue') },
        { path: 'organizations', meta: { title: '院系班级' }, component: () => import('@/views/admin/OrganizationsPage.vue') },
        { path: 'courses', meta: { title: '课程表管理' }, component: () => import('@/views/admin/CourseSchedulePage.vue') },
        { path: 'crisis', name: 'admin-crisis', meta: { title: '危机预警' }, component: () => import('@/views/admin/CrisisMonitorPage.vue') },
        { path: 'feedbacks', meta: { title: '反馈管理' }, component: () => import('@/views/admin/FeedbackPage.vue') },
        { path: 'system', name: 'admin-system', meta: { title: '系统监控' }, component: () => import('@/views/admin/SystemMonitorPage.vue') },
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
  // 已缓存登录用户时忽略游客标记，避免多标签页残留标记把登录态误判成游客
  const guest = isGuestMode() && !getUser()
  // 游客没有登录凭证：跳过 /auth/me 探活，避免每次导航都打一次必然 401 的请求
  const user = guest ? null : await ensureUser()
  const roleHome = (u: Record<string, unknown>) =>
    ({ teacher: '/teacher', admin: '/admin' } as Record<string, string>)[u.role as string] || '/student'

  // 改密页：登录后可随时进入（未改密用户不再被强制跳转，仅由提醒横幅引导）
  if (to.path === '/change-password') {
    return user ? true : '/login'
  }

  // 家长只读分享页：公开访问，无需登录（凭 token 校验）
  if (to.path.startsWith('/share/')) {
    return true
  }

  // 首次访问登录页：先展示产品介绍（已登录用户不受影响）
  if (to.path === '/login' && !user) {
    let seen = false
    try {
      seen = !!localStorage.getItem(WELCOME_SEEN_KEY)
    } catch {
      seen = true
    }
    if (!seen) return '/welcome'
  }

  // 登录页：已登录按角色重定向；游客可回登录页走账号密码/一键登录
  if (publicPaths.includes(to.path)) {
    if (!user) return
    return roleHome(user)
  }

  // 免费使用（游客）：仅放开对外开放页面，其余功能引导登录
  if (guest) {
    if (to.path === '/student') return '/student/campus'
    if (guestAllowedPaths.some((p) => to.path.startsWith(p))) return true
    return { path: '/login', query: { reason: 'login' } }
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
