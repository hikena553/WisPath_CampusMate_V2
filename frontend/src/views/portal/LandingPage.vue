<template>
  <div class="site-page">
    <header
      class="site-nav"
      :class="{ 'is-scrolled': navScrolled }"
      :style="{ '--nav-progress': navProgress }"
    >
      <div class="site-nav-inner">
        <router-link class="nav-brand" to="/">
          <img :src="siteLogo" :alt="siteName" class="nav-logo" />
          <span class="nav-name">{{ siteName }}</span>
        </router-link>

        <nav class="nav-links" aria-label="页面导航">
          <a href="#capabilities">平台能力</a>
          <a href="#roles">角色工作台</a>
          <div class="nav-download">
            <router-link to="/download">移动端下载</router-link>
            <div class="nav-qr-pop">
              <div class="nav-qr-card">
                <QrCode :value="downloadPageUrl" :size="112" />
                <div class="nav-qr-copy">
                  <strong>扫码下载移动端</strong>
                  <span>教师端 / 学生端统一安装包</span>
                  <router-link to="/download">前往下载页</router-link>
                </div>
              </div>
            </div>
          </div>
          <button type="button" class="nav-login" @click="goAdmin">
            {{ adminLoggedIn ? '进入后台' : '管理员登录' }}
          </button>
        </nav>
      </div>
    </header>

    <main class="site-main">
      <section class="hero">
        <span class="hero-badge">
          <span class="badge-dot"></span>
          绵阳城市学院 · 智慧校园 AI 服务平台
        </span>

        <h1 class="hero-title">
          <span class="hero-line">让每一次校园成长</span>
          <span class="hero-accent">都被看见</span>
        </h1>

        <p class="hero-sub">
          把校园资讯、学业记录与 AI 陪伴装进口袋。<br />
          教师端与学生端共用一个移动客户端，管理员通过网页控制台管理全站。
        </p>

        <div class="entry-card">
          <div class="entry-admin">
            <span class="entry-label">ADMIN CONSOLE</span>
            <h2>管理员控制台</h2>
            <p>处理账号与内容、维护站点配置、跟进密码重置与危机预警。</p>
            <button type="button" class="admin-btn" @click="goAdmin">
              <span>{{ adminLoggedIn ? '进入管理后台' : '管理员登录' }}</span>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 12h13M12.5 6.5 18 12l-5.5 5.5" />
              </svg>
            </button>
            <span class="admin-note">仅限管理员账号访问</span>
          </div>

          <div class="entry-divider" aria-hidden="true"></div>

          <div class="entry-qr">
            <div class="qr-frame">
              <QrCode :value="downloadPageUrl" :size="128" />
              <span class="qr-corner tl" aria-hidden="true"></span>
              <span class="qr-corner tr" aria-hidden="true"></span>
              <span class="qr-corner bl" aria-hidden="true"></span>
              <span class="qr-corner br" aria-hidden="true"></span>
            </div>
            <div class="qr-copy">
              <h3>扫码下载移动端</h3>
              <p>教师端 / 学生端统一安装包<br />支持 Android 手机</p>
              <a class="qr-direct" :href="downloadPageUrl">在手机浏览器打开下载页</a>
              <button type="button" class="qr-copy-link" @click="copyDownloadLink">
                {{ copyLabel }}
              </button>
            </div>
          </div>
        </div>

        <p class="hero-fineprint">
          {{ isLocalPreview ? '当前为本地预览，二维码指向 localhost；部署后将自动使用正式域名。' : '移动端与网页端共用同一套账号体系。' }}
        </p>
      </section>

      <section id="capabilities" class="capabilities">
        <div class="section-head reveal">
          <span class="section-label">ONE CAMPUS, ONE SPACE</span>
          <h2>一个入口，连接整个校园</h2>
          <p>从日常问答到成长记录，从办事申请到心理关怀，都在同一处完成。</p>
        </div>

        <ul class="cap-grid reveal" style="--reveal-delay: 90ms">
          <li v-for="item in capabilities" :key="item.title">
            <span class="cap-icon">
              <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path :d="item.icon" />
                <path v-if="item.icon2" :d="item.icon2" />
              </svg>
            </span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </li>
        </ul>
      </section>

      <section id="roles" class="roles">
        <div class="section-head reveal">
          <span class="section-label">THREE ROLES, ONE SYSTEM</span>
          <h2>为每个角色，留出恰好的空间</h2>
          <p>点击卡片，直接查看学生端、教师端的真实界面，以及管理员控制台。</p>
        </div>

        <div class="role-grid reveal" style="--reveal-delay: 90ms">
          <button
            v-for="role in roles"
            :key="role.name"
            type="button"
            class="role-card"
            aria-haspopup="dialog"
            @click="openPreview(role)"
          >
            <div class="role-top">
              <span class="role-index">{{ role.index }}</span>
              <span class="role-tag">{{ role.tag }}</span>
            </div>
            <h3>{{ role.name }}</h3>
            <p class="role-desc">{{ role.desc }}</p>
            <ul class="role-points">
              <li v-for="point in role.points" :key="point">
                <span class="role-dot"></span>
                <span>{{ point }}</span>
              </li>
            </ul>
            <span class="role-link">
              <span>{{ role.preview.device === 'browser' ? '查看控制台' : '查看移动端界面' }}</span>
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M5 12h13M12.5 6.5 18 12l-5.5 5.5" />
              </svg>
            </span>
          </button>
        </div>
      </section>

      <section class="ai-section">
        <div class="ai-head reveal">
          <span class="section-label">AI INSIDE</span>
          <h2>AI 不是一个按钮，<br />而是校园的日常</h2>
          <p>{{ siteName }}把模型能力藏进具体事务里：回答问题、记录成长、发现风险，再交给合适的人。</p>
        </div>

        <ul class="ai-list reveal" style="--reveal-delay: 90ms">
          <li v-for="item in aiFeatures" :key="item.title">
            <span class="ai-no">{{ item.no }}</span>
            <div class="ai-copy">
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="flow">
        <div class="section-head reveal">
          <span class="section-label">HOW IT WORKS</span>
          <h2>三步，开始使用{{ siteName }}</h2>
          <p>管理员保留网页控制台，教师与学生统一从移动端进入。</p>
        </div>

        <ol class="flow-list reveal" style="--reveal-delay: 90ms">
          <li v-for="(step, index) in flowSteps" :key="step.title">
            <span class="flow-num">{{ index + 1 }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </li>
        </ol>
      </section>

      <section class="faq">
        <div class="faq-head reveal">
          <span class="section-label">QUESTIONS</span>
          <h2>第一次使用，可能会问</h2>
        </div>

        <div class="faq-list reveal" style="--reveal-delay: 90ms">
          <details v-for="item in faqs" :key="item.q">
            <summary>
              <span>{{ item.q }}</span>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M6 9.5 12 15l6-5.5" />
              </svg>
            </summary>
            <p>{{ item.a }}</p>
          </details>
        </div>
      </section>

      <section class="closing reveal">
        <div class="closing-copy">
          <span class="section-label">READY WHEN YOU ARE</span>
          <h2>从一个入口，走进整个校园</h2>
          <p>管理员登录网页控制台；教师与学生扫码安装移动端，使用学校分配的账号直接登录。</p>
        </div>
        <div class="closing-actions">
          <button type="button" class="admin-btn" @click="goAdmin">
            <span>{{ adminLoggedIn ? '进入管理后台' : '管理员登录' }}</span>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M5 12h13M12.5 6.5 18 12l-5.5 5.5" />
            </svg>
          </button>
          <router-link class="ghost-btn" to="/download">下载移动端</router-link>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div class="footer-brand">
        <img :src="siteLogo" :alt="siteName" class="footer-logo" />
        <span>{{ siteName }} · 智慧校园 AI 服务平台</span>
      </div>
      <div class="footer-links">
        <router-link to="/download">移动端下载</router-link>
        <button type="button" @click="goAdmin">{{ adminLoggedIn ? '管理后台' : '管理员登录' }}</button>
      </div>
      <p class="footer-copy">
        <span>© {{ year }} 绵阳城市学院 · 保留所有权利</span>
        <a
          v-if="icpNumber"
          class="footer-record"
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
        >{{ icpNumber }}</a>
        <a
          v-if="policeNumber"
          class="footer-record"
          href="https://beian.mps.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
        >{{ policeNumber }}</a>
      </p>
    </footer>

    <AppPreviewOverlay
      v-model:open="previewOpen"
      :preview="activePreview"
      @admin="openAdminFromPreview"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import QrCode from '@/components/common/QrCode.vue'
import AppPreviewOverlay from './AppPreviewOverlay.vue'

const router = useRouter()
const auth = useAuthStore()
const { siteName, siteLogo, siteBaseUrl, icpNumber, policeNumber } = useSiteConfig()

const year = new Date().getFullYear()
const adminLoggedIn = computed(() => auth.user?.role === 'admin')

/** 对外地址：管理端配置的域名优先，其次构建变量，最后回退当前访问域 */
const downloadPageUrl = computed(() => `${siteBaseUrl.value}/download`)
const isLocalPreview = computed(() => {
  try {
    return ['localhost', '127.0.0.1'].includes(new URL(downloadPageUrl.value).hostname)
  } catch {
    return true
  }
})

const navScrolled = ref(false)
const navProgress = ref(0)
let revealObserver: IntersectionObserver | null = null
let scrollFrame = 0

function syncNavState() {
  navScrolled.value = window.scrollY > 16
  const max = document.documentElement.scrollHeight - window.innerHeight
  navProgress.value = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0
  scrollFrame = 0
}

function onWindowScroll() {
  if (scrollFrame) return
  scrollFrame = window.requestAnimationFrame(syncNavState)
}

function onWindowResize() {
  onWindowScroll()
}

onMounted(() => {
  window.addEventListener('scroll', onWindowScroll, { passive: true })
  window.addEventListener('resize', onWindowResize, { passive: true })
  syncNavState()

  const revealEls = Array.from(document.querySelectorAll<HTMLElement>('.reveal'))
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduceMotion || typeof IntersectionObserver === 'undefined') {
    revealEls.forEach((el) => el.classList.add('is-visible'))
    return
  }

  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-visible')
        revealObserver?.unobserve(entry.target)
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
  )
  revealEls.forEach((el) => revealObserver?.observe(el))
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onWindowScroll)
  window.removeEventListener('resize', onWindowResize)
  if (scrollFrame) window.cancelAnimationFrame(scrollFrame)
  revealObserver?.disconnect()
})

