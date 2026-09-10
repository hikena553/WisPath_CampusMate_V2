<template>
  <div class="profile-wrapper">
    <!-- 主页面 -->
    <transition :name="slideDirection">
      <div v-if="!currentPage" key="main" class="profile-page">
        <!-- 背景图区域 -->
        <div class="profile-banner" @click="openPage('banner')">
          <img v-if="bannerUrl" :src="bannerUrl" class="banner-img" />
          <div v-else class="banner-default" :style="{ background: bannerGradient }"></div>
          <div class="banner-overlay"></div>
          <div class="banner-edit-hint">
            <el-icon><Camera /></el-icon>
            <span>更换背景</span>
          </div>
        </div>

        <!-- 头部信息卡片 -->
        <div class="profile-header" @click="openPage('profile')">
          <el-avatar :size="54" :src="auth.user?.avatar || ''" class="header-avatar">
            {{ auth.userName?.[0] }}
          </el-avatar>
          <div class="header-info">
            <div class="header-name">{{ auth.userName }}</div>
            <div class="header-id">{{ auth.user?.username }}</div>
          </div>
          <el-icon class="header-arrow"><ArrowRight /></el-icon>
        </div>

        <!-- 个人成长展示 -->
        <div class="section-card">
          <div class="section-header">
            <div class="section-title">个人成长</div>
            <div class="section-more" @click="router.push('/student/growth')">查看详情</div>
          </div>
          <div class="growth-summary">
            <div class="growth-item">
              <div class="growth-value">{{ growthStats.awards || 0 }}</div>
              <div class="growth-label">获奖记录</div>
            </div>
            <div class="growth-item">
              <div class="growth-value">{{ growthStats.skills || 0 }}</div>
              <div class="growth-label">技能标签</div>
            </div>
            <div class="growth-item">
              <div class="growth-value">{{ growthStats.projects || 0 }}</div>
              <div class="growth-label">项目经历</div>
            </div>
          </div>
        </div>

        <!-- 客服与帮助 -->
        <div class="section-card">
          <div class="section-header">
            <div class="section-title">客服与帮助</div>
          </div>
          <div class="menu-list">
            <div class="menu-item" @click="openPage('feedback')">
              <el-icon :size="18"><ChatDotRound /></el-icon>
              <span class="menu-label">意见反馈</span>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="menu-item" @click="openPage('help')">
              <el-icon :size="18"><QuestionFilled /></el-icon>
              <span class="menu-label">使用帮助</span>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>

        <!-- 设置与隐私 -->
        <div class="section-card">
          <div class="section-header">
            <div class="section-title">设置与隐私</div>
          </div>
          <div class="menu-list">
            <div class="menu-item" @click="openPage('password')">
              <el-icon :size="18"><Lock /></el-icon>
              <span class="menu-label">修改密码</span>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="menu-item" @click="openPage('theme')">
              <el-icon :size="18"><Sunny /></el-icon>
              <span class="menu-label">主题设置</span>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="menu-item" @click="openPage('about')">
              <el-icon :size="18"><InfoFilled /></el-icon>
              <span class="menu-label">关于绵小城</span>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="menu-item" @click="logout">
              <el-icon :size="18"><SwitchButton /></el-icon>
              <span class="menu-label">退出登录</span>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>

        <div style="height: 80px;"></div>
      </div>
    </transition>

    <!-- 子页面 -->
    <transition :name="slideDirection">
      <div v-if="currentPage" key="sub" class="sub-page">
        <!-- 子页面头部 -->
        <div class="sub-page-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="sub-page-title">{{ pageTitle }}</div>
          <div class="sub-page-placeholder"></div>
        </div>

        <!-- 个人资料 -->
        <div v-if="currentPage === 'profile'" class="sub-page-content">
          <!-- 基本信息 -->
          <div class="form-group">
            <div class="form-group-title">基本信息</div>
            <el-form :model="profileForm" label-width="70px" class="sub-form">
              <el-form-item label="学号"><el-input :model-value="profileForm.username" disabled /></el-form-item>
              <el-form-item label="姓名"><el-input :model-value="profileForm.name" disabled /></el-form-item>
              <el-form-item label="学院"><el-input :model-value="profileForm.college" disabled /></el-form-item>
              <el-form-item label="班级"><el-input v-model="profileForm.className" placeholder="请输入班级" /></el-form-item>
            </el-form>
          </div>

          <!-- 个人信息 -->
          <div class="form-group">
            <div class="form-group-title">个人信息</div>
            <el-form :model="profileForm" label-width="70px" class="sub-form">
              <el-form-item label="性别">
                <el-select v-model="profileForm.gender" placeholder="请选择" style="width:100%">
                  <el-option label="男" value="男" /><el-option label="女" value="女" />
                </el-select>
              </el-form-item>
              <el-form-item label="年龄">
                <el-input-number v-model="profileForm.age" :min="1" :max="120" style="width:100%" />
              </el-form-item>
              <el-form-item label="籍贯"><el-input v-model="profileForm.hometown" placeholder="请输入籍贯" /></el-form-item>
              <el-form-item label="政治面貌">
                <el-select v-model="profileForm.political_status" placeholder="请选择" style="width:100%">
                  <el-option label="群众" value="群众" /><el-option label="共青团员" value="共青团员" />
                  <el-option label="中共预备党员" value="中共预备党员" /><el-option label="中共党员" value="中共党员" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <!-- 联系方式 -->
          <div class="form-group">
            <div class="form-group-title">联系方式</div>
            <el-form :model="profileForm" label-width="70px" class="sub-form">
              <el-form-item label="联系电话"><el-input v-model="profileForm.phone" placeholder="请输入手机号" /></el-form-item>
              <el-form-item label="辅导员">
                <el-select v-model="profileForm.tutor_id" placeholder="搜索选择辅导员" filterable style="width:100%">
                  <el-option v-for="t in teachers" :key="t.id" :label="`${t.name}（${t.username}）`" :value="t.id" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <div class="sub-page-footer">
            <el-button type="primary" @click="handleSaveProfile" :loading="saving" style="width:100%">保存</el-button>
          </div>
        </div>

        <!-- 修改密码 -->
        <div v-if="currentPage === 'password'" class="sub-page-content">
          <el-form :model="passwordForm" label-width="80px" class="sub-form">
            <el-form-item label="旧密码" required>
              <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入旧密码" />
            </el-form-item>
            <el-form-item label="新密码" required>
              <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="6-20位" />
            </el-form-item>
            <el-form-item label="确认密码" required>
              <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="再次输入" />
            </el-form-item>
            <el-form-item label="验证码" required>
              <div class="captcha-row">
                <el-input v-model="passwordForm.captcha" placeholder="请输入验证码" maxlength="4" />
                <div class="captcha-code" @click="refreshCaptcha">{{ captchaCode }}</div>
              </div>
            </el-form-item>
          </el-form>
          <div class="sub-page-footer">
            <el-button type="primary" @click="handleChangePassword" :loading="changingPassword" style="width:100%">确定</el-button>
          </div>
        </div>

        <!-- 意见反馈 -->
        <div v-if="currentPage === 'feedback'" class="sub-page-content">
          <!-- 提交表单 -->
          <div class="form-group">
            <div class="form-group-title">提交反馈</div>
            <el-form :model="feedbackForm" label-width="70px" class="sub-form">
              <el-form-item label="反馈类型">
                <el-select v-model="feedbackForm.type" style="width:100%">
                  <el-option label="问题反馈" value="bug" /><el-option label="功能建议" value="feature" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-form-item label="标题"><el-input v-model="feedbackForm.title" placeholder="请简要描述" maxlength="100" /></el-form-item>
              <el-form-item label="内容"><el-input v-model="feedbackForm.content" type="textarea" :rows="4" placeholder="请详细描述" /></el-form-item>
            </el-form>
            <div class="sub-page-footer">
              <el-button type="primary" @click="submitFeedback" :loading="submitting" style="width:100%">提交</el-button>
            </div>
          </div>

          <!-- 历史记录 -->
          <div class="form-group">
            <div class="form-group-title">历史反馈</div>
            <div v-loading="loadingFeedback" class="feedback-list">
              <div v-if="feedbackList.length === 0 && !loadingFeedback" class="empty-feedback">暂无反馈记录</div>
              <div v-for="item in feedbackList" :key="item.id" class="feedback-item">
                <div class="feedback-header">
                  <span class="feedback-type">{{ getTypeLabel(item.type) }}</span>
                  <el-tag :type="getStatusType(item.status)" size="small">{{ getStatusLabel(item.status) }}</el-tag>
                </div>
                <div class="feedback-title">{{ item.title }}</div>
                <div class="feedback-content">{{ item.content }}</div>
                <div v-if="item.reply" class="feedback-reply">
                  <div class="reply-label">官方回复：</div>
                  <div class="reply-content">{{ item.reply }}</div>
                </div>
                <div class="feedback-time">{{ item.created_at?.slice(0, 10) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 使用帮助 -->
        <div v-if="currentPage === 'help'" class="sub-page-content">
          <div class="help-content">
            <div class="help-item">
              <div class="help-question">如何联系绵小城？</div>
              <div class="help-answer">在首页直接输入你的问题，绵小城会即时回复。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看课表？</div>
              <div class="help-answer">输入"查课表"即可获取本周课程安排。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何请假？</div>
              <div class="help-answer">输入"我要请假"，按提示填写信息即可。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看成绩？</div>
              <div class="help-answer">输入"查成绩"即可查看各科成绩和GPA。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看通知？</div>
              <div class="help-answer">输入"查通知"即可获取教务处最新公告。</div>
            </div>
          </div>
        </div>

        <!-- 主题设置 -->
        <div v-if="currentPage === 'theme'" class="sub-page-content">
          <div class="theme-options">
            <div class="theme-option" :class="{ active: currentTheme === 'light' }" @click="setTheme('light')">
              <div class="theme-preview light-preview"></div>
              <span>浅色模式</span>
            </div>
          </div>
        </div>

        <!-- 关于绵小城 -->
        <div v-if="currentPage === 'about'" class="sub-page-content">
          <!-- 头部信息 -->
          <div class="about-header">
            <img src="/images/校徽_圆形.png" class="about-logo" />
            <div class="about-name">绵小城</div>
            <div class="about-version">v1.0.0</div>
            <div class="about-slogan">你的校园智能管家</div>
          </div>

          <!-- 功能简介 -->
          <div class="about-section">
            <div class="about-section-title">功能简介</div>
            <div class="about-text">
              绵小城是绵阳城市学院官方推出的智慧校园AI助手，基于大语言模型技术，为全校师生提供智能化的校园服务。通过自然语言对话，您可以轻松完成课表查询、成绩查询、请假申请、校园通知查看等日常事务，让校园生活更加便捷高效。
            </div>
          </div>

          <!-- 项目简介 -->
          <div class="about-section">
            <div class="about-section-title">项目简介</div>
            <div class="about-text">
              本项目采用前后端分离架构，前端使用 Vue 3 + TypeScript + Element Plus 构建，后端基于 FastAPI + Python 实现，集成大语言模型 API 提供智能对话能力。项目支持学生端和教师端，涵盖智能对话、办事服务、成长档案、校园风采等多个功能模块，致力于打造全方位的智慧校园生态。
            </div>
          </div>

          <!-- 核心功能 -->
          <div class="about-section">
            <div class="about-section-title">核心功能</div>
            <div class="about-features">
              <div class="feature-item">智能对话</div>
              <div class="feature-item">课表查询</div>
              <div class="feature-item">成绩查询</div>
              <div class="feature-item">请假申请</div>
              <div class="feature-item">成长记录</div>
              <div class="feature-item">校园通知</div>
              <div class="feature-item">学业分析</div>
              <div class="feature-item">办事服务</div>
            </div>
          </div>

          <!-- 开发团队 -->
          <div class="about-section">
            <div class="about-section-title">开发团队</div>
            <div class="about-team">
              <div class="team-info">
                <div class="team-name">阿里跳动</div>
                <div class="team-desc">由两位绵阳城市学院校内学生自主开发，致力于用技术创新提升校园数字化服务水平。</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 背景设置 -->
        <div v-if="currentPage === 'banner'" class="sub-page-content">
          <div class="banner-setting">
            <div class="banner-section-title">预设背景</div>
            <div class="preset-grid">
              <div
                v-for="preset in presetBanners"
                :key="preset.id"
                class="preset-item"
                :class="{ active: !bannerUrl && bannerGradient === preset.color }"
                :style="{ background: preset.color }"
                @click="selectPresetBanner(preset.color)"
              ></div>
            </div>
            
            <div class="banner-section-title" style="margin-top: 24px;">自定义图片</div>
            <div class="upload-area" @click="triggerBannerUpload">
              <el-icon :size="24"><Picture /></el-icon>
              <span>点击上传图片</span>
              <span class="upload-hint">支持 JPG、PNG，最大 5MB</span>
            </div>
            
            <div v-if="bannerUrl" class="current-banner">
              <div class="banner-section-title">当前背景</div>
              <img :src="bannerUrl" class="current-banner-preview" />
              <el-button size="small" @click="resetBanner" style="margin-top: 12px;">恢复默认</el-button>
            </div>
          </div>
          <input ref="bannerInputRef" type="file" accept="image/*" style="display:none" @change="handleBannerUpload" />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, getTeachers, changePassword } from '@/api/user'
import { createFeedback, getFeedbacks } from '@/api/feedback'
import { uploadFile } from '@/api/upload'
import {
  ArrowRight, ArrowLeft, Lock, SwitchButton, Sunny, InfoFilled,
  ChatDotRound, QuestionFilled, Camera, Picture
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

// 页面状态
const currentPage = ref<string | null>(null)
const slideDirection = ref('slide-left')

// 表单状态
const saving = ref(false)
const submitting = ref(false)
const changingPassword = ref(false)
const uploadingBanner = ref(false)
const teachers = ref<any[]>([])
const currentTheme = ref(localStorage.getItem('theme') || 'light')

// 背景图
const savedBanner = localStorage.getItem('profileBanner') || ''
const bannerUrl = ref(savedBanner ? savedBanner + (savedBanner.includes('?') ? '&' : '?') + '_t=' + Date.now() : '')
const bannerInputRef = ref<HTMLInputElement>()
const bannerGradient = computed(() => {
  return localStorage.getItem('profileBannerColor') || 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
})

// 预设背景图
const presetBanners = [
  { id: 'gradient1', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { id: 'gradient2', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { id: 'gradient3', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { id: 'gradient4', color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
  { id: 'gradient5', color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' },
  { id: 'gradient6', color: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)' },
]

// 成长统计
const growthStats = reactive({
  awards: 0,
  skills: 0,
  projects: 0,
})

const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '', captcha: '' })
const captchaCode = ref('')

function generateCaptcha() {
  const chars = '0123456789'
  let result = ''
  for (let i = 0; i < 4; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

function refreshCaptcha() {
  captchaCode.value = generateCaptcha()
}
const profileForm = reactive({
  username: '', name: '', college: '', gender: '', age: 18,
  hometown: '', phone: '', tutor_id: null as number | null,
  className: '', political_status: ''
})
const feedbackForm = reactive({ type: 'other', title: '', content: '' })
const feedbackList = ref<any[]>([])
const loadingFeedback = ref(false)

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    profile: '个人资料',
    password: '修改密码',
    feedback: '意见反馈',
    help: '使用帮助',
    theme: '主题设置',
    about: '关于绵小城',
    banner: '更换背景'
  }
  return titles[currentPage.value || ''] || ''
})

// 打开子页面
function openPage(page: string) {
  if (page === 'profile') {
    const u = auth.user
    if (u) {
      profileForm.username = u.username
      profileForm.name = u.name
      profileForm.college = u.college || ''
      profileForm.gender = u.gender || ''
      profileForm.age = u.age ?? 18
      profileForm.hometown = u.hometown || ''
      profileForm.phone = u.phone || ''
      profileForm.tutor_id = u.tutor_id ?? null
      profileForm.className = (u as any).class_name || ''
      profileForm.political_status = (u as any).political_status || ''
    }
  }
  slideDirection.value = 'slide-left'
  currentPage.value = page
}

// 关闭子页面
function closePage() {
  slideDirection.value = 'slide-right'
  currentPage.value = null
}

function selectPresetBanner(color: string) {
  bannerUrl.value = ''
  localStorage.setItem('profileBannerType', 'gradient')
  localStorage.setItem('profileBannerColor', color)
  localStorage.removeItem('profileBanner')
  ElMessage.success('背景已更新')
}

function triggerBannerUpload() {
  bannerInputRef.value?.click()
}

async function handleBannerUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  const file = input.files[0]
  
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请选择图片文件')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过5MB')
    return
  }
  
  uploadingBanner.value = true
  try {
    const { url } = await uploadFile(file)
    const cacheBusted = url + (url.includes('?') ? '&' : '?') + '_t=' + Date.now()
    bannerUrl.value = cacheBusted
    localStorage.setItem('profileBanner', url)
    localStorage.setItem('profileBannerType', 'image')
    localStorage.removeItem('profileBannerColor')
    ElMessage.success('背景已更新')
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploadingBanner.value = false
    input.value = ''
  }
}

function resetBanner() {
  bannerUrl.value = ''
  localStorage.removeItem('profileBanner')
  localStorage.removeItem('profileBannerType')
  localStorage.removeItem('profileBannerColor')
  ElMessage.success('已恢复默认背景')
}

function applyTheme(theme: string) {
  currentTheme.value = theme
  const root = document.documentElement
  
  if (theme === 'dark') {
    root.classList.add('dark')
    root.style.setProperty('--bg-color', '#1a1a1a')
    root.style.setProperty('--text-color', '#e5e5e5')
    root.style.setProperty('--card-bg', '#2a2a2a')
    root.style.setProperty('--border-color', '#3a3a3a')
  } else {
    root.classList.remove('dark')
    root.style.setProperty('--bg-color', '#f5f7fa')
    root.style.setProperty('--text-color', '#1a1a1a')
    root.style.setProperty('--card-bg', '#ffffff')
    root.style.setProperty('--border-color', '#f0f0f0')
  }
  
  localStorage.setItem('theme', theme)
}

function setTheme(theme: string) {
  applyTheme(theme)
  ElMessage.success('主题已切换')
}

function logout() { auth.logout(); router.push('/') }

async function handleChangePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    ElMessage.warning('请填写所有字段'); return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.error('两次输入的新密码不一致'); return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.error('新密码至少6位'); return
  }
  if (!passwordForm.captcha || passwordForm.captcha !== captchaCode.value) {
    ElMessage.error('验证码错误'); refreshCaptcha(); return
  }
  changingPassword.value = true
  try {
    await changePassword(passwordForm.old_password, passwordForm.new_password)
    ElMessage.success('密码修改成功')
    passwordForm.old_password = ''; passwordForm.new_password = ''; passwordForm.confirm_password = ''
    closePage()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '修改失败') }
  finally { changingPassword.value = false }
}

