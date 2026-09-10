<template>
  <div class="login-scene">
    <canvas ref="canvasRef" class="bg-canvas"></canvas>
    <div class="particles">
      <div v-for="n in 60" :key="'p1-'+n" class="particle" :style="particleStyle(n)"></div>
    </div>

    <!-- 登录页（底层） -->
    <div class="login-layer">
      <div class="brand">
        <div class="brand-icon-wrap">
          <img src="/images/mascot.png" alt="绵小城" class="brand-mascot" />
        </div>
        <div class="brand-text">
          <h1 class="brand-title">绵小城</h1>
          <p class="brand-sub">校园智能小助手</p>
        </div>
      </div>
      <div class="login-card">
        <h2 class="card-title">欢迎回来</h2>
        <p class="card-desc">学号 / 工号登录</p>
        <el-form ref="formRef" :model="form" :rules="rules" @keyup.enter="handleLogin">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="学号/工号" class="custom-input" size="large" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="密码" show-password class="custom-input" size="large" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" class="login-btn" size="large" @click="handleLogin">
              {{ loading ? '登录中...' : '进入绵小城' }}
            </el-button>
          </el-form-item>
        </el-form>
        <div class="login-footer">
          <span>绵阳城市学院</span>
          <span class="dot-sep">·</span>
          <span>Mianyang City College</span>
        </div>
      </div>
    </div>

    <!-- 产品介绍覆盖层 -->
    <div v-show="showIntro" class="intro" :class="{ hidden: introHidden }">
      <canvas ref="bg2Ref" class="bg-canvas" style="z-index:1"></canvas>
      <div class="particles" style="z-index:1">
        <div v-for="n in 60" :key="'p2-'+n" class="particle" :style="particleStyle(n + 100)"></div>
      </div>
      <div ref="trackRef" class="track">
        <section class="section">
          <div class="hero">
            <img src="/images/mascot.png" class="hero-mascot" alt="绵小城" />
            <h1 class="hero-title">你好，新同学</h1>
            <div class="hero-slogan"><em>绵小城</em>，你的校园 AI 伙伴</div>
            <div class="hero-sub">学习 · 生活 · 办事，一个助手全搞定</div>
          </div>
        </section>
        <section class="section">
          <div class="inner">
            <div class="copy">
              <span class="tag">SMART Q&amp;A</span>
              <h2 class="section-title">有问必答，<span class="hl">随时在线</span></h2>
              <p class="desc">学习卡壳了？生活迷茫了？随时问绵小城，<b>秒级响应</b>，全年无休，比辅导员回消息还快！</p>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="inner">
            <div class="copy">
              <span class="tag">VOICE CHAT</span>
              <h2 class="section-title">想说就说，<span class="hl2">声临其境</span></h2>
              <p class="desc">打字太慢？直接开麦！和绵小城<b>实时语音聊天</b>，像和老朋友煲电话粥，亲切又自然。</p>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="inner">
            <div class="copy">
              <span class="tag">CAMPUS TOUR</span>
              <h2 class="section-title">校园这么大，<span class="hl3">带你逛遍</span></h2>
              <p class="desc"><b>VR 全景</b> + 高清风景，足不出户打卡安州、游仙每一个角落，校园美景尽收眼底。</p>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="inner">
            <div class="copy">
              <span class="tag">STUDY CENTER</span>
              <h2 class="section-title">课表成绩，<span class="hl">心里有数</span></h2>
              <p class="desc">课表、成绩分析、成长档案，<b>一屏看全</b>你的学业进度，再也不做稀里糊涂的学生。</p>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="inner">
            <div class="copy">
              <span class="tag">ONE-STOP SERVICE</span>
              <h2 class="section-title">办事少跑腿，<span class="hl2">一站搞定</span></h2>
              <p class="desc">失物招领、办事流程，校园事务统统交给绵小城，你只管<b>好好学习</b>。</p>
            </div>
          </div>
        </section>
      </div>

      <button class="skip-btn" @click="onSkip">跳过 ⏭</button>
      <div class="dots">
        <span v-for="(_, i) in sections" :key="i" class="dot" :class="{ active: currentSection === i }" @click="goTo(i)"></span>
      </div>
      <div class="hint">
        <span>{{ hintText }}</span>
        <span class="arrow"></span>
      </div>
    </div>

    <!-- 结尾过渡：探索之旅 -->
    <div v-show="showClosing" class="closing" :class="{ show: closingShow, exit: closingExit }">
      <div class="particles closing-particles">
        <div v-for="n in 20" :key="'p3-'+n" class="particle closing-particle" :style="closingParticleStyle(n)"></div>
      </div>
      <div class="closing-text">开始专属于你的探索之旅吧</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { loginApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const canvasRef = ref<HTMLCanvasElement>()
const bg2Ref = ref<HTMLCanvasElement>()
const trackRef = ref<HTMLDivElement>()
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入学号/工工号' }],
  password: [{ required: true, message: '请输入密码' }],
}

