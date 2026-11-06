<template>
  <div class="reg-page">
    <div class="reg-shell">
      <button type="button" class="reg-back" @click="goLogin">
        <span class="reg-back-arrow">‹</span> 返回登录
      </button>

      <!-- 第一步：先选择身份 -->
      <template v-if="step === 'role'">
        <header class="reg-head">
          <h1>选择身份</h1>
          <p>请先确认你的校园身份，填写对应的注册信息</p>
        </header>

        <div class="role-list">
          <button type="button" class="role-card" @click="chooseRole('student')">
            <span class="role-icon">学</span>
            <span class="role-text">
              <strong>学生</strong>
              <span>使用学号注册，需选择学院、专业与导师</span>
            </span>
            <span class="role-arrow">›</span>
          </button>
          <button type="button" class="role-card" @click="chooseRole('teacher')">
            <span class="role-icon">师</span>
            <span class="role-text">
              <strong>教师</strong>
              <span>使用工号注册，只需填写所属学院</span>
            </span>
            <span class="role-arrow">›</span>
          </button>
        </div>

        <p class="reg-foot">
          已有账号？<a class="reg-link" href="javascript:void(0)" @click="goLogin">直接登录</a>
        </p>
      </template>

      <!-- 第二步：填写注册信息 -->
      <template v-else>
        <header class="reg-head">
          <h1>{{ isTeacher ? '教师注册' : '学生注册' }}</h1>
          <p>
            {{ isTeacher ? '工号' : '学号' }}作为登录账号，需补全{{ isTeacher ? '所属学院' : '学院、专业、导师' }}与手机号、QQ 号{{
              thirdPartyAuthEnabled ? '，并完成手机号或 QQ 真实验证' : qqNativeEnabled ? '，并完成 QQ 授权验证' : ''
            }}
          </p>
        </header>

        <form class="reg-form" @submit.prevent="handleSubmit">
          <div class="role-summary">
            <span class="role-summary-tag">{{ isTeacher ? '教师身份' : '学生身份' }}</span>
            <button type="button" class="role-swap" @click="backToRole">切换身份</button>
          </div>

          <div class="field">
            <label class="field-label" for="reg-account">{{ isTeacher ? '工号' : '学号' }} <i class="req">*</i></label>
            <input
              id="reg-account"
              v-model.trim="form.studentNo"
              type="text"
              inputmode="numeric"
              maxlength="15"
              :placeholder="isTeacher ? '请输入 5-15 位工号' : '请输入 5-15 位学号'"
              autocomplete="username"
            />
          </div>
          <div class="field">
            <label class="field-label" for="reg-name">姓名 <i class="req">*</i></label>
            <input
              id="reg-name"
              v-model.trim="form.name"
              type="text"
              maxlength="20"
              placeholder="请输入真实姓名"
            />
          </div>
          <div class="field">
            <label class="field-label" for="reg-password">密码 <i class="req">*</i></label>
            <div class="pw-row">
              <input
                id="reg-password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                maxlength="20"
                placeholder="8-20 位，需同时包含字母和数字"
                autocomplete="new-password"
              />
              <button
                type="button"
                class="eye-btn"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg
                  v-if="!showPassword"
                  viewBox="0 0 24 24"
                  width="19"
                  height="19"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2.5 12S6 5.8 12 5.8 21.5 12 21.5 12 18 18.2 12 18.2 2.5 12 2.5 12Z" />
                  <circle cx="12" cy="12" r="3.1" />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  width="19"
                  height="19"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 3l18 18" />
                  <path d="M10.6 6.1A9.7 9.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-3.1 3.7" />
                  <path d="M6.4 7.9A16.8 16.8 0 0 0 2.5 12S6 18 12 18a9.5 9.5 0 0 0 4.2-1" />
                  <path d="M9.8 10.2a3.1 3.1 0 0 0 4.2 4.2" />
                </svg>
              </button>
            </div>
          </div>
          <div class="field">
            <label class="field-label" for="reg-confirm">确认密码 <i class="req">*</i></label>
            <div class="pw-row">
              <input
                id="reg-confirm"
                v-model="form.confirm"
                :type="showConfirm ? 'text' : 'password'"
                maxlength="20"
                placeholder="请再次输入密码"
                autocomplete="new-password"
              />
              <button
                type="button"
                class="eye-btn"
                :aria-label="showConfirm ? '隐藏密码' : '显示密码'"
                @click="showConfirm = !showConfirm"
              >
                <svg
                  v-if="!showConfirm"
                  viewBox="0 0 24 24"
                  width="19"
                  height="19"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2.5 12S6 5.8 12 5.8 21.5 12 21.5 12 18 18.2 12 18.2 2.5 12 2.5 12Z" />
                  <circle cx="12" cy="12" r="3.1" />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  width="19"
                  height="19"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 3l18 18" />
                  <path d="M10.6 6.1A9.7 9.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-3.1 3.7" />
                  <path d="M6.4 7.9A16.8 16.8 0 0 0 2.5 12S6 18 12 18a9.5 9.5 0 0 0 4.2-1" />
                  <path d="M9.8 10.2a3.1 3.1 0 0 0 4.2 4.2" />
                </svg>
              </button>
            </div>
          </div>

          <div class="field">
            <label class="field-label">学院 <i class="req">*</i></label>
            <RegSelect
              v-model="form.collegeId"
              :options="collegeOptions"
              placeholder="选择学院"
              @change="onCollegeChange"
            />
          </div>

          <template v-if="!isTeacher">
            <div class="field">
              <label class="field-label">专业 <i class="req">*</i></label>
              <RegSelect
                v-model="form.majorId"
                :options="majorOptions"
                :disabled="!form.collegeId"
                :placeholder="form.collegeId ? '选择专业' : '请先选择学院'"
              />
            </div>
            <div class="field">
              <label class="field-label">导师 <em class="opt">选填</em></label>
              <RegSelect
                v-model="form.tutorId"
                :options="tutorOptions"
                :disabled="!form.collegeId"
                :placeholder="form.collegeId ? '选择导师（可不选）' : '请先选择学院'"
              />
            </div>
          </template>

        <!-- 第三方与原生 QQ 通道均不可用（申请期间）：直接收集手机号、QQ 号 -->
        <template v-if="!thirdPartyAuthEnabled && !qqNativeEnabled">
          <div class="field">
            <label class="field-label" for="reg-phone">手机号 <i class="req">*</i></label>
            <input
              id="reg-phone"
              v-model.trim="form.phone"
              type="tel"
              inputmode="numeric"
              maxlength="11"
              placeholder="请输入 11 位手机号"
              autocomplete="tel"
            />
          </div>
          <div class="field">
            <label class="field-label" for="reg-qq">QQ 号 <i class="req">*</i></label>
            <input
              id="reg-qq"
              v-model.trim="form.qq"
              type="text"
              inputmode="numeric"
              maxlength="12"
              placeholder="必填，用于找回密码"
            />
          </div>
          <div class="field">
            <label class="field-label" for="reg-captcha">图形验证码 <i class="req">*</i></label>
            <div class="captcha-field">
              <input
                id="reg-captcha"
                v-model.trim="captchaCode"
                type="text"
                maxlength="4"
                placeholder="请输入 4 位验证码"
                autocomplete="off"
              />
              <button type="button" class="captcha-btn" title="看不清？点击刷新" @click="loadCaptcha">
                <img v-if="captchaImage" :src="captchaImage" alt="图形验证码" />
                <span v-else>刷新</span>
              </button>
            </div>
          </div>
        </template>

        <!-- 验证通道开放后：手机号短信验证（Web） / QQ 授权（Web 或 App 原生） -->
        <template v-else>
          <!-- App 内仅 QQ 授权可用（短信未开放），不展示验证方式切换 -->
          <div v-if="thirdPartyAuthEnabled" class="field">
            <span class="field-label">验证方式 <i class="req">*</i></span>
            <div class="verify-tabs">
              <button
                type="button"
                class="verify-tab"
                :class="{ active: verifyMode === 'phone' }"
                @click="verifyMode = 'phone'"
              >
                手机号验证
              </button>
              <button
                type="button"
                class="verify-tab"
                :class="{ active: verifyMode === 'qq' }"
                @click="verifyMode = 'qq'"
              >
                QQ 授权
              </button>
            </div>
          </div>

          <div v-if="thirdPartyAuthEnabled && verifyMode === 'phone'">
            <div class="field">
              <label class="field-label" for="reg-phone">手机号 <i class="req">*</i></label>
              <input
                id="reg-phone"
                v-model.trim="form.phone"
                type="tel"
                inputmode="numeric"
                maxlength="11"
                placeholder="请输入 11 位手机号"
                @input="phoneVerifiedPhone = ''"
              />
            </div>
            <div class="field">
              <label class="field-label" for="reg-captcha">图形验证码 <i class="req">*</i></label>
              <div class="captcha-field">
                <input
                  id="reg-captcha"
                  v-model.trim="captchaCode"
                  type="text"
                  maxlength="4"
                  placeholder="请输入 4 位验证码"
                  autocomplete="off"
                />
                <button type="button" class="captcha-btn" title="看不清？点击刷新" @click="loadCaptcha">
                  <img v-if="captchaImage" :src="captchaImage" alt="图形验证码" />
                  <span v-else>刷新</span>
                </button>
              </div>
            </div>
            <div class="field">
              <label class="field-label" for="reg-sms">短信验证码 <i class="req">*</i></label>
              <div class="code-field">
                <input
                  id="reg-sms"
                  v-model.trim="form.smsCode"
                  type="text"
                  inputmode="numeric"
                  maxlength="6"
                  placeholder="请输入 6 位验证码"
                  autocomplete="one-time-code"
                />
                <button
                  type="button"
                  class="code-btn"
                  :disabled="cooldown > 0 || sending"
                  @click="handleSendSms"
                >
                  {{ sending ? '发送中…' : cooldown > 0 ? `${cooldown}s 后重发` : '获取验证码' }}
                </button>
              </div>
            </div>

            <div v-if="phoneVerifiedPhone" class="verified-badge">
              手机号已验证：{{ maskPhone(phoneVerifiedPhone) }}
            </div>
            <button v-else type="button" class="verify-btn" :disabled="verifying" @click="handleVerifyPhone">
              {{ verifying ? '验证中…' : '验证手机号' }}
            </button>
          </div>

          <div v-else>
            <div v-if="qqTicket" class="verified-badge">
              QQ 已授权{{ qqNickname ? `：${qqNickname}` : '' }}
            </div>
            <template v-else>
              <p class="verify-note">
                {{ qqNativeEnabled ? '拉起手机 QQ 完成授权，再继续填写下方信息完成注册' : '授权 QQ 互联后回到本页，无需短信即可完成注册' }}
              </p>
              <button
                type="button"
                class="verify-btn"
                :disabled="qqLoading"
                @click="qqNativeEnabled ? handleQqNativeAuth() : handleQqAuth()"
              >
                {{ qqLoading ? '授权中…' : '授权 QQ 注册' }}
              </button>
            </template>
          </div>

          <div class="field">
            <label class="field-label" for="reg-qq">QQ 号 <i class="req">*</i></label>
            <input
              id="reg-qq"
              v-model.trim="form.qq"
              type="text"
              inputmode="numeric"
              maxlength="12"
              placeholder="必填，用于找回密码"
            />
          </div>
        </template>

        <p v-if="formError || hint" class="submit-hint" :class="{ error: !!formError }">
          {{ formError || hint }}
        </p>

        <button type="submit" class="submit-btn" :disabled="submitting">
          {{ submitting ? '注册中…' : '注册并登录' }}
        </button>

        <p class="reg-foot">
          已有账号？<a class="reg-link" href="javascript:void(0)" @click="goLogin">直接登录</a>
        </p>
        </form>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getCaptcha,
  getQqAuthorizeUrl,
  getRegisterOptions,
  qqMobileAuthorizeApi,
  registerApi,
  sendRegisterSms,
  verifyRegisterPhone,
  type RegisterOptions,
} from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { saveQuickAccountFromLogin } from '@/utils/quickLogin'
import { THIRD_PARTY_AUTH_ENABLED, QQ_NATIVE_AUTH_ENABLED } from '@/utils/features'
import { qqNativeAuthAvailable, qqNativeErrorCode, qqNativeErrorMessage, qqNativeLogin } from '@/utils/qqAuth'
import RegSelect from './RegSelect.vue'