async function handleSaveProfile() {
  saving.value = true
  try {
    const updated = await updateProfile({
      gender: profileForm.gender || null, age: profileForm.age || null,
      hometown: profileForm.hometown || null, phone: profileForm.phone || null,
      tutor_id: profileForm.tutor_id || null,
      class_name: profileForm.className || null,
      political_status: profileForm.political_status || null,
    })
    auth.updateUser(updated as any)
    ElMessage.success('保存成功')
    closePage()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { saving.value = false }
}

async function submitFeedback() {
  if (!feedbackForm.title || !feedbackForm.content) {
    ElMessage.warning('请填写标题和内容'); return
  }
  submitting.value = true
  try {
    await createFeedback(feedbackForm)
    ElMessage.success('反馈已提交')
    feedbackForm.title = ''; feedbackForm.content = ''
    loadFeedbacks()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '提交失败') }
  finally { submitting.value = false }
}

async function loadFeedbacks() {
  loadingFeedback.value = true
  try {
    feedbackList.value = await getFeedbacks()
  } catch { feedbackList.value = [] }
  finally { loadingFeedback.value = false }
}

function getTypeLabel(type: string) {
  const labels: Record<string, string> = {
    bug: '问题反馈',
    feature: '功能建议',
    other: '其他'
  }
  return labels[type] || '其他'
}

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待处理',
    replied: '已回复',
    resolved: '已解决'
  }
  return labels[status] || status
}

