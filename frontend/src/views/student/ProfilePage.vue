<template>
  <div class="profile-wrapper">
    <!-- 主页面 -->
    <transition :name="slideDirection">
      <div v-if="!currentPage" key="main" class="profile-page">
        <!-- 个人中心头部（抖音范式）：封面铺满整行，身份信息以暗色渐变压底后「悬浮」在背景之上 -->
        <section class="pf-hero" :style="heroBannerStyle">
          <div class="pf-hero-scrim"></div>

          <button type="button" class="pf-hero-edit" @click="openPage('banner')">
            <el-icon :size="13"><Camera /></el-icon>
            更换背景
          </button>

          <div class="pf-hero-cast" @click="openPage('profile')">
            <el-avatar :size="64" :src="auth.user?.avatar || ''" class="pf-avatar">
              {{ auth.userName?.[0] }}
            </el-avatar>
            <div class="pf-cast-main">
              <div class="pf-cast-name-row">
                <h2 class="pf-cast-name">{{ auth.userName }}</h2>
                <span class="pf-cast-role">学生</span>
              </div>
              <p class="pf-cast-sub">
                学号：{{ auth.user?.username || '—' }}
                <span class="pf-cast-sep">·</span>{{ auth.user?.college || '未设置学院' }}
              </p>
            </div>
            <span class="pf-cast-btn">
              编辑资料
              <el-icon :size="12"><ArrowRight /></el-icon>
            </span>
          </div>

          <div class="pf-hero-stats">
            <div class="pf-hero-stat">
              <b>{{ growthStats.awards || 0 }}</b>
              <span>成长记录</span>
            </div>
            <i class="pf-hero-stat-sep"></i>
            <div class="pf-hero-stat">
              <b>{{ imageComplete }}%</b>
              <span>画像完整度</span>
            </div>
          </div>
        </section>

        <!-- 内容面板：圆角上浮压住封面底边，形成「悬浮于背景之上」的层次 -->
        <div class="pf-body">
          <!-- 个人成长 -->
          <section class="pf-section">
            <div class="pf-section-head">
              <h3 class="pf-section-title">个人成长</h3>
              <button type="button" class="pf-section-more" @click="router.push('/student/growth')">
                查看详情
                <el-icon :size="12"><ArrowRight /></el-icon>
              </button>
            </div>
            <div class="pf-section-body">
              <div class="growth-summary">
                <div class="growth-item">
                  <div class="growth-value">{{ growthStats.awards || 0 }}</div>
                  <div class="growth-label">成长记录</div>
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

              <!-- 成长画像：完整度 + 技能/兴趣 + 目标入口 -->
              <div class="growth-profile-block">
                <div class="profile-line">
                  <div class="profile-line-label">
                    <el-icon :size="14"><Calendar /></el-icon>
                    <span>成长画像完整度</span>
                  </div>
                  <span class="profile-line-value">{{ imageComplete }}%</span>
                </div>
                <el-progress
                  :percentage="imageComplete"
                  :stroke-width="8"
                  :show-text="false"
                  :color="imageComplete === 100 ? 'var(--tui-success)' : 'var(--tui-brand)'"
                  class="profile-progress"
                />
                <div class="profile-tip" v-if="imageComplete < 100">
                  完善技能、兴趣与目标后，AI 将为你提供更精准的成长建议
                </div>
                <div class="profile-tip" v-else>
                  画像已完整，AI 服务已全面开启
                </div>

                <div v-if="(growthProfile?.skills?.length || 0) > 0 || (growthProfile?.interests?.length || 0) > 0" class="profile-tags">
                  <span v-for="s in (growthProfile?.skills || [])" :key="'s' + s" class="profile-tag is-skill">{{ s }}</span>
                  <span v-for="i in (growthProfile?.interests || [])" :key="'i' + i" class="profile-tag">{{ i }}</span>
                </div>

                <div class="profile-goal-row">
                  <div class="profile-goal-text">
                    <el-icon :size="14"><FolderOpened /></el-icon>
                    <span>发展目标 {{ goalCount }} 个</span>
                  </div>
                  <button type="button" class="profile-goal-btn" @click="router.push('/student/plan')">去制定计划</button>
                </div>
              </div>
            </div>
          </section>

          <!-- 客服与帮助：分组内嵌列表（抖音设置页 / Vant CellGroup 范式） -->
          <section class="pf-section">
            <h3 class="pf-section-title">客服与帮助</h3>
            <div class="pf-list">
              <button type="button" class="pf-row" @click="openPage('feedback')">
                <span class="pf-row-icon is-violet"><el-icon :size="17"><ChatDotRound /></el-icon></span>
                <span class="pf-row-label">意见反馈</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="pf-row" @click="openPage('help')">
                <span class="pf-row-icon is-cyan"><el-icon :size="17"><QuestionFilled /></el-icon></span>
                <span class="pf-row-label">使用帮助</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </section>

          <!-- 设置与隐私 -->
          <section class="pf-section">
            <h3 class="pf-section-title">设置与隐私</h3>
            <div class="pf-list">
              <button type="button" class="pf-row" @click="openPage('password')">
                <span class="pf-row-icon is-violet"><el-icon :size="17"><Lock /></el-icon></span>
                <span class="pf-row-label">修改密码</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="pf-row" @click="openPage('theme')">
                <span class="pf-row-icon is-warn"><el-icon :size="17"><Sunny /></el-icon></span>
                <span class="pf-row-label">主题设置</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="pf-row" @click="openPage('about')">
                <span class="pf-row-icon"><el-icon :size="17"><InfoFilled /></el-icon></span>
                <span class="pf-row-label">关于{{ agentName }}</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
              <button type="button" class="pf-row" @click="logout">
                <span class="pf-row-icon is-danger"><el-icon :size="17"><SwitchButton /></el-icon></span>
                <span class="pf-row-label">退出登录</span>
                <el-icon class="pf-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </section>
        </div>
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

        <!-- 账号与安全（抖音设置页范式）：只读展示 + 点按行弹窗编辑，不再铺一屏输入框 -->
        <div v-if="currentPage === 'profile'" class="sub-page-content set-page">
          <!-- 头像：抖音「编辑资料」里的一行，右侧直接显示当前头像 -->
          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="triggerAvatarInput">
                <span class="set-row-label">头像</span>
                <span class="set-row-value">
                  <el-avatar :size="28" :src="profileForm.avatar" shape="square" class="set-row-avatar">
                    {{ profileForm.name?.[0] || '?' }}
                  </el-avatar>
                </span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
            <input ref="avatarInputRef" type="file" accept="image/*" style="display:none" @change="onAvatarSelect" />
          </div>

          <div v-for="g in accGroups" :key="g.title" class="set-group">
            <div class="set-group-title">{{ g.title }}</div>
            <div class="set-list">
              <button
                v-for="f in g.fields"
                :key="f.key"
                type="button"
                class="set-row"
                :class="{ 'is-readonly': f.readonly }"
                @click="openFieldEdit(f)"
              >
                <span class="set-row-label">{{ f.label }}</span>
                <span class="set-row-value" :class="{ 'is-empty': !fieldValue(f) }">
                  {{ fieldValue(f) || (f.readonly ? '—' : '未设置') }}
                </span>
                <el-icon v-if="!f.readonly" class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
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
                  <el-option label="投诉" value="complaint" /><el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
              <el-form-item label="标题"><el-input v-model="feedbackForm.title" placeholder="请简要描述" maxlength="100" /></el-form-item>
              <el-form-item label="内容"><el-input v-model="feedbackForm.content" type="textarea" :rows="4" placeholder="请详细描述" /></el-form-item>
              <el-form-item label="联系方式"><el-input v-model="feedbackForm.contact" placeholder="手机号/邮箱，方便我们联系您" /></el-form-item>
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
              <div class="help-question">如何联系{{ agentName }}？</div>
              <div class="help-answer">在首页直接输入你的问题，{{ agentName }}会即时回复。</div>
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
            <img :src="siteLogo" class="about-logo" />
            <div class="about-name">{{ siteName }}</div>
            <div class="about-version">v1.0.0</div>
            <div class="about-slogan">你的校园智能管家</div>
          </div>

          <!-- 功能简介 -->
          <div class="about-section">
            <div class="about-section-title">功能简介</div>
            <div class="about-text">
              {{ agentName }}是绵阳城市学院官方推出的智慧校园AI助手，基于大语言模型技术，为全校师生提供智能化的校园服务。通过自然语言对话，您可以轻松完成课表查询、成绩查询、请假申请、校园通知查看等日常事务，让校园生活更加便捷高效。
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

        <!-- 更换背景（抖音背景选择器范式）：顶部实时预览 + 背景宫格，点选即时生效 -->
        <div v-if="currentPage === 'banner'" class="sub-page-content set-page">
          <div class="set-group">
            <div class="set-group-title">当前背景</div>
            <div class="bg-preview" :style="heroBannerStyle">
              <div class="bg-preview-scrim"></div>
              <div class="bg-preview-cast">
                <el-avatar :size="40" :src="auth.user?.avatar || ''" class="bg-preview-avatar">
                  {{ auth.userName?.[0] }}
                </el-avatar>
                <div>
                  <div class="bg-preview-name">{{ auth.userName }}</div>
                  <div class="bg-preview-sub">学号：{{ auth.user?.username || '—' }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="set-group">
            <div class="set-group-title">选择背景</div>
            <div class="bg-grid">
              <button
                v-for="preset in presetBanners"
                :key="preset.id"
                type="button"
                class="bg-cell"
                :class="{ 'is-active': !bannerUrl && bannerGradient === preset.color }"
                :style="{ background: preset.color }"
                @click="selectPresetBanner(preset.color)"
              >
                <span v-if="!bannerUrl && bannerGradient === preset.color" class="bg-cell-check">
                  <el-icon :size="11"><Check /></el-icon>
                </span>
              </button>
              <button type="button" class="bg-cell bg-cell-upload" @click="triggerBannerUpload">
                <el-icon :size="18"><Plus /></el-icon>
                <span>从相册选择</span>
              </button>
            </div>
            <p class="bg-hint">自定义背景支持 JPG / PNG，最大 5MB</p>
          </div>

          <div class="set-group">
            <div class="set-list">
              <button type="button" class="set-row" @click="resetBanner">
                <span class="set-row-label">恢复默认背景</span>
                <span class="set-row-value">使用系统预设渐变</span>
                <el-icon class="set-row-arrow" :size="14"><ArrowRight /></el-icon>
              </button>
            </div>
          </div>

          <input ref="bannerInputRef" type="file" accept="image/*" style="display:none" @change="handleBannerUpload" />
        </div>
      </div>
    </transition>

    <!-- 账号与安全：字段编辑弹窗（抖音「点按设置项 → 就地编辑」范式） -->
    <el-dialog
      v-model="editVisible"
      :title="editField ? `修改${editField.label}` : ''"
      width="86%"
      align-center
    >
      <el-input
        v-if="editField && editField.type === 'text'"
        v-model="editValue"
        :placeholder="editField.placeholder || '请输入'"
        clearable
      />
      <el-input-number
        v-else-if="editField && editField.type === 'number'"
        v-model="editValue"
        :min="1"
        :max="120"
        style="width:100%"
      />
      <el-select v-else v-model="editValue" placeholder="请选择" filterable style="width:100%">
        <el-option v-for="o in editField?.options || []" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmFieldEdit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 头像裁剪 -->
    <el-dialog v-model="avatarCropVisible" title="裁剪头像" width="420px" :close-on-click-modal="false" @opened="onAvatarCropOpened">
      <div class="crop-container">
        <img ref="avatarCropImgRef" style="max-width:100%;display:block" />
      </div>
      <template #footer>
        <el-button @click="cancelAvatarCrop">取消</el-button>
        <el-button type="primary" @click="handleAvatarCropConfirm">确认裁剪</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import { useAuthStore } from '@/stores/auth'
import { updateProfile, getTeachers, changePassword } from '@/api/user'
import { createFeedback, getFeedbacks } from '@/api/feedback'
import { uploadFile } from '@/api/upload'
import { getGrowthProfile, getProjects, type GrowthProfile } from '@/api/growth'
import { getGoals } from '@/api/plan'
import { useSiteConfig } from '@/composables/useSiteConfig'
import {
  ArrowRight, ArrowLeft, Lock, SwitchButton, Sunny, InfoFilled,
  ChatDotRound, QuestionFilled, Camera, Calendar, FolderOpened, Check, Plus
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// 关于页品牌信息与站点配置同源
const { siteName, siteLogo, agentName } = useSiteConfig()

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

// 成长统计
const growthStats = reactive({
  awards: 0,
  skills: 0,
  projects: 0,
})

// 成长画像（供 AI 驾驶舱与推荐使用）
const growthProfile = ref<GrowthProfile | null>(null)
const goalCount = ref(0)
const imageComplete = computed(() => {
  let score = 0
  if ((growthProfile.value?.skills?.length || 0) > 0) score += 30
  if ((growthProfile.value?.interests?.length || 0) > 0) score += 20
  if (goalCount.value > 0) score += 25
  if (growthStats.projects > 0 || (growthProfile.value?.total_records || 0) > 0) score += 25
  return score
})

async function loadGrowth() {
  try {
    const [p, pros, goals] = await Promise.all([getGrowthProfile(), getProjects(), getGoals()])
    growthProfile.value = p
    growthStats.awards = p?.total_records || 0
    growthStats.skills = p?.total_skills || 0
    growthStats.projects = pros?.length || 0
    goalCount.value = goals?.length || 0
  } catch { /* ignore */ }
}

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
  className: '', political_status: '', avatar: ''
})

