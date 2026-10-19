<template>
  <div class="profile-wrapper" :class="{ 'is-web': !isMobile }">
    <!-- ===== 移动端主页面：封面头部（身份悬浮于背景之上）+ 分组菜单（桌面端改由左侧导航承担） ===== -->
    <transition v-if="isMobile" :name="slideDirection">
      <div v-if="!currentPage" key="main" class="profile-page">
        <!-- 个人中心头部（抖音范式）：封面铺满整行，身份信息以暗色渐变压底后「悬浮」在背景之上，
             姓名 / 工号 / 学院与关键数据直接压在封面上，不再另立一张直白的白色卡片。 -->
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
                <span class="pf-cast-role">教师</span>
              </div>
              <p class="pf-cast-sub">
                工号：{{ auth.user?.username || '—' }}
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
              <b>{{ profileForm.className || '—' }}</b>
              <span>所带班级</span>
            </div>
            <i class="pf-hero-stat-sep"></i>
            <div class="pf-hero-stat">
              <b>{{ profileCompletion }}%</b>
              <span>资料完整度</span>
            </div>
          </div>
        </section>

        <!-- 内容面板：圆角上浮压住封面底边，形成「悬浮于背景之上」的层次 -->
        <div class="pf-body">
          <!-- 客服与帮助：分组内嵌列表（抖音设置页 / Vant CellGroup 范式） -->
          <section class="pf-section">
            <h3 class="pf-section-title">客服与帮助</h3>
            <div class="pf-list">
              <button type="button" class="pf-row" @click="openPage('announcements')">
                <span class="pf-row-icon"><el-icon :size="17"><Bell /></el-icon></span>
                <span class="pf-row-label">校园公告</span>
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

    <!-- ===== 桌面端身份横幅：网页端的个人信息「名片」区 =====
         与移动端「卡片堆叠」不同，桌面端用整行横幅承载背景图 + 头像 + 身份信息 + 关键信息胶囊，
         它是页面的视觉锚点，也把「个人背景」从移动端的二级页面提升为第一屏可直接操作的能力。 -->
    <section v-if="!isMobile" class="profile-hero">
      <div class="hero-banner" :class="{ 'is-image': !!bannerUrl }" :style="heroBannerStyle">
        <div class="hero-banner-veil"></div>
        <button type="button" class="hero-banner-edit" @click="currentPage = 'banner'">
          <el-icon :size="14"><Camera /></el-icon>
          更换背景
        </button>
      </div>

      <div class="hero-identity">
        <el-avatar :size="76" :src="auth.user?.avatar || ''" class="hero-avatar">
          {{ auth.userName?.[0] }}
        </el-avatar>
        <div class="hero-meta">
          <div class="hero-name-row">
            <h2 class="hero-name">{{ auth.userName }}</h2>
            <span class="hero-role">教师</span>
          </div>
          <div class="hero-sub">
            <span><el-icon :size="13"><User /></el-icon>工号 {{ auth.user?.username || '—' }}</span>
            <span><el-icon :size="13"><School /></el-icon>{{ auth.user?.college || '未设置学院' }}</span>
          </div>
        </div>
        <div class="hero-facts">
          <div class="hero-fact">
            <span class="hero-fact-num">{{ profileForm.className || '—' }}</span>
            <span class="hero-fact-lb">所带班级</span>
          </div>
          <div class="hero-fact">
            <span class="hero-fact-num">{{ profileCompletion }}%</span>
            <span class="hero-fact-lb">资料完整度</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 桌面端主体：左侧导航 + 右侧内容 =====
           .profile-body 不参与两端分支判断：它只做桌面端的行容器，
           移动端以 display:contents 退化为「无盒子」，子元素仍按原样定位。 -->
    <div class="profile-body">
      <aside v-if="!isMobile" class="profile-side">
        <nav v-for="g in desktopMenuGroups" :key="g.title" class="side-group">
          <div class="side-group-title">{{ g.title }}</div>
          <button
            v-for="m in g.items"
            :key="m.key"
            type="button"
            class="side-item"
            :class="{ active: activeTab === m.key }"
            @click="currentPage = m.key"
          >
            <el-icon :size="16"><component :is="m.icon" /></el-icon>
            <span class="side-item-label">{{ m.label }}</span>
          </button>
        </nav>

        <button type="button" class="side-item side-item-danger" @click="logout">
          <el-icon :size="16"><SwitchButton /></el-icon>
          <span class="side-item-label">退出登录</span>
        </button>
      </aside>

      <!-- ===== 内容区：移动端走整页切换，桌面端常驻右侧内容栏 ===== -->
      <transition :name="isMobile ? slideDirection : ''">
      <div v-if="activeTab" :key="activeTab" :class="isMobile ? 'sub-page' : 'profile-main'">
        <!-- 移动端子页返回栏（桌面端由左侧导航承担切换） -->
        <div v-if="isMobile" class="sub-page-header">
          <el-button text circle class="back-btn" @click="closePage">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </el-button>
          <div class="sub-page-title">{{ pageTitle }}</div>
          <div class="sub-page-placeholder"></div>
        </div>
        <div v-else class="web-head">
          <h2 class="web-head-title">{{ pageTitle }}</h2>
          <p class="web-head-sub">{{ pageSubtitle }}</p>
        </div>

        <!-- 账号与安全（抖音设置页范式）：只读展示 + 点按行弹窗编辑，不再铺一屏输入框 -->
        <div v-if="activeTab === 'profile'" class="sub-page-content set-page">
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
            <el-button type="primary" class="footer-btn" @click="handleSaveProfile" :loading="saving">保存</el-button>
          </div>
        </div>

        <!-- 修改密码 -->
        <div v-if="activeTab === 'password'" class="sub-page-content">
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
            <el-button type="primary" class="footer-btn" @click="handleChangePassword" :loading="changingPassword">确定</el-button>
          </div>
        </div>

        <!-- 校园公告 -->
        <div v-if="activeTab === 'announcements'" class="sub-page-content">
          <div v-loading="loadingAnnouncements" class="announcement-list">
            <div v-if="announcements.length === 0 && !loadingAnnouncements" class="empty-announcement">暂无校园公告</div>
            <a v-for="(item, index) in announcements" :key="'a' + index" :href="item.url || '#'" target="_blank" class="announcement-item">
              <div class="announcement-title">{{ item.title }}</div>
              <div class="announcement-date">{{ item.date }}</div>
            </a>
          </div>
        </div>

        <!-- 使用帮助 -->
        <div v-if="activeTab === 'help'" class="sub-page-content">
          <div class="help-content">
            <div class="help-item">
              <div class="help-question">如何联系{{ agentName }}？</div>
              <div class="help-answer">在首页直接输入你的问题，{{ agentName }}会即时回复。</div>
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
        <div v-if="activeTab === 'theme'" class="sub-page-content">
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
        <div v-if="activeTab === 'about'" class="sub-page-content">
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
              {{ agentName }}是绵阳城市学院官方推出的智慧校园AI助手，基于大语言模型技术，为全校师生提供智能化的校园服务。通过自然语言对话，您可以轻松完成课表查询、成绩查询、请假审批、校园通知查看等日常事务，让校园管理更加便捷高效。
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

        <!-- 更换背景（抖音背景选择器范式）：顶部实时预览 + 背景宫格，点选即时生效 -->
        <div v-if="activeTab === 'banner'" class="sub-page-content set-page">
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
                  <div class="bg-preview-sub">工号：{{ auth.user?.username || '—' }}</div>
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
    </div>

    <!-- 账号与安全：字段编辑弹窗（抖音「点按设置项 → 就地编辑」范式） -->
    <el-dialog
      v-model="editVisible"
      :title="editField ? `修改${editField.label}` : ''"
      :width="isMobile ? '86%' : '420px'"
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
      <el-select v-else v-model="editValue" placeholder="请选择" style="width:100%">
        <el-option v-for="o in editField?.options || []" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmFieldEdit">确定</el-button>
      </template>
    </el-dialog>
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
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useResponsive } from '@/composables/useResponsive'
import {
  ArrowRight, ArrowLeft, Lock, SwitchButton, Sunny, InfoFilled,
  QuestionFilled, Bell, Camera, Picture, User, School, Check, Plus
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()
const { isMobile } = useResponsive()

// 关于页品牌信息与站点配置同源
const { siteName, siteLogo, agentName } = useSiteConfig()

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

/**
 * 账号与安全：字段描述表（抖音设置项范式）。
 * 页面只读展示「左侧标签 + 右侧值 + 箭头」，点按行弹出编辑弹窗，
 * 避免把 8 个输入框一次性铺在页面上。
 */
interface AccField {
  key: string
  label: string
  type: 'text' | 'select' | 'number'
  options?: { label: string; value: string }[]
  placeholder?: string
  readonly?: boolean
}

const accGroups: { title: string; fields: AccField[] }[] = [
  {
    title: '账号信息',
    fields: [
      { key: 'username', label: '工号', type: 'text', readonly: true },
      { key: 'name', label: '姓名', type: 'text', readonly: true },
      { key: 'college', label: '学院', type: 'text', readonly: true },
      { key: 'className', label: '所带班级', type: 'text', placeholder: '请输入所带班级' },
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
      { key: 'title', label: '职称', type: 'text', placeholder: '请输入职称' },
      { key: 'department', label: '所属单位', type: 'text', placeholder: '请输入所属单位' },
    ],
  },
]

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

// 校园公告
const announcements = ref<Announcement[]>([])
const loadingAnnouncements = ref(false)

/** 身份背景（移动端 .pf-hero 与桌面端横幅共用）：优先用已上传图片，否则用预设渐变 */
const heroBannerStyle = computed(() =>
  bannerUrl.value ? { backgroundImage: `url(${bannerUrl.value})` } : { background: bannerGradient.value }
)

/** 资料完整度：桌面端身份横幅里的一个轻量进度指标，驱动用户补齐联系方式 */
const profileCompletion = computed(() => {
  const fields = [
    profileForm.className, profileForm.gender, profileForm.hometown,
    profileForm.phone, profileForm.political_status, profileForm.title, profileForm.department,
  ]
  const filled = fields.filter((v) => v !== '' && v !== null && v !== undefined).length
  return Math.round((filled / fields.length) * 100)
})

/** 桌面端当前内容页：未选择时默认落在「账号与安全」，符合设置页的常规范式 */
const activeTab = computed(() => currentPage.value || (isMobile.value ? '' : 'profile'))

// 页面标题
const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    profile: '账号与安全',
    password: '修改密码',
    announcements: '校园公告',
    help: '使用帮助',
    theme: '主题设置',
    about: `关于${agentName.value}`,
    banner: '更换背景'
  }
  return titles[activeTab.value] || ''
})

