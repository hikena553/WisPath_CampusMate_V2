<template>
  <div class="welcome-page">
    <div class="welcome-body">
      <section class="hero">
        <img :src="siteMascot" :alt="siteName" class="hero-img" />
        <h1>让每一次成长<br />都被看见</h1>
        <p class="lede">有些日子过得很轻，轻到需要有人替你记得。</p>
      </section>

      <ul class="features">
        <li v-for="(item, index) in features" :key="item.title" :style="{ '--i': index }">
          <span class="icon">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <path :d="item.icon" />
              <path v-if="item.icon2" :d="item.icon2" />
            </svg>
          </span>
          <div class="copy">
            <strong>{{ item.title }}</strong>
            <p>{{ item.desc }}</p>
          </div>
        </li>
      </ul>

      <section class="culture">
        <span class="culture-label">我们相信</span>
        <p class="culture-words">陪伴 · 记录 · 连接</p>
        <p class="culture-desc">大学不是一场赶路<br />我们只想把你路过的光，留得久一点。</p>
      </section>

      <footer class="actions">
        <button type="button" class="btn-primary" @click="finish('/login')">开始使用</button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSiteConfig } from '@/composables/useSiteConfig'

const router = useRouter()
const { siteName, siteMascot } = useSiteConfig()

/** 首次打开引导页的本地标记（与 router/index.ts 保持一致） */
const WELCOME_SEEN_KEY = 'mian02_welcome_seen'

const features = [
  {
    title: '学业中心',
    desc: '把远方，走成今天的一步',
    icon: 'M20 12a8 8 0 1 1-8-8 8 8 0 0 1 8 8z',
    icon2: 'M14.9 9.1l-2.2 4.8-4.8 2.2 2.2-4.8z',
  },
  {
    title: '工作台',
    desc: '琐碎有人接，你只管向前',
    icon: 'M4 4h6.5v6.5H4z',
    icon2: 'M13.5 4H20v6.5h-6.5zM4 13.5h6.5V20H4zM13.5 13.5H20V20h-6.5z',
  },
  {
    title: '智能体',
    desc: '话不必说完，它也听得懂',
    icon: 'M4.5 5.5h15v10h-9l-4 3.2v-3.2h-2z',
    icon2: 'M9 10.5h6',
  },
]

watch(
  siteName,
  (name) => {
    document.title = `认识${name}`
  },
  { immediate: true }
)

function finish(path: string) {
  try {
    localStorage.setItem(WELCOME_SEEN_KEY, '1')
  } catch {
    // 隐私模式写入失败时不影响进入登录
  }
  router.replace(path)
}
</script>

