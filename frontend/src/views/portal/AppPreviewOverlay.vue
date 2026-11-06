<template>
  <Teleport to="body">
    <Transition name="pv">
      <div
        v-if="open && preview"
        class="pv"
        role="dialog"
        aria-modal="true"
        :aria-label="`${preview.tag} 界面预览`"
      >
        <button ref="closeBtn" type="button" class="pv-close" aria-label="关闭预览" @click="close">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>

        <div class="pv-scroll" @click.self="close">
          <div class="pv-panel">
          <div class="pv-copy">
            <span class="pv-kicker">
              <span class="pv-kicker-dot"></span>
              {{ preview.tag }}
            </span>

            <h2 class="pv-title">{{ preview.title }}</h2>
            <p class="pv-desc">{{ preview.desc }}</p>

            <ul v-if="preview.slides.length > 1" class="pv-list">
              <li v-for="(slide, index) in preview.slides" :key="slide.label">
                <button
                  type="button"
                  :class="{ 'is-active': index === shownIndex }"
                  @click="go(index)"
                >
                  <span class="pv-no">{{ String(index + 1).padStart(2, '0') }}</span>
                  <span class="pv-text">
                    <strong>{{ slide.label }}</strong>
                    <em>{{ slide.caption }}</em>
                  </span>
                </button>
              </li>
            </ul>

            <div class="pv-actions">
              <button v-if="preview.device === 'browser'" type="button" class="pv-cta" @click="emit('admin')">
                登录
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M5 12h13M12.5 6.5 18 12l-5.5 5.5" />
                </svg>
              </button>
              <router-link v-else class="pv-cta" to="/download" @click="close">
                下载移动端
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M5 12h13M12.5 6.5 18 12l-5.5 5.5" />
                </svg>
              </router-link>
              <button type="button" class="pv-ghost" @click="close">返回</button>
            </div>
          </div>

          <div class="pv-stage">
            <!-- 手机：iPhone 外框 + 灵动岛 + 状态栏 -->
            <div v-if="preview.device === 'phone'" class="phone">
              <div class="phone-frame">
                <div class="phone-screen">
                  <Transition :name="`shot-${direction}`" mode="out-in">
                    <img
                      :key="activeSlide.src"
                      class="shot-img"
                      :src="activeSlide.src"
                      :alt="activeSlide.label"
                      decoding="async"
                    />
                  </Transition>

                  <div class="phone-status" aria-hidden="true">
                    <span class="status-time">9:41</span>
                    <span class="status-icons">
                      <svg viewBox="0 0 18 12" width="17" height="11" fill="currentColor">
                        <rect x="0" y="8" width="3" height="4" rx="1" />
                        <rect x="5" y="6" width="3" height="6" rx="1" />
                        <rect x="10" y="3.5" width="3" height="8.5" rx="1" />
                        <rect x="15" y="1" width="3" height="11" rx="1" />
                      </svg>
                      <svg viewBox="0 0 16 12" width="15" height="11" fill="currentColor">
                        <path d="M8 11.2 1.3 4.5a9.4 9.4 0 0 1 13.4 0L8 11.2z" />
                      </svg>
                      <svg viewBox="0 0 26 12" width="24" height="11" fill="none">
                        <rect x="0.7" y="0.7" width="21" height="10.6" rx="3.2" stroke="currentColor" stroke-opacity="0.5" stroke-width="1.2" />
                        <rect x="2.4" y="2.4" width="15" height="7.2" rx="2" fill="currentColor" />
                        <path d="M23.4 4.2v3.6c1.1-.3 1.6-1 1.6-1.8s-.5-1.5-1.6-1.8z" fill="currentColor" fill-opacity="0.5" />
                      </svg>
                    </span>
                  </div>

                  <span class="phone-island" aria-hidden="true"></span>
                  <span class="phone-home" aria-hidden="true"></span>
                </div>
              </div>
              <span class="phone-btn phone-btn-a" aria-hidden="true"></span>
              <span class="phone-btn phone-btn-b" aria-hidden="true"></span>
              <span class="phone-btn phone-btn-c" aria-hidden="true"></span>
              <span class="phone-glow" aria-hidden="true"></span>
            </div>

            <!-- 管理端：浏览器窗口外框 -->
            <div v-else class="browser">
              <div class="browser-chrome">
                <span class="browser-dots" aria-hidden="true">
                  <i></i><i></i><i></i>
                </span>
                <div class="browser-tabs" aria-label="控制台页面">
                  <button
                    v-for="(slide, index) in preview.slides"
                    :key="slide.src"
                    type="button"
                    :aria-pressed="index === shownIndex"
                    :class="{ 'is-active': index === shownIndex }"
                    @mouseenter="hoverIndex = index"
                    @mouseleave="hoverIndex = null"
                    @focus="hoverIndex = index"
                    @blur="hoverIndex = null"
                    @click="go(index)"
                  >
                    {{ slide.label }}
                  </button>
                </div>
                <span class="browser-live">
                  <span class="browser-live-dot"></span>
                  交互预览
                </span>
              </div>
              <div class="browser-body">
                <Transition :name="`shot-${direction}`" mode="out-in">
                  <img
                    :key="activeSlide.src"
                    class="browser-img"
                    :src="activeSlide.src"
                    :alt="activeSlide.label"
                    decoding="async"
                  />
                </Transition>
              </div>
              <span class="browser-glow" aria-hidden="true"></span>
            </div>

            <div v-if="preview.device === 'phone' && preview.slides.length > 1" class="pv-thumbs">
              <button
                v-for="(slide, index) in preview.slides"
                :key="slide.src"
                type="button"
                :class="{ 'is-active': index === shownIndex }"
                :aria-label="slide.label"
                @mouseenter="hoverIndex = index"
                @mouseleave="hoverIndex = null"
                @focus="hoverIndex = index"
                @blur="hoverIndex = null"
                @click="go(index)"
              >
                <img :src="slide.src" alt="" loading="lazy" />
              </button>
            </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts">
