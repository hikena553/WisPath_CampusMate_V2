<template>
  <Teleport to="body">
    <transition name="wxg-fade">
      <div v-if="open" class="wxg" role="dialog" aria-modal="true" aria-label="微信内请用浏览器打开">
        <div class="wxg-mask" @click="emit('close')"></div>

        <!-- 指向右上角微信「···」菜单的虚线箭头 -->
        <svg class="wxg-arrow" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path
            class="wxg-arrow__line"
            d="M 6 94 C 44 94, 82 66, 94 6"
            pathLength="100"
            vector-effect="non-scaling-stroke"
          />
        </svg>
        <div class="wxg-corner" aria-hidden="true">
          <span class="wxg-corner__pulse"></span>
          <span class="wxg-corner__dots">···</span>
          <span class="wxg-corner__tag">点这里</span>
        </div>

        <div class="wxg-card">
          <span class="wxg-badge">微信内无法直接下载</span>
          <h2>请点右上角「···」<br />选择「在浏览器打开」</h2>
          <p class="wxg-desc">
            微信内置浏览器不支持安装 APK 文件。用浏览器重新打开本页后，再点「下载 Android 安装包」即可正常安装。
          </p>
          <ol class="wxg-steps">
            <li><b>1</b><span>点击右上角「···」菜单</span></li>
            <li><b>2</b><span>选择「在浏览器打开」</span></li>
          </ol>
          <div class="wxg-actions">
            <button type="button" class="wxg-btn wxg-btn--ghost" @click="copyLink">{{ copyLabel }}</button>
            <button type="button" class="wxg-btn wxg-btn--primary" @click="emit('close')">我知道了</button>
          </div>
          <p class="wxg-tip">
            iPhone 选「在 Safari 中打开」，Android 选「在浏览器打开」；也可以复制链接后到浏览器地址栏粘贴。
          </p>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps<{ open: boolean; url: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const copied = ref(false)
let timer = 0

const copyLabel = computed(() => (copied.value ? '链接已复制' : '复制下载链接'))

async function copyLink() {
  const text = props.url
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 微信内置浏览器里 clipboard API 可能不可用，退回 textarea + execCommand
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', 'readonly')
    ta.style.position = 'fixed'
    ta.style.top = '0'
    ta.style.left = '0'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
    } catch {
      /* 复制失败时保持按钮可重复点击 */
    }
    document.body.removeChild(ta)
  }
  copied.value = true
  window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    copied.value = false
  }, 2200)
}

onBeforeUnmount(() => window.clearTimeout(timer))
</script>

<style scoped>
.wxg {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 0 16px calc(18px + env(safe-area-inset-bottom));
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-tap-highlight-color: transparent;
}

.wxg-mask {
  position: absolute;
  inset: 0;
  background: rgba(8, 10, 18, 0.7);
  -webkit-backdrop-filter: blur(2px);
  backdrop-filter: blur(2px);
}

/* 虚线箭头：从卡片上方弯向屏幕右上角（微信「···」菜单方向） */
.wxg-arrow {
  position: absolute;
  top: 0;
  right: 0;
  width: 66vw;
  max-width: 320px;
  height: 54vh;
  color: #07c160;
  pointer-events: none;
  filter: drop-shadow(0 2px 6px rgba(7, 193, 96, 0.35));
}

.wxg-arrow__line {
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-dasharray: 3 2.6;
  animation: wxg-march 0.9s linear infinite;
}

@keyframes wxg-march {
  to {
    stroke-dashoffset: -5.6;
  }
}

/* 右上角「···」高亮圈 + 点这里 */
.wxg-corner {
  position: absolute;
  top: 6px;
  right: 10px;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}

.wxg-corner__pulse {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2.5px solid #07c160;
  background: rgba(7, 193, 96, 0.16);
  box-shadow: 0 0 0 0 rgba(7, 193, 96, 0.55);
  animation: wxg-pulse 1.6s ease-out infinite;
}

@keyframes wxg-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(7, 193, 96, 0.55);
  }
  70% {
    box-shadow: 0 0 0 16px rgba(7, 193, 96, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(7, 193, 96, 0);
  }
}

.wxg-corner__dots {
  position: relative;
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 1px;
  transform: translateY(-2px);
}

.wxg-corner__tag {
  position: absolute;
  right: 46px;
  top: 16px;
  padding: 4px 9px;
  border-radius: 999px;
  background: #07c160;
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(7, 193, 96, 0.4);
}

.wxg-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 460px;
  margin: 0 auto;
  padding: 20px 20px 16px;
  border-radius: 22px;
  background: #ffffff;
  box-shadow: 0 24px 60px -20px rgba(0, 0, 0, 0.45);
}

.wxg-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(7, 193, 96, 0.1);
  color: #05a250;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.wxg-card h2 {
  margin: 10px 0 0;
  font-size: 19px;
  line-height: 1.45;
  font-weight: 700;
  color: #111114;
  letter-spacing: -0.2px;
}

.wxg-desc {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #71727b;
}

.wxg-steps {
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.wxg-steps li {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  color: #3f4048;
}

.wxg-steps b {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #f1f3f6;
  color: #5f6068;
  font-size: 11px;
  font-weight: 700;
}

.wxg-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.wxg-btn {
  flex: 1;
  height: 42px;
  border: none;
  border-radius: 999px;
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.2px;
  cursor: pointer;
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.wxg-btn:active {
  transform: scale(0.985);
}

.wxg-btn--ghost {
  background: #f2f3f6;
  color: #3f4048;
}

.wxg-btn--primary {
  background: #111114;
  color: #ffffff;
}

.wxg-tip {
  margin: 11px 0 0;
  font-size: 10.5px;
  line-height: 1.6;
  color: #9a9ba3;
  text-align: center;
}

.wxg-fade-enter-active,
.wxg-fade-leave-active {
  transition: opacity 0.2s ease;
}

.wxg-fade-enter-from,
.wxg-fade-leave-to {
  opacity: 0;
}

@media (max-height: 640px) {
  .wxg-card {
    padding: 16px 18px 12px;
    border-radius: 18px;
  }

  .wxg-card h2 {
    font-size: 17px;
  }

  .wxg-desc {
    display: none;
  }

  .wxg-tip {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .wxg-arrow__line,
  .wxg-corner__pulse {
    animation: none;
  }
}
</style>