const copyState = ref<'idle' | 'done' | 'fail'>('idle')
const copyLabel = computed(() => {
  if (copyState.value === 'done') return '链接已复制'
  if (copyState.value === 'fail') return '复制失败'
  return '复制下载链接'
})

async function copyDownloadLink() {
  try {
    await navigator.clipboard.writeText(downloadPageUrl.value)
    copyState.value = 'done'
  } catch {
    copyState.value = 'fail'
  }
  window.setTimeout(() => {
    copyState.value = 'idle'
  }, 1800)
}

function goAdmin() {
  if (adminLoggedIn.value) {
    router.push('/admin')
    return
  }
  // role=admin 让路由守卫跳过首次打开的产品介绍页，直接进入管理员登录表单
  router.push({ path: '/login', query: { role: 'admin' } })
}

const capabilities = [
  {
    title: 'AI 校园伙伴',
    desc: '随时提问课程、校历与校园服务，回答都带校内出处。',
    icon: 'M4.5 5.5h15v10h-9l-4 3.2v-3.2h-2z',
    icon2: 'M9 10.5h6',
  },
  {
    title: '成长档案',
    desc: '把课程、荣誉、实践与项目沉淀成一份可回溯的个人档案。',
    icon: 'M12 4v16M4 12h16',
    icon2: 'M7.5 7.5 12 12l4.5-4.5',
  },
  {
    title: '学业与办事',
    desc: '课表、成绩、请假与证明材料，在移动端一次办完。',
    icon: 'M5 4.5h14v15H5z',
    icon2: 'M8.5 9h7M8.5 12.5h7M8.5 16h4.5',
  },
  {
    title: '关怀与预警',
    desc: '倾听每一次情绪波动，让需要帮助的人更早被看见。',
    icon: 'M12 19s-7-4.3-7-9a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 4.7-7 9-7 9z',
  },
]