/** 桌面端内容区副标题：说明该分组做什么，替代移动端的整页标题感 */
const pageSubtitle = computed(() => {
  const subs: Record<string, string> = {
    profile: '管理账号信息与登录安全，保存后即时生效',
    password: '定期更换密码可提升账号安全性',
    banner: '选择预设渐变或上传图片，作为个人中心顶栏背景',
    announcements: '来自学校的通知与公告，点击可在新窗口查看详情',
    help: `关于${agentName.value}的常见用法与快捷指令说明`,
    theme: '当前系统仅支持浅色模式',
    about: '产品信息、技术架构与开发团队',
  }
  return subs[activeTab.value] || ''
})

/**
 * 桌面端左侧菜单：桌面改用语网页端的「左导航 + 右内容」设置页结构，
 * 取代移动端「整页推入 + 返回」的交互；退出登录是动作项，单独渲染在菜单底部。
 */
const desktopMenuGroups = [
  {
    title: '账号',
    items: [
      { key: 'profile', label: '账号与安全', icon: User },
      { key: 'password', label: '修改密码', icon: Lock },
      { key: 'banner', label: '个人背景', icon: Picture },
    ],
  },
  {
    title: '帮助与设置',
    items: [
      { key: 'announcements', label: '校园公告', icon: Bell },
      { key: 'help', label: '使用帮助', icon: QuestionFilled },
      { key: 'theme', label: '主题设置', icon: Sunny },
      { key: 'about', label: `关于${agentName.value}`, icon: InfoFilled },
    ],
  },
]

