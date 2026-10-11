<template>
  <!-- 首页头部：简约问候卡（吸顶固定）
       克制留白 + 一条品牌发丝边；吉祥物与品牌点承载产品个性，不再使用整块大渐变。
       外层 sticky 容器铺满整行并以页面底色遮挡，滚动时下方内容从卡片背后穿过。 -->
  <div class="hm-head-sticky">
    <section v-if="isMobile" class="hm-head">
      <div class="hm-head-main">
        <h1 class="hm-head-title">{{ greeting }}，{{ userName }}</h1>
        <p class="hm-head-meta">
          <span class="hm-dot"></span>{{ siteName }} · 教师端
          <span class="hm-sep">·</span>{{ todayShort }}
        </p>
      </div>
      <img :src="siteMascot" :alt="siteName" class="hm-head-mascot" />
    </section>

    <!-- 桌面端：同款问候卡 -->
    <section v-else class="hm-head hm-head-desk">
      <div class="hm-head-main">
        <h2 class="hm-head-title">{{ greeting }}，{{ userName }}</h2>
        <p class="hm-head-meta">
          <span class="hm-dot"></span>{{ siteName }} · 教师端
          <span class="hm-sep">·</span>{{ todayStr }}
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSiteConfig } from '@/composables/useSiteConfig'

// 吉祥物与站点名称取自站点配置：管理端变更后教师端同步
const { siteMascot, siteName } = useSiteConfig()

// 移动端用短日期，避免元信息行过长
const todayShort = computed(() => {
  const d = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getMonth() + 1}月${d.getDate()}日 星期${week[d.getDay()]}`
})

defineProps<{
  isMobile: boolean
  userName: string
  greeting: string
  todayStr: string
}>()
</script>

<style scoped>
/* ===== 吸顶容器 ===== */
/* 铺满整行（抵消 .home-dashboard 的左右内边距），以页面底色遮挡下方滚动内容，
   使问候卡在滚动时固定于顶部不动。 */
.hm-head-sticky {
  position: sticky;
  top: 0;
  z-index: 30;
  margin: 0 -16px;
  padding: 12px 16px;
  background: #f5f6f8;
}

/* ===== 问候卡 ===== */
.hm-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 0;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(37, 99, 235, 0.12);
  background: linear-gradient(135deg, #ffffff 0%, #f3f8ff 100%);
  box-shadow: 0 1px 2px rgba(15, 17, 21, 0.03);
}
.hm-head-main { min-width: 0; }
.hm-head-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.2px;
  color: #101828;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hm-head-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 5px 0 0;
  font-size: 12px;
  color: #667085;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hm-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
  flex-shrink: 0;
}
.hm-sep { color: #cbd0d8; }
.hm-head-mascot {
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  object-fit: contain;
  filter: drop-shadow(0 4px 10px rgba(37, 99, 235, 0.22));
}

/* ===== 桌面端 ===== */
.hm-head-desk { padding: 16px 20px; }

/* 移动端：容器左右内边距为 8px，吸顶容器同步收窄，保持铺满整行 */
@media (max-width: 767px) {
  .hm-head-sticky {
    margin: 0 -8px;
    padding: 8px 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hm-dot { box-shadow: none; }
}
</style>