/** 身份背景（移动端 .pf-hero / .bg-preview 共用）：优先用已上传图片，否则用预设渐变 */
const heroBannerStyle = computed(() =>
  bannerUrl.value ? { backgroundImage: `url(${bannerUrl.value})` } : { background: bannerGradient.value }
)

/**
 * 账号与安全：字段描述表（抖音设置项范式）。
 * 页面只读展示「左侧标签 + 右侧值 + 箭头」，点按行弹出编辑弹窗；
 * 用 computed 而非常量，是为了让「辅导员」的可选项跟随 teachers 异步加载。
 */
interface AccField {
  key: string
  label: string
  type: 'text' | 'select' | 'number'
  options?: { label: string; value: string | number }[]
  placeholder?: string
  readonly?: boolean
}

const accGroups = computed<{ title: string; fields: AccField[] }[]>(() => [
  {
    title: '账号信息',
    fields: [
      { key: 'username', label: '学号', type: 'text', readonly: true },
      { key: 'name', label: '姓名', type: 'text', readonly: true },
      { key: 'college', label: '学院', type: 'text', readonly: true },
      { key: 'className', label: '班级', type: 'text', placeholder: '请输入班级' },
    ],
  },
  {
    title: '个人资料',
    fields: [
      {
        key: 'gender', label: '性别', type: 'select',
        options: [{ label: '男', value: '男' }, { label: '女', value: '女' }],
      },
      { key: 'age', label: '年龄', type: 'number' },
      { key: 'hometown', label: '籍贯', type: 'text', placeholder: '请输入籍贯' },
      {
        key: 'political_status', label: '政治面貌', type: 'select',
        options: [
          { label: '群众', value: '群众' },
          { label: '共青团员', value: '共青团员' },
          { label: '中共预备党员', value: '中共预备党员' },
          { label: '中共党员', value: '中共党员' },
        ],
      },
    ],
  },
  {
    title: '联系方式',
    fields: [
      { key: 'phone', label: '联系电话', type: 'text', placeholder: '请输入手机号' },
      {
        key: 'tutor_id', label: '辅导员', type: 'select',
        options: teachers.value.map((t: any) => ({ label: `${t.name}（${t.username}）`, value: t.id })),
      },
    ],
  },
])

