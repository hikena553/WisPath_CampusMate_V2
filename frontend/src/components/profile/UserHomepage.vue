<template>
  <Teleport to="body">
    <Transition name="uh-page">
      <div v-if="visible" class="uh-page">
        <div class="uh-main">
          <!-- ===== 封面：QQ 资料卡的封面范式（不加卡片，身份直接压在渐变上） ===== -->
          <section class="uh-hero" :style="{ background: heroGradient }">
            <div class="uh-hero-scrim"></div>
            <img v-if="agentMark" :src="agentMark" class="uh-hero-mark" alt="" />

            <button type="button" class="uh-back" @click="close">
              <el-icon :size="16"><ArrowLeft /></el-icon>
            </button>
            <!-- 右上角「…」：好友主页才有，进入设置页（备注 / 分组 / 黑名单 / 删除好友） -->
            <button
              v-if="data && isFriend && !isSelf"
              type="button"
              class="uh-hero-more"
              @click="showSettings = true"
            >
              <el-icon :size="18"><MoreFilled /></el-icon>
            </button>

            <div v-if="loading" class="uh-hero-loading">正在打开主页…</div>
            <template v-else-if="data">
              <div class="uh-cast">
                <el-avatar :size="60" :src="data.avatar || undefined" class="uh-avatar">
                  {{ data.name?.[0] }}
                </el-avatar>
                <div class="uh-cast-main">
                  <div class="uh-name-row">
                    <h2 class="uh-name">{{ data.name }}</h2>
                    <span class="uh-role">{{ roleLabel }}</span>
                    <span class="uh-lv-chip">Lv.{{ data.level.level }}</span>
                  </div>
                  <p class="uh-signature">
                    {{ data.signature || '这个人很低调，还没写个性签名' }}
                  </p>
                </div>
              </div>
              <!-- 身份与关键数字压成两行文本：不占一整块统计区（主页要短） -->
              <div class="uh-facts">
                <span>{{ data.username }}</span>
                <template v-if="data.college"><i>·</i><span>{{ data.college }}</span></template>
                <template v-if="roleLine"><i>·</i><span>{{ roleLine }}</span></template>
              </div>
              <div class="uh-numbers">
                <span><b>{{ data.level.points }}</b>成长值</span>
                <i class="uh-sep"></i>
                <span><b>{{ data.earned_count }}</b>勋章</span>
                <i class="uh-sep"></i>
                <span><b>{{ friendCount }}</b>好友</span>
              </div>
            </template>
          </section>

          <!-- ===== 内容：微信 / QQ 设置页范式 —— 灰底分隔带 + 白底分组行，两层色差分层，不用卡片 ===== -->
          <div class="uh-body">
            <div v-if="error || (data === null && !loading)" class="uh-empty">
              <el-icon :size="40" color="#c0c4cc"><User /></el-icon>
              <span>{{ error || '该用户不存在' }}</span>
            </div>

            <template v-else-if="data">
              <!-- 我们之间：灰色底上的小标签，不占白组 -->
              <div v-if="mutualPills.length" class="uh-mutual">
                <span v-for="p in mutualPills" :key="p">{{ p }}</span>
              </div>

              <!-- 我的勋章：整排勋章直接铺在灰底上（没有卡片外框），
                   一排排开、超宽横向滑动，点任意一枚进「勋章墙」看详情 -->
              <div class="uh-strip-head">
                <h3 class="uh-strip-title">我的勋章</h3>
                <button type="button" class="uh-strip-more" @click="showWall = true">
                  已点亮 {{ data.earned_count }}/{{ data.total_count }}
                  <el-icon :size="11"><ArrowRight /></el-icon>
                </button>
              </div>
              <div class="uh-badges">
                <button
                  v-for="b in allBadges"
                  :key="b.code"
                  type="button"
                  class="uh-badge"
                  :class="[`tier-${b.tier}`, { 'is-locked': !b.earned }]"
                  :title="b.earned
                    ? `${b.name} · ${b.desc}`
                    : `${b.name} · ${b.target_label}（${b.progress}%）`"
                  @click="showWall = true"
                >
                  <span class="uh-badge-disc"><i>{{ b.icon }}</i></span>
                  <span class="uh-badge-name">{{ b.name }}</span>
                </button>
              </div>

              <!-- 资料 + 近期亮点：合并成同一块白组（关于 TA → 亮点），
                   组内只用细线与浅灰小标签分区，不再拆成两个独立分区 -->
              <h3 class="uh-group-label">资料与近期亮点</h3>
              <div class="uh-group">
                <div v-for="f in aboutFields" :key="f.label" class="uh-cell">
                  <span class="uh-cell-label">{{ f.label }}</span>
                  <span class="uh-cell-value">{{ f.value }}</span>
                </div>
                <template v-if="topHighlights.length">
                  <div class="uh-inline-label">近期亮点</div>
                  <div v-for="(h, i) in topHighlights" :key="i" class="uh-cell">
                    <span class="uh-cell-icon">{{ h.icon }}</span>
                    <span class="uh-cell-stack">
                      <span class="uh-cell-title">{{ h.title }}</span>
                      <span class="uh-cell-sub">{{ h.subtitle }}</span>
                    </span>
                    <span class="uh-cell-value is-quiet">{{ h.date }}</span>
                  </div>
                </template>
              </div>
            </template>
          </div>
        </div>

        <!-- ===== 固定底部操作条 ===== -->
        <div v-if="data && !error" class="uh-actionbar">
          <button
            type="button"
            class="uh-btn is-primary"
            @click="goChat(isFriend ? undefined : greeting)"
          >
            发消息
          </button>
        </div>

        <!-- ===== 二级：勋章墙 ===== -->
        <Transition name="uh-sub">
          <div v-if="showWall && data" class="uh-subpage">
            <div class="uh-subhead">
              <button type="button" class="uh-back-dark" @click="showWall = false">
                <el-icon :size="18"><ArrowLeft /></el-icon>
              </button>
              <span class="uh-subhead-title">{{ data.name }}的勋章墙</span>
              <span class="uh-subhead-holder"></span>
            </div>
            <div class="uh-subbody">
              <BadgeWall :earned="earnedBadges" :locked="lockedBadges" :level="data.level" />
            </div>
          </div>
        </Transition>

        <!-- ===== 二级：设置（图二内容：备注 / 分组 / 权限 / 免打扰 / 黑名单 / 删除好友） ===== -->
        <Transition name="uh-sub">
          <div v-if="showSettings && data" class="uh-subpage uh-settings">
            <div class="uh-subhead">
              <button type="button" class="uh-back-dark" @click="showSettings = false">
                <el-icon :size="18"><ArrowLeft /></el-icon>
              </button>
              <span class="uh-subhead-title">设置</span>
              <span class="uh-subhead-holder"></span>
            </div>
            <div class="uh-set-body">
              <div class="uh-set-group">
                <button type="button" class="uh-cell" @click="editRemark">
                  <span class="uh-cell-label">备注</span>
                  <span class="uh-cell-value">{{ pref.remark || '未设置' }}</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
                <div class="uh-cell">
                  <span class="uh-cell-label">分组</span>
                  <span class="uh-cell-value">我的好友</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </div>
              </div>

              <div class="uh-set-group">
                <button type="button" class="uh-cell" @click="comingSoon('推荐该联系人')">
                  <span class="uh-cell-label">推荐该联系人</span>
                  <span class="uh-cell-value"></span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
                <button type="button" class="uh-cell" @click="comingSoon('权限设置')">
                  <span class="uh-cell-label">权限设置</span>
                  <span class="uh-cell-value"></span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
              </div>

              <div class="uh-set-group">
                <button type="button" class="uh-cell" @click="pref.care = !pref.care">
                  <span class="uh-cell-label">特别关心</span>
                  <span class="uh-cell-value">{{ pref.care ? '已开启' : '未开启' }}</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
                <button type="button" class="uh-cell" @click="comingSoon('亲密关系')">
                  <span class="uh-cell-label">亲密关系</span>
                  <span class="uh-cell-value"></span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
                <button type="button" class="uh-cell" @click="comingSoon('关于他的线索')">
                  <span class="uh-cell-label">关于他的线索</span>
                  <span class="uh-cell-value"></span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
              </div>

              <div class="uh-set-group">
                <div class="uh-cell">
                  <span class="uh-cell-label">好友消息免打扰</span>
                  <span class="uh-cell-value"></span>
                  <el-switch v-model="pref.mute" size="small" class="uh-switch" />
                </div>
                <div class="uh-cell">
                  <span class="uh-cell-label">加入黑名单</span>
                  <span class="uh-cell-value"></span>
                  <el-switch v-model="pref.blocked" size="small" class="uh-switch" />
                </div>
              </div>

              <!-- 删除好友：放在设置列表末尾的独立白色行，随内容滚动，不再吸底 -->
              <div class="uh-set-group uh-set-del-group">
                <button type="button" class="uh-cell uh-del" :disabled="removing" @click="removeFriend">
                  删除好友
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import BadgeWall from '@/components/profile/BadgeWall.vue'
import { deleteSession } from '@/api/messages'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useUserHomepage } from '@/composables/useUserHomepage'
import {
  ArrowLeft, ArrowRight, MoreFilled, User,
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()
const { siteMascot } = useSiteConfig()
const { visible, loading, data, error, close } = useUserHomepage()

/** 二级页：勋章墙 / 设置，跟随浮层生命周期复位 */
const showWall = ref(false)
const showSettings = ref(false)
watch(visible, (v) => {
  if (!v) {
    showWall.value = false
    showSettings.value = false
  }
})

const removing = ref(false)
const agentMark = computed(() => siteMascot.value || '')

const ROLE_LABELS: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
/** 封面底色：按角色给一套低饱和渐变，学生偏紫蓝、教师偏青绿，管理员走中性石板色 */
const ROLE_GRADIENTS: Record<string, string> = {
  student: 'linear-gradient(140deg, #4a6cf7 0%, #6d5cf0 52%, #8b45e8 100%)',
  teacher: 'linear-gradient(140deg, #0e9f8f 0%, #0b7f92 52%, #12628f 100%)',
  admin: 'linear-gradient(140deg, #5a6b83 0%, #3d4c63 100%)',
}

const roleLabel = computed(() => ROLE_LABELS[data.value?.role || ''] || '用户')
/** 渐变之上叠一层右上角柔光，避免大色块显得死板 */
const heroGradient = computed(() => {
  const base = ROLE_GRADIENTS[data.value?.role || 'student'] || ROLE_GRADIENTS.student
  return `radial-gradient(circle at 82% 6%, rgba(255, 255, 255, 0.32) 0%, rgba(255, 255, 255, 0) 56%), ${base}`
})

/** 学生看班级、教师看职称与所属单位 */
const roleLine = computed(() => {
  const d = data.value
  if (!d) return ''
  if (d.role === 'student') return d.class_name || ''
  return d.title || d.department || ''
})

const friendCount = computed(() => data.value?.stats.find((s) => s.key === 'contacts')?.value ?? 0)
const isFriend = computed(() => !!data.value?.mutual.has_conversation)
const isSelf = computed(() => !!data.value && data.value.id === auth.user?.id)

/** 好友设置项（备注 / 特别关心 / 免打扰 / 黑名单）：本地保存，仅自己可见 */
interface FriendPref {
  remark: string
  care: boolean
  mute: boolean
  blocked: boolean
}
const emptyPref = (): FriendPref => ({ remark: '', care: false, mute: false, blocked: false })
const pref = ref<FriendPref>(emptyPref())
const prefKey = (userId: number) => `uh-friend-pref-${userId}`

watch(() => data.value?.id, (id) => {
  if (!id) {
    pref.value = emptyPref()
    return
  }
  const raw = localStorage.getItem(prefKey(id))
  pref.value = raw ? { ...emptyPref(), ...JSON.parse(raw) } : emptyPref()
}, { immediate: true })

watch(pref, (value) => {
  const id = data.value?.id
  if (id) localStorage.setItem(prefKey(id), JSON.stringify(value))
}, { deep: true })

/** 尚未开发的入口：给出明确提示，不做无声无响应的死按钮 */
function comingSoon(name: string) {
  ElMessage.info(`${name}暂未开放，可以先用「发消息」联系 TA`)
}

/** 备注：仅自己可见的本地备注名，协议账号本身不改名 */
async function editRemark() {
  const d = data.value
  if (!d) return
  try {
    const { value } = await ElMessageBox.prompt('设置一个仅自己可见的备注名', '备注', {
      inputValue: pref.value.remark,
      inputPlaceholder: `例如：同班 ${d.name}`,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    pref.value.remark = (value || '').trim()
    ElMessage.success(pref.value.remark ? '备注已保存' : '备注已清除')
  } catch {
    /* 取消 */
  }
}

const earnedBadges = computed(() => (data.value?.badges || []).filter((b) => b.earned))
const lockedBadges = computed(() => (data.value?.badges || []).filter((b) => !b.earned))
/** 勋章带：已点亮在前保持获得顺序，未点亮按进度倒序排在后面，一整排横向滑动 */
const allBadges = computed(() => [
  ...earnedBadges.value,
  ...[...lockedBadges.value].sort((a, b) => b.progress - a.progress),
])
/** 主页只留 3 条亮点，其余留给勋章墙与资料，保证一屏多一点读完 */
const topHighlights = computed(() => (data.value?.highlights || []).slice(0, 3))

const aboutFields = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    { label: d.role === 'student' ? '学号' : '工号', value: d.username },
    { label: '学院', value: d.college || '' },
    d.role === 'student'
      ? { label: '班级', value: d.class_name || '' }
      : { label: '职称', value: d.title || '' },
    { label: '所属单位', value: d.department || '' },
  ].filter((f) => f.value)
})

