<template>
  <div class="callback-page">
    <div class="callback-card">
      <div class="callback-mark" :class="{ ok: state === 'success', err: state === 'error' }">
        <svg v-if="state === 'success'" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4.5 12.5l4.6 4.6L19.5 6.8" />
        </svg>
        <svg v-else-if="state === 'error'" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
        <span v-else class="spinner"></span>
      </div>

      <h1>{{ title }}</h1>
      <p class="callback-desc">{{ message }}</p>

      <button v-if="state !== 'loading'" type="button" class="callback-btn" @click="goBack">
        {{ state === 'success' ? '返回首页' : '返回登录' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { exchangeQqTicket, getCurrentIdentity } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { saveQuickAccountFromLogin } from '@/utils/quickLogin'
import { setUser } from '@/utils/token'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const state = ref<'loading' | 'success' | 'error'>('loading')
const message = ref('正在验证 QQ 授权信息…')

const errorMap: Record<string, string> = {
  not_configured: 'QQ 互联尚未配置，请联系管理员补充 QQ_APP_ID / QQ_APP_KEY / QQ_REDIRECT_URI',
  state_invalid: '授权信息已失效，请返回登录页重新发起 QQ 登录',
  exchange_failed: 'QQ 授权校验失败，请稍后重试',
  unbound: '该 QQ 尚未绑定校园账号，请先在个人中心完成 QQ 授权绑定',
  qq_occupied: '该 QQ 已绑定其他校园账号，请更换 QQ 或先解绑',
  forbidden: '该账号类型不支持 QQ 登录',
  access_denied: '你已取消 QQ 授权',
}

const title = computed(() => {
  if (state.value === 'loading') return '正在登录'
  return state.value === 'success' ? '登录成功' : 'QQ 登录未完成'
})

const roleMap: Record<string, string> = { student: '/student', teacher: '/teacher', admin: '/admin' }

onMounted(async () => {
  const error = typeof route.query.error === 'string' ? route.query.error : ''
  if (error) {
    state.value = 'error'
    message.value = errorMap[error] || 'QQ 登录失败，请返回登录页重试'
    return
  }

  // 绑定模式：后端已完成 openid 写入，这里刷新一次用户信息并回个人中心
  if (route.query.bind === 'ok') {
    try {
      const identity: any = await getCurrentIdentity()
      setUser(identity)
      auth.updateUser(identity)
      state.value = 'success'
      message.value = 'QQ 绑定成功，正在返回个人中心…'
      const target = `${roleMap[identity.role] || '/student'}/profile`
      window.setTimeout(() => router.replace(target), 600)
    } catch {
      state.value = 'error'
      message.value = 'QQ 绑定结果确认失败，请刷新个人中心查看'
    }
    return
  }

  const ticket = typeof route.query.ticket === 'string' ? route.query.ticket : ''
  if (!ticket) {
    state.value = 'error'
    message.value = '缺少 QQ 登录凭证，请返回登录页重新登录'
    return
  }

  try {
    const res: any = await exchangeQqTicket(ticket)
    if (!res?.access_token) throw new Error('响应异常')
    auth.login(res.access_token, res.user)
    saveQuickAccountFromLogin(res)
    state.value = 'success'
    message.value = 'QQ 授权验证通过，正在进入校园空间…'
    window.setTimeout(() => router.replace(roleMap[res.user.role] || '/student'), 600)
  } catch (e: any) {
    state.value = 'error'
    message.value = e?.response?.data?.detail || 'QQ 登录失败，请返回登录页重试'
  }
})

function goBack() {
  if (state.value === 'success' && auth.user?.role) {
    router.replace(roleMap[auth.user.role] || '/student')
    return
  }
  router.replace('/login')
}
</script>

<style scoped>
.callback-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #f2f2f4;
  color: #16161a;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.callback-card {
  width: 100%;
  max-width: 360px;
  padding: 34px 26px 28px;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(20, 20, 25, 0.08);
  text-align: center;
}

.callback-mark {
  width: 52px;
  height: 52px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f4f4f6;
  color: #111111;
}
.callback-mark.ok {
  background: #111111;
  color: #ffffff;
}
.callback-mark.err {
  background: #f4f4f6;
  color: #111111;
}

.spinner {
  width: 22px;
  height: 22px;
  border: 2px solid #d8d8de;
  border-top-color: #111111;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.callback-card h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.callback-desc {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #76767f;
}

.callback-btn {
  width: 100%;
  height: 46px;
  margin-top: 24px;
  border: none;
  border-radius: 23px;
  background: #111111;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
}
.callback-btn:active {
  transform: scale(0.99);
}
</style>