const editVisible = ref(false)
const editField = ref<AccField | null>(null)
const editValue = ref<any>('')

/** 行右侧展示的文本：下拉项显示选项文案，空值由模板回退为占位文案 */
function fieldValue(f: AccField): string {
  const v = (profileForm as any)[f.key]
  if (v === null || v === undefined || v === '') return ''
  if (f.type === 'select') return f.options?.find((o) => o.value === v)?.label || String(v)
  return String(v)
}

function openFieldEdit(f: AccField) {
  if (f.readonly) return
  editField.value = f
  editValue.value = (profileForm as any)[f.key] ?? ''
  editVisible.value = true
}

function confirmFieldEdit() {
  const f = editField.value
  if (!f) return
  ;(profileForm as any)[f.key] = f.type === 'number' ? Number(editValue.value) || 1 : editValue.value
  editVisible.value = false
}

const feedbackForm = reactive({ type: 'other', title: '', content: '', contact: '' })
const feedbackList = ref<any[]>([])
const loadingFeedback = ref(false)

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    profile: '账号与安全',
    password: '修改密码',
    feedback: '意见反馈',
    help: '使用帮助',
    theme: '主题设置',
    about: `关于${agentName.value}`,
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
      profileForm.avatar = (u as any).avatar || ''
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

// 头像裁剪
const avatarCropVisible = ref(false)
const avatarInputRef = ref<HTMLInputElement>()
const avatarCropImgRef = ref<HTMLImageElement>()
let avatarCropper: Cropper | null = null
let pendingAvatarSrc = ''