/** 用当前登录用户回填个人资料表单 */
function fillProfileForm() {
  const u = auth.user
  if (!u) return
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

// 打开子页面
function openPage(page: string) {
  if (page === 'profile') fillProfileForm()
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
  // 身份名片（移动端与桌面端）都要展示「所带班级 / 资料完整度」，故挂载即回填表单
  fillProfileForm()
})
</script>

<style scoped>
.profile-wrapper {
  position: relative;
  height: 100%;
  overflow: hidden;
}

/* ===== 桌面端：身份横幅 + 左导航 + 右内容的网页设置页布局 ===== */
.profile-wrapper.is-web {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 16px 0;
  background: #f5f7fa;
  overflow: hidden;
}

/* 移动端：行容器退化为无盒子，子元素（子页）仍相对 .profile-wrapper 定位 */
.profile-body { display: contents; }

/* ===== 身份横幅：整行名片，含背景图 + 头像 + 身份 + 关键信息 ===== */
.profile-hero {
  flex: 0 0 auto;
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  overflow: hidden;
}
.hero-banner {
  position: relative;
  height: 132px;
  background-size: cover;
  background-position: center;
}
.hero-banner-veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(15, 17, 21, 0.06) 0%, rgba(15, 17, 21, 0.28) 100%);
}
.hero-banner-edit {
  position: absolute;
  right: 12px;
  top: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 999px;
  background: rgba(15, 17, 21, 0.34);
  color: #fff;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  backdrop-filter: blur(4px);
}
.hero-banner-edit:hover { background: rgba(15, 17, 21, 0.5); }

