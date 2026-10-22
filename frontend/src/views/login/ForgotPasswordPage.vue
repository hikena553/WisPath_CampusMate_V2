<template>
  <div class="forgot-page">
    <div class="forgot-body">
      <button type="button" class="back-btn" @click="router.push('/login')">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 5l-7 7 7 7" />
        </svg>
        <span>返回登录</span>
      </button>

      <!-- 已提交：展示等待 / 处理结果 -->
      <template v-if="status">
        <div class="status-head">
          <span class="status-icon" :class="status.status">
            <svg v-if="status.status === 'pending'" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7.5V12l3 1.8" />
            </svg>
            <svg v-else-if="status.status === 'reset'" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4.5 12.5l4.8 4.8L19.5 7" />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v5" />
              <path d="M12 16h.01" />
            </svg>
          </span>
          <h1>{{ statusTitle }}</h1>
          <p class="status-desc">{{ status.message }}</p>
        </div>

        <dl class="status-meta">
          <div>
            <dt>申请账号</dt>
            <dd>{{ statusUsername }}</dd>
          </div>
          <div>
            <dt>提交时间</dt>
            <dd>{{ formatTime(status.submitted_at) }}</dd>
          </div>
          <div>
            <dt>当前状态</dt>
            <dd :class="['state', status.status]">{{ statusLabel }}</dd>
          </div>
        </dl>

        <p v-if="status.status === 'pending'" class="tip">
          管理员处理后会通过站内消息通知你。预计 {{ remaining }} 小时内可完成，届时请使用初始密码
          <b>123456</b> 登录并立即修改。
        </p>

        <div class="actions">
          <button type="button" class="btn-primary" @click="router.push('/login')">
            {{ status.status === 'reset' ? '去登录' : '返回登录' }}
          </button>
          <button
            v-if="status.status === 'pending'"
            type="button"
            class="btn-ghost"
            :disabled="refreshing"
            @click="refreshStatus"
          >
            {{ refreshing ? '查询中…' : '刷新进度' }}
          </button>
        </div>
      </template>

      <!-- 未提交：身份核验表单 -->
      <template v-else>
        <header class="intro">
          <h1>找回密码</h1>
          <p>核验在校身份后，系统自动通知管理员重置密码</p>
        </header>

        <ol class="steps">
          <li class="on"><i>1</i><span>身份核验</span></li>
          <li><i>2</i><span>管理员处理</span></li>
          <li><i>3</i><span>重置完成</span></li>
        </ol>

        <form class="form" @submit.prevent="handleSubmit">
          <div class="group">
            <div class="row" :class="{ invalid: fieldError.username }">
              <label for="fp-username">学号 / 工号 <i class="req">*</i></label>
              <input
                id="fp-username"
                v-model.trim="form.username"
                type="text"
                placeholder="请输入学号或工号"
                autocomplete="username"
                @input="clearFieldError('username')"
              />
              <p v-if="fieldError.username" class="field-error">{{ fieldError.username }}</p>
            </div>

            <div class="row" :class="{ invalid: fieldError.name }">
              <label for="fp-name">姓名 <i class="req">*</i></label>
              <input
                id="fp-name"
                v-model.trim="form.name"
                type="text"
                placeholder="请输入真实姓名"
                autocomplete="name"
                @input="clearFieldError('name')"
              />
              <p v-if="fieldError.name" class="field-error">{{ fieldError.name }}</p>
            </div>

            <div class="row" :class="{ invalid: fieldError.contact }">
              <label for="fp-contact">已绑定的手机号 / QQ <i class="req">*</i></label>
              <input
                id="fp-contact"
                v-model.trim="form.contact"
                type="text"
                placeholder="与个人资料中绑定的一致"
                @input="clearFieldError('contact')"
              />
              <p v-if="fieldError.contact" class="field-error">{{ fieldError.contact }}</p>
            </div>

            <div class="row" :class="{ invalid: fieldError.captcha }">
              <label for="fp-captcha">验证码 <i class="req">*</i></label>
              <div class="captcha-row">
                <input
                  id="fp-captcha"
                  v-model.trim="form.captcha"
                  type="text"
                  inputmode="text"
                  maxlength="4"
                  placeholder="输入 4 位字符"
                  autocomplete="off"
                  @input="clearFieldError('captcha')"
                />
                <button
                  type="button"
                  class="captcha-img"
                  aria-label="刷新验证码"
                  :disabled="captchaLoading"
                  @click="loadCaptcha"
                >
                  <img v-if="captcha?.image" :src="captcha.image" alt="验证码" />
                  <span v-else>{{ captchaLoading ? '加载中' : '点击获取' }}</span>
                </button>
              </div>
              <p v-if="fieldError.captcha" class="field-error">{{ fieldError.captcha }}</p>
              <p v-else class="field-hint">看不清？点击右侧图片刷新</p>
            </div>

            <div class="row">
              <label for="fp-reason">补充说明 <em>选填</em></label>
              <textarea
                id="fp-reason"
                v-model.trim="form.reason"
                rows="2"
                placeholder="例如：原密码遗忘，需要协助重置"
              />
            </div>
          </div>

          <p v-if="submitError" class="submit-error">{{ submitError }}</p>

          <button type="submit" class="btn-primary" :disabled="submitting">
            {{ submitting ? '核验中…' : '提交申请' }}
          </button>
        </form>

        <p class="tip">
          未绑定手机号或 QQ 时无法在线核验，请联系辅导员或管理员处理。管理员通过后密码将重置为初始密码
          <b>123456</b>。
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  forgotPasswordApi,
  getCaptcha,
  getForgotPasswordStatus,
  type CaptchaChallenge,
  type ForgotPasswordStatus,
} from '@/api/auth'
import { loadPendingPasswordReset, savePendingPasswordReset } from '@/utils/passwordReset'