function getStatusType(status: string) {
  const types: Record<string, string> = {
    pending: 'warning',
    replied: 'success',
    resolved: 'info'
  }
  return types[status] || 'info'
}

onMounted(async () => {
  try { teachers.value = await getTeachers() } catch {}
  refreshCaptcha()
  loadFeedbacks()
  applyTheme('light')
})
</script>

<style scoped>
.profile-wrapper {
  position: relative;
  height: 100%;
  overflow: hidden;
}

/* 滑动动画 */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(100%);
}
.slide-left-leave-to {
  transform: translateX(-30%);
}
.slide-right-enter-from {
  transform: translateX(-30%);
}
.slide-right-leave-to {
  transform: translateX(100%);
}

/* 主页面 */
.profile-page {
  height: 100%;
  overflow-y: auto;
  background: #f5f7fa;
  position: absolute;
  width: 100%;
}

/* 子页面 */
.sub-page {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
  z-index: 10;
}

.sub-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.back-btn {
  width: 36px;
  height: 36px;
  color: #333;
}

.sub-page-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.sub-page-placeholder {
  width: 36px;
}

.sub-page-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.sub-form {
  background: #fff;
  border-radius: 16px;
  padding: 16px 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* 表单分组 */
.form-group {
  margin-bottom: 16px;
}

.form-group-title {
  font-size: 13px;
  font-weight: 600;
  color: #999;
  margin-bottom: 10px;
  padding-left: 4px;
}

/* 验证码 */
.captcha-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.captcha-row .el-input {
  flex: 1;
}

.captcha-code {
  width: 100px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 8px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
}

/* 表单样式优化 */
.sub-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.sub-form :deep(.el-form-item__label) {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  line-height: 40px;
}

.sub-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e4e7ed inset;
  padding: 4px 12px;
  transition: all 0.2s;
}