type PreviewDevice = 'phone' | 'browser'

interface PreviewSlide {
  src: string
  label: string
  caption: string
}

interface RolePreview {
  device: PreviewDevice
  tag: string
  title: string
  desc: string
  slides: PreviewSlide[]
}

interface Role {
  index: string
  tag: string
  name: string
  desc: string
  points: string[]
  preview: RolePreview
}

/** 界面截图放在 public 下，按 BASE_URL 拼接以兼容子路径部署 */
const shot = (file: string) => `${import.meta.env.BASE_URL.replace(/\/$/, '')}/images/app-preview/${file}`

const roles: Role[] = [
  {
    index: '01',
    tag: 'STUDENT',
    name: '学生端',
    desc: '把校园生活装进口袋，让每一次进步都有迹可循。',
    points: ['AI 对话与校园问答', '课表、成绩与 GPA 查询', '成长档案、作品集与技能标签', '请假、证明等办事服务'],
    preview: {
      device: 'phone',
      tag: '学生端 · 移动客户端',
      title: '校园生活，装进口袋',
      desc: '问 AI、看课表、查成绩、记成长，学生端的日常都在这台手机里完成。',
      slides: [
        { src: shot('student-home.png'), label: 'AI 对话', caption: '和绵小城聊天，课表、待办与校园服务一句话问清楚。' },
        { src: shot('student-schedule.png'), label: '学业中心', caption: '今日学业、心情记录与待办，在一个页面里收拢。' },
        { src: shot('student-grades.png'), label: '成绩分析', caption: '学分绩点、排名与学期趋势，一眼看到自己的位置。' },
        { src: shot('student-growth.png'), label: '成长轨迹', caption: '课程、竞赛与实践，沉淀成可回溯的成长档案。' },
        { src: shot('student-campus.png'), label: '校园资讯', caption: '校内通知、教学动态与学院新闻，实时更新。' },
      ],
    },
  },
  {
    index: '02',
    tag: 'TEACHER',
    name: '教师端',
    desc: '把关注落到具体的人身上，从班级概览走到一对一跟进。',
    points: ['班级概览与学生档案', '请假审批与实时消息', '心理预警与关怀记录', '家校沟通与匿名问卷'],
    preview: {
      device: 'phone',
      tag: '教师端 · 移动客户端',
      title: '把关注落到具体的人',
      desc: 'AI 先整理好今天该处理的事，教师只需要判断与跟进，从名单走进每一个学生。',
      slides: [
        { src: shot('teacher-tasks.png'), label: '今日重点', caption: 'AI 替你排好优先级，今天先做哪件事一目了然。' },
        { src: shot('teacher-students.png'), label: '学生名单', caption: '按风险分层查看学生，需要关注的人排在最前面。' },
        { src: shot('teacher-approval.png'), label: '审批管理', caption: '请假与办事申请集中处理，材料齐全再决定。' },
        { src: shot('teacher-ai.png'), label: '主动洞察', caption: '结合近 7 天数据，提前提示该联系的学生。' },
        { src: shot('teacher-portfolio.png'), label: '成长档案', caption: '横向对比全班，把每个学生的成果放在一张图上。' },
      ],
    },
  },
  {
    index: '03',
    tag: 'ADMIN',
    name: '管理端',
    desc: '把账号、内容与系统状态稳稳托住，让平台可以长期运行。',
    points: ['教师 / 学生账号与院系班级', '课程表、知识库与资讯源维护', '密码重置与反馈处理', '系统监控与站点配置'],
    preview: {
      device: 'browser',
      tag: '管理端 · 网页控制台',
      title: '整个平台的驾驶舱',
      desc: '师生规模、心理预警、内容运转与系统状态集中在一屏，管理员在电脑上完成日常运营。',
      slides: [
        { src: shot('admin-console.png'), label: '运营总览', caption: '师生规模、心理预警、内容与系统状态，一屏掌握。' },
        { src: shot('admin-students.png'), label: '学生管理', caption: '438 名学生的院系分布与风险分层，支持按班级筛选。' },
        { src: shot('admin-crisis.png'), label: '危机预警', caption: 'AI 预警闭环：发现、干预、随访到归档全程留痕。' },
        { src: shot('admin-system.png'), label: '系统监控', caption: '服务、任务与外部集成状态，异常第一时间看到。' },
      ],
    },
  },
]

const previewOpen = ref(false)
const activePreview = ref<RolePreview | null>(null)

function openPreview(role: Role) {
  activePreview.value = role.preview
  previewOpen.value = true
}

function openAdminFromPreview() {
  previewOpen.value = false
  goAdmin()
}