/** 「我们之间」：只在存在真实关联时展示，自己看自己时不显示 */
const mutualPills = computed(() => {
  const m = data.value?.mutual
  if (!m || data.value?.id === auth.user?.id) return []
  const pills: string[] = []
  if (m.is_my_tutor) pills.push('我的辅导员')
  if (m.is_my_student) pills.push('我的学生')
  if (m.same_college) pills.push('同学院')
  if (m.common_groups > 0) pills.push(`同在 ${m.common_groups} 个群聊`)
  return pills
})

/** 加为好友时预填的问候草稿：让用户自己按下发送，不替对方/自己发消息 */
const greeting = computed(() => `你好，我是${auth.userName || ''}，想和你认识一下 👋`)

/**
 * 打开与该用户的会话：
 * 教师端落到 /teacher/messages，学生端落到工作台的「消息中心」，
 * 用 query 带上 chat / chatName / draft，由消息页负责打开会话并预填草稿。
 */
function goChat(draft?: string) {
  const d = data.value
  if (!d) return
  if (d.role === 'admin' || auth.user?.role === 'admin') return
  const query: Record<string, string> = { chat: String(d.id), chatName: d.name }
  if (draft) query.draft = draft
  const path = auth.user?.role === 'teacher' ? '/teacher/messages' : '/student/workbench'
  close()
  router.push({ path, query })
}