.sub-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.sub-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.sub-form :deep(.el-select .el-input__wrapper) {
  border-radius: 10px;
}

.sub-form :deep(.el-textarea__inner) {
  border-radius: 10px;
  padding: 12px;
  resize: none;
}

.sub-form :deep(.el-input-number) {
  width: 100%;
}

.sub-form :deep(.el-input-number .el-input__wrapper) {
  border-radius: 10px;
}

.sub-page-footer {
  padding: 14px 0;
  margin-top: 8px;
}

.sub-page-footer .el-button {
  height: 40px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
}

/* 背景图 */
.profile-banner {
  position: relative;
  height: 120px;
  overflow: hidden;
  cursor: pointer;
}
.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.banner-default {
  width: 100%;
  height: 100%;
}
.banner-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(transparent, #f5f7fa);
}
.banner-edit-hint {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(0,0,0,0.5);
  color: #fff;
  border-radius: 16px;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 2;
}
.profile-banner:hover .banner-edit-hint {
  opacity: 1;
}

/* 头部信息 */
.profile-header {
  position: relative;
  margin: -28px 16px 14px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  cursor: pointer;
  z-index: 1;
}
.header-avatar {
  border: 3px solid #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  font-size: 20px;
}
.header-info { flex: 1; }
.header-name {
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
}
.header-id {
  font-size: 12px;
  color: #999;
  margin-top: 3px;
}
.header-arrow {
  color: #ccc;
  font-size: 16px;
}

