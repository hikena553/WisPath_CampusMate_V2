<template>
  <div class="join-page">
    <div class="join-card">
      <div class="join-logo">
        <img v-if="siteLogo" :src="siteLogo" alt="站点标识" />
      </div>

      <!-- 加载中 -->
      <template v-if="state === 'loading'">
        <div class="join-title">正在处理邀请…</div>
        <div class="join-desc">请稍候</div>
      </template>

      <!-- 加入失败（失效 / 解散 / 未登录） -->
      <template v-else-if="state === 'error'">
        <div class="join-title">无法加入群聊</div>
        <div class="join-desc">{{ errorText }}</div>
        <button class="join-btn" type="button" @click="goHome">返回首页</button>
      </template>

      <!-- 待确认 / 已加入 -->
      <template v-else>
        <div class="join-avatar">
          <img v-if="result?.group_id && groupAvatar" :src="groupAvatar" alt="群头像" />
          <span v-else>{{ (groupName || '群')[0] }}</span>
        </div>
        <div class="join-title">{{ groupName }}</div>
        <div class="join-desc">
          {{ result?.already_member ? '你已在该群聊中' : '已成功加入群聊' }}
        </div>
        <button class="join-btn" type="button" @click="goToGroup">进入群聊</button>
        <div class="join-hint">加入后可在消息中心查看群消息</div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 群邀请落地页：扫描群二维码 / 打开邀请链接后进入此页。
 * 校验邀请码 → 入群（幂等）→ 按角色跳转。
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { joinGroupByCode, getGroup, type GroupJoinResult } from '@/api/groups'

type State = 'loading' | 'ready' | 'joining' | 'error'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { siteLogo } = useSiteConfig()

const state = ref<State>('loading')
const errorText = ref('邀请链接无效或已失效')
const result = ref<GroupJoinResult | null>(null)
const groupName = ref('')
const groupAvatar = ref('')

const code = computed(() => String(route.params.code || ''))

function roleHome() {
  const role = auth.user?.role
  if (role === 'teacher') return '/teacher'
  if (role === 'admin') return '/admin'
  return '/student'
}

function goHome() {
  router.replace(roleHome())
}

onMounted(async () => {
  if (!code.value) {
    state.value = 'error'
    return
  }
  // 直接尝试入群（幂等）：已在群内也能拿到群信息，无需先查询
  try {
    const res = await joinGroupByCode(code.value)
    result.value = res
    groupName.value = res.group_name
    try {
      const g = await getGroup(res.group_id)
      groupAvatar.value = g.avatar || ''
    } catch { /* 群头像拉取失败不影响加入流程 */ }
    state.value = 'ready'
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    errorText.value = detail || '邀请链接无效或已失效'
    state.value = 'error'
  }
})

/** 入群后按角色进入对应端：教师直达群聊，学生进入消息中心 */
function goToGroup() {
  const res = result.value
  if (!res) return
  if (auth.user?.role === 'teacher' || auth.user?.role === 'admin') {
    router.replace({ path: '/teacher/messages', query: { groupId: String(res.group_id), groupName: res.group_name } })
    return
  }
  router.replace('/student/workbench')
}
</script>

<style scoped>
.join-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--dt-bg, #f5f6f7);
}

.join-card {
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 24px 28px;
  background: var(--dt-surface, #fff);
  border-radius: 16px;
  box-shadow: 0 8px 28px rgba(15, 17, 21, 0.08);
}

.join-logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--dt-primary-soft, #e8f3ff);
}

.join-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.join-avatar {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--dt-primary-soft, #e8f3ff);
  color: var(--dt-primary-strong, #0070d9);
  font-size: 28px;
  font-weight: 600;
  margin-top: 4px;
}

.join-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.join-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--dt-text, #171a1d);
  text-align: center;
  word-break: break-word;
}

.join-desc {
  font-size: 13px;
  color: var(--dt-text-tertiary, #8a9099);
  text-align: center;
}

.join-btn {
  margin-top: 10px;
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: var(--dt-primary, #0089ff);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.18s ease;
}

.join-btn:active:not(:disabled) {
  background: var(--dt-primary-press, #0063bf);
}

.join-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.join-hint {
  font-size: 12px;
  color: var(--dt-text-quiet, #b6bcc4);
}
</style>