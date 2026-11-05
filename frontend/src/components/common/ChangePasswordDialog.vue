<template>
  <!-- 修改密码（旧密码 / 新密码 / 确认新密码 / 图形验证码） -->
  <ActionSheet
    :model-value="modelValue"
    title="修改密码"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="onVisibleChange"
  >
    <el-form :model="form" label-width="96px" @submit.prevent>
      <el-form-item label="旧密码" required>
        <el-input v-model="form.old_password" type="password" show-password placeholder="请输入旧密码" />
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
    <template #footer>
      <el-button @click="onVisibleChange(false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </ActionSheet>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import ActionSheet from '@/components/common/ActionSheet.vue'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/user'
import { getCaptcha } from '@/api/auth'
import type { CaptchaChallenge } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const auth = useAuthStore()
const submitting = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm_password: '', captcha_code: '' })
const captcha = ref<CaptchaChallenge | null>(null)
const captchaLoading = ref(false)

// 打开弹窗时加载验证码，关闭时清空
watch(() => props.modelValue, (v) => {
  if (v) { loadCaptcha() } else { reset() }
})

function reset() {
  form.old_password = ''
  form.new_password = ''
  form.confirm_password = ''
  form.captcha_code = ''
  captcha.value = null
}

function onVisibleChange(visible: boolean) {
  emit('update:modelValue', visible)
}

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

/** 与后端校验规则保持一致，避免提交后才报错 */
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
    if (auth.user) auth.updateUser({ ...auth.user, password_changed: true })
    ElMessage.success('密码修改成功')
    onVisibleChange(false)
    emit('success')
  } catch (e: any) {
    const detail = e?.response?.data?.detail || '修改失败，请重试'
    ElMessage.error(detail)
    // 验证码错误或过期时刷新图片
    if (detail.includes('验证码')) loadCaptcha()
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.captcha-row .el-input {
  flex: 1;
}
.captcha-img-btn {
  flex-shrink: 0;
  width: 108px;
  height: 40px;
  padding: 0;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #f6f6f7;
  cursor: pointer;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s ease;
}
.captcha-img-btn:hover:not(:disabled) { opacity: 0.85; }
.captcha-img-btn:disabled { cursor: not-allowed; opacity: 0.6; }
.captcha-img-btn img {
  width: 100%;
  height: 100%;
  object-fit: fill;
  display: block;
}
.captcha-img-btn span {
  font-size: 13px;
  color: #909399;
}
</style>