const aiFeatures = [
  {
    no: '01',
    title: '对话即服务',
    desc: '课程、校历、制度与办事流程都能直接问，回答带校内出处，支持语音与文件理解。',
  },
  {
    no: '02',
    title: '记录会生长',
    desc: '课程、荣誉、竞赛、实践与项目自动沉淀为成长档案，形成可回溯的个人轨迹。',
  },
  {
    no: '03',
    title: '风险更早被看见',
    desc: '结合对话与行为信号生成分级预警，让教师能及时接手、持续跟进、形成闭环。',
  },
  {
    no: '04',
    title: '数据留在校内',
    desc: '业务数据与知识库分离存储，权限按角色收敛，敏感信息只对合适的人可见。',
  },
]

const flowSteps = [
  {
    title: '管理员登录控制台',
    desc: '在电脑上打开官网，使用管理员账号进入后台，完成账号、内容与站点配置。',
  },
  {
    title: '师生安装移动端',
    desc: '扫描二维码下载 Android 安装包，教师端与学生端共用同一个客户端。',
  },
  {
    title: '用学校账号登录',
    desc: '学号 / 工号与初始密码直接登录；忘记密码可在登录页提交重置申请。',
  },
]

const faqs = [
  {
    q: '移动端和网页端是同一套账号吗？',
    a: '是。两端共用同一套账号体系与业务数据，登录后会按角色自动进入对应空间，记录实时同步。',
  },
  {
    q: '为什么官网只提供管理员登录？',
    a: '教师端与学生端统一收敛到移动客户端，网页端只为管理员保留控制台入口，避免多入口带来权限与体验上的混乱。',
  },
  {
    q: '支持 iOS 设备吗？',
    a: '当前提供 Android 安装包；iOS 设备可先通过网页端使用校园资讯、学业查询等主要功能。',
  },
  {
    q: '忘记密码怎么办？',
    a: '在登录页提交密码重置申请，系统会通知管理员处理，处理进度可在登录页查看。',
  },
  {
    q: '扫码后打不开下载页？',
    a: '请确认手机能访问官网所在域名；也可以直接在手机浏览器输入下载页地址，或复制页面上的下载链接。',
  },
]

watch(
  siteName,
  (name) => {
    document.title = `${name} — 智慧校园 AI 服务平台`
  },
  { immediate: true }
)
</script>

<style scoped>
.site-page {
  position: relative;
  min-height: 100vh;
  /* 用 clip 而不是 hidden，避免创建新的滚动容器导致吸顶导航失效 */
  overflow-x: clip;
  background: #ffffff;
  color: #111114;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ===== 顶部极光与网格：DeepSeek 式留白氛围 ===== */
.site-page::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 820px;
  pointer-events: none;
  background:
    radial-gradient(46% 44% at 50% 0%, rgba(77, 107, 254, 0.16) 0%, rgba(77, 107, 254, 0) 72%),
    radial-gradient(38% 34% at 84% 6%, rgba(124, 92, 255, 0.11) 0%, rgba(124, 92, 255, 0) 72%),
    radial-gradient(34% 28% at 12% 4%, rgba(56, 189, 248, 0.09) 0%, rgba(56, 189, 248, 0) 70%);
  transform-origin: 50% 0%;
  animation: auroraDrift 18s ease-in-out infinite alternate;
}

.site-page::after {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 720px;
  pointer-events: none;
  background-image:
    linear-gradient(to right, rgba(17, 17, 20, 0.045) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(17, 17, 20, 0.045) 1px, transparent 1px);
  background-size: 40px 40px;
  background-position: center top;
  -webkit-mask-image: radial-gradient(96% 72% at 50% 0%, #000 0%, rgba(0, 0, 0, 0.5) 46%, transparent 78%);
  mask-image: radial-gradient(96% 72% at 50% 0%, #000 0%, rgba(0, 0, 0, 0.5) 46%, transparent 78%);
}

/* ===== 导航 ===== */
/* 外层只负责吸顶与定位，透明背景让内容从两侧穿过 */
.site-nav {
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 10px 24px 0;
  pointer-events: none;
}

/* 内层在滚动时收拢成一块悬浮玻璃 */
.site-nav-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  max-width: 1180px;
  margin: 0 auto;
  padding: 10px 22px;
  pointer-events: auto;
  border: 1px solid transparent;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0);
  transition:
    max-width 0.5s cubic-bezier(0.16, 1, 0.3, 1),
    margin 0.5s cubic-bezier(0.16, 1, 0.3, 1),
    padding 0.5s cubic-bezier(0.16, 1, 0.3, 1),
    background 0.4s ease,
    border-color 0.4s ease,
    box-shadow 0.4s ease;
}

/* 底部发丝进度线：往下阅读时缓慢铺开 */
.site-nav-inner::after {
  content: '';
  position: absolute;
  left: 12%;
  right: 12%;
  bottom: 0;
  height: 1.5px;
  border-radius: 2px;
  background: linear-gradient(90deg, rgba(77, 107, 254, 0.9), rgba(124, 92, 255, 0.9));
  transform: scaleX(var(--nav-progress, 0));
  transform-origin: 0 50%;
  opacity: 0.6;
  pointer-events: none;
}

.site-nav.is-scrolled .site-nav-inner {
  max-width: 940px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.74);
  border-color: rgba(17, 17, 20, 0.08);
  box-shadow:
    0 18px 44px -30px rgba(38, 52, 118, 0.5),
    0 2px 10px -6px rgba(17, 17, 20, 0.12);
  backdrop-filter: saturate(180%) blur(18px);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.nav-brand:hover {
  opacity: 0.72;
}

.nav-logo {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: contain;
  background: #ffffff;
  box-shadow: 0 0 0 1px rgba(17, 17, 20, 0.06);
}

.nav-name {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12.5px;
  color: #5f6068;
}

/* 链接做成轻量的胶囊悬停，避免只有文字变色 */
.nav-links > a,
.nav-download > a {
  padding: 7px 12px;
  border-radius: 999px;
  color: inherit;
  text-decoration: none;
  transition: background 0.2s ease, color 0.2s ease;
}

