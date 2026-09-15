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

        <!-- 客服与帮助 -->
        <div class="section-card">
          <div class="section-header">
            <div class="section-title">客服与帮助</div>
          </div>
          <div class="menu-list">
            <div class="menu-item" @click="openPage('announcements')">
              <el-icon :size="18"><Bell /></el-icon>
              <span class="menu-label">校园公告</span>
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
              <el-form-item label="工号"><el-input :model-value="profileForm.username" disabled /></el-form-item>
              <el-form-item label="姓名"><el-input :model-value="profileForm.name" disabled /></el-form-item>
              <el-form-item label="学院"><el-input :model-value="profileForm.college" disabled /></el-form-item>
              <el-form-item label="所带班级"><el-input v-model="profileForm.className" placeholder="请输入所带班级" /></el-form-item>
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
              <el-form-item label="职称"><el-input v-model="profileForm.title" placeholder="请输入职称" /></el-form-item>
              <el-form-item label="所属单位"><el-input v-model="profileForm.department" placeholder="请输入所属单位" /></el-form-item>
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

        <!-- 校园公告 -->
        <div v-if="currentPage === 'announcements'" class="sub-page-content">
          <div v-loading="loadingAnnouncements" class="announcement-list">
            <div v-if="announcements.length === 0 && !loadingAnnouncements" class="empty-announcement">暂无校园公告</div>
            <a v-for="(item, index) in announcements" :key="'a' + index" :href="item.url || '#'" target="_blank" class="announcement-item">
              <div class="announcement-title">{{ item.title }}</div>
              <div class="announcement-date">{{ item.date }}</div>
            </a>
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
              <div class="help-question">如何查看学生档案？</div>
              <div class="help-answer">输入"查学生档案"，即可查看所带班级学生的详细信息。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何审批请假？</div>
              <div class="help-answer">输入"审批请假"，即可查看和处理学生的请假申请。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看班级数据？</div>
              <div class="help-answer">输入"查班级数据"，即可获取班级考勤、成绩等统计数据。</div>
            </div>
            <div class="help-item">
              <div class="help-question">如何查看消息？</div>
              <div class="help-answer">输入"查消息"即可获取最新的系统通知和公告。</div>
            </div>
          </div>
        </div>

        <!-- 主题设置（仅浅色模式提示） -->
        <div v-if="currentPage === 'theme'" class="sub-page-content">
          <div class="theme-options">
            <div class="theme-option active">
              <div class="theme-preview light-preview"></div>
              <span>浅色模式</span>
            </div>
          </div>
          <div class="theme-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>当前系统仅支持浅色模式</span>
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
              绵小城是绵阳城市学院官方推出的智慧校园AI助手，基于大语言模型技术，为全校师生提供智能化的校园服务。通过自然语言对话，您可以轻松完成课表查询、成绩查询、请假审批、校园通知查看等日常事务，让校园管理更加便捷高效。
            </div>
          </div>

          <!-- 项目简介 -->
          <div class="about-section">
            <div class="about-section-title">项目简介</div>
            <div class="about-text">
              本项目采用前后端分离架构，前端使用 Vue 3 + TypeScript + Element Plus 构建，后端基于 FastAPI + Python 实现，集成大语言模型 API 提供智能对话能力。项目支持学生端和教师端，涵盖智能对话、办事服务、学生成长档案、校园风采等多个功能模块，致力于打造全方位的智慧校园生态。
            </div>
          </div>

          <!-- 核心功能 -->
          <div class="about-section">
            <div class="about-section-title">核心功能</div>
            <div class="about-features">
              <div class="feature-item">智能对话</div>
              <div class="feature-item">课表查询</div>
              <div class="feature-item">成绩查询</div>
              <div class="feature-item">请假审批</div>
              <div class="feature-item">学生档案</div>
              <div class="feature-item">校园通知</div>
              <div class="feature-item">班级管理</div>
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
            
            <div class="banner-section-title" style="margin-top: 16px;">自定义图片</div>
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
import { updateProfile, changePassword } from '@/api/user'
import { uploadFile } from '@/api/upload'
import { getAnnouncements } from '@/api/campus'
import type { Announcement } from '@/types'
import {
  ArrowRight, ArrowLeft, Lock, SwitchButton, Sunny, InfoFilled,
  QuestionFilled, Bell, Camera, Picture
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

// 页面状态
const currentPage = ref<string | null>(null)
const slideDirection = ref('slide-left')

// 表单状态
const saving = ref(false)
const changingPassword = ref(false)
const uploadingBanner = ref(false)

// 背景图
const savedBanner = localStorage.getItem('profileBanner') || ''
const bannerUrl = ref(savedBanner ? savedBanner + (savedBanner.includes('?') ? '&' : '?') + '_t=' + Date.now() : '')
const bannerInputRef = ref<HTMLInputElement>()
const DEFAULT_GRADIENT = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
const bannerGradient = ref(localStorage.getItem('profileBannerColor') || DEFAULT_GRADIENT)

// 预设背景图
const presetBanners = [
  { id: 'gradient1', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { id: 'gradient2', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { id: 'gradient3', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { id: 'gradient4', color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' },
  { id: 'gradient5', color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' },
  { id: 'gradient6', color: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)' },
]

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
  hometown: '', phone: '', className: '', political_status: '',
  title: '', department: ''
})

// 校园公告
const announcements = ref<Announcement[]>([])
const loadingAnnouncements = ref(false)

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    profile: '个人资料',
    password: '修改密码',
    announcements: '校园公告',
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
      profileForm.className = (u as any).class_name || ''
      profileForm.political_status = (u as any).political_status || ''
      profileForm.title = (u as any).title || ''
      profileForm.department = (u as any).department || ''
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
  bannerGradient.value = color
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
  bannerGradient.value = DEFAULT_GRADIENT
  localStorage.removeItem('profileBanner')
  localStorage.removeItem('profileBannerType')
  localStorage.removeItem('profileBannerColor')
  ElMessage.success('已恢复默认背景')
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
      class_name: profileForm.className || null,
      political_status: profileForm.political_status || null,
      title: profileForm.title || null,
      department: profileForm.department || null,
    })
    auth.updateUser(updated as any)
    ElMessage.success('保存成功')
    closePage()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
  finally { saving.value = false }
}

async function loadAnnouncements() {
  loadingAnnouncements.value = true
  try {
    announcements.value = await getAnnouncements()
  } catch {
    announcements.value = []
  } finally {
    loadingAnnouncements.value = false
  }
}

onMounted(() => {
  refreshCaptcha()
  loadAnnouncements()
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
  padding: 10px 12px;
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
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.sub-page-placeholder {
  width: 36px;
}

.sub-page-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.sub-form {
  background: #fff;
  border-radius: 12px;
  padding: 12px 10px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* 表单分组 */
.form-group {
  margin-bottom: 12px;
}

.form-group-title {
  font-size: 12px;
  font-weight: 600;
  color: #999;
  margin-bottom: 8px;
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
  width: 96px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 8px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
}

/* 表单样式优化 */
.sub-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.sub-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: #333;
  font-weight: 500;
  line-height: 36px;
}

.sub-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #e4e7ed inset;
  padding: 2px 10px;
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
  border-radius: 8px;
  padding: 8px;
  resize: none;
}

.sub-form :deep(.el-input-number) {
  width: 100%;
}

.sub-form :deep(.el-input-number .el-input__wrapper) {
  border-radius: 10px;
}

.sub-page-footer {
  padding: 10px 0 4px;
  margin-top: 4px;
}

.sub-page-footer .el-button {
  height: 38px;
  border-radius: 10px;
  font-size: 13px;
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
  padding: 14px 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.banner-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.preset-item {
  height: 50px;
  border-radius: 10px;
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
  gap: 8px;
  padding: 20px;
  border: 2px dashed #e4e7ed;
  border-radius: 10px;
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
  margin-top: 12px;
}
.current-banner-preview {
  width: 100%;
  height: 88px;
  object-fit: cover;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

/* 主题设置 */
.theme-options {
  display: flex;
  gap: 16px;
  justify-content: center;
  background: #fff;
  border-radius: 12px;
  padding: 14px 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.2s;
  background: #f9fafb;
}
.theme-option.active {
  border-color: #409eff;
  background: rgba(64,158,255,0.05);
}
.theme-option span {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}
.theme-preview {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  border: 2px solid #eee;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.light-preview { background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%); }

.theme-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: #f0f8ff;
  border-radius: 10px;
  color: #409eff;
  font-size: 12px;
}

/* 关于 */
.about-header {
  text-align: center;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.about-logo {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  margin-bottom: 6px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.about-name {
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
}
.about-version {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.about-slogan {
  font-size: 13px;
  color: #666;
  margin-top: 6px;
}
.about-section {
  background: #fff;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.about-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}
.about-text {
  font-size: 13px;
  color: #666;
  line-height: 1.7;
  text-align: justify;
}
.about-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.feature-item {
  padding: 6px 12px;
  background: linear-gradient(135deg, #f0f8ff 0%, #e8f4ff 100%);
  border-radius: 16px;
  font-size: 12px;
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
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}
.team-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.6;
}

/* 帮助 */
.help-content {
  background: #fff;
  border-radius: 12px;
  padding: 4px 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.help-item {
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.help-item:last-child { border-bottom: none; }
.help-question {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.help-question::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 14px;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  border-radius: 2px;
  flex-shrink: 0;
}
.help-answer {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  padding-left: 12px;
}

/* 公告列表 */
.announcement-list {
  background: #fff;
  border-radius: 12px;
  padding: 4px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  min-height: 100px;
}

.empty-announcement {
  text-align: center;
  color: #999;
  padding: 24px 0;
  font-size: 13px;
}

.announcement-item {
  display: block;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  text-decoration: none;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  line-height: 1.5;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.announcement-date {
  font-size: 11px;
  color: #ccc;
}
</style>
