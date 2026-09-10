import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUser } from '@/utils/token'

declare module 'vue-router' {
  interface RouteMeta {
    role?: string
    keepAlive?: boolean
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
        { path: 'growth', redirect: '/student/schedule?tab=growth' },
        { path: 'schedule', component: () => import('@/views/student/SchedulePage.vue') },
        { path: 'grade', component: () => import('@/views/student/GradeAnalysisPage.vue') },
        { path: 'grade-analysis', component: () => import('@/views/student/GradeAnalysisPage.vue') },
        { path: 'service', component: () => import('@/views/student/ServicePage.vue') },
        { path: 'workbench', component: () => import('@/views/student/WorkbenchPage.vue') },
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
        { path: 'messages', name: 'teacher-messages', component: () => import('@/views/teacher/MessagesPage.vue'), meta: { keepAlive: false } },
        { path: 'profile', name: 'teacher-profile', component: () => import('@/views/teacher/ProfilePage.vue'), meta: { keepAlive: false } },
      ],
    },
    {
      path: '/admin',
      component: () => import('@/components/layout/AdminLayout.vue'),
      meta: { role: 'admin' },
      children: [
        { path: '', component: () => import('@/views/admin/HomePage.vue') },
        { path: 'knowledge', component: () => import('@/views/admin/KnowledgePage.vue') },
        { path: 'teachers', component: () => import('@/views/admin/TeachersPage.vue') },
        { path: 'students', component: () => import('@/views/admin/StudentsPage.vue') },
        { path: 'organizations', component: () => import('@/views/admin/OrganizationsPage.vue') },
        { path: 'courses', component: () => import('@/views/admin/CourseSchedulePage.vue') },
        { path: 'feedbacks', component: () => import('@/views/admin/FeedbackPage.vue') },
        { path: 'settings', component: () => import('@/views/admin/SettingPage.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const token = getToken()
  const user = getUser()
  
  // 未登录跳转登录页
  if (!token && !publicPaths.includes(to.path)) return '/login'
  
  // 已登录但访问登录页，根据角色重定向
  if (token && to.path === '/login') {
    const roleMap: Record<string, string> = { teacher: '/teacher', admin: '/admin' }
    return roleMap[(user?.role as string) || ''] || '/student'
  }
  
  // 角色检查
  if (token && user && to.meta.role) {
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
  }
})

export default router