/* 区域卡片 */
.section-card {
  margin: 12px 16px;
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}
.section-more {
  font-size: 12px;
  color: #999;
  cursor: pointer;
}

/* 成长统计 */
.growth-summary {
  display: flex;
  justify-content: space-around;
}
.growth-item { text-align: center; }
.growth-value {
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
}
.growth-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 菜单列表 */
.menu-list {
  display: flex;
  flex-direction: column;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  color: #333;
}
.menu-item:last-child { border-bottom: none; }
.menu-item:active { background: #f5f7fa; }
.menu-label {
  flex: 1;
  font-size: 14px;
}
.menu-arrow {
  color: #ccc;
  font-size: 14px;
}

/* 背景设置 */
.banner-setting {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}
.banner-section-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 12px;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.preset-item {
  height: 60px;
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}
.preset-item:hover { transform: scale(1.02); }
.preset-item.active {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64,158,255,0.3);
}
.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  border: 2px dashed #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  color: #999;
  transition: all 0.2s;
}
.upload-area:hover {
  border-color: #409eff;
  color: #409eff;
}
.upload-hint {
  font-size: 12px;
  color: #ccc;
}
.current-banner {
  margin-top: 16px;
}
.current-banner-preview {
  width: 100%;
  height: 88px;
  object-fit: cover;
  border-radius: 8px;
}