const route = useRoute()
const router = useRouter()

const form = reactive({ username: '', name: '', contact: '', reason: '', captcha: '' })
const fieldError = reactive({ username: '', name: '', contact: '', captcha: '' })
const submitError = ref('')
const submitting = ref(false)
const refreshing = ref(false)
const status = ref<ForgotPasswordStatus | null>(null)
const statusUsername = ref('')
const captcha = ref<CaptchaChallenge | null>(null)
const captchaLoading = ref(false)

let pollTimer: number | undefined

const statusTitle = computed(() => {
  if (!status.value) return ''
  if (status.value.status === 'reset') return '密码已重置'
  if (status.value.status === 'rejected') return '申请未通过'
  return '已通知管理员'
})

const statusLabel = computed(() => {
  if (!status.value) return ''
  return { pending: '等待处理', reset: '已重置', rejected: '已驳回' }[status.value.status]
})

const remaining = computed(() => status.value?.eta_hours ?? 2)

function formatTime(value: string): string {
  if (!value) return '—'
  const d = new Date(value)
  if (!Number.isFinite(d.getTime())) return '—'
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function clearFieldError(key: keyof typeof fieldError) {
  fieldError[key] = ''
  submitError.value = ''
}

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await getCaptcha()
    form.captcha = ''
    fieldError.captcha = ''
  } catch {
    captcha.value = null
  } finally {
    captchaLoading.value = false
  }
}

function validate(): boolean {
  let ok = true
  fieldError.username = form.username ? '' : '请输入学号 / 工号'
  fieldError.name = form.name ? '' : '请输入姓名'
  fieldError.contact = form.contact ? '' : '请输入已绑定的手机号或 QQ'
  fieldError.captcha = form.captcha ? '' : '请输入验证码'
  for (const message of Object.values(fieldError)) {
    if (message) ok = false
  }
  return ok
}

function applyStatus(data: ForgotPasswordStatus, username: string) {
  status.value = data
  statusUsername.value = username
  if (data.status === 'pending') {
    savePendingPasswordReset({
      id: data.id,
      username,
      submittedAt: data.submitted_at,
      etaHours: data.eta_hours,
    })
  }
}

async function handleSubmit() {
  submitError.value = ''
  if (!validate()) return
  if (!captcha.value) {
    submitError.value = '验证码未加载，请点击图片重试'
    return
  }
  submitting.value = true
  try {
    const data = await forgotPasswordApi({
      username: form.username,
      name: form.name,
      contact: form.contact,
      reason: form.reason || undefined,
      captcha_id: captcha.value.captcha_id,
      captcha: form.captcha,
    })
    applyStatus(data as unknown as ForgotPasswordStatus, form.username)
    stopPolling()
    startPolling()
  } catch (e: any) {
    const detail = e?.response?.data?.detail || '提交失败，请稍后重试'
    submitError.value = detail
    if (detail.includes('验证码')) {
      fieldError.captcha = detail
    } else if (detail.includes('学号') || detail.includes('工号')) {
      fieldError.username = detail
    } else if (detail.includes('姓名')) {
      fieldError.name = detail
    } else if (detail.includes('手机号') || detail.includes('QQ')) {
      fieldError.contact = detail
    }
    // 验证码一次性使用，失败后必须刷新
    await loadCaptcha()
  } finally {
    submitting.value = false
  }
}

