<template>
  <div class="gs-page">
    <div class="gs-card">
      <div class="gs-brand">
        <img src="/images/校徽_圆形.png" alt="校徽" class="gs-logo" />
        <span>绵阳城市学院 · 家校沟通</span>
      </div>

      <div v-if="loading" class="gs-state">加载中…</div>

      <div v-else-if="error" class="gs-state gs-error">
        <el-icon :size="38" color="#f04438"><WarningFilled /></el-icon>
        <p>{{ error }}</p>
        <small>如需查看，请联系辅导员重新生成分享链接</small>
      </div>

      <template v-else-if="data">
        <div class="gs-head">
          <el-tag size="small" effect="light" round>{{ data.scene_label }}</el-tag>
          <span class="gs-date">{{ (data.created_at || '').slice(0, 10) }}</span>
        </div>
        <div class="gs-content">{{ data.content_summary }}</div>
        <div class="gs-footer">
          <span>辅导员：{{ data.teacher_name || '—' }}</span>
          <span>链接有效期至 {{ (data.expires_at || '').slice(0, 10) }}</span>
        </div>
        <div class="gs-note">
          <el-icon :size="12"><Lock /></el-icon>
          本页面为一次性只读视图，无需登录，链接到期或被撤销后自动失效
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Lock, WarningFilled } from '@element-plus/icons-vue'
import { viewSharedLog, type SharedLogView } from '@/api/guardian'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref<SharedLogView | null>(null)

onMounted(async () => {
  const token = String(route.params.token || '')
  if (!token) {
    error.value = '链接无效'
    loading.value = false
    return
  }
  try {
    data.value = await viewSharedLog(token)
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    error.value = status === 410 ? '该分享链接已被撤销或已过期' : '链接不存在或已失效'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.gs-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: linear-gradient(160deg, #f5f8ff 0%, #eef2f9 100%);
}
.gs-card {
  width: 100%;
  max-width: 520px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(16, 24, 40, 0.08);
  padding: 22px 22px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.gs-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  font-weight: 600;
  color: #101828;
}
.gs-logo { width: 26px; height: 26px; object-fit: contain; }

.gs-state {
  padding: 34px 0;
  text-align: center;
  color: #98a2b3;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.gs-state p { margin: 0; }
.gs-error small { font-size: 11.5px; color: #b0b7c3; }

.gs-head { display: flex; align-items: center; justify-content: space-between; }
.gs-date { font-size: 11.5px; color: #98a2b3; }

.gs-content {
  font-size: 14px;
  color: #344054;
  line-height: 1.75;
  background: #f9fafb;
  border-radius: 12px;
  padding: 14px 16px;
  white-space: pre-wrap;
}

.gs-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: #98a2b3;
}
.gs-note {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: #98a2b3;
  border-top: 1px solid #f2f4f7;
  padding-top: 11px;
}
</style>