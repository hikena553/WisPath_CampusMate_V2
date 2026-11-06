<template>
  <div class="qlb-group">
    <div class="qlb-title">快捷登录</div>
    <div class="qlb-list">
      <button type="button" class="qlb-row" @click="openPhoneSheet">
        <span class="qlb-label">手机号登录</span>
        <span class="qlb-value" :class="{ muted: !userPhone }">
          {{ userPhone ? `${maskPhone(userPhone)} · 已开启` : '未绑定' }}
        </span>
        <span class="qlb-arrow">›</span>
      </button>

      <button type="button" class="qlb-row" @click="handleQqRow">
        <span class="qlb-label">QQ 登录</span>
        <span class="qlb-value" :class="{ muted: !qqBound }">{{ qqDesc }}</span>
        <span class="qlb-arrow">›</span>
      </button>
    </div>
    <p class="qlb-note">手机号与 QQ 仅用于登录验证，不会被他人看到</p>
  </div>

  <ActionSheet v-model="phoneSheet" title="绑定手机号" width="360px">
    <div class="qlb-form">
      <input
        v-model.trim="phoneInput"
        class="qlb-input"
        type="tel"
        inputmode="numeric"
        maxlength="11"
        placeholder="请输入 11 位手机号"
      />
      <div class="qlb-code-row">
        <input
          v-model.trim="codeInput"
          class="qlb-input"
          type="text"
          inputmode="numeric"
          maxlength="6"
          placeholder="短信验证码"
        />
        <button type="button" class="qlb-code-btn" :disabled="cooldown > 0 || sending" @click="sendCode">
          {{ sending ? '发送中…' : cooldown > 0 ? `${cooldown}s 后重发` : '获取验证码' }}
        </button>
      </div>
      <p class="qlb-hint" :class="{ error: !!error, ok: !error && !!hint }">
        {{ error || hint || '绑定后可使用「手机号 + 短信验证码」登录' }}
      </p>
    </div>
    <template #footer>
      <div class="qlb-foot">
        <button type="button" class="qlb-btn ghost" @click="phoneSheet = false">取消</button>
        <button type="button" class="qlb-btn solid" :disabled="binding" @click="confirmBind">
          {{ binding ? '绑定中…' : '验证并绑定' }}
        </button>
      </div>
    </template>
  </ActionSheet>

  <ActionSheet v-model="qqSheet" title="QQ 授权登录" width="360px">
    <div class="qlb-form">
      <p class="qlb-qq-state">已绑定 {{ auth.user?.qq_nickname || 'QQ 账号' }}</p>
      <p class="qlb-hint">重新授权会用新的 QQ 覆盖当前绑定；解除后将无法使用 QQ 登录</p>
    </div>
    <template #footer>
      <div class="qlb-foot three">
        <button type="button" class="qlb-btn ghost" @click="qqSheet = false">取消</button>
        <button type="button" class="qlb-btn ghost" :disabled="authorizing" @click="handleQqReauth">
          {{ authorizing ? '授权中…' : '重新授权' }}
        </button>
        <button type="button" class="qlb-btn solid" :disabled="unbinding" @click="handleUnbind">
          {{ unbinding ? '解绑中…' : '解除绑定' }}
        </button>
      </div>
    </template>
  </ActionSheet>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ActionSheet from '@/components/common/ActionSheet.vue'