async function refreshStatus() {
  if (!status.value) return
  refreshing.value = true
  try {
    const data = await getForgotPasswordStatus(status.value.id, statusUsername.value)
    applyStatus(data as unknown as ForgotPasswordStatus, statusUsername.value)
  } catch {
    // 网络异常时保留现有状态，不打断等待
  } finally {
    refreshing.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(() => {
    if (status.value?.status === 'pending') void refreshStatus()
    else stopPolling()
  }, 30_000)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = undefined
  }
}

onMounted(async () => {
  const id = Number(route.query.id)
  const username = String(route.query.username || '')
  if (id && username) {
    statusUsername.value = username
    await refreshStatus()
    if (status.value?.status === 'pending') startPolling()
    return
  }
  const pending = loadPendingPasswordReset()
  if (pending) {
    status.value = {
      id: pending.id,
      status: 'pending',
      submitted_at: pending.submittedAt,
      eta_hours: pending.etaHours,
      message: `已通知管理员，预计 ${pending.etaHours} 小时内完成重置，请稍后尝试重新登录`,
    }
    statusUsername.value = pending.username
    startPolling()
    return
  }
  await loadCaptcha()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.forgot-page {
  position: fixed;
  inset: 0;
  overflow-y: auto;
  display: flex;
  justify-content: center;
  background: #f2f2f4;
  color: #16161a;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.forgot-body {
  width: 100%;
  max-width: 400px;
  padding: calc(env(safe-area-inset-top) + 10px) 22px calc(env(safe-area-inset-bottom) + 28px);
  display: flex;
  flex-direction: column;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  align-self: flex-start;
  padding: 6px 8px 6px 0;
  border: none;
  background: transparent;
  color: #6f6f78;
  font-size: 13px;
  cursor: pointer;
}
.back-btn:active {
  color: #111111;
}

.intro {
  margin-top: 12px;
}
.intro h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
.intro p {
  margin: 9px 0 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: #8a8a8f;
}

/* ===== 步骤条 ===== */
.steps {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}
.steps li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #a4a4ac;
  white-space: nowrap;
}
.steps li + li::before {
  content: '';
  width: 14px;
  height: 1px;
  margin-right: 1px;
  background: #dcdce1;
}
.steps i {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e6e6ea;
  color: #8a8a8f;
  font-style: normal;
  font-size: 10.5px;
  font-weight: 600;
}
.steps li.on {
  color: #16161a;
  font-weight: 600;
}
.steps li.on i {
  background: #111111;
  color: #fff;
}

/* ===== 表单：单张白卡分组，弱化输入框边框 ===== */
.form {
  margin-top: 18px;
}

.group {
  padding: 0 20px;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(20, 20, 25, 0.03);
}

.row {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 17px 0 18px;
}
.row + .row {
  border-top: 1px solid #f2f2f4;
}

.row label {
  font-size: 13px;
  color: #8a8a8f;
}
.row label .req {
  margin-left: 2px;
  font-style: normal;
  color: #b42318;
  font-weight: 600;
}
.row label em {
  margin-left: 5px;
  font-style: normal;
  font-size: 12px;
  color: #b0b0b8;
}

.row input,
.row textarea {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: #16161a;
  font-size: 17px;
  font-family: inherit;
  outline: none;
  resize: none;
}
.row textarea {
  font-size: 15px;
  line-height: 1.55;
}
.row input::placeholder,
.row textarea::placeholder {
  color: #a4a4ac;
  font-size: 15px;
}
.row.invalid input {
  color: #b42318;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.captcha-row input {
  flex: 1;
  min-width: 0;
  letter-spacing: 3px;
}
.captcha-row input::placeholder {
  letter-spacing: 0;
}

.captcha-img {
  width: 120px;
  height: 48px;
  flex-shrink: 0;
  padding: 0;
  border: 1px solid #ececf0;
  border-radius: 10px;
  background: #f6f6f7;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9a9aa0;
  font-size: 12px;
  cursor: pointer;
}
.captcha-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.captcha-img:disabled {
  opacity: 0.7;
  cursor: default;
}

.field-error {
  margin: 1px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #b42318;
}
.field-hint {
  margin: 1px 0 0;
  font-size: 11.5px;
  color: #a8a8ae;
}

.submit-error {
  margin: 16px 0 0;
  padding: 12px 14px;
  border-radius: 10px;
  background: #ffffff;
  font-size: 12.5px;
  line-height: 1.6;
  color: #b42318;
}

.btn-primary {
  width: 100%;
  height: 56px;
  margin-top: 22px;
  border: none;
  border-radius: 28px;
  background: #111111;
  color: #fff;
  font-size: 16.5px;
  font-weight: 600;
  letter-spacing: 1.5px;
  cursor: pointer;
  transition: background 0.16s ease, transform 0.16s ease;
}
.btn-primary:active:not(:disabled) {
  background: #000;
  transform: scale(0.99);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn-ghost {
  width: 100%;
  height: 50px;
  margin-top: 12px;
  border: 1px solid #e0e0e5;
  border-radius: 25px;
  background: transparent;
  color: #6f6f78;
  font-size: 15px;
  cursor: pointer;
}
.btn-ghost:disabled {
  opacity: 0.6;
  cursor: default;
}

.tip {
  margin: 18px 0 0;
  font-size: 12px;
  line-height: 1.75;
  color: #9a9aa3;
  text-align: center;
}
.tip b {
  color: #6f6f78;
  font-weight: 600;
}

/* ===== 结果态 ===== */
.status-head {
  margin-top: 34px;
  text-align: center;
}
.status-icon {
  width: 62px;
  height: 62px;
  margin: 0 auto;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.status-icon.pending {
  background: #ffffff;
  color: #111111;
}
.status-icon.reset {
  background: #ffffff;
  color: #16a34a;
}
.status-icon.rejected {
  background: #ffffff;
  color: #76767f;
}
.status-head h1 {
  margin: 18px 0 0;
  font-size: 22px;
  font-weight: 700;
}
.status-desc {
  margin: 10px auto 0;
  max-width: 320px;
  font-size: 13px;
  line-height: 1.7;
  color: #76767f;
}

.status-meta {
  margin: 24px 0 0;
  padding: 4px 16px;
  border-radius: 16px;
  background: #ffffff;
}
.status-meta > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 13px 0;
}
.status-meta > div + div {
  border-top: 1px solid #f2f2f4;
}
.status-meta dt {
  font-size: 12.5px;
  color: #8a8a8f;
}
.status-meta dd {
  margin: 0;
  font-size: 13px;
  color: #16161a;
}
.status-meta dd.state {
  font-weight: 600;
}
.status-meta dd.state.pending {
  color: #111111;
}
.status-meta dd.state.reset {
  color: #16a34a;
}

.actions {
  margin-top: 22px;
  display: flex;
  flex-direction: column;
}

/* ===== 桌面端：居中白色卡片 + 放大表单，适配宽屏 ===== */
@media (min-width: 900px) {
  .forgot-page {
    align-items: center;
    padding: 48px 24px;
    background:
      radial-gradient(75% 55% at 12% 0%, #ffffff 0%, rgba(255, 255, 255, 0) 62%),
      #f2f2f4;
  }

  .forgot-body {
    max-width: 440px;
    padding: 26px 28px 28px;
    border-radius: 22px;
    background: #ffffff;
    box-shadow: 0 24px 60px rgba(17, 17, 17, 0.07), 0 2px 6px rgba(17, 17, 17, 0.03);
  }

  .intro h1 {
    font-size: 24px;
  }
  .intro p {
    margin-top: 7px;
    font-size: 12.5px;
  }

  .steps {
    margin-top: 16px;
  }
  .steps li {
    font-size: 11.5px;
  }

  .form {
    margin-top: 16px;
  }
  .group {
    background: #fafafb;
    border: 1px solid #f1f1f4;
  }
  .row {
    padding: 13px 0 14px;
  }
  .row label {
    font-size: 12.5px;
  }
  .row input {
    font-size: 16px;
  }
  .row input::placeholder {
    font-size: 14.5px;
  }
  .captcha-img {
    width: 110px;
    height: 44px;
  }

  .btn-primary {
    height: 50px;
    margin-top: 18px;
    font-size: 15.5px;
  }

  .tip {
    margin-top: 14px;
    font-size: 11.5px;
  }

  .status-meta dt {
    font-size: 12.5px;
  }
  .status-meta dd {
    font-size: 13px;
  }
  .status-meta > div {
    padding: 12px 0;
  }
}
</style>
