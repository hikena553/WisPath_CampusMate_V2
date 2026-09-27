<template>
  <div v-if="isMobile" class="sub-page-header">
    <el-button text circle class="back-btn" @click="goBack">
      <el-icon :size="20"><ArrowLeft /></el-icon>
    </el-button>
    <div class="sub-page-title">{{ title }}</div>
    <div class="sub-page-placeholder">
      <slot name="right" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps<{
  title: string
  fallback: string
}>()

const { isMobile } = useResponsive()
const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push(props.fallback)
  }
}
</script>

<style scoped>
.sub-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.back-btn {
  width: 36px;
  height: 36px;
  color: #333;
}

.sub-page-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a1a;
}

.sub-page-placeholder {
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
</style>