function triggerAvatarInput() {
  avatarInputRef.value?.click()
}

function onAvatarSelect(e: Event) {
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
  const reader = new FileReader()
  reader.onload = () => {
    pendingAvatarSrc = reader.result as string
    avatarCropVisible.value = true
  }
  reader.readAsDataURL(file)
  input.value = ''
}

function onAvatarCropOpened() {
  avatarCropper?.destroy()
  const img = avatarCropImgRef.value
  if (!img) return
  img.src = pendingAvatarSrc
  avatarCropper = new Cropper(img, {
    aspectRatio: 1,
    viewMode: 1,
    autoCropArea: 1,
    background: false,
  })
}

function cancelAvatarCrop() {
  avatarCropVisible.value = false
  avatarCropper?.destroy()
  avatarCropper = null
  pendingAvatarSrc = ''
}

async function handleAvatarCropConfirm() {
  const cropper = avatarCropper
  if (!cropper) return
  const canvas = cropper.getCroppedCanvas({ width: 200, height: 200 })
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
  if (!blob) { ElMessage.error('裁剪失败'); return }
  try {
    const { url } = await uploadFile(new File([blob], 'avatar.png', { type: 'image/png' }))
    profileForm.avatar = url
    ElMessage.success('头像已更新，点击保存后生效')
  } catch {
    ElMessage.error('上传失败')
  }
  cancelAvatarCrop()
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
      avatar: profileForm.avatar || null,
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
    await createFeedback({
      type: feedbackForm.type,
      title: feedbackForm.title,
      content: feedbackForm.content,
      contact: feedbackForm.contact || undefined,
    })
    ElMessage.success('反馈已提交')
    feedbackForm.title = ''; feedbackForm.content = ''; feedbackForm.contact = ''
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
  loadGrowth()
  applyTheme('light')
  // 支持外部跳转直达子页（如工作台"意见反馈"入口）
  const page = route.query.page as string | undefined
  if (page && ['profile', 'password', 'feedback', 'help', 'theme', 'about', 'banner'].includes(page)) {
    openPage(page)
  }
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

/* 主页面：封面通栏铺满，页内边距交由内容面板（.pf-body）承担 */
.profile-page {
  position: absolute;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background: var(--tui-bg);
  padding: 0;
}

/* 子页面 */
.sub-page {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--tui-bg);
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

/* 头像裁剪容器 */
.crop-container {
  max-height: 320px;
  overflow: hidden;
  display: flex;
  justify-content: center;
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

/* ===== 个人中心头部（抖音范式）：封面通栏 + 身份悬浮于背景之上 ===== */
.pf-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: 212px;
  padding: 14px 16px 30px;
  background-color: #d8dee6;
  background-size: cover;
  background-position: center;
  overflow: hidden;
}
/* 自下而上的暗色压底：白字在任意背景图/渐变上都可读，同时把封面「压」成背景层 */
.pf-hero-scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(10, 12, 16, 0.06) 0%,
    rgba(10, 12, 16, 0.16) 44%,
    rgba(10, 12, 16, 0.68) 100%
  );
}
.pf-hero-edit {
  position: absolute;
  right: 14px;
  top: 14px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 999px;
  background: rgba(10, 12, 16, 0.32);
  color: #fff;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  backdrop-filter: blur(6px);
}
.pf-hero-edit:active { background: rgba(10, 12, 16, 0.48); }

