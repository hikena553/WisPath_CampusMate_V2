<!-- 系统公告条：展示管理端「系统设置 → 系统公告」下发的内容，供教师端/学生端同步显示。
     管理员关闭/修改公告后，各端通过站点配置同步刷新；用户可关闭，关闭状态按内容记忆。 -->
<template>
  <div v-if="visible" class="site-announce">
    <el-icon class="sa-icon"><BellFilled /></el-icon>
    <span class="sa-tag">系统公告</span>
    <span class="sa-text">{{ siteAnnouncement }}</span>
    <el-icon class="sa-close" title="关闭" @click="dismiss"><Close /></el-icon>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { BellFilled, Close } from '@element-plus/icons-vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

const { siteAnnouncement } = useSiteConfig()

const DISMISS_KEY = 'site_announcement_dismissed'

/** 简易内容指纹：公告内容变化后重新展示（不同内容互不影响） */
function fingerprint(text: string): string {
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) | 0
  }
  return `${text.length}-${hash}`
}

const dismissed = ref(false)

watch(
  siteAnnouncement,
  (text) => {
    dismissed.value = !text || localStorage.getItem(DISMISS_KEY) === fingerprint(text)
  },
  { immediate: true }
)

const visible = computed(() => !!siteAnnouncement.value && !dismissed.value)

function dismiss() {
  dismissed.value = true
  const text = siteAnnouncement.value
  if (text) localStorage.setItem(DISMISS_KEY, fingerprint(text))
}
</script>

<style scoped>
.site-announce {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 7px 14px;
  background: linear-gradient(90deg, #fff7e6, #fffbf0);
  border-bottom: 1px solid #ffe0a3;
  color: #92510a;
  font-size: 13px;
  line-height: 1.4;
}
.sa-icon {
  color: #d48806;
  flex-shrink: 0;
}
.sa-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  background: #ffe7ba;
  color: #ad6800;
  font-size: 11px;
  font-weight: 600;
}
.sa-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sa-close {
  flex-shrink: 0;
  cursor: pointer;
  color: #ad8b4a;
}
.sa-close:hover {
  color: #92510a;
}
@media (max-width: 767px) {
  .sa-text {
    white-space: normal;
  }
}
</style>