.nav-links > a:hover,
.nav-download:hover > a {
  background: rgba(17, 17, 20, 0.05);
  color: #111114;
}

/* 移动端下载：悬停/聚焦时展开二维码浮层 */
.nav-download {
  position: relative;
  display: flex;
  align-items: center;
}

/* 透明连接区，避免鼠标从文字移动到浮层时浮层提前收起 */
.nav-download::after {
  content: '';
  position: absolute;
  top: 100%;
  left: -18px;
  right: -18px;
  height: 30px;
}

.nav-qr-pop {
  position: absolute;
  top: calc(100% + 28px);
  right: -12px;
  z-index: 30;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(-6px);
  transition: opacity 0.18s ease, transform 0.18s ease, visibility 0.18s;
}

.nav-download:hover .nav-qr-pop,
.nav-download:focus-within .nav-qr-pop {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateY(0);
}

.nav-qr-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 13px;
  width: 304px;
  padding: 13px 16px 13px 13px;
  border: 1px solid rgba(17, 17, 20, 0.09);
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 26px 60px -32px rgba(38, 52, 118, 0.36), 0 2px 8px rgba(17, 17, 20, 0.04);
}

.nav-qr-card canvas {
  flex-shrink: 0;
}

.nav-qr-card::before {
  content: '';
  position: absolute;
  top: -5px;
  right: 24px;
  width: 9px;
  height: 9px;
  background: #ffffff;
  border-left: 1px solid rgba(17, 17, 20, 0.09);
  border-top: 1px solid rgba(17, 17, 20, 0.09);
  transform: rotate(45deg);
}

.nav-qr-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.nav-qr-copy strong {
  font-size: 12.5px;
  font-weight: 650;
  color: #111114;
}

.nav-qr-copy span {
  font-size: 10.5px;
  color: #8c8d96;
}

.nav-qr-copy a {
  margin-top: 3px;
  font-size: 10.5px;
  color: #4d6bfe;
  text-decoration: none;
}

.nav-qr-copy a:hover {
  text-decoration: underline;
}

.nav-login {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  padding: 8px 16px;
  border: none;
  border-radius: 999px;
  background: #111114;
  color: #ffffff;
  font: inherit;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.2px;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.28s ease;
}

.nav-login:hover {
  background: #000000;
  transform: translateY(-1px);
  box-shadow: 0 10px 22px -14px rgba(17, 17, 20, 0.75);
}

.nav-login:active {
  transform: scale(0.98);
}

/* ===== 主视觉 ===== */
.site-main {
  position: relative;
  z-index: 1;
}

/* 滚动进入视口时淡入上浮，参考 Apple 产品页的分段揭示节奏 */
.reveal {
  opacity: 0;
  transform: translateY(34px);
  filter: blur(8px);
  transition:
    opacity 0.9s cubic-bezier(0.16, 1, 0.3, 1) var(--reveal-delay, 0ms),
    transform 0.9s cubic-bezier(0.16, 1, 0.3, 1) var(--reveal-delay, 0ms),
    filter 0.9s cubic-bezier(0.16, 1, 0.3, 1) var(--reveal-delay, 0ms);
}

.reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
  filter: blur(0);
}