const DRAFT_KEY = 'mian02_register_draft'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
/** 第三方登录开关（短信 / QQ 互联网站应用申请期间关闭，注册页改为直接填写手机号、QQ 号） */
const thirdPartyAuthEnabled = THIRD_PARTY_AUTH_ENABLED
/** QQ 互联移动端（App 壳内原生 SDK 授权），浏览器恒为 false */
const qqNativeEnabled = QQ_NATIVE_AUTH_ENABLED && qqNativeAuthAvailable()
/** 未走短信 / QQ 票据验证时，提交注册需图形验证码防刷 */
const captchaRequired = computed(() => !thirdPartyAuthEnabled && !qqNativeEnabled)

const options = ref<RegisterOptions>({ colleges: [], majors: [], tutors: [] })
/** 注册流程：先选身份，再填写注册信息 */
const step = ref<'role' | 'form'>('role')
const form = reactive({
  role: 'student' as 'student' | 'teacher',
  studentNo: '',
  name: '',
  password: '',
  confirm: '',
  collegeId: 0,
  majorId: 0,
  tutorId: 0,
  phone: '',
  smsCode: '',
  qq: '',
})

const isTeacher = computed(() => form.role === 'teacher')
/** 当前身份对应的账号称谓 */
const accountLabel = computed(() => (isTeacher.value ? '工号' : '学号'))

