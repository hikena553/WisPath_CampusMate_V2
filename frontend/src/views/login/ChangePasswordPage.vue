<template>
  <div class="pwd-page">
    <div class="pwd-card">
      <div class="pwd-brand">
        <span class="pwd-tag">WisPath CampusMate</span>
        <h1 class="pwd-title">{{ isInitial ? '修改初始密码' : '修改密码' }}</h1>
        <p class="pwd-tip">
          <template v-if="isInitial">
            检测到当前账号仍在使用初始密码。为保障账号安全，
            <b>建议尽快修改</b>（不影响其他功能使用）。
          </template>
          <template v-else>
            定期修改密码可以更好地保护账号安全，新密码需与原密码不同。
          </template>
        </p>
      </div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="旧密码" required>
          <el-input v-model="form.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="form.new_password" type="password" show-password placeholder="至少 8 位，需同时包含字母和数字" />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input
            v-model="form.confirm_password"
            type="password"
            show-password
            placeholder="再次输入新密码"
          />
        </el-form-item>
        <el-form-item label="验证码" required>
          <div class="captcha-row">
            <el-input
              v-model="form.captcha_code"
              maxlength="4"
              placeholder="输入图中字符"
              @keyup.enter="submit"
            />
            <button
              type="button"
              class="captcha-img-btn"
              :class="{ loading: captchaLoading }"
              aria-label="刷新验证码"
              :disabled="captchaLoading"
              @click="loadCaptcha"
            >
              <img v-if="captcha?.image" :src="captcha.image" alt="验证码" />
              <span v-else>{{ captchaLoading ? '加载中' : '点击获取' }}</span>
            </button>
          </div>
        </el-form-item>
      </el-form>

      <el-button type="primary" class="pwd-submit" :loading="submitting" @click="submit">
        确认修改
      </el-button>

      <div class="pwd-foot">
        <span class="pwd-user">{{ auth.userName || '当前账号' }}</span>
        <el-button link type="primary" @click="onLogout">退出登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/user'
import { getCaptcha } from '@/api/auth'
import type { CaptchaChallenge } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { confirmLogout } from '@/utils/logout'

const router = useRouter()
const auth = useAuthStore()

const submitting = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm_password: '', captcha_code: '' })
const captcha = ref<CaptchaChallenge | null>(null)
const captchaLoading = ref(false)
/** 仅在账号仍未修改过初始密码时展示对应提示 */
const isInitial = computed(() => auth.user?.password_changed === false)

onMounted(() => { loadCaptcha() })

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await getCaptcha()
    form.captcha_code = ''
  } catch {
    captcha.value = null
  } finally {
    captchaLoading.value = false
  }
}

const roleHome: Record<string, string> = { teacher: '/teacher', admin: '/admin', student: '/student' }

/** 与后端 /api/auth/change-password 的校验规则保持一致，避免提交后才报错 */
function validate(): string | null {
  if (!form.old_password || !form.new_password || !form.confirm_password || !form.captcha_code) {
    return '请填写所有字段'
  }
  if (form.new_password !== form.confirm_password) return '两次输入的新密码不一致'
  if (form.new_password.length < 8) return '新密码至少 8 位'
  if (!/[A-Za-z]/.test(form.new_password) || !/\d/.test(form.new_password)) return '新密码必须同时包含字母和数字'
  if (form.new_password === form.old_password) return '新密码不能与旧密码相同'
  return null
}

async function submit() {
  const invalid = validate()
  if (invalid) {
    ElMessage.warning(invalid)
    return
  }
  if (!captcha.value) {
    ElMessage.warning('验证码未加载，请点击图片重试')
    return
  }
  submitting.value = true
  try {
    await changePassword(form.old_password, form.new_password, captcha.value.captcha_id, form.captcha_code)
    // 同步缓存里的 password_changed，避免路由守卫再次把人送回本页
    if (auth.user) auth.updateUser({ ...auth.user, password_changed: true })
    ElMessage.success('密码修改成功')
    router.replace(roleHome[auth.user?.role || 'student'] || '/student')
  } catch (e: any) {
    const detail = e?.response?.data?.detail || '修改失败，请重试'
    ElMessage.error(detail)
    if (detail.includes('验证码')) loadCaptcha()
  } finally {
    submitting.value = false
  }
}

function onLogout() {
  confirmLogout()
}
</script>

<style scoped>
.pwd-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #0a0a2e 0%, #1a1a4e 30%, #0d2137 70%, #0a0a2e 100%);
}

.pwd-card {
  width: 100%;
  max-width: 420px;
  padding: 32px 28px 20px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
}

.pwd-tag {
  display: inline-block;
  padding: 4px 12px;
  margin-bottom: 14px;
  border-radius: 20px;
  font-size: 11px;
  letter-spacing: 2px;
  color: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.08);
}

.pwd-title {
  margin: 0 0 10px;
  font-size: 22px;
  color: #fff;
}

.pwd-tip {
  margin: 0 0 22px;
  font-size: 13px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.72);
}

.pwd-tip b {
  color: #ffd54d;
  font-weight: 600;
}

.pwd-card :deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  padding-bottom: 4px;
}

.pwd-card :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  box-shadow: none;
}

.pwd-card :deep(.el-input__inner) {
  color: #fff;
}

.pwd-card :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.42);
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.captcha-row .el-input { flex: 1; }
.captcha-img-btn {
  flex-shrink: 0;
  width: 108px;
  height: 40px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s ease;
}
.captcha-img-btn:hover:not(:disabled) { opacity: 0.85; }
.captcha-img-btn:disabled { cursor: not-allowed; opacity: 0.6; }
.captcha-img-btn img { width: 100%; height: 100%; object-fit: fill; display: block; }
.captcha-img-btn span { font-size: 13px; color: rgba(255, 255, 255, 0.7); }

.pwd-submit {
  width: 100%;
  height: 46px;
  margin-top: 6px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  background: linear-gradient(135deg, #409eff, #6366f1);
}

.pwd-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.35);
}

.pwd-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.pwd-user {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>