.hero {
  max-width: 1040px;
  margin: 0 auto;
  padding: clamp(64px, 11vh, 118px) 28px 0;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border: 1px solid rgba(17, 17, 20, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  font-size: 11.5px;
  letter-spacing: 0.6px;
  color: #5f6068;
  opacity: 0;
  transform: translateY(10px);
  animation: rise 0.6s 0.05s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4d6bfe, #7c5cff);
}

.hero-title {
  margin: 22px 0 0;
  font-size: clamp(40px, 6.2vw, 72px);
  line-height: 1.16;
  font-weight: 700;
  letter-spacing: -1.5px;
  opacity: 0;
  transform: translateY(14px);
  animation: rise 0.72s 0.14s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.hero-line,
.hero-accent {
  display: block;
}

.hero-accent {
  /* 两行标题之间单独留白，比单纯加大行高更可控 */
  margin-top: 10px;
  background: linear-gradient(105deg, #4d6bfe 6%, #7c5cff 56%, #3f8cff 96%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: accentFlow 9s ease-in-out infinite alternate;
}

.hero-sub {
  margin: 20px auto 0;
  max-width: 560px;
  font-size: 14.5px;
  line-height: 1.85;
  color: #70717a;
  opacity: 0;
  transform: translateY(12px);
  animation: rise 0.72s 0.24s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

/* ===== 入口卡片：参考 DeepSeek 首页输入框的圆角大卡 ===== */
.entry-card {
  display: flex;
  align-items: center;
  max-width: 860px;
  margin: clamp(34px, 6vh, 54px) auto 0;
  padding: 34px 38px;
  border: 1px solid rgba(17, 17, 20, 0.1);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
    0 30px 70px -34px rgba(38, 52, 118, 0.28),
    0 2px 8px rgba(17, 17, 20, 0.03);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  text-align: left;
  opacity: 0;
  transform: translateY(18px);
  animation: rise 0.8s 0.34s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.entry-admin {
  flex: 1 1 auto;
  min-width: 0;
}

.entry-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2.4px;
  color: #9a9ba3;
}

.entry-admin h2 {
  margin: 10px 0 0;
  font-size: 25px;
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.entry-admin p {
  margin: 10px 0 0;
  max-width: 340px;
  font-size: 12.5px;
  line-height: 1.8;
  color: #71727b;
}

.admin-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 24px;
  padding: 12px 22px;
  border: none;
  border-radius: 999px;
  background: #111114;
  color: #ffffff;
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  cursor: pointer;
  transition:
    background 0.25s ease,
    transform 0.35s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.35s ease;
}

.admin-btn:hover {
  background: #000000;
  transform: translateY(-2px);
  box-shadow: 0 14px 30px -18px rgba(17, 17, 20, 0.5);
}

.admin-btn:active {
  transform: scale(0.985);
}

.admin-btn svg {
  transition: transform 0.18s ease;
}

.admin-btn:hover svg {
  transform: translateX(2px);
}

.admin-note {
  display: block;
  margin-top: 14px;
  font-size: 11px;
  color: #a0a1a9;
}

.entry-divider {
  flex: 0 0 1px;
  width: 1px;
  height: 176px;
  margin: 0 34px;
  background: linear-gradient(to bottom, rgba(17, 17, 20, 0), rgba(17, 17, 20, 0.09) 24%, rgba(17, 17, 20, 0.09) 76%, rgba(17, 17, 20, 0));
}

.entry-qr {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 18px;
}

.qr-frame {
  position: relative;
  flex-shrink: 0;
  padding: 9px;
  border-radius: 16px;
  background: #ffffff;
}

/* 四角定位框：呼应扫码的视觉暗示 */
.qr-corner {
  position: absolute;
  width: 13px;
  height: 13px;
  border-color: #4d6bfe;
  border-style: solid;
  opacity: 0.7;
}

.qr-corner.tl {
  top: 3px;
  left: 3px;
  border-width: 1.5px 0 0 1.5px;
  border-radius: 5px 0 0 0;
}

.qr-corner.tr {
  top: 3px;
  right: 3px;
  border-width: 1.5px 1.5px 0 0;
  border-radius: 0 5px 0 0;
}

.qr-corner.bl {
  bottom: 3px;
  left: 3px;
  border-width: 0 0 1.5px 1.5px;
  border-radius: 0 0 0 5px;
}

.qr-corner.br {
  bottom: 3px;
  right: 3px;
  border-width: 0 1.5px 1.5px 0;
  border-radius: 0 0 5px 0;
}

.qr-copy {
  min-width: 0;
}

.qr-copy h3 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.qr-copy p {
  margin: 8px 0 0;
  font-size: 11.5px;
  line-height: 1.7;
  color: #7c7d86;
}

.qr-direct {
  display: inline-block;
  margin-top: 12px;
  font-size: 11.5px;
  color: #4d6bfe;
  text-decoration: none;
}

.qr-direct:hover {
  text-decoration: underline;
}

.qr-copy-link {
  display: block;
  margin-top: 8px;
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 11px;
  color: #a0a1a9;
  cursor: pointer;
  transition: color 0.16s ease;
}

.qr-copy-link:hover {
  color: #5f6068;
}

.hero-fineprint {
  margin: 16px auto 0;
  font-size: 11px;
  color: #a3a4ac;
}

/* ===== 能力区 ===== */
.capabilities {
  max-width: 1040px;
  margin: 0 auto;
  padding: clamp(72px, 12vh, 120px) 28px 0;
}

.section-head {
  text-align: center;
}

.section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2.6px;
  color: #a0a1a9;
}

.section-head h2 {
  margin: 12px 0 0;
  font-size: clamp(25px, 3vw, 32px);
  font-weight: 700;
  letter-spacing: -0.6px;
}

.section-head p {
  margin: 12px auto 0;
  max-width: 460px;
  font-size: 13px;
  line-height: 1.8;
  color: #7c7d86;
}

.cap-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 34px 0 0;
  padding: 0;
  list-style: none;
}

.cap-grid li {
  padding: 22px 22px 24px;
  border: 1px solid rgba(17, 17, 20, 0.07);
  border-radius: 18px;
  background: #ffffff;
  transition:
    border-color 0.3s ease,
    box-shadow 0.3s ease,
    transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.cap-grid li:hover {
  border-color: rgba(77, 107, 254, 0.28);
  box-shadow: 0 22px 46px -30px rgba(38, 52, 118, 0.38);
  transform: translateY(-4px) scale(1.012);
}

.cap-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(140deg, rgba(77, 107, 254, 0.12), rgba(124, 92, 255, 0.08));
  color: #4d6bfe;
}

.cap-grid h3 {
  margin: 16px 0 0;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: 0.1px;
}

.cap-grid p {
  margin: 7px 0 0;
  font-size: 12px;
  line-height: 1.75;
  color: #81828b;
}

/* ===== 三类角色 ===== */
.roles {
  max-width: 1040px;
  margin: 0 auto;
  padding: clamp(72px, 12vh, 120px) 28px 0;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 34px;
}

.role-card {
  display: block;
  width: 100%;
  padding: 24px 24px 20px;
  border: 1px solid rgba(17, 17, 20, 0.07);
  border-radius: 20px;
  background: linear-gradient(180deg, #fbfbfd 0%, #ffffff 48%);
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.3s ease,
    box-shadow 0.3s ease,
    transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.role-card:hover {
  border-color: rgba(77, 107, 254, 0.24);
  box-shadow: 0 24px 52px -36px rgba(38, 52, 118, 0.4);
  transform: translateY(-4px);
}

.role-card:focus-visible {
  outline: 2px solid #4d6bfe;
  outline-offset: 3px;
}

.role-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(17, 17, 20, 0.07);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #8c8d96;
  transition: color 0.25s ease;
}

.role-link svg {
  color: #4d6bfe;
  opacity: 0.65;
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease;
}

.role-card:hover .role-link {
  color: #111114;
}

.role-card:hover .role-link svg {
  opacity: 1;
  transform: translateX(3px);
}

.role-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.role-index {
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.5px;
  color: #d5d6dd;
}

.role-tag {
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 1.8px;
  color: #a0a1a9;
}

.role-card h3 {
  margin: 18px 0 0;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.2px;
}

.role-desc {
  margin: 9px 0 0;
  font-size: 12.5px;
  line-height: 1.8;
  color: #7c7d86;
}

.role-points {
  margin: 18px 0 0;
  padding: 16px 0 0;
  border-top: 1px solid rgba(17, 17, 20, 0.07);
  list-style: none;
}

.role-points li {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 6px 0;
  font-size: 12px;
  line-height: 1.6;
  color: #5f6068;
}

.role-dot {
  width: 4px;
  height: 4px;
  flex-shrink: 0;
  margin-top: 7px;
  border-radius: 50%;
  background: #4d6bfe;
  opacity: 0.75;
}

/* ===== AI 能力 ===== */
.ai-section {
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  gap: clamp(36px, 6vw, 84px);
  align-items: start;
  max-width: 1040px;
  margin: 0 auto;
  padding: clamp(72px, 12vh, 120px) 28px 0;
}

.ai-head h2 {
  margin: 12px 0 0;
  font-size: clamp(26px, 3.2vw, 36px);
  line-height: 1.28;
  font-weight: 700;
  letter-spacing: -0.8px;
}

.ai-head p {
  margin: 16px 0 0;
  font-size: 13px;
  line-height: 1.85;
  color: #7c7d86;
}

.ai-list {
  margin: 0;
  padding: 0;
  border-top: 1px solid rgba(17, 17, 20, 0.08);
  list-style: none;
}

.ai-list li {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 21px 0 22px;
  border-bottom: 1px solid rgba(17, 17, 20, 0.08);
}

.ai-no {
  flex-shrink: 0;
  padding-top: 2px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 1.2px;
  color: #b0b1b9;
}

.ai-copy h3 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 650;
  letter-spacing: 0.1px;
}

.ai-copy p {
  margin: 7px 0 0;
  font-size: 12.5px;
  line-height: 1.85;
  color: #7c7d86;
}

/* ===== 使用流程 ===== */
.flow {
  max-width: 1040px;
  margin: 0 auto;
  padding: clamp(72px, 12vh, 120px) 28px 0;
}

.flow-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 34px 0 0;
  padding: 0;
  list-style: none;
}

.flow-list li {
  padding: 22px 24px 24px;
  border-top: 1px solid rgba(17, 17, 20, 0.1);
}

.flow-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid rgba(77, 107, 254, 0.35);
  background: rgba(77, 107, 254, 0.06);
  font-size: 11.5px;
  font-weight: 650;
  color: #4d6bfe;
}