export interface PreviewSlide {
  src: string
  label: string
  caption: string
}

export interface RolePreview {
  device: 'phone' | 'browser'
  tag: string
  title: string
  desc: string
  slides: PreviewSlide[]
}
</script>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  preview: RolePreview | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'admin'): void
}>()

const activeIndex = ref(0)
const hoverIndex = ref<number | null>(null)
const direction = ref<'next' | 'prev'>('next')
const closeBtn = ref<HTMLButtonElement | null>(null)

/** 悬停在缩略图 / 标签上时临时预览该图，移开后回到已选中的一张 */
const shownIndex = computed(() => {
  const total = props.preview?.slides.length ?? 0
  const hover = hoverIndex.value
  return hover !== null && hover >= 0 && hover < total ? hover : activeIndex.value
})

const activeSlide = computed(
  () => props.preview?.slides[shownIndex.value] ?? props.preview?.slides[0] ?? { src: '', label: '', caption: '' }
)

watch(shownIndex, (next, prev) => {
  if (next === prev) return
  direction.value = next >= prev ? 'next' : 'prev'
})

function go(index: number) {
  activeIndex.value = index
}

function close() {
  emit('update:open', false)
}

function onKeydown(event: KeyboardEvent) {
  if (!props.open) return
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key === 'ArrowRight' && props.preview && props.preview.slides.length > 1) {
    go((activeIndex.value + 1) % props.preview.slides.length)
  }
  if (event.key === 'ArrowLeft' && props.preview && props.preview.slides.length > 1) {
    go((activeIndex.value - 1 + props.preview.slides.length) % props.preview.slides.length)
  }
}

let previousOverflow = ''
watch(
  () => props.open,
  async (open) => {
    if (open) {
      activeIndex.value = 0
      hoverIndex.value = null
      direction.value = 'next'
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', onKeydown)
      props.preview?.slides.forEach((slide) => {
        const img = new Image()
        img.src = slide.src
      })
      await nextTick()
      closeBtn.value?.focus({ preventScroll: true })
    } else {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKeydown)
    }
  }
)

onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.pv {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(249, 250, 253, 0.88);
  backdrop-filter: saturate(180%) blur(26px);
  -webkit-backdrop-filter: saturate(180%) blur(26px);
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #111114;
  overflow: hidden;
}

/* 独立滚动容器：关闭按钮固定在视口，不随内容滚走 */
.pv-scroll {
  position: absolute;
  inset: 0;
  display: flex;
  padding: clamp(20px, 4vh, 44px) 24px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.pv-enter-active,
.pv-leave-active {
  transition: opacity 0.4s ease;
}

.pv-enter-active .pv-panel,
.pv-leave-active .pv-panel {
  transition: opacity 0.45s ease, transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.pv-enter-from,
.pv-leave-to {
  opacity: 0;
}

.pv-enter-from .pv-panel,
.pv-leave-to .pv-panel {
  opacity: 0;
  transform: translateY(22px) scale(0.965);
}

.pv-close {
  position: absolute;
  top: 20px;
  right: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(17, 17, 20, 0.1);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.82);
  color: #5f6068;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.pv-close:hover {
  background: #ffffff;
  color: #111114;
  transform: rotate(90deg);
}

.pv-close:focus-visible,
.pv-list button:focus-visible,
.pv-thumbs button:focus-visible,
.pv-cta:focus-visible,
.pv-ghost:focus-visible {
  outline: 2px solid #4d6bfe;
  outline-offset: 3px;
}

.pv-panel {
  display: grid;
  grid-template-columns: minmax(0, 0.82fr) minmax(0, 1fr);
  align-items: center;
  gap: clamp(32px, 5vw, 72px);
  width: 100%;
  max-width: 1060px;
  margin: auto;
}

/* ===== 文案区 ===== */
.pv-copy {
  min-width: 0;
}

/* 打开时文案错峰上浮，和手机一起进入 */
.pv-kicker,
.pv-title,
.pv-desc,
.pv-list,
.pv-actions {
  animation: pvRise 0.62s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.pv-title {
  animation-delay: 0.07s;
}

.pv-desc {
  animation-delay: 0.12s;
}

.pv-list {
  animation-delay: 0.18s;
}

.pv-actions {
  animation-delay: 0.24s;
}

@keyframes pvRise {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.pv-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #8c8d96;
  text-transform: uppercase;
}

.pv-kicker-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d6bfe, #7c5cff);
}

.pv-title {
  margin: 14px 0 0;
  font-size: clamp(28px, 3.2vw, 38px);
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.9px;
}

.pv-desc {
  margin: 14px 0 0;
  max-width: 380px;
  font-size: 13px;
  line-height: 1.85;
  color: #71727b;
}

.pv-list {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid rgba(17, 17, 20, 0.08);
}

.pv-list li {
  border-bottom: 1px solid rgba(17, 17, 20, 0.08);
}

.pv-list button {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 15px 10px 16px 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  font: inherit;
  text-align: left;
  color: #a0a1a9;
  cursor: pointer;
  transition: background 0.25s ease, color 0.25s ease;
}

.pv-list button:hover {
  background: rgba(17, 17, 20, 0.03);
  color: #5f6068;
}

.pv-list button.is-active {
  color: #111114;
  background: rgba(77, 107, 254, 0.06);
}

.pv-no {
  flex-shrink: 0;
  padding-top: 2px;
  font-size: 10.5px;
  font-weight: 650;
  letter-spacing: 1px;
  color: #b0b1b9;
  transition: color 0.25s ease;
}

.pv-list button.is-active .pv-no {
  color: #4d6bfe;
}

.pv-text {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.pv-text strong {
  font-size: 14.5px;
  font-weight: 650;
  letter-spacing: 0.1px;
}

.pv-text em {
  font-style: normal;
  font-size: 12px;
  line-height: 1.7;
  color: #8c8d96;
}

.pv-list button.is-active .pv-text em {
  color: #71727b;
}

.pv-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 26px;
}

.pv-cta {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 11px 20px;
  border: none;
  border-radius: 999px;
  background: #111114;
  color: #ffffff;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.pv-cta:hover {
  background: #000000;
  transform: translateY(-2px);
}

.pv-cta svg {
  transition: transform 0.2s ease;
}

.pv-cta:hover svg {
  transform: translateX(2px);
}

.pv-ghost {
  padding: 11px 18px;
  border: 1px solid rgba(17, 17, 20, 0.14);
  border-radius: 999px;
  background: #ffffff;
  color: #5f6068;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease;
}

.pv-ghost:hover {
  border-color: #111114;
  color: #111114;
}

/* ===== 舞台：iPhone ===== */
.pv-stage {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  min-width: 0;
}

.phone {
  position: relative;
  display: flex;
  justify-content: center;
}

.phone-frame {
  position: relative;
  padding: 9px;
  border-radius: 54px;
  background: linear-gradient(150deg, #4a4a52 0%, #1d1d22 22%, #0c0c0f 58%, #2b2b31 100%);
  box-shadow:
    0 44px 90px -34px rgba(19, 24, 58, 0.55),
    0 18px 40px -22px rgba(19, 24, 58, 0.4),
    inset 0 0 0 1px rgba(255, 255, 255, 0.16),
    inset 0 1px 1px rgba(255, 255, 255, 0.4);
}

.phone-screen {
  position: relative;
  height: clamp(420px, 60vh, 566px);
  aspect-ratio: 390 / 844;
  overflow: hidden;
  border-radius: 46px;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.5);
}

.shot-img {
  position: absolute;
  top: 40px;
  left: 0;
  width: 100%;
  height: calc(100% - 40px);
  object-fit: cover;
  object-position: top center;
  border-radius: inherit;
}

.shot-next-enter-active,
.shot-next-leave-active,
.shot-prev-enter-active,
.shot-prev-leave-active {
  transition: opacity 0.24s ease, transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
}

.shot-next-enter-from {
  opacity: 0;
  transform: translateX(12%) scale(1.015);
}

.shot-next-leave-to {
  opacity: 0;
  transform: translateX(-9%);
}

.shot-prev-enter-from {
  opacity: 0;
  transform: translateX(-12%) scale(1.015);
}

.shot-prev-leave-to {
  opacity: 0;
  transform: translateX(9%);
}

.phone-status {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 40px;
  padding: 0 26px 0 30px;
  color: #111114;
  pointer-events: none;
}

.status-time {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.status-icons {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #111114;
}

.phone-island {
  position: absolute;
  top: 9px;
  left: 50%;
  z-index: 4;
  width: 74px;
  height: 21px;
  border-radius: 999px;
  background: #050506;
  transform: translateX(-50%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
}

.phone-home {
  position: absolute;
  bottom: 7px;
  left: 50%;
  z-index: 4;
  width: 116px;
  height: 4px;
  border-radius: 999px;
  background: rgba(17, 17, 20, 0.5);
  transform: translateX(-50%);
}

.phone-btn {
  position: absolute;
  width: 3px;
  border-radius: 2px;
  background: linear-gradient(180deg, #3a3a42, #16161a);
}

.phone-btn-a {
  top: 108px;
  left: -3px;
  height: 28px;
}

.phone-btn-b {
  top: 150px;
  left: -3px;
  height: 52px;
}

.phone-btn-c {
  top: 128px;
  right: -3px;
  height: 76px;
}

.phone-glow {
  position: absolute;
  inset: 14% -22% -18%;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(77, 107, 254, 0.22), rgba(124, 92, 255, 0.06) 62%, transparent 78%);
  filter: blur(18px);
}

/* ===== 舞台：浏览器 ===== */
.browser {
  position: relative;
  width: 100%;
  max-width: 600px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow:
    0 44px 90px -40px rgba(19, 24, 58, 0.5),
    0 16px 34px -20px rgba(19, 24, 58, 0.35),
    0 0 0 1px rgba(17, 17, 20, 0.1);
  overflow: hidden;
}

.browser-chrome {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(17, 17, 20, 0.07);
  background: linear-gradient(180deg, #fbfbfd, #f4f4f7);
}

.browser-dots {
  display: inline-flex;
  gap: 6px;
  flex-shrink: 0;
}

.browser-dots i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #d9dae0;
}

/* 可点击 / 可悬停预览的控制台页签，让管理端预览真正可交互 */
.browser-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.browser-tabs::-webkit-scrollbar {
  display: none;
}

.browser-tabs button {
  padding: 5px 10px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #85868e;
  font: inherit;
  font-size: 10.5px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.22s ease, color 0.22s ease, box-shadow 0.22s ease;
}

.browser-tabs button:hover {
  background: rgba(17, 17, 20, 0.05);
  color: #111114;
}

.browser-tabs button.is-active {
  background: #ffffff;
  color: #111114;
  box-shadow: inset 0 0 0 1px rgba(17, 17, 20, 0.07), 0 1px 3px rgba(17, 17, 20, 0.06);
}

.browser-tabs button:focus-visible {
  outline: 2px solid #4d6bfe;
  outline-offset: 2px;
}

.browser-live {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #8c8d96;
}

.browser-live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d6bfe, #7c5cff);
  animation: livePulse 2.4s ease-in-out infinite;
}

@keyframes livePulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(0.9);
  }
  50% {
    opacity: 1;
    transform: scale(1.15);
  }
}