.pf-hero-cast {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}
.pf-avatar {
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.24);
}
.pf-cast-main { flex: 1; min-width: 0; }
.pf-cast-name-row { display: flex; align-items: center; gap: 7px; }
.pf-cast-name {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.32);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-cast-role {
  flex-shrink: 0;
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.pf-cast-sub {
  margin: 5px 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.84);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-cast-sep { margin: 0 6px; color: rgba(255, 255, 255, 0.5); }
.pf-cast-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  backdrop-filter: blur(8px);
}

.pf-hero-stats {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 18px;
  margin-top: 16px;
  padding-left: 2px;
}
.pf-hero-stat { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pf-hero-stat b {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.1;
  color: #fff;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.3);
  max-width: 132px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-hero-stat span { font-size: 11px; color: rgba(255, 255, 255, 0.72); }
.pf-hero-stat-sep { width: 1px; height: 24px; background: rgba(255, 255, 255, 0.24); }

/* ===== 内容面板：圆角上浮，压住封面底边，形成「悬浮于背景之上」的层次 ===== */
.pf-body {
  position: relative;
  z-index: 2;
  margin-top: -16px;
  padding: 14px 12px 16px;
  border-radius: 20px 20px 0 0;
  background: var(--tui-bg);
}
.pf-body .pf-section:first-child { margin-top: 0; }

/* ===== 分区卡片 + 内嵌列表行 ===== */
.pf-section {
  margin-top: 12px;
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}
.pf-section-title {
  margin: 0;
  padding: 12px 14px 0;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--tui-text-quiet);
}
.pf-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px 0;
}
.pf-section-head .pf-section-title { padding: 0; }
.pf-section-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  cursor: pointer;
}
.pf-section-more:active { color: var(--tui-text-secondary); }
.pf-section-body { padding: 10px 14px 14px; }