.flow-list h3 {
  margin: 16px 0 0;
  font-size: 15px;
  font-weight: 650;
}

.flow-list p {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.8;
  color: #7c7d86;
}

/* ===== 常见问题 ===== */
.faq {
  display: grid;
  grid-template-columns: minmax(0, 0.75fr) minmax(0, 1.25fr);
  gap: clamp(36px, 6vw, 84px);
  align-items: start;
  max-width: 1040px;
  margin: 0 auto;
  padding: clamp(72px, 12vh, 120px) 28px 0;
}

.faq-head h2 {
  margin: 12px 0 0;
  font-size: clamp(24px, 2.8vw, 30px);
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.faq-list details {
  border-top: 1px solid rgba(17, 17, 20, 0.08);
}

.faq-list details:last-child {
  border-bottom: 1px solid rgba(17, 17, 20, 0.08);
}

.faq-list summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 17px 0;
  font-size: 13.5px;
  font-weight: 600;
  color: #27272c;
  cursor: pointer;
  list-style: none;
}

.faq-list summary::-webkit-details-marker {
  display: none;
}

.faq-list summary svg {
  flex-shrink: 0;
  color: #9a9ba3;
  transition: transform 0.2s ease, color 0.2s ease;
}

.faq-list details[open] summary svg {
  transform: rotate(180deg);
  color: #4d6bfe;
}

.faq-list details p {
  margin: -2px 0 18px;
  padding-right: 30px;
  font-size: 12.5px;
  line-height: 1.85;
  color: #7c7d86;
}

/* ===== 结尾行动区 ===== */
.closing {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  max-width: 984px;
  margin: clamp(72px, 12vh, 120px) auto 0;
  padding: 38px 40px;
  border: 1px solid rgba(17, 17, 20, 0.08);
  border-radius: 24px;
  background:
    radial-gradient(90% 140% at 100% 0%, rgba(124, 92, 255, 0.1) 0%, rgba(124, 92, 255, 0) 64%),
    linear-gradient(120deg, #f7f8fc 0%, #ffffff 60%);
}

.closing-copy h2 {
  margin: 12px 0 0;
  font-size: clamp(24px, 3vw, 32px);
  line-height: 1.28;
  font-weight: 700;
  letter-spacing: -0.6px;
}

.closing-copy p {
  margin: 10px 0 0;
  max-width: 480px;
  font-size: 12.5px;
  line-height: 1.8;
  color: #7c7d86;
}

.closing-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}

.closing .admin-btn {
  margin-top: 0;
}

.ghost-btn {
  display: inline-flex;
  align-items: center;
  padding: 12px 22px;
  border: 1px solid rgba(17, 17, 20, 0.16);
  border-radius: 999px;
  background: #ffffff;
  color: #111114;
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-decoration: none;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
}

.ghost-btn:hover {
  border-color: #111114;
  background: #111114;
  color: #ffffff;
}

/* ===== 页脚 ===== */
.site-footer {
  max-width: 1040px;
  margin: clamp(64px, 10vh, 104px) auto 0;
  padding: 26px 28px 34px;
  border-top: 1px solid rgba(17, 17, 20, 0.07);
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 14px;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  color: #7c7d86;
}

.footer-logo {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: contain;
  background: #ffffff;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 11.5px;
}

.footer-links a,
.footer-links button {
  padding: 0;
  border: none;
  background: transparent;
  color: #7c7d86;
  font: inherit;
  text-decoration: none;
  cursor: pointer;
}

.footer-links a:hover,
.footer-links button:hover {
  color: #111114;
}

