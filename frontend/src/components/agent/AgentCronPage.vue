<template>
  <Teleport to="body">
    <!-- 覆盖式子页：动画复用全局 .subpage（styles/animations.css），本页不自带。 -->
    <Transition name="subpage" :duration="320" @after-leave="emit('closed')">
      <div v-if="visible" class="acp-root" role="dialog" aria-modal="true" aria-label="定时任务">
        <header class="acp-head">
          <button type="button" class="acp-back" aria-label="返回" @click="close">
            <el-icon :size="22"><ArrowLeft /></el-icon>
          </button>
          <h1 class="acp-title">定时任务</h1>
          <span class="acp-head-space"></span>
        </header>

        <div v-loading="loading" class="acp-scroll">
          <el-empty v-if="!loading && tasks.length === 0" description="还没有定时任务">
            <p class="acp-empty-tip">在对话框跟我说「每天早上 8 点帮我汇总校园资讯」就能建一个</p>
          </el-empty>

          <div v-else class="acp-list">
            <div v-for="t in tasks" :key="t.id" class="acp-item" :class="{ disabled: !t.enabled }">
              <div
                class="acp-item-main"
                role="button"
                tabindex="0"
                @click="openConversation(t)"
                @keyup.enter="openConversation(t)"
              >
                <div class="acp-item-name">{{ t.name }}</div>
                <div class="acp-item-meta">
                  {{ t.schedule_text }}<template v-if="t.last_run_at"> · 上次 {{ fmtTime(t.last_run_at) }}</template>
                </div>
              </div>
              <div class="acp-item-ops">
                <el-button text size="small" type="primary" :loading="runningId === t.id" @click.stop="runNow(t)">立即执行</el-button>
                <el-switch aria-label="启用或暂停该任务" :model-value="t.enabled" @change="(v: string | number | boolean) => toggle(t, Boolean(v))" />
                <el-button text size="small" type="danger" @click.stop="remove(t)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteCronTask, listCronTasks, runCronTaskNow, updateCronTask, type CronTaskItem,
} from '@/api/cronTask'

const emit = defineEmits<{ (e: 'closed'): void }>()
const router = useRouter()

/* 与 ArticleDetailPage / CampusSearchPage 同一套约定：父页 v-if 挂载即打开
   （onMounted 置 visible），close() 播退场动画，after-leave 才通知父页卸载。 */
const visible = ref(false)
const tasks = ref<CronTaskItem[]>([])
const loading = ref(false)
const runningId = ref<number | null>(null)

function close() {
  visible.value = false
}

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
  runningId.value = t.id
  try {
    await runCronTaskNow(t.id)
    ElMessage.success('已触发，AI 正在执行，结果稍后送达会话')
    await load()
  } catch (e: unknown) {
    // 5xx / 断网已由 request.ts 拦截器统一弹窗，这里只补 4xx 业务错误
    // （400 已暂停 / 409 忙，拦截器不弹），避免双 toast 且文案矛盾
    toastBizError(e, '执行失败，请稍后再试')
  } finally {
    runningId.value = null
  }
}

function openConversation(t: CronTaskItem) {
  close()
  router.push(`/student/agent?conv=${t.conversation_id}`)
}

function fmtTime(iso: string) {
  // 后端统一给北京时间 ISO（带 +08:00），new Date 解析后直接取本地字段即为正确展示
  const d = new Date(iso)
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(() => {
  visible.value = true
  load()
})
</script>

<style scoped>
/* 定位照抄 .csp-root：全屏覆盖 + 独立层；动画由全局 .subpage keyframes 驱动。
   z-index 2600 与 ArticleDetailPage / CampusSearchPage 同层 */
.acp-root {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.acp-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: calc(8px + env(safe-area-inset-top, 0px)) 14px 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
.acp-back {
  display: flex;
  align-items: center;
  border: none;
  background: none;
  cursor: pointer;
  color: #333;
}
.acp-title {
  flex: 1;
  margin: 0;
  font-size: 16.5px;
  font-weight: 600;
  color: #222;
}
.acp-head-space { width: 34px; }
.acp-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 16px calc(40px + env(safe-area-inset-bottom, 0px));
}
.acp-empty-tip {
  margin: 4px 0 0;
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
}
.acp-list { display: flex; flex-direction: column; gap: 10px; }
.acp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #f7f8fa;
  border: 1px solid rgba(91, 141, 239, 0.08);
}
.acp-item.disabled { opacity: 0.55; }
.acp-item-main { flex: 1; min-width: 0; cursor: pointer; }
.acp-item-name {
  font-size: 14.5px;
  font-weight: 600;
  color: #2b2f36;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.acp-item-meta { margin-top: 3px; font-size: 12.5px; color: #8a9099; }
.acp-item-ops { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
</style>