import { bindPhoneApi, getQqAuthorizeUrl, qqMobileBindApi, sendSmsCode, unbindQqApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { syncQuickAccount } from '@/utils/quickLogin'
import { QQ_NATIVE_AUTH_ENABLED } from '@/utils/features'
import { qqNativeAuthAvailable, qqNativeLogin } from '@/utils/qqAuth'
import type { UserInfo } from '@/types'

defineOptions({ name: 'QuickLoginBind' })

const emit = defineEmits<{
  (e: 'phone-bound', user: UserInfo): void
}>()

const auth = useAuthStore()

/** QQ 互联移动端（App 壳内原生 SDK 授权），浏览器恒为 false */
const qqNativeEnabled = QQ_NATIVE_AUTH_ENABLED && qqNativeAuthAvailable()

const userPhone = computed(() => auth.user?.phone || '')
const qqBound = computed(() => !!auth.user?.qq_bound)
const qqDesc = computed(() => {
  if (!qqBound.value) return '未绑定'
  const nickname = auth.user?.qq_nickname
  return nickname ? `已绑定 · ${nickname}` : '已绑定'
})

const phoneSheet = ref(false)
const qqSheet = ref(false)
const phoneInput = ref('')
const codeInput = ref('')
const error = ref('')
const hint = ref('')
const sending = ref(false)
const binding = ref(false)
const authorizing = ref(false)
const unbinding = ref(false)
const cooldown = ref(0)
let cooldownTimer: number | undefined

function maskPhone(phone: string) {
  return phone.length === 11 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone
}

function openPhoneSheet() {
  phoneInput.value = userPhone.value
  codeInput.value = ''
  error.value = ''
  hint.value = ''
  phoneSheet.value = true
}

function handleQqRow() {
  if (qqBound.value) {
    qqSheet.value = true
    return
  }
  if (qqNativeEnabled) {
    handleQqNativeBind()
    return
  }
  startQqAuth('bind')
}

/** 绑定态的「重新授权」入口：App 内走原生，浏览器走网站应用回跳 */
function handleQqReauth() {
  if (qqNativeEnabled) {
    handleQqNativeBind()
    return
  }
  startQqAuth('bind')
}

async function startQqAuth(mode: 'login' | 'bind') {
  if (authorizing.value) return
  authorizing.value = true
  try {
    const res: any = await getQqAuthorizeUrl(mode)
    if (!res?.url) throw new Error('响应异常')
    window.location.href = res.url
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.info(detail || 'QQ 授权暂不可用，请稍后重试')
  } finally {
    authorizing.value = false
  }
}

/** App 内：拉起手机 QQ 授权 → 后端核验后绑定到当前账号 */
async function handleQqNativeBind() {
  if (authorizing.value) return
  authorizing.value = true
  try {
    const session = await qqNativeLogin()
    const updated = await qqMobileBindApi(session.accessToken, session.openId)
    auth.updateUser(updated)
    syncQuickAccount(updated)
    ElMessage.success('QQ 绑定成功')
    qqSheet.value = false
  } catch (e: any) {
    const code = String(e?.message || '')
    if (code === 'QQ_NOT_INSTALLED') {
      ElMessage.warning('未检测到手机 QQ，请安装后重试')
    } else if (code !== 'USER_CANCEL') {
      ElMessage.warning(e?.response?.data?.detail || 'QQ 授权失败，请稍后重试')
    }
  } finally {
    authorizing.value = false
  }
}

async function sendCode() {
  if (sending.value || cooldown.value > 0) return
  error.value = ''
  hint.value = ''
  if (!/^1[3-9]\d{9}$/.test(phoneInput.value)) {
    error.value = '请输入正确的 11 位手机号'
    return
  }
  sending.value = true
  try {
    const res: any = await sendSmsCode(phoneInput.value, 'bind')
    if (res?.debug_code) {
      codeInput.value = res.debug_code
      hint.value = `演示环境验证码：${res.debug_code}`
    } else {
      hint.value = '验证码已发送'
    }
    startCooldown(Number(res?.cooldown) || 60)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '验证码发送失败，请稍后重试'
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

async function confirmBind() {
  if (binding.value) return
  error.value = ''
  if (!/^1[3-9]\d{9}$/.test(phoneInput.value)) {
    error.value = '请输入正确的 11 位手机号'
    return
  }
  if (!/^\d{6}$/.test(codeInput.value)) {
    error.value = '请输入 6 位短信验证码'
    return
  }
  binding.value = true
  try {
    const updated = await bindPhoneApi(phoneInput.value, codeInput.value)
    auth.updateUser(updated)
    syncQuickAccount(updated)
    emit('phone-bound', updated)
    ElMessage.success('手机号绑定成功')
    phoneSheet.value = false
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '绑定失败，请重试'
  } finally {
    binding.value = false
  }
}

async function handleUnbind() {
  if (unbinding.value) return
  unbinding.value = true
  try {
    const updated = await unbindQqApi()
    auth.updateUser(updated)
    syncQuickAccount(updated)
    ElMessage.success('已解除 QQ 绑定')
    qqSheet.value = false
  } catch (e: any) {
    ElMessage.warning(e?.response?.data?.detail || '解绑失败，请稍后重试')
  } finally {
    unbinding.value = false
  }
}

onBeforeUnmount(() => {
  if (cooldownTimer) window.clearInterval(cooldownTimer)
})
</script>

<style scoped>
.qlb-group {
  margin-top: 14px;
}

.qlb-title {
  padding: 0 14px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #a4a4ac;
  letter-spacing: 0.3px;
}

.qlb-list {
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(20, 20, 25, 0.03);
}

.qlb-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.qlb-row + .qlb-row {
  border-top: 1px solid #f0f0f3;
}
.qlb-row:active {
  background: #fafafb;
}

.qlb-label {
  flex-shrink: 0;
  font-size: 13.5px;
  color: #16161a;
}

.qlb-value {
  flex: 1;
  text-align: right;
  font-size: 12.5px;
  color: #16161a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.qlb-value.muted {
  color: #a4a4ac;
}

.qlb-arrow {
  flex-shrink: 0;
  color: #c0c0c8;
  font-size: 15px;
  line-height: 1;
}

.qlb-note {
  margin: 8px 0 0;
  padding: 0 14px;
  font-size: 11.5px;
  line-height: 1.5;
  color: #a4a4ac;
}

/* ===== 表单 ===== */
.qlb-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.qlb-input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 1px solid #e8e8ec;
  border-radius: 12px;
  background: #ffffff;
  color: #16161a;
  font-size: 15px;
  font-family: inherit;
  outline: none;
}
.qlb-input:focus {
  border-color: #111111;
}

.qlb-code-row {
  display: flex;
  gap: 8px;
}
.qlb-code-row .qlb-input {
  flex: 1;
  min-width: 0;
}

.qlb-code-btn {
  flex-shrink: 0;
  height: 44px;
  padding: 0 12px;
  border: 1px solid #e8e8ec;
  border-radius: 12px;
  background: #ffffff;
  color: #111111;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}
.qlb-code-btn:disabled {
  color: #a4a4ac;
  cursor: default;
}

.qlb-hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: #76767f;
}
.qlb-hint.error {
  color: #b42318;
}
.qlb-hint.ok {
  color: #111111;
}

.qlb-qq-state {
  margin: 0;
  font-size: 14px;
  color: #16161a;
}

.qlb-foot {
  display: flex;
  gap: 8px;
}
.qlb-btn {
  flex: 1;
  height: 40px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
}
.qlb-btn.ghost {
  border: 1px solid #e3e3e8;
  background: #ffffff;
  color: #16161a;
}
.qlb-btn.solid {
  border: 1px solid #111111;
  background: #111111;
  color: #ffffff;
}
.qlb-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