// ---- Intro state ----
const showIntro = ref(false)
const introHidden = ref(false)
const showClosing = ref(false)
const closingShow = ref(false)
const closingExit = ref(false)
const currentSection = ref(0)
const hintText = ref('向下滑动')
const sections = ref<number[]>(new Array(6).fill(0))
let introLocked = false
let wheelAcc = 0
let startY: number | null = null

function particleStyle(_n: number) {
  const size = 2 + Math.random() * 4
  return {
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${Math.random() * 8}s`,
    animationDuration: `${6 + Math.random() * 6}s`,
    opacity: 0.2 + Math.random() * 0.5,
  }
}

function closingParticleStyle(_n: number) {
  const size = 2 + Math.random() * 4
  return {
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${Math.random() * 8}s`,
    animationDuration: `${6 + Math.random() * 6}s`,
    opacity: 0.2 + Math.random() * 0.4,
  }
}

// ---- Intro navigation ----
function goTo(i: number) {
  if (i < 0 || i >= sections.value.length || introLocked) return
  introLocked = true
  currentSection.value = i
  if (trackRef.value) {
    trackRef.value.style.transform = `translateY(-${i * 100}vh)`
  }
  hintText.value = i === sections.value.length - 1 ? '继续下滑，开始探索' : '向下滑动'
  setTimeout(() => { introLocked = false }, 720)
}

function nextSection() {
  if (currentSection.value >= sections.value.length - 1) { showClosingOverlay(); return }
  goTo(currentSection.value + 1)
}

function prevSection() { goTo(currentSection.value - 1) }

function showClosingOverlay() {
  showIntro.value = true
  introHidden.value = true
  showClosing.value = true
  setTimeout(() => { closingShow.value = true }, 50)
}

function exitClosing() {
  if (!closingShow.value || closingExit.value) return
  closingShow.value = false
  closingExit.value = true
  setTimeout(() => {
    closingExit.value = false
    showClosing.value = false
    showIntro.value = false
    document.activeElement && (document.activeElement as HTMLElement).blur()
  }, 2400)
}

function onSkip() {
  if (closingShow.value) exitClosing()
  else showClosingOverlay()
}

// ---- Wheel / Touch / Key handlers ----
function onWheel(e: WheelEvent) {
  if (!showIntro.value || introHidden.value) {
    if (closingShow.value) exitClosing()
    return
  }
  e.preventDefault()
  if (introLocked) return
  wheelAcc += e.deltaY
  if (Math.abs(wheelAcc) > 40) {
    if (wheelAcc > 0) nextSection(); else prevSection()
    wheelAcc = 0
  }
}

function onTouchStart(e: TouchEvent) { startY = e.touches[0].clientY }
function onTouchEnd(e: TouchEvent) {
  if (!showIntro.value || introHidden.value) {
    if (closingShow.value) exitClosing()
    return
  }
  if (startY === null) return
  const dy = e.changedTouches[0].clientY - startY
  if (Math.abs(dy) > 50) { dy < 0 ? nextSection() : prevSection() }
  startY = null
}

function onKeydown(e: KeyboardEvent) {
  if (!showIntro.value || introHidden.value) {
    if (closingShow.value) exitClosing()
    return
  }
  if (e.key === 'ArrowDown' || e.key === 'PageDown') nextSection()
  else if (e.key === 'ArrowUp' || e.key === 'PageUp') prevSection()
}

// ---- Login ----
async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res: any = await loginApi(form)
    if (!res?.access_token) throw new Error('响应异常')
    auth.login(res.access_token, res.user)
    ElMessage.success('登录成功')
    if (res.user && !res.user.password_changed && res.user.role !== 'admin') {
      ElMessage.warning('请及时修改初始密码')
    }
    const roleMap: Record<string, string> = { student: '/student', teacher: '/teacher', admin: '/admin' }
    router.push(roleMap[res.user.role] || '/student')
  } catch (e: any) {
    if (e?.response) {
      ElMessage.error(e.response.data?.detail || `请求失败 (${e.response.status})`)
    } else if (e?.request) {
      ElMessage.error('无法连接服务器，请确认后端已启动（uvicorn app.main:app --reload）')
    } else {
      ElMessage.error('登录失败，请重试')
    }
  } finally {
    loading.value = false
  }
}

