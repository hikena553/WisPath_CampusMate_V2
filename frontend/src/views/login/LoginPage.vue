<template>
  <div class="login-page">
    <div class="login-body">
      <header class="brand">
        <img :src="siteMascot" :alt="siteName" class="brand-logo" />
        <h1>欢迎回来</h1>
        <p>登录{{ siteName }}，继续你的校园生活</p>
      </header>

      <div v-if="loginReasonVisible" class="reason-bar">
        <span class="reason-dot"></span>
        <span class="reason-text">{{ loginReason }}</span>
        <button type="button" class="reason-close" aria-label="关闭提示" @click="dismissReason">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      <button
        v-if="pendingReset"
        type="button"
        class="reset-banner"
        @click="router.push({ path: '/forgot-password', query: { id: pendingReset.id, username: pendingReset.username } })"
      >
        <span class="reset-dot"></span>
        <span class="reset-text">
          密码重置申请已通知管理员，{{
            remainingHours(pendingReset) > 0
              ? `预计 ${remainingHours(pendingReset)} 小时内完成，请稍后重新登录`
              : '管理员即将处理，请稍后重新登录'
          }}
        </span>
        <span class="reset-action">查进度</span>
      </button>

      <form class="form" @submit.prevent="handleLogin">
        <div class="field">
          <input
            ref="usernameRef"
            v-model.trim="form.username"
            type="text"
            autocomplete="username"
            placeholder="学号 / 工号"
            :class="{ invalid: errorField === 'username' }"
            @input="errorField = ''"
          />
        </div>

        <div class="field">
          <input
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            placeholder="密码"
            :class="{ invalid: errorField === 'password' }"
            @input="errorField = ''"
          />
          <button
            type="button"
            class="eye-btn"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            @click="showPassword = !showPassword"
          >
            <svg v-if="!showPassword" viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2.5 12S6 5.8 12 5.8 21.5 12 21.5 12 18 18.2 12 18.2 2.5 12 2.5 12Z" />
              <circle cx="12" cy="12" r="3.1" />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 3l18 18" />
              <path d="M10.6 6.1A9.7 9.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-3.1 3.7" />
              <path d="M6.4 7.9A16.8 16.8 0 0 0 2.5 12S6 18 12 18a9.5 9.5 0 0 0 4.2-1" />
              <path d="M9.8 10.2a3.1 3.1 0 0 0 4.2 4.2" />
            </svg>
          </button>
        </div>

        <div class="form-meta">
          <span class="error-text">{{ formError }}</span>
          <router-link class="forgot-link" to="/forgot-password">忘记密码？</router-link>
        </div>

        <button type="submit" class="btn-primary" :disabled="loginLoading">
          {{ loginLoading ? '登录中…' : '登录' }}
        </button>
      </form>

      <button type="button" class="guest-link" @click="handleGuest">
        免费使用，仅开放部分功能
      </button>

      <div class="other">
        <span class="other-line"></span>
        <span class="other-text">其他登录方式</span>
        <span class="other-line"></span>
      </div>

      <div class="quick-row">
        <button
          type="button"
          class="quick-item"
          :disabled="quickLoading === 'phone'"
          @click="handleQuickLogin('phone')"
        >
          <span class="quick-circle">
            <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <rect x="6.5" y="2.8" width="11" height="18.4" rx="2.6" />
              <path d="M10.4 18.3h3.2" />
            </svg>
          </span>
          <span class="quick-name">{{ quickLoading === 'phone' ? '认证中…' : '手机号' }}</span>
        </button>

        <button
          type="button"
          class="quick-item"
          :disabled="quickLoading === 'qq'"
          @click="handleQuickLogin('qq')"
        >
          <span class="quick-circle qq">QQ</span>
          <span class="quick-name">{{ quickLoading === 'qq' ? '认证中…' : 'QQ' }}</span>
        </button>
      </div>

      <label class="agree">
        <input v-model="agreed" type="checkbox" />
        <span>
          我已阅读并同意
          <button type="button" class="agree-link" @click.prevent.stop="openLegal('agreement')">《用户协议》</button>
          和
          <button type="button" class="agree-link" @click.prevent.stop="openLegal('privacy')">《隐私政策》</button>
        </span>
      </label>
    </div>

    <LegalDoc v-if="legalType" :type="legalType" @close="legalType = ''" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { loginApi, quickLoginApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import LegalDoc from './LegalDoc.vue'
import {
  clearQuickAccount,
  getQuickAccount,
  saveQuickAccountFromLogin,
  type QuickChannel,
} from '@/utils/quickLogin'
import {
  clearPendingPasswordReset,
  loadPendingPasswordReset,
  remainingHours,
  type PendingPasswordReset,
} from '@/utils/passwordReset'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { siteName, siteMascot } = useSiteConfig()

watch(
  siteName,
  (name) => {
    document.title = `${name} — 登录`
  },
  { immediate: true }
)

const form = reactive({ username: '', password: '' })
const agreed = ref(false)
const showPassword = ref(false)
const loginLoading = ref(false)
const quickLoading = ref<'' | QuickChannel>('')
const usernameRef = ref<HTMLInputElement>()
const formError = ref('')
const errorField = ref<'username' | 'password' | ''>('')
const pendingReset = ref<PendingPasswordReset | null>(loadPendingPasswordReset())
const legalType = ref<'' | 'agreement' | 'privacy'>('')
const loginReason = ref('')
const reasonDismissed = ref(false)

let bannerTimer: number | undefined
let toastTimer: number | undefined
/** 登录结果只处理一次，防止回车 + 点击并发导致重复弹提示 */
let loginCommitted = false

function ensureAgreed(): boolean {
  if (agreed.value) return true
  ElMessage.warning('请先勾选用户协议与隐私政策')
  return false
}

function openLegal(type: 'agreement' | 'privacy') {
  legalType.value = type
}

function dismissReason() {
  reasonDismissed.value = true
}

const loginReasonVisible = computed(() => !reasonDismissed.value && !!loginReason.value)

watch(
  () => route.query.reason,
  (value) => {
    const feature = typeof value === 'string' ? value.trim() : ''
    loginReason.value =
      feature && feature !== 'login' ? `登录后即可${feature}，并解锁全部校园能力` : feature ? '登录后可解锁全部功能' : ''
    reasonDismissed.value = false
  },
  { immediate: true }
)

const roleMap: Record<string, string> = { student: '/student', teacher: '/teacher', admin: '/admin' }

function afterLogin(res: any) {
  // 同一会话只处理一次登录结果：回车与按钮点击可能并发触发，避免重复提示
  if (loginCommitted) return
  loginCommitted = true
  auth.login(res.access_token, res.user)
  saveQuickAccountFromLogin(res)
  clearPendingPasswordReset()
  pendingReset.value = null
  router.replace(roleMap[res.user.role] || '/student')
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    // 初始密码提醒由页面顶部的常驻提示条承担，这里只报登录成功，避免同屏两条提示
    ElMessage.success('登录成功')
  }, 260)
}