const verifyMode = ref<'phone' | 'qq'>('phone')
/** 密码默认掩码显示，可切换明文查看 */
const showPassword = ref(false)
const showConfirm = ref(false)
const captchaId = ref('')
const captchaImage = ref('')
const captchaCode = ref('')
const phoneTicket = ref('')
const phoneVerifiedPhone = ref('')
const qqTicket = ref('')
const qqNickname = ref('')
const hint = ref('')
const formError = ref('')
const sending = ref(false)
const verifying = ref(false)
const submitting = ref(false)
const qqLoading = ref(false)
const cooldown = ref(0)
let cooldownTimer: number | undefined

const selectedCollege = computed(() => options.value.colleges.find((c) => c.id === form.collegeId))
const majorList = computed(() => options.value.majors.filter((m) => m.college_id === form.collegeId))
const tutorList = computed(() => {
  const list = options.value.tutors.filter(
    (t) => !selectedCollege.value || !t.college || t.college === selectedCollege.value.name,
  )
  return list.length ? list : options.value.tutors
})

/** 自定义下拉（RegSelect）选项 */
const collegeOptions = computed(() => options.value.colleges.map((c) => ({ id: c.id, label: c.name })))
const majorOptions = computed(() => majorList.value.map((m) => ({ id: m.id, label: m.name })))
const tutorOptions = computed(() =>
  tutorList.value.map((t) => ({ id: t.id, label: t.name + (t.title ? ` · ${t.title}` : '') })),
)