// ---- Canvas starfield ----
let animId = 0
const mouse = { x: -9999, y: -9999 }

function initStarfield(canvas: HTMLCanvasElement, count: number) {
  const ctx = canvas.getContext('2d')!
  const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
  resize()
  window.addEventListener('resize', resize)

  const onMouse = (e: MouseEvent) => { mouse.x = e.clientX; mouse.y = e.clientY }
  const onLeave = () => { mouse.x = -9999; mouse.y = -9999 }
  window.addEventListener('mousemove', onMouse)
  window.addEventListener('mouseleave', onLeave)

  const dots: { x: number; y: number; vx: number; vy: number; r: number; baseVx: number; baseVy: number }[] = []
  for (let i = 0; i < count; i++) {
    const baseVx = (Math.random() - 0.5) * 0.5
    const baseVy = (Math.random() - 0.5) * 0.5
    dots.push({
      x: Math.random() * canvas.width, y: Math.random() * canvas.height,
      vx: baseVx, vy: baseVy, r: 1 + Math.random() * 2,
      baseVx, baseVy,
    })
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    for (let i = 0; i < dots.length; i++) {
      const d = dots[i]
      const dx = d.x - mouse.x, dy = d.y - mouse.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 200 && dist > 0) {
        const force = (200 - dist) / 200 * 2
        d.vx += (dx / dist) * force * 0.15
        d.vy += (dy / dist) * force * 0.15
      }
      d.vx += (d.baseVx - d.vx) * 0.01
      d.vy += (d.baseVy - d.vy) * 0.01
      d.x += d.vx; d.y += d.vy
      if (d.x < 0) d.x = canvas.width
      if (d.x > canvas.width) d.x = 0
      if (d.y < 0) d.y = canvas.height
      if (d.y > canvas.height) d.y = 0

      ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(64,158,255,0.25)'; ctx.fill()
      for (let j = i + 1; j < dots.length; j++) {
        const dx2 = dots[i].x - dots[j].x, dy2 = dots[i].y - dots[j].y
        const dist2 = Math.sqrt(dx2 * dx2 + dy2 * dy2)
        if (dist2 < 150) {
          ctx.beginPath(); ctx.moveTo(dots[i].x, dots[i].y); ctx.lineTo(dots[j].x, dots[j].y)
          ctx.strokeStyle = `rgba(64,158,255,${0.08 * (1 - dist2 / 150)})`
          ctx.stroke()
        }
      }
    }
    animId = requestAnimationFrame(draw)
  }
  draw()
}

onMounted(() => {
  document.body.style.overflow = 'hidden'
  const canvas = canvasRef.value!
  if (canvas) initStarfield(canvas, 110)

  if (bg2Ref.value) initStarfield(bg2Ref.value, 110)

  // First visit check
  const visited = localStorage.getItem('mianxiaocheng_intro_viewed')
  if (!visited) {
    showIntro.value = true
    localStorage.setItem('mianxiaocheng_intro_viewed', '1')
  }

  window.addEventListener('wheel', onWheel, { passive: false })
  window.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('touchend', onTouchEnd, { passive: true })
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  cancelAnimationFrame(animId)
  document.body.style.overflow = ''
  window.removeEventListener('wheel', onWheel)
  window.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('touchend', onTouchEnd)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.login-scene {
  position: relative; width: 100vw; height: 100vh; overflow: hidden;
  background: linear-gradient(135deg, #0a0a2e 0%, #1a1a4e 30%, #0d2137 70%, #0a0a2e 100%);
}
.bg-canvas { position: absolute; inset: 0; z-index: 1; }
.particles { position: absolute; inset: 0; z-index: 1; pointer-events: none; }
.particle {
  position: absolute; border-radius: 50%;
  background: radial-gradient(circle, rgba(100,180,255,0.6), transparent);
  animation: float-up linear infinite;
}
@keyframes float-up {
  0% { transform: translateY(0) scale(1); opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 0.3; }
  100% { transform: translateY(-100vh) scale(0.5); opacity: 0; }
}

/* ============ 登录层 ============ */
.login-layer {
  position: relative; z-index: 2; display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%; gap: 60px; padding: 40px;
}
.brand { text-align: center; animation: fadeUp 1s ease-out; }
.brand-icon-wrap {
  position: relative; width: 160px; height: 160px; margin: 0 auto 28px;
  display: flex; align-items: center; justify-content: center;
}
.brand-mascot { width: 140px; height: 140px; object-fit: contain; animation: mascot-float 3s ease-in-out infinite; }
@keyframes mascot-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }
.brand-title { font-size: 48px; font-weight: 800; color: #fff; margin: 0; letter-spacing: 4px; text-shadow: 0 2px 20px rgba(64,158,255,0.3); }
.brand-sub { font-size: 16px; color: rgba(255,255,255,0.5); margin-top: 8px; letter-spacing: 2px; }

.login-card {
  width: 380px; padding: 40px; border-radius: 20px;
  background: rgba(255,255,255,0.06); backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.1);
  animation: fadeUp 1s ease-out 0.2s both;
}
@keyframes fadeUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.card-title { font-size: 24px; font-weight: 700; color: #fff; margin: 0 0 4px; }
.card-desc { font-size: 14px; color: rgba(255,255,255,0.4); margin: 0 0 28px; }

.custom-input :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.12);
  border-radius: 12px; box-shadow: none !important; padding: 2px 16px;
}
.custom-input :deep(.el-input__inner) { color: #fff; height: 48px; caret-color: transparent; }
.custom-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.3); }
.custom-input :deep(.el-input__wrapper.is-focus) { border-color: rgba(64,158,255,0.5); }
.custom-input :deep(.el-input__wrapper.is-focus .el-input__inner) { caret-color: auto; }