async function handleLogin() {
  if (loginLoading.value) return
  if (!ensureAgreed()) return
  if (!form.username) {
    errorField.value = 'username'
    formError.value = '请输入学号 / 工号'
    return
  }
  if (!form.password) {
    errorField.value = 'password'
    formError.value = '请输入密码'
    return
  }
  formError.value = ''
  errorField.value = ''
  loginLoading.value = true
  try {
    const res: any = await loginApi(form)
    if (!res?.access_token) throw new Error('响应异常')
    afterLogin(res)
  } catch (e: any) {
    if (e?.response) {
      formError.value = e.response.data?.detail || `请求失败 (${e.response.status})`
    } else if (e?.request) {
      formError.value = '无法连接服务器，请稍后重试'
    } else {
      formError.value = '登录失败，请重试'
    }
  } finally {
    loginLoading.value = false
  }
}

/**
 * 一键登录：先完成设备认证（长期凭证），再由后端校验该手机号/QQ 是否绑定账号。
 * 不在页面一开始就判定「不可用」——只有认证通过后查到未绑定，才提示无账号。
 */
async function handleQuickLogin(channel: QuickChannel) {
  if (!ensureAgreed()) return
  const account = getQuickAccount()
  if (!account?.token) {
    ElMessage({
      type: 'info',
      message: `请先用账号密码登录完成身份认证，认证通过后即可使用${channel === 'phone' ? '手机号' : 'QQ'}一键登录`,
      duration: 3600,
    })
    return
  }
  quickLoading.value = channel
  try {
    const res: any = await quickLoginApi(account.token, channel)
    if (!res?.access_token) throw new Error('响应异常')
    afterLogin(res)
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    if (e?.response?.status === 401) {
      clearQuickAccount()
    }
    ElMessage.warning(detail || '认证未通过，请使用账号密码登录')
  } finally {
    quickLoading.value = ''
  }
}