function maskPhone(phone: string) {
  return phone.length === 11 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone
}

function goLogin() {
  router.replace('/login')
}

/** 选择身份后进入注册信息填写 */
function chooseRole(role: 'student' | 'teacher') {
  form.role = role
  step.value = 'form'
  formError.value = ''
  hint.value = ''
  if (role === 'teacher') {
    form.majorId = 0
    form.tutorId = 0
  }
}

function backToRole() {
  step.value = 'role'
  formError.value = ''
  hint.value = ''
}

function onCollegeChange() {
  form.majorId = 0
  form.tutorId = 0
}

async function loadOptions() {
  try {
    options.value = await getRegisterOptions()
  } catch {
    formError.value = '学院、专业、导师信息加载失败，请稍后刷新重试'
  }
}

async function loadCaptcha() {
  captchaCode.value = ''
  try {
    const res = await getCaptcha()
    captchaId.value = res.captcha_id
    captchaImage.value = res.image
  } catch {
    captchaImage.value = ''
  }
}

async function handleSendSms() {
  if (sending.value || cooldown.value > 0) return
  formError.value = ''
  hint.value = ''
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    formError.value = '请输入正确的 11 位手机号'
    return
  }
  if (!captchaCode.value.trim()) {
    formError.value = '请输入图形验证码'
    return
  }
  sending.value = true
  try {
    const res: any = await sendRegisterSms(form.phone, captchaId.value, captchaCode.value)
    if (res?.debug_code) {
      form.smsCode = res.debug_code
      hint.value = `演示环境验证码：${res.debug_code}`
    } else {
      hint.value = '验证码已发送'
    }
    startCooldown(Number(res?.cooldown) || 60)
    await loadCaptcha()
  } catch (e: any) {
    formError.value = e?.response?.data?.detail || '验证码发送失败，请稍后重试'
    await loadCaptcha()
  } finally {
    sending.value = false
  }
}