.login-btn {
  width: 100%; height: 48px; border-radius: 12px; font-size: 16px;
  background: linear-gradient(135deg, #409eff, #6366f1); border: none;
  transition: transform .2s, box-shadow .2s;
}
.login-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(64,158,255,0.35); }

.login-footer { text-align: center; font-size: 12px; color: rgba(255,255,255,0.25); margin-top: 20px; }
.dot-sep { margin: 0 6px; }

/* ============ 介绍覆盖层 ============ */
.intro {
  position: absolute; inset: 0; z-index: 10; overflow: hidden;
  background: linear-gradient(160deg, #0a0a2e 0%, #151348 35%, #0d2137 75%, #0a0a2e 100%);
  transition: opacity 0.8s ease, visibility 0.8s;
}
.intro.hidden { opacity: 0; visibility: hidden; pointer-events: none; }

.track { position: absolute; inset: 0; z-index: 2; transition: transform 0.7s cubic-bezier(0.65,0,0.35,1); }
.section {
  position: relative; width: 100vw; height: 100vh;
  display: flex; align-items: center; justify-content: center; padding: 60px 80px;
}
.inner { width: 100%; max-width: 800px; margin: 0 auto; }
.copy { max-width: 640px; margin: 0 auto; text-align: center; }
.tag { display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 12px; letter-spacing: 3px; font-weight: 700; margin-bottom: 22px; color: #fff; border: 1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.08); }
.section-title { font-size: 54px; font-weight: 900; line-height: 1.2; color: #fff; letter-spacing: 1px; margin-bottom: 24px; text-shadow: 0 4px 30px rgba(0,0,0,0.35); }
.section-title :deep(.hl) { background: linear-gradient(90deg,#ffd54d,#ff8a65); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.section-title :deep(.hl2) { background: linear-gradient(90deg,#7dd3fc,#a78bfa); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.section-title :deep(.hl3) { background: linear-gradient(90deg,#f472b6,#fb923c); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.desc { font-size: 20px; line-height: 1.9; color: rgba(255,255,255,0.75); letter-spacing: 1px; }
.desc :deep(b) { color: #ffd54d; font-weight: 800; }

.hero { text-align: center; }
.hero-mascot { width: 180px; height: 180px; object-fit: contain; animation: mascot-float 3s ease-in-out infinite; }
.hero-title {
  font-size: clamp(48px, 7vw, 72px); font-weight: 900; letter-spacing: 6px; margin: 18px 0 8px;
  background: linear-gradient(90deg,#fff,#bfe0ff,#fff); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; background-size: 200% auto; animation: shine 4s linear infinite;
}
@keyframes shine { to { background-position: 200% center; } }
.hero-slogan { font-size: 26px; font-weight: 500; color: rgba(255,255,255,0.7); margin-bottom: 16px; letter-spacing: 2px; }
.hero-slogan em { font-style: normal; background: linear-gradient(90deg,#ffd54d,#ff8a65,#f472b6); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.hero-sub { font-size: 18px; color: rgba(255,255,255,0.6); letter-spacing: 3px; }

.dots { position: absolute; right: 34px; top: 50%; transform: translateY(-50%); z-index: 20; display: flex; flex-direction: column; gap: 12px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: rgba(255,255,255,0.22); transition: all 0.3s; cursor: pointer; display: block; }
.dot.active { background: linear-gradient(135deg,#409eff,#a78bfa); height: 26px; border-radius: 5px; }
.skip-btn {
  position: absolute; top: 28px; right: 28px; z-index: 20; padding: 8px 20px; border-radius: 20px;
  font-size: 13px; color: rgba(255,255,255,0.75); background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.16); cursor: pointer; backdrop-filter: blur(10px);
}
.skip-btn:hover { color: #fff; background: rgba(255,255,255,0.16); }
.hint {
  position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%); z-index: 20;
  color: rgba(255,255,255,0.45); font-size: 11px; font-weight: 300; letter-spacing: 3px;
  display: flex; flex-direction: column; align-items: center; gap: 6px;
}
.hint .arrow {
  width: 13px; height: 13px; border-right: 1.5px solid rgba(255,255,255,0.55);
  border-bottom: 1.5px solid rgba(255,255,255,0.55); transform: rotate(45deg); animation: bob 1.6s ease-in-out infinite;
}
@keyframes bob { 0%,100% { transform: rotate(45deg) translate(0,0); opacity: 0.4; } 50% { transform: rotate(45deg) translate(6px,6px); opacity: 1; } }

/* ============ 结尾过渡层 ============ */
.closing {
  position: absolute; inset: 0; z-index: 30;
  background: linear-gradient(160deg, #0a0a2e 0%, #151348 35%, #0d2137 75%, #0a0a2e 100%);
  opacity: 0; visibility: hidden; transition: opacity 1.2s ease, visibility 1.2s;
  caret-color: transparent; cursor: default;
  display: flex; align-items: center; justify-content: center;
}
.closing.show { opacity: 1; visibility: visible; }
.closing.exit { opacity: 0; }
.closing-particles { position: absolute; inset: 0; pointer-events: none; z-index: 0; }
.closing-particle {
  background: radial-gradient(circle, rgba(167,139,250,0.45), rgba(244,114,182,0.2), transparent);
}
.closing-text {
  position: relative; z-index: 1;
  font-size: clamp(22px, 4.8vw, 60px); font-weight: 900; text-align: center; line-height: 1.4;
  letter-spacing: 14px; white-space: nowrap;
  background: linear-gradient(100deg, #a78bfa, #f472b6, #fb923c, #facc15, #a78bfa);
  background-size: 300% auto;
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  opacity: 0; transform: scale(0.7); filter: blur(10px);
  caret-color: transparent; user-select: none;
}
.closing.show .closing-text {
  animation: ct-in 1s cubic-bezier(0.22,1,0.36,1) forwards, ct-shine 3.5s linear 1s infinite;
}
.closing.exit .closing-text { animation: ct-out 2.2s ease forwards; }
@keyframes ct-in { to { opacity: 1; transform: scale(1); filter: blur(0); } }
@keyframes ct-out { to { opacity: 0; transform: scale(2.5); filter: blur(12px); } }
@keyframes ct-shine { to { background-position: 300% center; } }

/* ============ 响应式 ============ */
@media (max-width: 860px) {
  .inner { padding: 0 16px; }
  .section { padding: 40px 24px; }
  .section-title { font-size: 34px; }
  .desc { font-size: 16px; }
  .hero-title { font-size: 54px; }
  .dots { right: 14px; }
}
@media (max-width: 767px) {
  .login-layer { flex-direction: column; gap: 20px; padding: 20px 16px; transform: translateY(-20px); }
  .brand { display: flex; align-items: center; gap: 16px; text-align: left; }
  .brand-icon-wrap { width: 72px; height: 72px; margin-bottom: 0; flex-shrink: 0; }
  .brand-mascot { width: 72px; height: 72px; }
  .brand-title { font-size: 28px; letter-spacing: 2px; margin: 0; }
  .brand-sub { font-size: 13px; margin-top: 4px; }
  .login-card { width: 100%; max-width: 340px; padding: 24px 20px; border-radius: 16px; }
  .card-title { font-size: 20px; }
  .card-desc { font-size: 13px; margin-bottom: 20px; }
  .custom-input :deep(.el-input__inner) { height: 42px; }
  .login-btn { height: 42px; font-size: 15px; border-radius: 10px; }
}
</style>