function handleGuest() {
  if (!ensureAgreed()) return
  auth.enterGuest()
  router.replace('/student/campus')
}

onMounted(() => {
  nextTick(() => usernameRef.value?.focus())
  // 申请提交后停留在登录页时，定时刷新剩余等待时间提示
  bannerTimer = window.setInterval(() => {
    pendingReset.value = loadPendingPasswordReset()
  }, 60_000)
})

onBeforeUnmount(() => {
  if (bannerTimer) window.clearInterval(bannerTimer)
})
</script>

<style scoped>
.login-page {
  /* 固定铺满视口，避免外层容器留白露出其它底色 */
  position: fixed;
  inset: 0;
  overflow-y: auto;
  display: flex;
  justify-content: center;
  padding: calc(env(safe-area-inset-top) + 10px) 24px calc(env(safe-area-inset-bottom) + 14px);
  /* 纯色铺满：不再叠加顶部白色径向渐变，避免四角/顶部露出白色 */
  background: #f2f2f4;
  color: #16161a;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.login-body {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
}

/* ===== 品牌区 ===== */
.brand {
  padding-top: clamp(26px, 6vh, 52px);
  text-align: center;
}

.brand-logo {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  object-fit: contain;
  background: #fff;
  padding: 6px;
  box-shadow: 0 6px 18px rgba(20, 20, 25, 0.08);
}

.brand h1 {
  margin: 18px 0 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.4px;
  color: #16161a;
}

.brand p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #9a9aa3;
  letter-spacing: 0.2px;
}

/* ===== 登录原因提示（非弹窗） ===== */
.reason-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 11px 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e8e8ec;
  font-size: 12px;
  line-height: 1.55;
  color: #4a4a52;
}

.reason-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #111111;
  flex-shrink: 0;
}

.reason-text {
  flex: 1;
}

.reason-close {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #a1a1a6;
  cursor: pointer;
  flex-shrink: 0;
}

/* ===== 忘记密码等待提示 ===== */
.reset-banner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 22px;
  padding: 12px 13px;
  border: none;
  border-radius: 12px;
  background: #f1f1f3;
  color: #3d3d43;
  font-size: 12px;
  line-height: 1.6;
  text-align: left;
  cursor: pointer;
}
.reset-dot {
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: 50%;
  background: #111111;
  flex-shrink: 0;
}
.reset-text {
  flex: 1;
}
.reset-action {
  flex-shrink: 0;
  color: #111111;
  font-weight: 600;
}

/* ===== 表单 ===== */
.form {
  margin-top: clamp(26px, 5vh, 36px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  position: relative;
}

.field input {
  width: 100%;
  height: 54px;
  padding: 0 46px 0 16px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(20, 20, 25, 0.03);
  color: #16161a;
  /* ≥16px：避免 iOS Safari 聚焦输入框时自动放大页面 */
  font-size: 16px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}
.field input::placeholder {
  color: #a4a4ac;
  font-size: 15px;
}
.field input:focus {
  border-color: #111111;
  box-shadow: 0 0 0 3px rgba(17, 17, 17, 0.08);
}
.field input.invalid {
  border-color: #111111;
  background: #f7f7f8;
}

.eye-btn {
  position: absolute;
  right: 7px;
  top: 50%;
  transform: translateY(-50%);
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #a4a4ac;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.eye-btn:active {
  color: #6f6f78;
}

.form-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 18px;
  padding: 0 2px;
}

.error-text {
  font-size: 12px;
  line-height: 1.45;
  color: #b42318;
}

.forgot-link {
  margin-left: auto;
  color: #76767f;
  font-size: 12.5px;
  text-decoration: none;
  white-space: nowrap;
}
.forgot-link:hover {
  color: #111111;
}