function startCooldown(seconds: number) {
  cooldown.value = Math.max(1, seconds)
  window.clearInterval(cooldownTimer)
  cooldownTimer = window.setInterval(() => {
    cooldown.value -= 1
    if (cooldown.value <= 0) window.clearInterval(cooldownTimer)
  }, 1000)
}

async function handleVerifyPhone() {
  if (verifying.value) return
  formError.value = ''
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    formError.value = '请输入正确的 11 位手机号'
    return
  }
  if (!/^\d{6}$/.test(form.smsCode)) {
    formError.value = '请输入 6 位短信验证码'
    return
  }
  verifying.value = true
  try {
    const res = await verifyRegisterPhone(form.phone, form.smsCode)
    phoneTicket.value = res.phone_ticket
    phoneVerifiedPhone.value = res.phone
    hint.value = ''
    ElMessage.success('手机号验证通过')
  } catch (e: any) {
    formError.value = e?.response?.data?.detail || '手机号验证失败，请重试'
  } finally {
    verifying.value = false
  }
}

function saveDraft() {
  try {
    sessionStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        role: form.role,
        studentNo: form.studentNo,
        name: form.name,
        collegeId: form.collegeId,
        majorId: form.majorId,
        tutorId: form.tutorId,
        phone: form.phone,
        qq: form.qq,
        verifyMode: verifyMode.value,
      }),
    )
  } catch {
    /* 忽略存储异常 */
  }
}

function restoreDraft() {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (!raw) return
    const draft = JSON.parse(raw)
    form.role = draft.role === 'teacher' ? 'teacher' : 'student'
    form.studentNo = draft.studentNo || ''
    form.name = draft.name || ''
    form.collegeId = draft.collegeId || 0
    form.majorId = draft.majorId || 0
    form.tutorId = draft.tutorId || 0
    form.phone = draft.phone || ''
    form.qq = draft.qq || ''
  } catch {
    /* 忽略解析异常 */
  }
}

async function handleQqAuth() {
  if (qqLoading.value) return
  saveDraft()
  qqLoading.value = true
  try {
    const res: any = await getQqAuthorizeUrl('register')
    if (!res?.url) throw new Error('响应异常')
    window.location.href = res.url
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    formError.value = detail || 'QQ 授权暂不可用，请改用手机号验证'
  } finally {
    qqLoading.value = false
  }
}

