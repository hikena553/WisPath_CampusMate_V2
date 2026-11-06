<template>
  <div class="download-page">
    <header class="dl-nav">
      <router-link class="dl-brand" to="/">
        <img :src="siteLogo" :alt="siteName" class="dl-logo" />
        <span>{{ siteName }}</span>
      </router-link>
      <router-link class="dl-back" to="/">返回官网</router-link>
    </header>

    <main class="dl-main">
      <section class="dl-card">
        <div class="dl-copy">
          <span class="dl-label">ANDROID CLIENT</span>
          <h1>下载{{ siteName }}移动端</h1>
          <p class="dl-sub">
            教师端与学生端使用同一个安装包，登录后按账号角色进入对应工作空间。<br />
            账号由学校统一分配，无需注册。
          </p>

          <a
            class="dl-btn"
            :class="{ disabled: checkState === 'missing' }"
            :href="inWeChat || checkState === 'missing' ? undefined : apkUrl"
            :aria-disabled="checkState === 'missing'"
            @click="onDownloadClick"
          >
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19.5h14" />
            </svg>
            {{ inWeChat ? '在浏览器中打开下载' : '下载 Android 安装包' }}
          </a>

          <p v-if="inWeChat" class="dl-wechat-tip">
            微信内无法直接下载，请点右上角「···」→「在浏览器打开」
          </p>
          <p class="dl-hint" :class="{ warn: checkState === 'missing' }">
            {{ statusText }}
          </p>

          <ul class="dl-steps">
            <li><span>1</span><p>在电脑上扫码，或直接在手机浏览器打开本页。</p></li>
            <li><span>2</span><p>下载完成后，按系统提示允许安装来自浏览器的应用。</p></li>
            <li><span>3</span><p>打开{{ siteName }}，使用学号 / 工号与初始密码登录。</p></li>
          </ul>

          <p class="dl-note">当前仅提供 Android 安装包；iOS 设备请使用网页端访问。</p>
        </div>

        <aside class="dl-qr">
          <div class="qr-box">
            <QrCode :value="pageUrl" :size="150" />
          </div>
          <strong>扫码在手机打开</strong>
          <span>教师端 / 学生端通用</span>
        </aside>
      </section>
    </main>

    <footer class="dl-footer">
      © {{ year }} 绵阳城市学院 · {{ siteName }}
    </footer>

    <WeChatOpenGuide :open="guideOpen" :url="pageUrl" @close="guideOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useSiteConfig } from '@/composables/useSiteConfig'
import QrCode from '@/components/common/QrCode.vue'
import WeChatOpenGuide from '@/components/common/WeChatOpenGuide.vue'
import { isWeChatBrowser } from '@/utils/wechat'

const { siteName, siteLogo, siteBaseUrl } = useSiteConfig()
const year = new Date().getFullYear()

// 与管理端「备案与域名」保持一致：配置域名后二维码与安装包地址自动指向正式地址
const pageUrl = computed(() => `${siteBaseUrl.value}/download`)
const apkUrl = computed(
  () =>
    ((import.meta.env.VITE_APK_DOWNLOAD_URL as string | undefined) || '').trim() ||
    `${siteBaseUrl.value}/download/SmartCampus.apk`
)

const checkState = ref<'checking' | 'ready' | 'missing' | 'unknown'>('checking')

// 微信内置浏览器无法直接下载 APK：进页面即弹出「用浏览器打开」指引
const inWeChat = ref(false)
const guideOpen = ref(false)

const statusText = computed(() => {
  if (inWeChat.value) return '微信内请先用浏览器打开本页'
  if (checkState.value === 'checking') return '正在检查安装包…'
  if (checkState.value === 'missing') return '安装包正在准备中，请稍后再试'
  return 'Android 7.0 及以上'
})

/**
 * 探测安装包是否已上传。
 * nginx 对不存在的静态文件会回退到 index.html 并返回 200，
 * 因此除状态码外还要排除 text/html，避免把官网页面误判为安装包。
 */
async function checkApk() {
  try {
    const res = await fetch(apkUrl.value, { method: 'HEAD' })
    const type = res.headers.get('content-type') || ''
    checkState.value = res.ok && !type.includes('text/html') ? 'ready' : 'missing'
  } catch {
    checkState.value = 'unknown'
  }
}

function onDownloadClick(event: MouseEvent) {
  if (inWeChat.value) {
    event.preventDefault()
    guideOpen.value = true
    return
  }
  if (checkState.value === 'missing') {
    event.preventDefault()
  }
}

onMounted(() => {
  inWeChat.value = isWeChatBrowser()
  if (inWeChat.value) {
    window.setTimeout(() => {
      guideOpen.value = true
    }, 260)
  }
  void checkApk()
})
// 站点配置异步加载，域名变化后重新探测安装包地址
watch(apkUrl, () => void checkApk())