.btn-primary {
  height: 54px;
  margin-top: 4px;
  border: none;
  border-radius: 27px;
  background: #111111;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  cursor: pointer;
  box-shadow: 0 10px 20px rgba(17, 17, 17, 0.12);
  transition: background 0.16s ease, transform 0.16s ease, opacity 0.16s ease;
  -webkit-tap-highlight-color: transparent;
}
.btn-primary:hover:not(:disabled) {
  background: #000000;
}
.btn-primary:active:not(:disabled) {
  transform: scale(0.99);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.guest-link {
  align-self: center;
  margin-top: 15px;
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: #76767f;
  font-size: 13px;
  cursor: pointer;
}
.guest-link:active {
  color: #16161a;
}

/* ===== 其他登录方式 ===== */
.other {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: clamp(30px, 6vh, 46px);
}
.other-line {
  flex: 1;
  height: 1px;
  background: #e3e3e8;
}
.other-text {
  font-size: 11px;
  color: #a4a4ac;
  letter-spacing: 0.4px;
}

.quick-row {
  display: flex;
  justify-content: center;
  gap: 52px;
  margin-top: 18px;
}

.quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.quick-item:disabled {
  cursor: default;
  opacity: 0.55;
}

.quick-circle {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #e9e9ee;
  color: #111111;
  box-shadow: 0 2px 6px rgba(20, 20, 25, 0.04);
  transition: transform 0.16s ease;
}
.quick-item:active .quick-circle {
  transform: scale(0.95);
}
.quick-circle.qq {
  color: #111111;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.quick-name {
  font-size: 11.5px;
  color: #76767f;
}

/* ===== 协议 ===== */
.agree {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  margin: clamp(28px, 6vh, 52px) auto 0;
  max-width: 330px;
  font-size: 11px;
  line-height: 1.7;
  color: #9a9aa3;
  text-align: center;
  cursor: pointer;
}
.agree input {
  width: 13px;
  height: 13px;
  margin: 2px 0 0;
  flex-shrink: 0;
  accent-color: #111111;
  cursor: pointer;
}
.agree span {
  text-align: center;
}
.agree-link {
  padding: 0;
  border: none;
  background: transparent;
  color: #76767f;
  font: inherit;
  cursor: pointer;
}
.agree-link:hover {
  color: #111111;
  text-decoration: underline;
}

@media (max-height: 720px) {
  .brand {
    padding-top: 26px;
  }
  .brand-logo {
    width: 56px;
    height: 56px;
    border-radius: 17px;
  }
  .brand h1 {
    margin-top: 14px;
    font-size: 22px;
  }
  .form {
    margin-top: 22px;
    gap: 10px;
  }
  .other {
    margin-top: 26px;
  }
  .agree {
    margin-top: 22px;
  }
}

@media (max-width: 360px) {
  .quick-row {
    gap: 40px;
  }
}

/* ===== 桌面端：居中卡片 + 放大字号，避免在宽屏上缩成一条窄列 ===== */
@media (min-width: 900px) {
  .login-page {
    align-items: center;
    padding: 48px 24px;
    background:
      radial-gradient(75% 55% at 12% 0%, #ffffff 0%, rgba(255, 255, 255, 0) 62%),
      #f2f2f4;
  }

  .login-body {
    max-width: 460px;
    padding: 40px 40px 34px;
    border-radius: 26px;
    background: #ffffff;
    box-shadow: 0 30px 80px rgba(17, 17, 17, 0.07), 0 2px 6px rgba(17, 17, 17, 0.03);
  }

  .brand {
    padding-top: 0;
  }
  .brand-logo {
    width: 74px;
    height: 74px;
    border-radius: 22px;
    box-shadow: none;
  }
  .brand h1 {
    margin-top: 22px;
    font-size: 28px;
  }
  .brand p {
    margin-top: 10px;
    font-size: 14px;
  }

  .reason-bar {
    margin-top: 20px;
    font-size: 12.5px;
  }
  .reset-banner {
    margin-top: 24px;
  }

  .form {
    margin-top: 26px;
    gap: 14px;
  }
  .field input {
    height: 56px;
    background: #f7f7f8;
    border-color: #f0f0f2;
  }
  .field input:focus {
    background: #ffffff;
  }
  .btn-primary {
    height: 56px;
    font-size: 16.5px;
  }

  .guest-link {
    margin-top: 18px;
  }
  .other {
    margin-top: 30px;
  }
  .agree {
    margin-top: 26px;
  }
}
</style>