.browser-body {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: #f6f6f9;
}

.browser-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top left;
  display: block;
}

.browser-glow {
  position: absolute;
  inset: 10% -12% -12%;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(77, 107, 254, 0.2), transparent 76%);
  filter: blur(20px);
}

/* ===== 缩略图 ===== */
.pv-thumbs {
  display: flex;
  align-items: center;
  gap: 9px;
}

.pv-thumbs button {
  width: 44px;
  height: 92px;
  padding: 0;
  border: 1px solid rgba(17, 17, 20, 0.1);
  border-radius: 9px;
  background: #ffffff;
  overflow: hidden;
  cursor: pointer;
  opacity: 0.7;
  transform: translateY(0);
  transition:
    opacity 0.25s ease,
    transform 0.35s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.25s ease,
    border-color 0.25s ease;
}

.pv-thumbs button:hover {
  opacity: 0.85;
}

.pv-thumbs button.is-active {
  opacity: 1;
  transform: translateY(-3px);
  border-color: rgba(77, 107, 254, 0.5);
  box-shadow: 0 10px 22px -12px rgba(38, 52, 118, 0.6);
}

.pv-thumbs img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top;
  display: block;
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .pv-panel {
    grid-template-columns: minmax(0, 1fr);
    gap: 26px;
  }

  .pv-stage {
    order: -1;
    width: 100%;
  }

  .phone-screen {
    height: min(52vh, 440px);
  }

  .pv-copy {
    text-align: left;
    padding-bottom: 8px;
  }

  .pv-title {
    font-size: 26px;
  }

  .pv-desc {
    max-width: none;
  }

  .pv-list {
    margin-top: 20px;
  }

  .pv-list button {
    padding: 13px 8px 14px 8px;
  }
}

@media (max-width: 560px) {
  .pv-scroll {
    padding: 16px 18px 28px;
  }

  .pv-close {
    top: 14px;
    right: 14px;
    width: 34px;
    height: 34px;
  }

  .phone-screen {
    height: min(42vh, 340px);
  }

  .pv-thumbs button {
    width: 34px;
    height: 72px;
  }

  .browser {
    max-width: 100%;
  }

  .browser-live {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .browser-live-dot {
    animation: none;
  }

  .pv-kicker,
  .pv-title,
  .pv-desc,
  .pv-list,
  .pv-actions {
    animation: none;
  }

  .pv-enter-active,
  .pv-leave-active,
  .pv-enter-active .pv-panel,
  .pv-leave-active .pv-panel,
  .shot-next-enter-active,
  .shot-next-leave-active,
  .shot-prev-enter-active,
  .shot-prev-leave-active,
  .pv-thumbs button {
    transition: none;
  }
}
</style>
