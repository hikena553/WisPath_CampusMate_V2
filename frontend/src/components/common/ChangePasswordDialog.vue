<template>
  <el-dialog
    :model-value="modelValue"
    title="修改密码"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="onVisibleChange"
    @closed="reset"
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
          @keyup.enter="submit"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="onVisibleChange(false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/user'
import { useAuthStore } from '@/stores/auth'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const auth = useAuthStore()
const submitting = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm_password: '' })

function reset() {
  form.old_password = ''
  form.new_password = ''
  form.confirm_password = ''
}

function onVisibleChange(visible: boolean) {
  emit('update:modelValue', visible)
}

/** 与后端 /api/auth/change-password 的校验规则保持一致，避免提交后才报错 */
function validate(): string | null {
  if (!form.old_password || !form.new_password || !form.confirm_password) return '请填写所有字段'
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
  submitting.value = true
  try {
    await changePassword(form.old_password, form.new_password)
    // 同步缓存里的 password_changed：强改密中间件与路由守卫都以它为准
    if (auth.user) auth.updateUser({ ...auth.user, password_changed: true })
    ElMessage.success('密码修改成功')
    onVisibleChange(false)
    emit('success')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '修改失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>