.footer-copy {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 16px;
  margin: 4px 0 0;
  font-size: 10.5px;
  color: #b0b1b9;
}

/* 备案号：按工信部要求展示，并链接到官方查询系统 */
.footer-record {
  color: #b0b1b9;
  text-decoration: none;
  transition: color 0.16s ease;
}

.footer-record:hover {
  color: #5f6068;
}

@keyframes rise {
  from {
    filter: blur(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

/* 顶部极光缓慢漂移，避免页面静止时过于生硬 */
@keyframes auroraDrift {
  0% {
    transform: translate3d(-1.2%, 0, 0) scale(1);
    opacity: 0.92;
  }
  100% {
    transform: translate3d(1.2%, 1.5%, 0) scale(1.05);
    opacity: 1;
  }
}

@keyframes accentFlow {
  to {
    background-position: 100% 0;
  }
}

/* ===== 中等宽度（小笔记本 / 浏览器 125% 缩放）：能力四宫格收为两列 ===== */
@media (max-width: 1120px) {
  .cap-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* ===== 移动端 ===== */
@media (max-width: 860px) {
  .site-nav {
    padding: 8px 14px 0;
  }

  .site-nav-inner {
    padding: 10px 18px;
  }

  .site-nav.is-scrolled .site-nav-inner {
    padding: 10px 14px;
  }

  .nav-links {
    gap: 16px;
  }

  .nav-links > a,
  .nav-download {
    display: none;
  }

  .nav-login {
    margin-left: 0;
    padding: 8px 15px;
    font-size: 12px;
  }

  .hero {
    padding-top: 54px;
  }

  .hero-title {
    margin-top: 18px;
    letter-spacing: -1px;
  }

  .hero-sub {
    font-size: 13px;
    padding: 0 4px;
  }

  .entry-card {
    flex-direction: column;
    align-items: stretch;
    gap: 24px;
    padding: 26px 22px;
    border-radius: 24px;
    text-align: left;
  }

  .entry-divider {
    flex: 0 0 1px;
    width: 100%;
    height: 1px;
    margin: 0;
    background: linear-gradient(to right, rgba(17, 17, 20, 0), rgba(17, 17, 20, 0.09) 20%, rgba(17, 17, 20, 0.09) 80%, rgba(17, 17, 20, 0));
  }

  .entry-qr {
    gap: 16px;
  }

  .entry-admin p {
    max-width: none;
  }

  .admin-btn {
    margin-top: 18px;
  }

  .capabilities {
    padding-top: 64px;
  }

  .cap-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 11px;
    margin-top: 26px;
  }

  .cap-grid li {
    padding: 18px 17px 20px;
  }

  .roles,
  .ai-section,
  .flow,
  .faq {
    padding-top: 64px;
  }

  .role-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 11px;
    margin-top: 26px;
  }

  .role-card {
    padding: 22px 20px 24px;
  }

  .ai-section {
    grid-template-columns: minmax(0, 1fr);
    gap: 28px;
  }

  .ai-head h2 {
    font-size: 26px;
  }

  .flow-list {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
    margin-top: 26px;
  }

  .flow-list li {
    padding: 20px 0 22px;
  }

  .faq {
    grid-template-columns: minmax(0, 1fr);
    gap: 20px;
  }

  .faq-list summary {
    font-size: 13px;
  }

  .faq-list details p {
    padding-right: 0;
  }

  .closing {
    flex-direction: column;
    align-items: flex-start;
    gap: 24px;
    margin-top: 60px;
    padding: 28px 24px;
  }

  .closing-actions {
    width: 100%;
  }

  .closing .admin-btn,
  .closing .ghost-btn {
    flex: 1 1 auto;
    justify-content: center;
  }

  .site-footer {
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
    margin-top: 60px;
    padding: 22px 20px 28px;
  }

  .footer-links {
    gap: 16px;
  }
}

/* ===== 窄屏（手机 / 浏览器 200% 缩放）：压缩留白，避免内容被挤成横向滚动 ===== */
@media (max-width: 640px) {
  .site-nav {
    padding: 8px 10px 0;
  }

  .site-nav-inner {
    padding: 9px 14px;
  }

  .site-nav.is-scrolled .site-nav-inner {
    padding: 9px 12px;
  }

  .nav-logo {
    width: 24px;
    height: 24px;
  }

  .nav-name {
    max-width: 132px;
    overflow: hidden;
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .hero {
    padding: 44px 20px 0;
  }

  .hero-badge {
    max-width: 100%;
    padding: 6px 12px;
    font-size: 10.5px;
  }

  .hero-title {
    font-size: clamp(34px, 9.6vw, 46px);
    letter-spacing: -0.8px;
  }

  .hero-sub {
    font-size: 12.5px;
  }

  .entry-card {
    gap: 20px;
    padding: 22px 18px;
    border-radius: 20px;
  }

  .entry-admin h2 {
    font-size: 21px;
  }

  .section-head h2 {
    font-size: 23px;
  }

  .closing {
    padding: 24px 18px;
    border-radius: 20px;
  }

  .closing-copy h2 {
    font-size: 22px;
  }

  .site-footer {
    padding: 20px 18px 26px;
  }

  .footer-brand {
    font-size: 11.5px;
  }
}

/* 手机竖屏 / 极窄窗口：二维码与下载说明改为上下排列 */
@media (max-width: 520px) {
  .entry-qr {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 400px) {
  .cap-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-badge,
  .hero-title,
  .hero-sub,
  .entry-card {
    opacity: 1;
    transform: none;
    animation: none;
  }

  .reveal {
    opacity: 1;
    transform: none;
    filter: none;
    transition: none;
  }

  .site-page::before,
  .hero-accent {
    animation: none;
  }
}

/* ===== 宽屏 ===== */
@media (min-width: 1280px) {
  .entry-card {
    max-width: 900px;
  }
}
</style>
