<template>
  <div class="login-scene">
    <canvas ref="canvasRef" class="bg-canvas"></canvas>
    <div class="particles">
      <div v-for="n in 60" :key="n" class="particle" :style="particleStyle(n)"></div>
    </div>
    <div class="login-layer">
      <div class="brand">
        <div class="brand-icon-wrap">
          <img src="/images/mascot.png" alt="绵小城" class="brand-mascot" />
        </div>
        <h1 class="brand-title">绵小城</h1>
        <p class="brand-sub">智慧校园 · AI 服务平台</p>
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
              {{ loading ? '登录中...' : '进入智慧校园' }}
            </el-button>
          </el-form-item>
        </el-form>
        <div class="login-footer">
          <span>绵阳城市学院</span>
          <span class="dot">·</span>
          <span>Mianyang City College</span>
        </div>
      </div>
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
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入学号/工号' }],
  password: [{ required: true, message: '请输入密码' }],
}

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

let animId = 0
const mouse = { x: -9999, y: -9999 }

onMounted(() => {
  document.body.style.overflow = 'hidden'
  const canvas = canvasRef.value!
  if (!canvas) return
  const ctx = canvas.getContext('2d')!
  const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
  resize(); window.addEventListener('resize', resize)

  const onMouse = (e: MouseEvent) => { mouse.x = e.clientX; mouse.y = e.clientY }
  const onLeave = () => { mouse.x = -9999; mouse.y = -9999 }
  window.addEventListener('mousemove', onMouse)
  window.addEventListener('mouseleave', onLeave)

  const dots: { x: number; y: number; vx: number; vy: number; r: number; baseVx: number; baseVy: number }[] = []
  for (let i = 0; i < 120; i++) {
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
})

onUnmounted(() => {
  cancelAnimationFrame(animId)
  document.body.style.overflow = ''
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

.login-layer {
  position: relative; z-index: 2; display: flex; align-items: center; justify-content: center;
  width: 100%; height: 100%; gap: 60px; padding: 40px;
}

.brand { text-align: center; animation: fadeUp 1s ease-out; }
.brand-icon-wrap {
  position: relative;
  width: 160px;
  height: 160px;
  margin: 0 auto 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-mascot {
  width: 140px;
  height: 140px;
  object-fit: contain;
  animation: mascot-float 3s ease-in-out infinite;
}

@keyframes mascot-float {
  0%, 100% { 
    transform: translateY(0); 
  }
  50% { 
    transform: translateY(-12px); 
  }
}

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
.custom-input :deep(.el-input__inner) { color: #fff; height: 48px; }
.custom-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.3); }

.login-btn {
  width: 100%; height: 48px; border-radius: 12px; font-size: 16px;
  background: linear-gradient(135deg, #409eff, #6366f1); border: none;
  transition: transform .2s, box-shadow .2s;
}
.login-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(64,158,255,0.35); }

.login-footer {
  text-align: center; font-size: 12px; color: rgba(255,255,255,0.25); margin-top: 20px;
}
.dot { margin: 0 6px; }

@media (max-width: 767px) {
  .login-layer { flex-direction: column; gap: 20px; padding: 20px 16px; transform: translateY(-20px); }
  .brand-icon-wrap { width: 80px; height: 80px; margin-bottom: 12px; }
  .brand-mascot { width: 64px; height: 64px; }
  .brand-title { font-size: 26px; letter-spacing: 2px; }
  .brand-sub { font-size: 13px; margin-top: 4px; }
  .login-card { width: 100%; max-width: 340px; padding: 24px 20px; border-radius: 16px; }
  .card-title { font-size: 20px; }
  .card-desc { font-size: 13px; margin-bottom: 20px; }
  .custom-input :deep(.el-input__inner) { height: 42px; }
  .login-btn { height: 42px; font-size: 15px; border-radius: 10px; }
}
</style>