.pf-list { display: flex; flex-direction: column; }
.pf-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: none;
  border-bottom: 1px solid var(--tui-border);
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.pf-row:last-child { border-bottom: none; }
.pf-row:active { background: var(--tui-surface-muted); }
.pf-row-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: var(--tui-radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--tui-brand-soft);
  color: var(--tui-brand);
  box-shadow: inset 0 0 0 1px rgba(15, 17, 21, 0.03);
}
.pf-row-icon.is-cyan { background: #ecfeff; color: #0891b2; }
.pf-row-icon.is-violet { background: #f4f3ff; color: #6941c6; }
.pf-row-icon.is-warn { background: var(--tui-warn-soft); color: #f79009; }
.pf-row-icon.is-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }
.pf-row-label {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--tui-text);
}
.pf-row-arrow { color: #cbd0d8; flex-shrink: 0; }

/* ===== 个人成长 ===== */
.growth-summary {
  display: flex;
  justify-content: space-around;
}
.growth-item { text-align: center; }
.growth-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.growth-label {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin-top: 3px;
}
.growth-profile-block {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--tui-border);
}
.profile-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.profile-line-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
}
.profile-line-value {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-brand);
  font-variant-numeric: tabular-nums;
}
.profile-progress { margin-bottom: 8px; }
.profile-tip {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin-bottom: 10px;
}
.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.profile-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid var(--tui-border);
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
  font-size: 11.5px;
  font-weight: 500;
}
.profile-tag.is-skill {
  border-color: transparent;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
}
.profile-goal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.profile-goal-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
}
.profile-goal-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 999px;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
}
.profile-goal-btn:active { background: #e0ecff; }

/* ===== 设置项列表（抖音设置页范式）：左标签 + 右值 + 箭头 ===== */
.set-page .set-group { margin-bottom: 12px; }
.set-page .set-group-title {
  margin: 0 0 8px 2px;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--tui-text-quiet);
}
.set-page .set-list {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}
.set-page .set-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px 14px;
  border: none;
  border-bottom: 1px solid var(--tui-border);
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.set-page .set-row:last-child { border-bottom: none; }
.set-page .set-row:active { background: var(--tui-surface-muted); }
.set-page .set-row.is-readonly { cursor: default; }
.set-page .set-row.is-readonly:active { background: transparent; }
.set-page .set-row-label {
  flex-shrink: 0;
  font-size: 13.5px;
  color: var(--tui-text);
}
.set-page .set-row-value {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 13px;
  color: var(--tui-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.set-page .set-row-value.is-empty { color: var(--tui-text-quiet); }
.set-page .set-row-arrow { color: #cbd0d8; flex-shrink: 0; }
.set-page .set-row-avatar {
  flex-shrink: 0;
  border-radius: 8px;
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
  font-size: 12px;
}

/* ===== 更换背景（抖音背景选择器范式）：实时预览 + 背景宫格 ===== */
.set-page .bg-preview {
  position: relative;
  display: flex;
  align-items: flex-end;
  height: 152px;
  padding: 14px;
  border-radius: var(--tui-radius);
  background-color: #d8dee6;
  background-size: cover;
  background-position: center;
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}
.set-page .bg-preview-scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(10, 12, 16, 0.04) 0%,
    rgba(10, 12, 16, 0.18) 45%,
    rgba(10, 12, 16, 0.64) 100%
  );
}
.set-page .bg-preview-cast {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.set-page .bg-preview-avatar {
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}
.set-page .bg-preview-name {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.3);
}
.set-page .bg-preview-sub {
  margin-top: 2px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.82);
}
.set-page .bg-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.set-page .bg-cell {
  position: relative;
  height: 62px;
  padding: 0;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-sm);
  background-color: var(--tui-surface-muted);
  background-size: cover;
  background-position: center;
  cursor: pointer;
  overflow: hidden;
}
.set-page .bg-cell.is-active {
  border-color: transparent;
  box-shadow: 0 0 0 2px var(--tui-brand);
}
.set-page .bg-cell-check {
  position: absolute;
  right: 4px;
  bottom: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--tui-brand);
  color: #fff;
}
.set-page .bg-cell-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-style: dashed;
  color: var(--tui-text-tertiary);
  font-size: 11.5px;
}
.set-page .bg-cell-upload:active { background: var(--tui-surface-sunken); }
.set-page .bg-hint {
  margin: 8px 2px 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
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