/** App 内：拉起手机 QQ 授权，票据就地保存在页面状态里（无需跳转回跳） */
async function handleQqNativeAuth() {
  if (qqLoading.value) return
  saveDraft()
  qqLoading.value = true
  try {
    const session = await qqNativeLogin()
    const res = await qqMobileAuthorizeApi(session.accessToken, session.openId)
    if (res.status === 'unregistered' && res.register_ticket) {
      qqTicket.value = res.register_ticket
      qqNickname.value = res.nickname || ''
      formError.value = ''
    } else if (res.status === 'login' && res.login?.access_token) {
      // 该 QQ 已绑定校园账号：无需重复注册，直接登录
      auth.login(res.login.access_token, res.login.user)
      saveQuickAccountFromLogin(res.login)
      ElMessage.success('该 QQ 已绑定校园账号，已直接登录')
      router.replace(res.login.user.role === 'teacher' ? '/teacher' : '/student')
      return
    } else {
      throw new Error('响应异常')
    }
  } catch (e: any) {
    const code = qqNativeErrorCode(e)
    if (code === 'QQ_NOT_INSTALLED') {
      ElMessage.warning('未检测到手机 QQ，请安装后重试')
    } else if (code !== 'USER_CANCEL') {
      formError.value = e?.response?.data?.detail || qqNativeErrorMessage(e, 'QQ 授权失败，请稍后重试')
    }
  } finally {
    qqLoading.value = false
  }
}

function validate(): string {
  if (!/^\d{5,15}$/.test(form.studentNo)) return `${accountLabel.value}必须为 5-15 位数字`
  if (!/^(?=.*[A-Za-z])(?=.*[0-9])[\x21-\x7e]{8,20}$/.test(form.password)) {
    return '密码需为 8-20 位，且同时包含字母和数字'
  }
  if (form.password !== form.confirm) return '两次输入的密码不一致'
  if (form.name.trim().length < 2) return '请填写真实姓名'
  if (!form.collegeId) return '请选择学院'
  if (!isTeacher.value) {
    if (!form.majorId) return '请选择专业'
    // 导师为选填项，不强制选择
  }
  if (thirdPartyAuthEnabled || qqNativeEnabled) {
    // App 内仅 QQ 授权可用（手机号短信通道未开放），不展示也不接受手机号验证
    if (thirdPartyAuthEnabled && verifyMode.value === 'phone') {
      if (!phoneTicket.value) return '请先完成手机号验证'
    } else if (!qqTicket.value) {
      return '请先完成 QQ 授权'
    }
    if (!form.qq) return '请填写 QQ 号'
    if (!/^\d{5,12}$/.test(form.qq)) return 'QQ 号格式不正确'
  } else {
    if (!/^1[3-9]\d{9}$/.test(form.phone)) return '请输入正确的 11 位手机号'
    if (!form.qq) return '请填写 QQ 号'
    if (!/^\d{5,12}$/.test(form.qq)) return '请填写有效的 QQ 号（5-12 位数字）'
    if (!captchaCode.value.trim()) return '请输入图形验证码'
  }
  return ''
}

async function handleSubmit() {
  if (submitting.value) return
  formError.value = ''
  const invalid = validate()
  if (invalid) {
    formError.value = invalid
    return
  }
  submitting.value = true
  try {
    const res: any = await registerApi({
      role: form.role,
      student_no: form.studentNo,
      password: form.password,
      name: form.name.trim(),
      college_id: form.collegeId,
      major_id: isTeacher.value ? 0 : form.majorId,
      tutor_id: isTeacher.value ? 0 : form.tutorId,
      // QQ 票据通道（含 App 原生授权）下手机号选填，后端已支持
      phone:
        thirdPartyAuthEnabled || qqNativeEnabled
          ? thirdPartyAuthEnabled && verifyMode.value === 'phone'
            ? phoneVerifiedPhone.value || null
            : null
          : form.phone,
      qq: form.qq || null,
      phone_ticket: thirdPartyAuthEnabled ? phoneTicket.value || null : null,
      qq_ticket: thirdPartyAuthEnabled || qqNativeEnabled ? qqTicket.value || null : null,
      // 图形验证码一次性使用，后端校验失败时需刷新重填
      captcha_id: captchaRequired.value ? captchaId.value : undefined,
      captcha_code: captchaRequired.value ? captchaCode.value : undefined,
    })
    if (!res?.access_token) throw new Error('响应异常')
    auth.login(res.access_token, res.user)
    saveQuickAccountFromLogin(res)
    sessionStorage.removeItem(DRAFT_KEY)
    ElMessage.success('注册成功，正在进入校园空间')
    router.replace(form.role === 'teacher' ? '/teacher' : '/student')
  } catch (e: any) {
    formError.value = e?.response?.data?.detail || '注册失败，请稍后重试'
    if (captchaRequired.value) await loadCaptcha()
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const ticket = typeof route.query.qq_ticket === 'string' ? route.query.qq_ticket : ''
  const nickname = typeof route.query.qq_nickname === 'string' ? route.query.qq_nickname : ''
  if ((thirdPartyAuthEnabled || qqNativeEnabled) && ticket) {
    qqTicket.value = ticket
    qqNickname.value = nickname
    verifyMode.value = 'qq'
    restoreDraft()
    step.value = 'form'
  }
  if ((thirdPartyAuthEnabled || qqNativeEnabled) && route.query.error === 'qq_occupied') {
    formError.value = '该 QQ 已绑定其他账号，请更换 QQ 或改用手机号验证'
    step.value = 'form'
  }

  await loadOptions()
  if (!isTeacher.value && form.collegeId && !majorList.value.length) {
    form.collegeId = 0
    form.majorId = 0
    form.tutorId = 0
  }
  await loadCaptcha()
})