/** 删除好友：二次确认后从我的会话列表移除该联系人（服务端记隐藏水位，对方不受影响） */
async function removeFriend() {
  const d = data.value
  if (!d) return
  try {
    await ElMessageBox.confirm(
      `确定把「${d.name}」从消息列表移除？聊天记录保留、对方不受影响。`,
      '删除好友',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  removing.value = true
  try {
    await deleteSession(`s-${d.id}`)
    if (data.value) data.value.mutual.has_conversation = false
    showSettings.value = false
    ElMessage.success(`已移除 ${d.name}`)
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  } finally {
    removing.value = false
  }
}
</script>

<style scoped>
.uh-page {
  position: fixed;
  inset: 0;
  z-index: 3100;
  background: var(--tui-bg, #f2f3f5);
  overflow: hidden;
}
.uh-main {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  scrollbar-width: none;
}
.uh-main::-webkit-scrollbar { display: none; width: 0; }

/* ===== 封面 ===== */
.uh-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: 208px;
  padding: 14px 16px 24px;
  overflow: hidden;
}
.uh-hero-scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(12, 16, 24, 0.02) 0%,
    rgba(12, 16, 24, 0.14) 48%,
    rgba(12, 16, 24, 0.58) 100%
  );
}
.uh-hero-mark {
  position: absolute;
  right: -12px;
  bottom: -8px;
  width: 100px;
  height: 100px;
  object-fit: contain;
  opacity: 0.15;
  pointer-events: none;
}
.uh-back {
  position: absolute;
  left: 12px;
  top: calc(12px + env(safe-area-inset-top));
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.36);
  border-radius: 50%;
  background: rgba(10, 12, 16, 0.3);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(6px);
}
.uh-back:active { background: rgba(10, 12, 16, 0.46); }
.uh-hero-more {
  position: absolute;
  right: 12px;
  top: calc(12px + env(safe-area-inset-top));
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.36);
  border-radius: 50%;
  background: rgba(10, 12, 16, 0.3);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(6px);
}
.uh-hero-more:active { background: rgba(10, 12, 16, 0.46); }
.uh-hero-loading {
  position: relative;
  z-index: 1;
  padding-bottom: 16px;
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
}
.uh-cast { position: relative; z-index: 1; display: flex; align-items: center; gap: 12px; }
.uh-avatar {
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 21px;
  font-weight: 700;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.26);
}
.uh-cast-main { flex: 1; min-width: 0; }
.uh-name-row { display: flex; align-items: center; gap: 7px; }
.uh-name {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.32);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-role {
  flex-shrink: 0;
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.uh-lv-chip {
  flex-shrink: 0;
  padding: 1px 8px;
  border-radius: 999px;
  background: linear-gradient(135deg, #fde68a, #f59e0b);
  color: #4a2f04;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.3px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.26);
}
.uh-signature {
  margin: 6px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.92);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.uh-facts {
  position: relative;
  z-index: 1;
  margin-top: 10px;
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.78);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-facts i { margin: 0 5px; font-style: normal; color: rgba(255, 255, 255, 0.42); }
.uh-numbers {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.72);
}
.uh-numbers b {
  font-size: 15px;
  font-weight: 800;
  margin-right: 3px;
  color: #fff;
  font-variant-numeric: tabular-nums;
}
.uh-sep { width: 1px; height: 12px; background: rgba(255, 255, 255, 0.24); }

/* ===== 内容区：整块通铺，靠白底与灰底两层色差分块（微信 / QQ 设置页做法） ===== */
.uh-body {
  position: relative;
  z-index: 2;
  margin-top: -16px;
  padding: 30px 0 calc(88px + env(safe-area-inset-bottom));
  border-radius: 20px 20px 0 0;
  background: var(--tui-bg, #f2f3f5);
  min-height: 50vh;
}
.uh-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 56px 0;
  color: var(--tui-text-quiet, #98a2b3);
  font-size: 13px;
}

/* 灰色底上的关系标签：白底 + 发丝边，比蓝底更像系统标签 */
.uh-mutual {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 16px 2px;
}
.uh-mutual span {
  padding: 3px 10px;
  border-radius: 4px;
  border: 1px solid #e8ebf0;
  background: var(--tui-surface, #fff);
  color: #667085;
  font-size: 11.5px;
}

/* ===== 勋章带：无卡片外框，整排通铺在灰底上，超宽横向滑动 ===== */
.uh-strip-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 15px 16px 6px;
}
.uh-strip-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: #8b929e;
  letter-spacing: 0.3px;
}
.uh-strip-more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 11.5px;
  color: #98a2b3;
  cursor: pointer;
}
.uh-strip-more:active { color: var(--tui-brand, #2563eb); }
.uh-badges {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  -webkit-overflow-scrolling: touch;
  padding: 2px 16px 16px;
  scrollbar-width: none;
}
.uh-badges::-webkit-scrollbar { display: none; width: 0; }
.uh-badge {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 64px;
  padding: 0;
  border: none;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}
.uh-badge:active .uh-badge-disc { transform: scale(0.93); }
.uh-badge-disc {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  padding: 3px;
  border-radius: 50%;
  /* 外圈：分级渐变描边 */
  background: var(--uh-ring);
  box-shadow: 0 3px 10px var(--uh-glow);
  transition: transform 0.15s ease;
}
.uh-badge-disc i {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 26%, #3a445f 0%, #202737 72%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16), inset 0 -3px 8px rgba(0, 0, 0, 0.34);
  font-style: normal;
  font-size: 23px;
  line-height: 1;
}
/* 未点亮：环与内芯转灰、徽记降饱和，只做「灰底上的暗章」 */
.uh-badge.is-locked .uh-badge-disc {
  background: linear-gradient(140deg, #e6eaf0, #cfd6e0);
  box-shadow: none;
}
.uh-badge.is-locked .uh-badge-disc i {
  background: #f5f7fa;
  box-shadow: inset 0 0 0 1px rgba(16, 24, 40, 0.05);
  filter: grayscale(1);
  opacity: 0.45;
}
.uh-badge-name {
  max-width: 100%;
  font-size: 10.5px;
  line-height: 1.25;
  color: #475467;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-badge.is-locked .uh-badge-name { color: #aeb6c2; }
/* 分级配色：与勋章墙保持同一套色 */
.tier-bronze { --uh-ring: linear-gradient(140deg, #f7c891, #bb6a2a); --uh-glow: rgba(187, 106, 42, 0.3); }
.tier-silver { --uh-ring: linear-gradient(140deg, #f1f5f9, #98a6b8); --uh-glow: rgba(152, 166, 184, 0.32); }
.tier-gold { --uh-ring: linear-gradient(140deg, #ffeeb0, #dfa200); --uh-glow: rgba(223, 162, 0, 0.36); }
.tier-diamond { --uh-ring: linear-gradient(140deg, #cdefff, #22a0da); --uh-glow: rgba(34, 160, 218, 0.34); }

/* 组标签：直接坐在灰色底上（微信设置页的小标题位置） */
.uh-group-label {
  margin: 0;
  padding: 14px 16px 7px;
  font-size: 12.5px;
  font-weight: 600;
  color: #8b929e;
  letter-spacing: 0.3px;
}

/* 白底行组：无圆角、无边框、无阴影，仅靠底色差与行内细线分层 */
.uh-group {
  background: var(--tui-surface, #fff);
}

/* 组内小标签：把「近期亮点」并进同一块白组，只用浅灰底与细线分区 */
.uh-inline-label {
  padding: 9px 16px;
  border-bottom: 1px solid #f2f4f7;
  background: #fafbfc;
  color: #98a2b3;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.uh-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 48px;
  padding: 10px 16px;
  border: none;
  border-bottom: 1px solid #f2f4f7;
  background: transparent;
  font-family: inherit;
  font-size: 13.5px;
  text-align: left;
}
.uh-cell:last-child { border-bottom: none; }
.uh-cell-label { flex-shrink: 0; color: var(--tui-text, #344054); }
.uh-cell-value {
  flex: 1;
  min-width: 0;
  text-align: right;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-cell-value.is-quiet { flex: 0 0 auto; }
.uh-cell-icon { flex-shrink: 0; font-size: 15px; line-height: 1.4; }
.uh-cell-stack { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.uh-cell-title {
  color: var(--tui-text, #344054);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-cell-sub { font-size: 11px; color: #98a2b3; }

/* ===== 固定底部操作条：三键通栏（两个描边按钮 + 蓝色主按钮，图一格式） ===== */
.uh-actionbar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 6;
  display: flex;
  gap: 9px;
  padding: 9px 12px calc(9px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.98);
  border-top: 1px solid #ededed;
  backdrop-filter: blur(10px);
}
.uh-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: var(--tui-surface, #fff);
  color: #1f2329;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.uh-btn:active { background: #f2f3f5; }
/* 主操作：蓝色实心「发消息」，唯一操作按钮占满整条 */
.uh-btn.is-primary {
  border-color: #0099ff;
  background: #0099ff;
  color: #fff;
}
.uh-btn.is-primary:active { background: #0088e6; border-color: #0088e6; }
.uh-btn:disabled { opacity: 0.6; }

/* ===== 二级：勋章墙 ===== */
.uh-subpage {
  position: absolute;
  inset: 0;
  z-index: 8;
  display: flex;
  flex-direction: column;
  background: var(--tui-bg, #f2f3f5);
}
.uh-subhead {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  padding-top: calc(10px + env(safe-area-inset-top));
  background: var(--tui-surface, #fff);
}
.uh-back-dark {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #344054;
  cursor: pointer;
}
.uh-back-dark:active { background: #f2f4f7; }
.uh-subhead-title { font-size: 14.5px; font-weight: 700; color: #101828; }
.uh-subhead-holder { width: 34px; }
.uh-subbody {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  scrollbar-width: none;
}
.uh-subbody::-webkit-scrollbar { display: none; width: 0; }

/* ===== 二级：设置页（灰底分组 + 白底行组，底部红色删除好友） ===== */
.uh-settings { z-index: 9; }
.uh-set-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0 16px;
  scrollbar-width: none;
}
.uh-set-body::-webkit-scrollbar { display: none; width: 0; }
.uh-set-group {
  margin-bottom: 10px;
  background: var(--tui-surface, #fff);
}
.uh-chev { flex-shrink: 0; color: #c0c4cc; }
.uh-switch { flex-shrink: 0; }
/* 删除好友：设置列表末尾的独立白行，红字居中，随内容滚动 */
.uh-set-del-group { margin-top: 4px; }
.uh-del {
  justify-content: center;
  width: 100%;
  height: 50px;
  border: none;
  border-bottom: none;
  border-radius: 0;
  background: transparent;
  color: #fa5151;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}
.uh-del:active { background: #fdf0f0; }
.uh-del:disabled { opacity: 0.6; }

/* ===== 动效 ===== */
.uh-page-enter-active,
.uh-page-leave-active { transition: transform 0.3s cubic-bezier(0.33, 1, 0.68, 1); }
.uh-page-enter-from,
.uh-page-leave-to { transform: translateX(100%); }

.uh-sub-enter-active,
.uh-sub-leave-active { transition: transform 0.28s cubic-bezier(0.33, 1, 0.68, 1); }
.uh-sub-enter-from,
.uh-sub-leave-to { transform: translateX(100%); }
</style>