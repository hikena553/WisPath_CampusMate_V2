<template>
  <!-- 定时任务视图：直接占满对话区（不再 Teleport 整屏覆盖），
       与对话内容互为「同一页的两种视图」，侧边栏/顶部导航保持原位。 -->
  <section class="acv-root" :class="{ 'acv-nohead': !props.showHead }" aria-label="定时任务">
    <!-- 桌面端 / 无顶栏页面（/student/agent 深链）自带标题行；
         移动端主页面复用 ChatPanel 的毛玻璃顶栏（返回 + 定时任务），避免出现两层标题 -->
    <header v-if="props.showHead" class="acv-head">
      <button type="button" class="acv-back" aria-label="返回对话" @click="emit('close')">
        <el-icon :size="20"><ArrowLeft /></el-icon>
      </button>
      <h1 class="acv-title">定时任务</h1>
    </header>

    <!-- 任务 / 结果：任务=在跑的任务清单，结果=最近执行过的记录 -->
    <div class="acv-tabs" role="tablist" aria-label="定时任务分区">
      <button
        v-for="t in TABS" :key="t.key" type="button" role="tab"
        :aria-selected="tab === t.key"
        :class="['acv-tab', { active: tab === t.key }]"
        @click="tab = t.key"
      >{{ t.label }}</button>
    </div>

    <div v-loading="loading" class="acv-scroll">
      <!-- ── 任务 ── -->
      <template v-if="tab === 'tasks'">
        <div v-if="!loading && tasks.length === 0" class="acv-empty">
          <span class="acv-empty-icon"><el-icon :size="30"><Clock /></el-icon></span>
          <p class="acv-empty-title">还没有定时任务</p>
          <p class="acv-empty-tip">点右下角「＋」新建，或在对话框跟我说<br>「每天早上 8 点帮我汇总校园资讯」</p>
          <button type="button" class="acv-empty-btn" @click="openForm">
            <el-icon :size="15"><Plus /></el-icon>新建定时任务
          </button>
        </div>

        <div v-else class="acv-list">
          <article
            v-for="t in tasks" :key="t.id"
            class="acv-card acv-item" :class="{ disabled: !t.enabled }"
            role="button" tabindex="0"
            @click="openConversation(t)"
            @keyup.enter="openConversation(t)"
          >
            <div class="acv-card-top">
              <h2 class="acv-card-title acv-item-name">{{ t.name }}</h2>
              <span v-if="!t.enabled" class="acv-pill">已暂停</span>
              <el-dropdown trigger="click" placement="bottom-end" @command="(cmd: string) => onCommand(cmd, t)">
                <button type="button" class="acv-more" aria-label="任务操作" @click.stop>···</button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="run" :disabled="!t.enabled">立即执行</el-dropdown-item>
                    <el-dropdown-item command="toggle">{{ t.enabled ? '暂停任务' : '恢复任务' }}</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div class="acv-field">
              <span class="acv-field-label">执行内容</span>
              <p class="acv-field-value">{{ t.prompt }}</p>
            </div>

            <div class="acv-card-foot">
              <span class="acv-schedule acv-item-meta">
                <el-icon :size="14"><Clock /></el-icon>{{ t.schedule_text }}
              </span>
              <span class="acv-last">{{ relTime(t.last_run_at) }}</span>
            </div>
          </article>
        </div>
      </template>

      <!-- ── 结果 ── -->
      <template v-else>
        <div v-if="!loading && runs.length === 0" class="acv-empty">
          <span class="acv-empty-icon"><el-icon :size="30"><Document /></el-icon></span>
          <p class="acv-empty-title">还没有执行记录</p>
          <p class="acv-empty-tip">任务跑过一轮后，这里能看到最近的结果</p>
        </div>

        <div v-else class="acv-list">
          <article
            v-for="r in runs" :key="r.id"
            class="acv-card acv-run" role="button" tabindex="0"
            @click="openConversation(r)"
            @keyup.enter="openConversation(r)"
          >
            <div class="acv-card-top">
              <h2 class="acv-card-title">{{ r.name }}</h2>
              <span class="acv-last">{{ relTime(r.last_run_at) }}</span>
            </div>
            <div class="acv-card-foot no-divider">
              <span class="acv-schedule">
                <el-icon :size="14"><Clock /></el-icon>{{ r.schedule_text }}
              </span>
              <span class="acv-run-link">查看结果<el-icon :size="12"><ArrowRight /></el-icon></span>
            </div>
          </article>
        </div>
      </template>
    </div>

    <!-- 新建：悬浮按钮（参考图右下角的圆形 ＋），随视图贴住对话区右下角 -->
    <button type="button" class="acv-fab" aria-label="新建定时任务" @click="openForm">
      <el-icon :size="26"><Plus /></el-icon>
    </button>

    <!-- 新建表单：底部弹层（限制在对话区内，不再盖住侧边栏/底部导航） -->
    <Transition name="acv-sheet">
      <div v-if="formOpen" class="acv-sheet-mask" @click.self="closeForm">
        <form class="acv-sheet" @submit.prevent="submit">
          <span class="acv-sheet-handle" aria-hidden="true"></span>
          <div class="acv-sheet-head">
            <h2 class="acv-sheet-title">新建定时任务</h2>
            <button type="button" class="acv-sheet-close" aria-label="关闭" @click="closeForm">
              <el-icon :size="18"><Close /></el-icon>
            </button>
          </div>

          <label class="acv-field-row">
            <span class="acv-label">任务名称</span>
            <el-input v-model="form.name" maxlength="30" show-word-limit placeholder="如：早报汇总" />
          </label>

          <label class="acv-field-row">
            <span class="acv-label">执行内容</span>
            <el-input
              v-model="form.prompt" type="textarea" :rows="3" maxlength="300" show-word-limit
              placeholder="每次执行时交给 AI 的完整指令，如：汇总今天校园通知里与我有关的事，3 条以内"
            />
          </label>

          <div class="acv-field-row">
            <span class="acv-label">执行周期</span>
            <div class="acv-seg" role="tablist" aria-label="执行周期">
              <button
                v-for="k in KINDS" :key="k.key" type="button" role="tab"
                :aria-selected="form.schedule_kind === k.key"
                :class="['acv-seg-item', { active: form.schedule_kind === k.key }]"
                @click="form.schedule_kind = k.key"
              >{{ k.label }}</button>
            </div>
          </div>

          <div v-if="form.schedule_kind !== 'interval'" class="acv-field-row">
            <span class="acv-label">{{ form.schedule_kind === 'weekly' ? '星期与时间' : '执行时间' }}</span>
            <div class="acv-inline">
              <!-- 原生控件而非 el-select：弹层是对话区内的局部层，组件库下拉容易与层叠打架，
                   原生选择器在移动端还能直接唤起系统选择面板 -->
              <select v-if="form.schedule_kind === 'weekly'" v-model.number="form.weekday" class="acv-native acv-flex-1" aria-label="星期">
                <option v-for="(w, i) in WEEKDAYS" :key="i" :value="i">{{ w }}</option>
              </select>
              <input v-model="form.time" type="time" step="300" class="acv-native acv-flex-1" aria-label="时间" />
            </div>
          </div>

          <div v-else class="acv-field-row">
            <span class="acv-label">间隔时长</span>
            <div class="acv-inline">
              <el-input-number v-model="form.interval_hours" :min="1" :max="720" controls-position="right" />
              <span class="acv-unit">小时执行一次</span>
            </div>
          </div>

          <p class="acv-sheet-tip">
            到点后 AI 会在专属会话里自动执行一轮，并把结果发到「消息通知」。
          </p>

          <div class="acv-sheet-actions">
            <button type="button" class="acv-btn ghost" @click="closeForm">取消</button>
            <button type="submit" class="acv-btn primary" :disabled="submitting">
              {{ submitting ? '创建中…' : '创建任务' }}
            </button>
          </div>
        </form>
      </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft, ArrowRight, Clock, Close, Document, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCronTask, deleteCronTask, listCronTasks, runCronTaskNow, updateCronTask, type CronTaskItem,
} from '@/api/cronTask'