<style scoped>
.welcome-page {
  position: fixed;
  inset: 0;
  overflow-y: auto;
  display: flex;
  justify-content: center;
  background: #ffffff;
  background-image: radial-gradient(68% 42% at 50% 0%, #f6f7f9 0%, rgba(246, 247, 249, 0) 72%);
  color: #111111;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* 极淡网格底纹：固定铺满视口，顶部清晰、向下渐隐，形成「渐变消失」的网格 */
.welcome-page::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, rgba(17, 17, 17, 0.07) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(17, 17, 17, 0.07) 1px, transparent 1px);
  background-size: 26px 26px;
  background-position: center top;
  -webkit-mask-image: radial-gradient(120% 78% at 50% 0%, #000 0%, rgba(0, 0, 0, 0.62) 42%, transparent 76%);
  mask-image: radial-gradient(120% 78% at 50% 0%, #000 0%, rgba(0, 0, 0, 0.62) 42%, transparent 76%);
}

.welcome-body {
  position: relative;
  z-index: 1;
  box-sizing: border-box;
  width: 100%;
  max-width: 400px;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  padding: calc(env(safe-area-inset-top) + 56px) 28px calc(env(safe-area-inset-bottom) + 20px);
}

/* ===== 主视觉：吉祥物直接裸露，无任何圈层装饰 ===== */
.hero {
  margin-top: 0;
  text-align: center;
}

.hero-img {
  width: 92px;
  height: auto;
  margin: 0 auto;
  display: block;
  opacity: 0;
  animation: fade-in 0.55s 0.1s ease forwards;
}

.hero h1 {
  margin: 16px 0 0;
  font-size: 26px;
  line-height: 1.32;
  font-weight: 700;
  letter-spacing: 0.6px;
  opacity: 0;
  transform: translateY(12px);
  animation: fade-up 0.68s 0.2s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.lede {
  margin: 10px auto 0;
  max-width: 280px;
  font-size: 12.5px;
  line-height: 1.75;
  color: #7c7c83;
  opacity: 0;
  transform: translateY(10px);
  animation: fade-up 0.68s 0.32s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

/* ===== 能力区：图标 + 双行文案，靠发丝线分隔 ===== */
.features {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid #f0f0f2;
  opacity: 0;
  animation: fade-up 0.6s 0.44s ease forwards;
}

.features li {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f2;
}

.icon {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 11px;
  border: 1px solid #ececf0;
  background: #fafafb;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #16161a;
}

.copy {
  flex: 1;
  min-width: 0;
}

.copy strong {
  display: block;
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.copy p {
  margin: 3px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: #9a9aa0;
}

/* ===== 产品文化：轻量居中排版，不用卡片 ===== */
.culture {
  margin-top: 30px;
  padding-top: 22px;
  border-top: 1px solid #f0f0f2;
  text-align: center;
  opacity: 0;
  transform: translateY(10px);
  animation: fade-up 0.7s 0.56s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.culture-label {
  font-size: 11px;
  letter-spacing: 3px;
  color: #b0b0b6;
}

.culture-words {
  margin: 9px 0 0;
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 4px;
  color: #111111;
}

.culture-desc {
  margin: 9px auto 0;
  max-width: 268px;
  font-size: 11.5px;
  line-height: 1.75;
  color: #9a9aa0;
}

/* ===== 底部 ===== */
.actions {
  margin-top: auto;
  padding-top: 28px;
  padding-bottom: 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 0;
  animation: fade-up 0.7s 0.68s ease forwards;
}

.btn-primary {
  width: 100%;
  height: 52px;
  border: none;
  border-radius: 26px;
  background: #111111;
  color: #ffffff;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 1.5px;
  cursor: pointer;
  transition: transform 0.16s ease, background 0.16s ease;
}
.btn-primary:active {
  transform: scale(0.99);
  background: #000000;
}

@keyframes fade-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fade-in {
  to {
    opacity: 1;
  }
}

@media (max-height: 720px) {
  .welcome-body {
    padding-top: calc(env(safe-area-inset-top) + 32px);
    padding-bottom: calc(env(safe-area-inset-bottom) + 4px);
  }
  .hero {
    margin-top: 14px;
  }
  .hero-img {
    width: 78px;
  }
  .hero h1 {
    margin-top: 12px;
    font-size: 23px;
  }
  .lede {
    margin-top: 8px;
  }
  .features {
    margin-top: 20px;
  }
  .features li {
    padding: 11px 0;
  }
  .culture {
    margin-top: 20px;
    padding-top: 18px;
  }
  .culture-words {
    font-size: 17px;
  }
  .actions {
    padding-top: 12px;
    padding-bottom: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-img,
  .hero h1,
  .lede,
  .features,
  .culture,
  .actions {
    opacity: 1;
    transform: none;
    animation: none;
  }
}

/* ===== 桌面端：加宽版心、能力区三列、整体等比放大 ===== */
@media (min-width: 900px) {
  .welcome-page {
    align-items: center;
    background:
      radial-gradient(70% 50% at 50% 0%, #f8f9fb 0%, rgba(248, 249, 251, 0) 60%),
      #ffffff;
  }

  .welcome-page::before {
    background-size: 32px 32px;
  }

  .welcome-body {
    max-width: 780px;
    min-height: auto;
    margin: auto;
    padding: 56px 48px;
  }

  .hero {
    margin-top: 0;
  }
  .hero-img {
    width: 124px;
  }
  .hero h1 {
    margin-top: 22px;
    font-size: 36px;
    line-height: 1.28;
  }
  .lede {
    margin-top: 14px;
    max-width: 420px;
    font-size: 14.5px;
  }

  .features {
    margin-top: 40px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    border-top: none;
  }
  .features li {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
    padding: 22px 20px;
    border: 1px solid #f0f0f2;
    border-radius: 18px;
    background: #ffffff;
  }
  .icon {
    width: 42px;
    height: 42px;
    border-radius: 13px;
  }
  .copy strong {
    font-size: 16px;
  }
  .copy p {
    margin-top: 5px;
    font-size: 12.5px;
  }

  .culture {
    margin-top: 42px;
    padding-top: 30px;
  }
  .culture-label {
    font-size: 11.5px;
  }
  .culture-words {
    margin-top: 12px;
    font-size: 22px;
    letter-spacing: 5px;
  }
  .culture-desc {
    margin-top: 12px;
    max-width: 340px;
    font-size: 12.5px;
  }

  .actions {
    padding-top: 42px;
  }
  .btn-primary {
    width: 320px;
    height: 56px;
    font-size: 16px;
  }
}
</style>