.hero-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px 16px;
  margin-top: -34px;
}
.hero-avatar {
  border: 4px solid #fff;
  background: #eff4ff;
  color: #1d4ed8;
  font-size: 26px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 10px rgba(15, 17, 21, 0.12);
}
.hero-meta { flex: 1; min-width: 0; padding-top: 34px; }
.hero-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-name {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #101828;
}
.hero-role {
  padding: 1px 8px;
  border-radius: 999px;
  background: #eff4ff;
  color: #1d4ed8;
  font-size: 11.5px;
  font-weight: 600;
}
.hero-sub {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 5px;
  font-size: 12.5px;
  color: #667085;
}
.hero-sub > span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.hero-facts {
  display: flex;
  align-items: stretch;
  gap: 10px;
  padding-top: 34px;
  flex-shrink: 0;
}
.hero-fact {
  min-width: 104px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 14px;
  border-radius: 10px;
  background: #f9fafb;
  border: 1px solid #f2f4f7;
}
.hero-fact-num {
  font-size: 14px;
  font-weight: 700;
  color: #101828;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hero-fact-lb {
  font-size: 11px;
  color: #98a2b3;
}

/* ===== 主体：左导航 + 右内容，占满横幅以下的剩余高度 ===== */
.profile-wrapper.is-web .profile-body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 14px;
  padding-bottom: 16px;
}

.profile-side {
  flex: 0 0 232px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 12px;
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  overflow-y: auto;
  scrollbar-width: none;
}
.profile-side::-webkit-scrollbar { display: none; width: 0; }

.side-group { display: flex; flex-direction: column; gap: 2px; }
.side-group-title {
  padding: 0 8px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #98a2b3;
}

.side-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 9px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: #475467;
  font-family: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.side-item:hover { background: #f6f7f9; color: #101828; }
.side-item.active {
  background: #eff4ff;
  color: #1d4ed8;
  font-weight: 600;
}
.side-item-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-item-danger { color: #b42318; margin-top: auto; }
.side-item-danger:hover { background: #fef3f2; color: #912018; }

/* 右侧内容栏：常驻不滑动，滚动交给内部 */
.profile-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #f0f1f3;
  border-radius: 14px;
  overflow: hidden;
}

.web-head {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #f2f4f7;
  flex-shrink: 0;
}
.web-head-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #101828;
}
.web-head-sub {
  margin: 3px 0 0;
  font-size: 12px;
  color: #98a2b3;
}

/* 桌面端把移动端子页的绝对定位改成正常的文档流 */
.profile-wrapper.is-web .sub-page-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 20px;
  background: #fff;
  scrollbar-width: none;
}
.profile-wrapper.is-web .sub-page-content::-webkit-scrollbar { display: none; width: 0; }

/* 按钮改为常规宽度，不再整行拉伸 */
.profile-wrapper.is-web .sub-page-footer {
  display: flex;
  justify-content: flex-start;
  padding: 14px 0 0;
  background: transparent;
  border-top: 1px solid #f2f4f7;
  margin-top: 16px;
}
.footer-btn { min-width: 96px; }
@media (max-width: 767px) {
  .footer-btn { width: 100%; }
}

/* 桌面端表单区域宽度受控，避免输入框横跨整页 */
.profile-wrapper.is-web .sub-form { max-width: 520px; }

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

/* ===== 分组卡片 + 内嵌列表行 ===== */
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