/**
 * showHead：是否自绘标题行。
 * 移动端主页面（有毛玻璃顶栏）由 ChatPanel 提供「返回 + 定时任务」标题，这里不再重复；
 * 桌面端 / 无顶栏页面（/student/agent 深链）则自绘标题行，保证始终有返回对话的入口。
 */
const props = withDefaults(defineProps<{ showHead?: boolean }>(), { showHead: true })
const emit = defineEmits<{ (e: 'close'): void; (e: 'open', conversationId: number): void }>()

const tasks = ref<CronTaskItem[]>([])
const loading = ref(false)
const tab = ref<'tasks' | 'results'>('tasks')

const TABS = [
  { key: 'tasks' as const, label: '任务' },
  { key: 'results' as const, label: '结果' },
]
const KINDS = [
  { key: 'daily' as const, label: '每天' },
  { key: 'weekly' as const, label: '每周' },
  { key: 'interval' as const, label: '每隔' },
]
const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

/** 结果页数据：按上次执行时间倒序，只留有执行痕迹的任务 */
const runs = computed(() =>
  tasks.value
    .filter(t => t.last_run_at)
    .slice()
    .sort((a, b) => new Date(b.last_run_at as string).getTime() - new Date(a.last_run_at as string).getTime()),
)

/** 5xx/网络错误已由全局拦截器统一提示，这里只对 4xx 弹后端 detail，避免双 toast。 */
function toastBizError(e: unknown, fallback: string) {
  const status = (e as { response?: { status?: number } })?.response?.status
  if (status && status < 500) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || fallback)
  } else {
    console.error('cron task request failed', e)
  }
}