/* 主题设置 */
.theme-options {
  display: flex;
  gap: 16px;
  justify-content: center;
  background: #fff;
  border-radius: 16px;
  padding: 24px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 16px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  background: #f9fafb;
}
.theme-option:hover {
  background: #f5f7fa;
}
.theme-option.active {
  border-color: #409eff;
  background: rgba(64,158,255,0.05);
}
.theme-option span {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}
.theme-preview {
  width: 58px;
  height: 58px;
  border-radius: 14px;
  border: 2px solid #eee;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.light-preview { background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%); }


/* 关于 */
.about-header {
  text-align: center;
  background: #fff;
  border-radius: 16px;
  padding: 24px 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.about-logo {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  margin-bottom: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.about-name {
  font-size: 19px;
  font-weight: 700;
  color: #1a1a1a;
}
.about-version {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
.about-slogan {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}
.about-section {
  background: #fff;
  border-radius: 16px;
  padding: 16px 14px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.about-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid #409eff;
}
.about-text {
  font-size: 14px;
  color: #666;
  line-height: 1.8;
  text-align: justify;
}
.about-features {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.feature-item {
  padding: 8px 16px;
  background: linear-gradient(135deg, #f0f8ff 0%, #e8f4ff 100%);
  border-radius: 20px;
  font-size: 13px;
  color: #409eff;
  border: 1px solid rgba(64,158,255,0.15);
}
.about-team {
  display: flex;
  align-items: center;
  gap: 16px;
}
.team-info {
  flex: 1;
}
.team-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 6px;
}
.team-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}

/* 帮助 */
.help-content {
  background: #fff;
  border-radius: 16px;
  padding: 8px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.help-item {
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f5;
}
.help-item:last-child { border-bottom: none; }
.help-question {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.help-question::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
  flex-shrink: 0;
}
.help-answer {
  font-size: 14px;
  color: #666;
  line-height: 1.8;
  padding-left: 12px;
}

/* 背景设置 */
.banner-setting {
  background: #fff;
  border-radius: 16px;
  padding: 16px 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.banner-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.preset-item {
  height: 58px;
  border-radius: 12px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.preset-item:hover { 
  transform: scale(1.03);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.preset-item.active {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64,158,255,0.3);
}
.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 32px;
  border: 2px dashed #e4e7ed;
  border-radius: 12px;
  cursor: pointer;
  color: #999;
  transition: all 0.2s;
}
.upload-area:hover {
  border-color: #409eff;
  color: #409eff;
  background: rgba(64,158,255,0.02);
}
.upload-hint {
  font-size: 12px;
  color: #ccc;
}
.current-banner {
  margin-top: 16px;
}
.current-banner-preview {
  width: 100%;
  height: 88px;
  object-fit: cover;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* 反馈列表 */
.feedback-list {
  background: #fff;
  border-radius: 16px;
  padding: 8px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  min-height: 100px;
}

.empty-feedback {
  text-align: center;
  color: #999;
  padding: 32px 0;
  font-size: 14px;
}

.feedback-item {
  padding: 13px 0;
  border-bottom: 1px solid #f5f5f5;
}

.feedback-item:last-child {
  border-bottom: none;
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.feedback-type {
  font-size: 12px;
  color: #409eff;
  font-weight: 500;
}

.feedback-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
}

.feedback-content {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 8px;
}

.feedback-reply {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
}

.reply-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.reply-content {
  font-size: 13px;
  color: #333;
  line-height: 1.6;
}

.feedback-time {
  font-size: 12px;
  color: #ccc;
}
</style>