watch(
  siteName,
  (name) => {
    document.title = `下载 ${name} 移动端`
  },
  { immediate: true }
)
</script>

<style scoped>
.download-page {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
  background: #ffffff;
  color: #111114;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
  display: flex;
  flex-direction: column;
}

.download-page::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 620px;
  pointer-events: none;
  background:
    radial-gradient(50% 46% at 50% 0%, rgba(77, 107, 254, 0.13) 0%, rgba(77, 107, 254, 0) 72%),
    radial-gradient(36% 32% at 86% 4%, rgba(124, 92, 255, 0.09) 0%, rgba(124, 92, 255, 0) 72%);
}

.dl-nav {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  padding: 18px 26px;
}

.dl-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 700;
  color: inherit;
  text-decoration: none;
}

.dl-logo {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: contain;
  background: #ffffff;
}

.dl-back {
  font-size: 12.5px;
  color: #76777f;
  text-decoration: none;
}

.dl-back:hover {
  color: #111114;
}

.dl-main {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 30px 24px 60px;
}

.dl-card {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr);
  gap: 46px;
  align-items: center;
  width: 100%;
  max-width: 820px;
  padding: 42px 44px;
  border: 1px solid rgba(17, 17, 20, 0.09);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 30px 70px -36px rgba(38, 52, 118, 0.28),
    0 2px 8px rgba(17, 17, 20, 0.03);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.dl-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2.4px;
  color: #9a9ba3;
}

.dl-copy h1 {
  margin: 12px 0 0;
  font-size: clamp(26px, 3.4vw, 34px);
  line-height: 1.25;
  font-weight: 700;
  letter-spacing: -0.8px;
}

.dl-sub {
  margin: 14px 0 0;
  font-size: 13px;
  line-height: 1.85;
  color: #71727b;
}

.dl-btn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin-top: 26px;
  padding: 13px 24px;
  border-radius: 999px;
  background: #111114;
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-decoration: none;
  transition: background 0.16s ease, opacity 0.16s ease, transform 0.16s ease;
}

.dl-btn:hover {
  background: #000000;
}

.dl-btn:active {
  transform: scale(0.985);
}

.dl-btn.disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.dl-hint {
  margin: 12px 0 0;
  font-size: 11px;
  color: #9a9ba3;
}

.dl-hint.warn {
  color: #8a6d3b;
}

.dl-wechat-tip {
  margin: 14px 0 0;
  padding: 8px 13px;
  border-radius: 10px;
  background: rgba(7, 193, 96, 0.1);
  color: #059449;
  font-size: 12px;
  line-height: 1.55;
  font-weight: 550;
}

.dl-steps {
  margin: 28px 0 0;
  padding: 24px 0 0;
  border-top: 1px solid rgba(17, 17, 20, 0.07);
  list-style: none;
}

.dl-steps li {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 7px 0;
}

.dl-steps li span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 19px;
  height: 19px;
  flex-shrink: 0;
  margin-top: 1px;
  border-radius: 50%;
  background: #f1f2f6;
  font-size: 10.5px;
  font-weight: 600;
  color: #5f6068;
}

.dl-steps li p {
  margin: 0;
  font-size: 12px;
  line-height: 1.75;
  color: #7c7d86;
}

.dl-note {
  margin: 18px 0 0;
  font-size: 10.5px;
  color: #a3a4ac;
}

.dl-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  justify-self: center;
  text-align: center;
}

.qr-box {
  padding: 12px;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 20px 46px -30px rgba(38, 52, 118, 0.4);
  border: 1px solid rgba(17, 17, 20, 0.06);
}

.dl-qr strong {
  margin-top: 4px;
  font-size: 13.5px;
  font-weight: 650;
}

.dl-qr span {
  font-size: 11px;
  color: #9a9ba3;
}

.dl-footer {
  position: relative;
  z-index: 1;
  padding: 18px 24px 24px;
  text-align: center;
  font-size: 10.5px;
  color: #b0b1b9;
}

@media (max-width: 820px) {
  .dl-card {
    grid-template-columns: minmax(0, 1fr);
    gap: 26px;
    padding: 30px 24px;
    border-radius: 24px;
  }

  .dl-qr {
    display: none;
  }

  .dl-main {
    align-items: flex-start;
    padding: 14px 18px 40px;
  }

  .dl-nav {
    padding: 14px 18px;
  }

  .dl-copy h1 {
    font-size: 25px;
  }

  .dl-btn {
    width: 100%;
    justify-content: center;
    padding: 14px 18px;
  }

  .dl-steps li p {
    font-size: 12.5px;
  }
}
</style>