async function load() {
  loading.value = true
  try {
    tasks.value = await listCronTasks()
  } catch { /* 列表拉取失败保持空态 */ } finally {
    loading.value = false
  }
}

async function toggle(t: CronTaskItem, enabled: boolean) {
  try {
    const updated = await updateCronTask(t.id, { enabled })
    Object.assign(t, updated)
    ElMessage.success(enabled ? '已恢复' : '已暂停')
  } catch (e: unknown) {
    toastBizError(e, '操作失败，请重试')
  }
}

async function remove(t: CronTaskItem) {
  try {
    await ElMessageBox.confirm(
      `删除后「${t.name}」不再自动执行，历史结果仍保留在会话里。`,
      '删除定时任务',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }
  try {
    await deleteCronTask(t.id)
    tasks.value = tasks.value.filter(x => x.id !== t.id)
    ElMessage.success('已删除')
  } catch (e: unknown) {
    // 409（正在执行中）等 4xx 的后端 detail 由 toastBizError 透出
    toastBizError(e, '删除失败，请重试')
  }
}

async function runNow(t: CronTaskItem) {
  try {
    await runCronTaskNow(t.id)
    ElMessage.success('已触发，AI 正在执行，结果稍后送达会话')
    await load()
  } catch (e: unknown) {
    // 5xx / 断网已由 request.ts 拦截器统一弹窗，这里只补 4xx 业务错误
    // （400 已暂停 / 409 忙，拦截器不弹），避免双 toast 且文案矛盾
    toastBizError(e, '执行失败，请稍后再试')
  }
}

/** 卡片右上角「···」：立即执行 / 暂停恢复 / 删除 */
function onCommand(cmd: string, t: CronTaskItem) {
  if (cmd === 'run') return void runNow(t)
  if (cmd === 'toggle') return void toggle(t, !t.enabled)
  if (cmd === 'delete') return void remove(t)
}

/**
 * 点卡片看会话：交给 ChatPanel 就地切换（只切视图 + 重载消息），
 * 不做路由跳转——这里本来就是对话区的一部分，跳 /student/agent 会把侧边栏丢掉。
 */
function openConversation(t: CronTaskItem) {
  emit('open', t.conversation_id)
}

function relTime(iso: string | null) {
  if (!iso) return '未执行'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  return `${Math.floor(days / 30)}个月前`
}

/* ── 新建表单 ── */
const formOpen = ref(false)
const submitting = ref(false)
const form = reactive({
  name: '',
  prompt: '',
  schedule_kind: 'daily' as 'daily' | 'weekly' | 'interval',
  time: '08:00',
  weekday: 0,
  interval_hours: 6,
})

function openForm() {
  form.name = ''
  form.prompt = ''
  form.schedule_kind = 'daily'
  form.time = '08:00'
  form.weekday = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1
  form.interval_hours = 6
  formOpen.value = true
}

function closeForm() {
  formOpen.value = false
}

async function submit() {
  const name = form.name.trim()
  const prompt = form.prompt.trim()
  if (!name) { ElMessage.warning('请填写任务名称'); return }
  if (!prompt) { ElMessage.warning('请填写执行内容'); return }
  const [hour, minute] = form.time.split(':').map(Number)
  submitting.value = true
  try {
    const created = await createCronTask({
      name,
      prompt,
      schedule_kind: form.schedule_kind,
      // interval 不带时刻；daily/weekly 的时刻按北京时间解释（后端统一换算 UTC）
      hour: form.schedule_kind === 'interval' ? null : hour,
      minute: form.schedule_kind === 'interval' ? null : minute,
      weekday: form.schedule_kind === 'weekly' ? form.weekday : null,
      interval_hours: form.schedule_kind === 'interval' ? form.interval_hours : null,
    })
    tasks.value = [created, ...tasks.value]
    tab.value = 'tasks'
    formOpen.value = false
    ElMessage.success(`已创建「${created.name}」，${created.schedule_text}自动执行`)
  } catch (e: unknown) {
    toastBizError(e, '创建失败，请重试')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
/* 对话区内的整块视图：占满剩余空间，自身滚动，不做 fixed 覆盖 */
.acv-root {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1 1 0%;
  min-height: 0;
  background: var(--bg-primary, #f6f7f9);
}

/* ── 标题行（桌面端 / 无顶栏页面）── */
.acv-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: calc(10px + env(safe-area-inset-top, 0px)) 14px 0;
}
.acv-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px; height: 34px;
  border: none;
  background: none;
  border-radius: 10px;
  cursor: pointer;
  color: var(--text-primary, #222);
}
.acv-back:hover { background: rgba(15, 23, 42, .06); }
.acv-title {
  flex: 1;
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: .2px;
  color: var(--text-primary, #1a1a1a);
}

/* 任务 / 结果：文字页签，选中加粗变深（参考图靠字重和颜色区分，不用下划线块） */
.acv-tabs { display: flex; gap: 20px; padding: 2px 18px 6px; }
/* 移动端：让出悬浮毛玻璃顶栏的高度，页签不被压住 */
.acv-nohead .acv-tabs { padding-top: calc(50px + env(safe-area-inset-top, 0px)); }
.acv-tab {
  position: relative;
  border: none;
  background: none;
  padding: 6px 0 8px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-muted, #9aa0a6);
  cursor: pointer;
  transition: color .15s ease;
}
.acv-tab.active { color: var(--text-primary, #1a1a1a); font-weight: 600; }
.acv-tab.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 2px;
  width: 16px;
  height: 2.5px;
  margin-left: -8px;
  border-radius: 2px;
  background: var(--text-primary, #1a1a1a);
}

.acv-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 6px 16px calc(100px + env(safe-area-inset-bottom, 0px));
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

/* ── 任务卡片（参考图：白底圆角卡 / 标题 + 执行内容 + 分隔线 + 时钟&相对时间）── */
.acv-list { display: flex; flex-direction: column; gap: 12px; max-width: 820px; margin: 0 auto; }
.acv-card {
  padding: 15px 16px 13px;
  border-radius: 16px;
  background: var(--bg-card, #fff);
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 6px 18px rgba(15, 23, 42, .03);
  cursor: pointer;
  transition: transform .12s ease, box-shadow .12s ease;
}
.acv-card:active { transform: scale(.995); box-shadow: 0 1px 2px rgba(15, 23, 42, .06); }
.acv-card.disabled .acv-card-title,
.acv-card.disabled .acv-field-value { color: var(--text-muted, #a2a8b0); }
.acv-card-top { display: flex; align-items: center; gap: 8px; }
.acv-card-title {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--text-primary, #17181a);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.acv-pill {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(15, 23, 42, .06);
  font-size: 11px;
  color: var(--text-muted, #8a9099);
}
.acv-more {
  flex-shrink: 0;
  width: 28px; height: 24px;
  border: none;
  background: none;
  padding: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 1px;
  line-height: 1;
  color: var(--text-muted, #9aa0a6);
  cursor: pointer;
  border-radius: 8px;
}
.acv-more:active { background: rgba(15, 23, 42, .06); }

.acv-field { margin-top: 12px; }
.acv-field-label {
  display: block;
  font-size: 12.5px;
  color: var(--text-muted, #9aa0a6);
  margin-bottom: 3px;
}
.acv-field-value {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary, #3f444b);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.acv-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 13px;
  padding-top: 11px;
  border-top: 1px solid var(--border-light, #f0f1f4);
}
.acv-card-foot.no-divider { border-top: none; padding-top: 0; margin-top: 10px; }
.acv-schedule {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--text-muted, #8a9099);
  font-variant-numeric: tabular-nums;
}
.acv-last {
  font-size: 13px;
  color: var(--text-muted, #9aa0a6);
  font-variant-numeric: tabular-nums;
}
.acv-run-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: var(--accent-blue, #409eff);
}

/* 空态 */
.acv-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px 0;
  text-align: center;
}
.acv-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px; height: 64px;
  border-radius: 50%;
  background: var(--bg-card, #fff);
  color: #c2c8d0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}
.acv-empty-title {
  margin: 16px 0 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary, #4b5563);
}
.acv-empty-tip {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-muted, #909399);
}
.acv-empty-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 18px;
  padding: 9px 16px;
  border: 1px solid rgba(64, 158, 255, .3);
  border-radius: 999px;
  background: rgba(64, 158, 255, .07);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--accent-blue, #409eff);
  cursor: pointer;
}

/* 悬浮「＋」：贴住对话区右下角（不再相对浏览器窗口 fixed） */
.acv-fab {
  position: absolute;
  right: 20px;
  bottom: calc(20px + env(safe-area-inset-bottom, 0px));
  z-index: 25;
  width: 56px; height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: #4eb287;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 8px 22px rgba(78, 178, 135, .38);
  transition: transform .14s ease, box-shadow .14s ease;
}
.acv-fab:active { transform: scale(.94); box-shadow: 0 4px 14px rgba(78, 178, 135, .3); }

/* ── 新建表单弹层：只覆盖对话区 ── */
.acv-sheet-mask {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(15, 23, 42, .42);
  -webkit-backdrop-filter: blur(2px);
  backdrop-filter: blur(2px);
}
.acv-sheet {
  width: 100%;
  max-width: 520px;
  max-height: 88%;
  overflow-y: auto;
  padding: 8px 18px calc(18px + env(safe-area-inset-bottom, 0px));
  border-radius: 20px 20px 0 0;
  background: var(--bg-card, #fff);
  box-shadow: 0 -8px 32px rgba(15, 23, 42, .16);
}
.acv-sheet-handle {
  display: block;
  width: 36px; height: 4px;
  margin: 2px auto 10px;
  border-radius: 2px;
  background: rgba(15, 23, 42, .12);
}
.acv-sheet-head { display: flex; align-items: center; margin-bottom: 14px; }
.acv-sheet-title {
  flex: 1;
  margin: 0;
  font-size: 16.5px;
  font-weight: 600;
  color: var(--text-primary, #17181a);
}
.acv-sheet-close {
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border: none; background: none; border-radius: 50%;
  color: var(--text-muted, #9aa0a6);
  cursor: pointer;
}

.acv-field-row { display: block; margin-bottom: 14px; }
.acv-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #4b5563);
}
.acv-inline { display: flex; align-items: center; gap: 8px; }
.acv-flex-1 { flex: 1; min-width: 0; }
.acv-unit { font-size: 13px; color: var(--text-muted, #8a9099); }

/* 原生选择控件：去系统外观，统一成 44px 触屏高度 */
.acv-native {
  height: 44px;
  padding: 0 12px;
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 10px;
  background: var(--bg-secondary, #fff);
  font-family: inherit;
  font-size: 15px;
  color: var(--text-primary, #1f2328);
  -webkit-appearance: none;
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, currentColor 50%),
    linear-gradient(135deg, currentColor 50%, transparent 50%);
  background-position: calc(100% - 17px) 20px, calc(100% - 12px) 20px;
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
  cursor: pointer;
}
.acv-native:focus { outline: none; border-color: #409eff; box-shadow: 0 0 0 3px rgba(64, 158, 255, .12); }
/* 时间控件不画下拉箭头（系统自带时钟图标） */
input.acv-native {
  background-image: none;
  padding-right: 10px;
}

.acv-seg {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 12px;
  background: var(--bg-primary, #f2f3f6);
}
.acv-seg-item {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-family: inherit;
  font-size: 13.5px;
  color: var(--text-secondary, #5a6169);
  cursor: pointer;
  transition: background .15s ease, color .15s ease, box-shadow .15s ease;
}
.acv-seg-item.active {
  background: var(--bg-card, #fff);
  color: var(--text-primary, #17181a);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(15, 23, 42, .1);
}

.acv-sheet-tip {
  margin: 2px 0 14px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-muted, #9aa0a6);
}
.acv-sheet-actions { display: flex; gap: 10px; }
.acv-btn {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 12px;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform .12s ease, opacity .12s ease;
}
.acv-btn:active { transform: scale(.99); }
.acv-btn.ghost {
  background: var(--bg-primary, #f2f3f6);
  color: var(--text-secondary, #5a6169);
  font-weight: 500;
}
.acv-btn.primary { background: #409eff; color: #fff; }
.acv-btn.primary:disabled { opacity: .6; }

/* 弹层上滑 / 下滑 */
.acv-sheet-enter-active,
.acv-sheet-leave-active { transition: opacity .22s ease; }
.acv-sheet-enter-active .acv-sheet,
.acv-sheet-leave-active .acv-sheet { transition: transform .26s cubic-bezier(.32, .72, 0, 1); }
.acv-sheet-enter-from,
.acv-sheet-leave-to { opacity: 0; }
.acv-sheet-enter-from .acv-sheet,
.acv-sheet-leave-to .acv-sheet { transform: translateY(100%); }

/* 对话区较宽时（桌面端）弹层上下留白，圆角四角 */
@media (min-width: 768px) {
  .acv-sheet { border-radius: 20px; margin-bottom: 6vh; }
  .acv-sheet-mask { align-items: center; }
}
</style>