onBeforeUnmount(() => {
  if (cooldownTimer) window.clearInterval(cooldownTimer)
})
</script>

<style scoped>
.reg-page {
  min-height: 100vh;
  padding: 22px 24px 40px;
  background: #f2f2f4;
  color: #16161a;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.reg-shell {
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
}

.reg-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
  border: none;
  background: transparent;
  color: #76767f;
  font-size: 13px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.reg-back-arrow {
  font-size: 17px;
  line-height: 1;
}

.reg-head {
  margin: 16px 0 4px;
}
.reg-head h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.4px;
}
.reg-head p {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #76767f;
}

/* ===== 第一步：身份选择 ===== */
.role-list {
  margin: clamp(22px, 4vh, 32px) 0 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.role-card {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 18px 16px;
  border: 1px solid #e8e8ec;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(20, 20, 25, 0.03);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.16s ease, transform 0.16s ease;
  -webkit-tap-highlight-color: transparent;
}
.role-card:active {
  border-color: #111111;
  transform: scale(0.99);
}
.role-icon {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: #f2f2f4;
  color: #111111;
  font-size: 16px;
  font-weight: 700;
}
.role-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.role-text strong {
  font-size: 15px;
  color: #16161a;
}
.role-text span {
  font-size: 12.5px;
  line-height: 1.5;
  color: #76767f;
}
.role-arrow {
  flex-shrink: 0;
  color: #a4a4ac;
  font-size: 20px;
}

/* 当前身份提示 + 切换 */
.role-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.role-summary-tag {
  padding: 5px 12px;
  border-radius: 999px;
  background: #111111;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
}
.role-swap {
  padding: 4px 0;
  border: none;
  background: transparent;
  color: #76767f;
  font-size: 12.5px;
  text-decoration: underline;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

/* 与登录页一致的扁平表单：无卡片背景，统一输入样式 */
.reg-form {
  margin-top: clamp(18px, 3vh, 26px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  position: relative;
}

/* 字段标签：必填标 *，选填单独标注；占位高度固定，避免有无标签时输入框上下错位 */
.field-label {
  display: flex;
  align-items: center;
  gap: 2px;
  min-height: 18px;
  margin: 0 4px 6px;
  font-size: 12.5px;
  line-height: 18px;
  color: #76767f;
}
.field-label .req {
  font-style: normal;
  color: #b42318;
  font-weight: 600;
}
.field-label .opt {
  margin-left: 2px;
  font-style: normal;
  font-size: 11.5px;
  color: #b0b0b8;
}
.field input {
  width: 100%;
  height: 54px;
  padding: 0 16px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(20, 20, 25, 0.03);
  color: #16161a;
  /* ≥16px：避免 iOS Safari 聚焦输入框时自动放大页面 */
  font-size: 16px;
  font-family: inherit;
  outline: none;
  appearance: none;
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

/* 密码输入行：按钮与 input 同处一个 flex 行，天然垂直居中 */
.pw-row {
  position: relative;
  display: flex;
  align-items: center;
}
.pw-row input {
  flex: 1;
  width: 100%;
  min-width: 0;
  /* 右侧给眼睛图标留位 */
  padding-right: 52px;
}
/* 密码可见性切换按钮：输入框内右侧，眼睛图标 */
.eye-btn {
  position: absolute;
  right: 9px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #a4a4ac;
  line-height: 0;
  cursor: pointer;
  transition: color 0.16s ease, background-color 0.16s ease;
  -webkit-tap-highlight-color: transparent;
}
.eye-btn:hover {
  color: #6f6f78;
  background: rgba(17, 17, 17, 0.04);
}
.eye-btn:active {
  color: #111111;
}
.eye-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(17, 17, 17, 0.08);
}
.eye-btn svg {
  display: block;
  flex: 0 0 auto;
  pointer-events: none;
}
/* 输入框右侧留白，避免长密码文字压到眼睛图标（.pw-row input 内已声明，此处兜底） */
.field input[id='reg-password'],
.field input[id='reg-confirm'] {
  padding-right: 52px;
}

/* ===== 图形验证码 / 短信验证码行 ===== */
.captcha-field,
.code-field {
  display: flex;
  align-items: center;
  gap: 8px;
}
.captcha-field input,
.code-field input {
  flex: 1;
  width: auto;
  min-width: 0;
}

.captcha-btn {
  flex-shrink: 0;
  width: 124px;
  height: 54px;
  padding: 0;
  overflow: hidden;
  border: 1px solid #e3e3e8;
  border-radius: 14px;
  background: #ffffff;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.captcha-btn img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.captcha-btn span {
  font-size: 12px;
  color: #76767f;
}

.code-btn {
  flex-shrink: 0;
  height: 54px;
  padding: 0 14px;
  border: 1px solid #e3e3e8;
  border-radius: 14px;
  background: #ffffff;
  color: #111111;
  font-size: 12.5px;
  white-space: nowrap;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.code-btn:disabled {
  color: #a4a4ac;
  cursor: default;
}

/* ===== 第三方验证通道（资质通过后启用） ===== */
.verify-tabs {
  display: flex;
  gap: 8px;
}
.verify-tab {
  flex: 1;
  height: 42px;
  border: 1px solid #e3e3e8;
  border-radius: 21px;
  background: #ffffff;
  color: #76767f;
  font-size: 13px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.verify-tab.active {
  border-color: #111111;
  background: #111111;
  color: #ffffff;
}

.verify-btn {
  width: 100%;
  height: 48px;
  border: 1px solid #111111;
  border-radius: 14px;
  background: #ffffff;
  color: #111111;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.verify-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.verify-note {
  margin: 0 0 10px;
  font-size: 12px;
  line-height: 1.6;
  color: #76767f;
}

.verified-badge {
  padding: 13px 16px;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(20, 20, 25, 0.03);
  color: #111111;
  font-size: 13px;
}

.submit-hint {
  margin: -2px 2px 0;
  font-size: 12px;
  line-height: 1.5;
  color: #76767f;
}
.submit-hint.error {
  color: #b42318;
}

.submit-btn {
  width: 100%;
  height: 54px;
  margin-top: 4px;
  border: none;
  border-radius: 27px;
  background: #111111;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.reg-foot {
  margin: 2px 0 0;
  text-align: center;
  font-size: 12.5px;
  color: #76767f;
}
.reg-link {
  color: #111111;
  font-weight: 600;
  text-decoration: none;
}

@media (min-width: 769px) {
  .reg-page {
    padding-top: 40px;
  }
}

/* ===== 移动端：整屏自滚 + 状态栏/手势条安全区 ===== */
@media (max-width: 767px) {
  .reg-page {
    padding: calc(env(safe-area-inset-top, 0px) + 14px) 18px calc(env(safe-area-inset-bottom, 0px) + 36px);
  }
  .reg-shell {
    max-width: 480px;
  }
  .reg-back {
    margin-bottom: 10px;
  }
}
</style>
