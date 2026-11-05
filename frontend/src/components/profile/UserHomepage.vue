<template>
  <Teleport to="body">
    <!-- 进出场复用全站那套「子页覆盖」动画（styles/animations.css 的 .subpage）：
         与布局层最外层的进入 / 退出动画同一份实现，不再维护本组件的私有滑入曲线。
         :duration 320 = CSS 0.3s + 20ms 余量，兜底移除离场节点。 -->
    <Transition name="subpage" :duration="320">
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
                  <!-- 关系标识挂在名字后面：特别关心（我设的）/ 亲密关系（双方任一设的） -->
                  <div v-if="careOn || intimacyInfo" class="uh-mark-row">
                    <span v-if="careOn" class="uh-care-chip">特别关心</span>
                    <span
                      v-if="intimacyInfo"
                      class="uh-intimacy-chip"
                      :style="{ borderColor: intimacyInfo.color, color: intimacyInfo.color }"
                    >{{ intimacyInfo.icon }} {{ intimacyInfo.label }}</span>
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

              <!-- 勋章：主页第一块。整排铺在灰底上（没有卡片外框），
                   一排排开、超宽横向滑动，点任意一枚进「勋章墙」看详情。
                   排序按 QQ 资料卡的读法：先看这个人拿到了什么，再看说过什么。 -->
              <div class="uh-strip-head">
                <h3 class="uh-strip-title">{{ isSelf ? '我的勋章' : 'TA 的勋章' }}</h3>
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
                  :class="{ 'is-locked': !b.earned }"
                  :title="b.earned
                    ? `${b.name} · ${b.desc}`
                    : `${b.name} · ${b.target_label}（${b.progress}%）`"
                  @click="showWall = true"
                >
                  <BadgeMedal :icon="b.icon" :tier="b.tier" :earned="b.earned" :size="38" />
                  <span class="uh-badge-name">{{ b.name }}</span>
                </button>
              </div>

              <!-- 动态：TA 发过的帖子。行版式与设置页白组同构，不另起卡片流 -->
              <h3 class="uh-group-label">{{ isSelf ? '我的动态' : 'TA 的动态' }}</h3>

              <div v-if="postsLoading" class="uh-posts-state">正在加载动态…</div>

              <button
                v-else-if="postsError"
                type="button"
                class="uh-posts-state is-error"
                @click="loadUserPosts"
              >{{ postsError }}，点击重试</button>

              <template v-else-if="userPosts.length">
                <div class="uh-group">
                  <button
                    v-for="p in userPosts"
                    :key="p.id"
                    type="button"
                    class="uh-cell uh-post"
                    @click="activePostId = p.id"
                  >
                    <span class="uh-post-main">
                      <span class="uh-post-title">{{ p.title }}</span>
                      <span class="uh-post-meta">
                        <i class="uh-post-cat">{{ p.category }}</i>
                        <span>{{ postTime(p.created_at) }}</span>
                        <span v-if="p.like_count">· {{ p.like_count }} 赞</span>
                        <span v-if="p.comment_count">· {{ p.comment_count }} 评论</span>
                      </span>
                    </span>
                    <img v-if="p.images?.length" :src="p.images[0]" class="uh-post-thumb" alt="" loading="lazy" />
                    <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                  </button>
                </div>
                <button
                  v-if="postsMore"
                  type="button"
                  class="uh-post-more"
                  :disabled="postsLoadingMore"
                  @click="loadMorePosts"
                >{{ postsLoadingMore ? '加载中…' : '查看更多动态' }}</button>
              </template>

              <div v-else class="uh-posts-state is-empty">
                {{ isSelf ? '你还没有发过帖子' : 'TA 还没有发过帖子' }}
              </div>

              <!-- 近期亮点：与学生端个人主页成果卡一致的双列卡片 -->
              <h3 v-if="topHighlights.length" class="uh-group-label">近期亮点</h3>
              <div v-if="topHighlights.length" class="uh-hl-grid">
                <div v-for="(h, i) in topHighlights" :key="i" class="uh-hl-card">
                  <span class="uh-hl-icon">{{ h.icon }}</span>
                  <span class="uh-hl-title">{{ h.title }}</span>
                  <span class="uh-hl-sub">{{ h.subtitle }}</span>
                  <span class="uh-hl-date">{{ h.date }}</span>
                </div>
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

        <!-- ===== 二级：设置（QQ 好友设置那一页：备注 / 分组 / 推荐 / 权限 / 关心 / 亲密关系 / 免打扰 / 黑名单 / 删除） =====
             字段全部存在服务端（user_friend_settings），换设备也跟着走。 -->
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
                  <span class="uh-cell-value">{{ setting.remark || '未设置' }}</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
                <div class="uh-cell">
                  <span class="uh-cell-label">分组</span>
                  <span class="uh-cell-value">我的好友</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </div>
              </div>

              <div class="uh-set-group">
                <button type="button" class="uh-cell" @click="subPage = 'recommend'">
                  <span class="uh-cell-label">推荐该联系人</span>
                  <span class="uh-cell-value"></span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
                <button type="button" class="uh-cell" @click="subPage = 'permission'">
                  <span class="uh-cell-label">权限设置</span>
                  <span class="uh-cell-value">{{ permissionSummary }}</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
              </div>

              <div class="uh-set-group">
                <div class="uh-cell">
                  <span class="uh-cell-label">特别关心</span>
                  <span class="uh-cell-value">{{ setting.care ? '已开启' : '未开启' }}</span>
                  <el-switch
                    :model-value="setting.care"
                    size="small"
                    class="uh-switch"
                    @change="(v: any) => toggleCare(!!v)"
                  />
                </div>
                <button type="button" class="uh-cell" @click="subPage = 'intimacy'">
                  <span class="uh-cell-label">亲密关系</span>
                  <span class="uh-cell-value">{{ intimacyLabel || '未设置' }}</span>
                  <el-icon class="uh-chev" :size="13"><ArrowRight /></el-icon>
                </button>
              </div>

              <div class="uh-set-group">
                <div class="uh-cell">
                  <span class="uh-cell-label">好友消息免打扰</span>
                  <span class="uh-cell-value"></span>
                  <el-switch
                    :model-value="setting.mute"
                    size="small"
                    class="uh-switch"
                    @change="(v: any) => saveSetting({ mute: !!v })"
                  />
                </div>
                <div class="uh-cell">
                  <span class="uh-cell-label">加入黑名单</span>
                  <span class="uh-cell-value"></span>
                  <el-switch
                    :model-value="setting.blocked"
                    size="small"
                    class="uh-switch"
                    @change="(v: any) => saveSetting({ blocked: !!v })"
                  />
                </div>
              </div>

              <!-- 删除好友：放在设置列表末尾的独立白色行，随内容滚动，不再吸底 -->
              <div class="uh-set-group uh-set-del-group">
                <button type="button" class="uh-cell uh-del" :disabled="removing" @click="removeOrUnfollow">
                  {{ data.mutual.has_conversation ? '删除好友' : '取消关注' }}
                </button>
              </div>
            </div>
          </div>
        </Transition>

        <!-- ===== 三级：权限设置（QQ「动态权限」那一页：不看 TA 的动态 / 不让 TA 看我的动态） =====
             两个开关都会真的生效：前者过滤我的信息流，后者让对方的信息流过滤掉我的帖子。 -->
        <Transition name="uh-sub">
          <div v-if="subPage === 'permission' && data" class="uh-subpage uh-nested">
            <div class="uh-subhead">
              <button type="button" class="uh-back-dark" @click="subPage = ''">
                <el-icon :size="18"><ArrowLeft /></el-icon>
              </button>
              <span class="uh-subhead-title">权限设置</span>
              <span class="uh-subhead-holder"></span>
            </div>
            <div class="uh-set-body">
              <div class="uh-set-group">
                <div class="uh-cell">
                  <span class="uh-cell-label">不看 TA 的动态</span>
                  <span class="uh-cell-value"></span>
                  <el-switch
                    :model-value="setting.hide_peer_posts"
                    size="small"
                    class="uh-switch"
                    @change="(v: any) => saveSetting({ hide_peer_posts: !!v })"
                  />
                </div>
                <p class="uh-cell-hint">开启后，{{ data.name }}的帖子不再出现在你的信息流里（主动进 TA 主页仍可查看）。</p>
              </div>
              <div class="uh-set-group">
                <div class="uh-cell">
                  <span class="uh-cell-label">不让 TA 看我的动态</span>
                  <span class="uh-cell-value"></span>
                  <el-switch
                    :model-value="setting.hide_my_posts"
                    size="small"
                    class="uh-switch"
                    @change="(v: any) => saveSetting({ hide_my_posts: !!v })"
                  />
                </div>
                <p class="uh-cell-hint">开启后，{{ data.name }}的信息流和你的主页都不会再出现你发的帖子。</p>
              </div>
            </div>
          </div>
        </Transition>

        <!-- ===== 三级：亲密关系（QQ 亲密关系那套标识，选中即双方主页可见） ===== -->
        <Transition name="uh-sub">
          <div v-if="subPage === 'intimacy' && data" class="uh-subpage uh-nested">
            <div class="uh-subhead">
              <button type="button" class="uh-back-dark" @click="subPage = ''">
                <el-icon :size="18"><ArrowLeft /></el-icon>
              </button>
              <span class="uh-subhead-title">亲密关系</span>
              <span class="uh-subhead-holder"></span>
            </div>
            <div class="uh-set-body">
              <div class="uh-intimacy-grid">
                <button
                  v-for="o in INTIMACY_OPTIONS"
                  :key="o.code"
                  type="button"
                  class="uh-intimacy-card"
                  :class="{ on: setting.intimacy === o.code }"
                  :style="{ '--tone': o.color }"
                  @click="saveSetting({ intimacy: setting.intimacy === o.code ? '' : o.code })"
                >
                  <span class="uh-intimacy-icon">{{ o.icon }}</span>
                  <span class="uh-intimacy-name">{{ o.label }}</span>
                  <span v-if="setting.intimacy === o.code" class="uh-intimacy-on">已设置</span>
                </button>
              </div>
              <p class="uh-cell-hint uh-intimacy-hint">
                设置后，你们双方的主页都会挂上这枚关系标识；再点一次可取消。对方也可以在自己的设置里改。
              </p>
              <div v-if="peerIntimacyLabel" class="uh-set-group">
                <div class="uh-cell">
                  <span class="uh-cell-label">TA 把你设为</span>
                  <span class="uh-cell-value">{{ peerIntimacyLabel }}</span>
                </div>
              </div>
            </div>
          </div>
        </Transition>

        <!-- ===== 三级：推荐该联系人（挑一个好友，把 TA 推荐过去；走站内消息，真正发得出去） ===== -->
        <Transition name="uh-sub">
          <div v-if="subPage === 'recommend' && data" class="uh-subpage uh-nested">
            <div class="uh-subhead">
              <button type="button" class="uh-back-dark" @click="subPage = ''">
                <el-icon :size="18"><ArrowLeft /></el-icon>
              </button>
              <span class="uh-subhead-title">推荐给好友</span>
              <span class="uh-subhead-holder"></span>
            </div>
            <div class="uh-rec-body">
              <div class="uh-rec-card">
                <el-avatar :size="40" :src="data.avatar || undefined">{{ data.name?.[0] }}</el-avatar>
                <div class="uh-rec-card-main">
                  <span class="uh-rec-name">{{ data.name }}</span>
                  <span class="uh-rec-sub">{{ recommendCardLine }}</span>
                </div>
              </div>
              <el-input
                v-model="recommendKeyword"
                class="uh-rec-search"
                placeholder="搜索好友姓名 / 学号"
                clearable
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <div v-if="recommendLoading" class="uh-rec-state">正在加载好友…</div>
              <div v-else-if="!recommendFiltered.length" class="uh-rec-state">
                {{ recommendKeyword.trim() ? '没有匹配的好友' : '还没有可推荐的人，先去关注几位同学' }}
              </div>
              <template v-else>
                <button
                  v-for="f in recommendFiltered"
                  :key="f.id"
                  type="button"
                  class="uh-cell uh-rec-row"
                  :disabled="recommending === f.id"
                  @click="sendRecommend(f)"
                >
                  <el-avatar :size="34" :src="f.avatar || undefined">{{ f.name.slice(0, 1) }}</el-avatar>
                  <span class="uh-rec-row-name">{{ f.name }}<i>{{ f.username }}</i></span>
                  <span class="uh-rec-send">{{ recommending === f.id ? '发送中…' : '推荐' }}</span>
                </button>
              </template>
            </div>
          </div>
        </Transition>

        <!-- ===== 三级：帖子详情 =====
             主页里点一条动态就在这一层打开，不跳出去 —— 返回时主页还停在原来的滚动位置。
             z-index 抬到 3200：详情页默认 2600 会被本主页（3100）整个盖住。 -->
        <PostDetailPage
          v-if="activePostId"
          :post-id="activePostId"
          :z-index="3200"
          @close="postDetailLeaving = true"
          @closed="onPostDetailClosed"
          @updated="onPostUpdated"
          @deleted="onPostDeleted"
        />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
// v6.1 弹窗减负：备注/删除好友等轻交互走底部动作面板
import { actionPrompt, actionConfirm } from '@/composables/useActionSheet'
import { useResponsive } from '@/composables/useResponsive'
import { useBackLayer } from '@/composables/useBackLayer'

import BadgeWall from '@/components/profile/BadgeWall.vue'
import BadgeMedal from '@/components/profile/BadgeMedal.vue'
import PostDetailPage from '@/components/community/PostDetailPage.vue'
import { deleteSession, sendMessage } from '@/api/messages'
import {
  getContacts,
  unfollowUser,
  type ContactUser,
  type FriendSetting,
  type FriendSettingPatch,
} from '@/api/social'
import { getUserPosts, type CommunityPost } from '@/api/community'
import { useAuthStore } from '@/stores/auth'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { useUserHomepage } from '@/composables/useUserHomepage'
import {
  emptyFriendSetting,
  fetchFriendSettingState,
  saveFriendSetting,
  intimacyMeta,
  INTIMACY_OPTIONS,
} from '@/composables/useFriendSettings'
import { parseServerTime } from '@/utils/datetime'
import {
  ArrowLeft, ArrowRight, MoreFilled, Search, User,
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
/**
 * 「是不是我的人」：我关注的，或者聊过天的。
 *
 * 原来只看 has_conversation（聊过天），从好友列表点进来但还没说过话的人会被当成陌生人 ——
 * 右上角没有「…」，进不了备注 / 免打扰 / 删除，发消息还会塞一句自我介绍。
 * 本站口径是「好友 = 我关注的」，主页跟通讯录保持一致。
 */
const isFriend = computed(() => {
  const m = data.value?.mutual
  return !!m && (m.is_following || m.has_conversation)
})
const isSelf = computed(() => !!data.value && data.value.id === auth.user?.id)

/* ================= 好友设置（服务端持久化） =================
   备注 / 特别关心 / 免打扰 / 黑名单 / 动态权限 / 亲密关系 都存在
   user_friend_settings（见后端 models.social.FriendSetting）：
   关掉浏览器再回来还在，换手机登录也跟着走。缓存由 useFriendSettings 统一维护，
   消息列表的「特别」标读的是同一份数据。 */
const setting = ref<FriendSetting>(emptyFriendSetting(0))
const peerSetting = ref<FriendSetting | null>(null)
/** 三级页：权限设置 / 亲密关系 / 推荐给好友（在设置页之上再叠一层） */
const subPage = ref<'' | 'permission' | 'intimacy' | 'recommend'>('')

watch(visible, (v) => {
  if (!v) subPage.value = ''
})
// 关掉设置页时，它的三级子页要一起收：否则下次打开设置会直接落在上一次的子页上
watch(showSettings, (v) => {
  if (!v) subPage.value = ''
})

/** 移动端：主页 / 勋章墙 / 设置 / 三级页各算一层，系统返回一次只收一层（见 useBackLayer） */
const { isMobile: homepageIsMobile } = useResponsive()
useBackLayer(computed(() => homepageIsMobile.value && visible.value), close)
useBackLayer(computed(() => homepageIsMobile.value && showWall.value), () => { showWall.value = false })
useBackLayer(computed(() => homepageIsMobile.value && showSettings.value), () => { showSettings.value = false })
useBackLayer(computed(() => homepageIsMobile.value && !!subPage.value), () => { subPage.value = '' })

watch(() => data.value?.id, async (id) => {
  setting.value = emptyFriendSetting(0)
  peerSetting.value = null
  if (!id || id === auth.user?.id) return
  try {
    const state = await fetchFriendSettingState(id)
    // 换人竞态：请求回来时主页已经翻到别人了，这份结果必须丢掉
    if (data.value?.id !== id) return
    setting.value = state.mine
    peerSetting.value = state.peer
  } catch {
    // 拉不到就按「全默认」渲染：设置页是多步操作，不该为一次失败把整页拦成错误态
  }
}, { immediate: true })

/** 局部保存：先乐观翻开关，失败再回滚 —— 开关点下去要有立刻的反馈 */
async function saveSetting(patch: FriendSettingPatch) {
  const id = data.value?.id
  if (!id) return
  const prev = { ...setting.value }
  setting.value = { ...setting.value, ...patch } as FriendSetting
  try {
    const state = await saveFriendSetting(id, patch)
    setting.value = state.mine
    peerSetting.value = state.peer
  } catch (e: any) {
    setting.value = prev
    ElMessage.error(e?.response?.data?.detail || '设置保存失败，请稍后重试')
  }
}

const careOn = computed(() => setting.value.care)
const intimacyLabel = computed(() => intimacyMeta(setting.value.intimacy)?.label || '')
const peerIntimacyLabel = computed(() => intimacyMeta(peerSetting.value?.intimacy || '')?.label || '')
/** 关系标识：谁都行设一次，双方主页都能看到 —— 先看自己设的，再看对方设的 */
const intimacyInfo = computed(
  () => intimacyMeta(setting.value.intimacy) || intimacyMeta(peerSetting.value?.intimacy || '') || null,
)
/** 设置页那一行的摘要：不动开关也能看出「动过权限」 */
const permissionSummary = computed(() => {
  const n = (setting.value.hide_peer_posts ? 1 : 0) + (setting.value.hide_my_posts ? 1 : 0)
  return n === 0 ? '' : n === 2 ? '两项已设置' : '1 项已设置'
})

function toggleCare(next: boolean) {
  void saveSetting({ care: next })
  ElMessage.success(next ? '已设为特别关心' : '已取消特别关心')
}

/** 备注：仅自己可见的称呼，账号本身不改名 */
async function editRemark() {
  const d = data.value
  if (!d) return
  const value = await actionPrompt('设置一个仅自己可见的备注名', '备注', setting.value.remark, {
    placeholder: `例如：同班 ${d.name}`,
    confirmButtonText: '保存',
  })
  if (value === null) return
  const remark = (value || '').trim()
  await saveSetting({ remark })
  ElMessage.success(remark ? '备注已保存' : '备注已清除')
}

/* ================= 推荐该联系人 =================
   QQ 的做法是把这张资料卡推给另一个好友：这里走站内消息，
   选一个好友 → 发一条带账号信息的推荐消息过去，对方点开就能找到这个人。 */
const recommendKeyword = ref('')
const recommendFriends = ref<ContactUser[]>([])
const recommendLoading = ref(false)
const recommending = ref(0)

const recommendCardLine = computed(() => {
  const d = data.value
  if (!d) return ''
  const parts = [d.username, d.college, d.role === 'student' ? d.class_name : d.title]
  return parts.filter(Boolean).join(' · ')
})
const recommendFiltered = computed(() => {
  const kw = recommendKeyword.value.trim().toLowerCase()
  if (!kw) return recommendFriends.value
  return recommendFriends.value.filter(
    (f) => f.name.toLowerCase().includes(kw) || f.username.toLowerCase().includes(kw),
  )
})

watch(subPage, async (v) => {
  if (v !== 'recommend' || recommendFriends.value.length) return
  recommendLoading.value = true
  try {
    const friends = await getContacts({ tab: 'friends', limit: 200 })
    // 师生之间未必互关，好友名单经常是空的：退到「我关注的」兜底，
    // 否则这一页对大多数老师直接是一张死空态
    recommendFriends.value = friends.length
      ? friends
      : await getContacts({ tab: 'following', limit: 200 })
  } catch {
    ElMessage.error('好友列表加载失败')
  } finally {
    recommendLoading.value = false
  }
})

async function sendRecommend(friend: ContactUser) {
  const d = data.value
  if (!d || recommending.value) return
  recommending.value = friend.id
  try {
    const from = auth.userName || '我'
    const content = [
      `【推荐联系人】${d.name}（${d.username}）`,
      recommendCardLine.value,
      `${from} 觉得你们可能认识，去主页打个招呼吧～`,
    ].filter(Boolean).join('\n')
    await sendMessage(friend.id, content)
    ElMessage.success(`已推荐给 ${friend.name}`)
    subPage.value = ''
  } catch {
    ElMessage.error('推荐失败，请稍后再试')
  } finally {
    recommending.value = 0
  }
}

/* ================= TA 的动态 =================
   主页是「了解这个人」的地方：TA 说过什么，比勋章和字段更能说明问题。
   数据走 /community/users/{id}/posts（游标分页），卡片只显示摘要，
   点开在主页之上叠一层帖子详情（z-index 3200），不跳出主页上下文。 */

/**
 * 一次拉多少条：主页不是帖子流 —— 6 条够看清「TA 在发什么」，
 * 再多会把下方的勋章、资料整块推到屏幕外；其余靠「查看更多动态」。
 */
const POST_PAGE = 6

const userPosts = ref<CommunityPost[]>([])
const postsLoading = ref(false)
const postsError = ref('')
const postsMore = ref(false)
const postsLoadingMore = ref(false)
/** 正在查看的帖子 id：非 0 即挂载详情页（详情页「挂载即打开」） */
const activePostId = ref(0)
/** 详情退场中：等 after-leave 再卸载，否则退场动画没机会播 */
const postDetailLeaving = ref(false)

async function loadUserPosts() {
  const id = data.value?.id
  if (!id) return
  postsLoading.value = true
  postsError.value = ''
  try {
    const list = await getUserPosts(id, { limit: POST_PAGE })
    userPosts.value = list
    postsMore.value = list.length >= POST_PAGE
  } catch (e: any) {
    postsError.value = e?.response?.data?.detail || '动态加载失败'
    userPosts.value = []
    postsMore.value = false
  } finally {
    postsLoading.value = false
  }
}

/** 游标翻页：只取比手上最后一条更早的，翻页期间有人发新帖也不会重复 */
async function loadMorePosts() {
  const id = data.value?.id
  const last = userPosts.value[userPosts.value.length - 1]
  if (!id || !last || postsLoadingMore.value) return
  postsLoadingMore.value = true
  try {
    const list = await getUserPosts(id, { limit: POST_PAGE, before_id: last.id })
    userPosts.value = [...userPosts.value, ...list]
    postsMore.value = list.length >= POST_PAGE
  } catch {
    ElMessage.error('加载失败，请稍后重试')
  } finally {
    postsLoadingMore.value = false
  }
}

/** 列表里只放「月-日 时:分」：主页不是时间线，完整年份在这里是噪音 */
function postTime(iso: string | null): string {
  const ms = parseServerTime(iso)
  if (Number.isNaN(ms)) return ''
  const d = new Date(ms)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 详情里点赞 / 评论后同步列表上的计数，避免「刚点完赞回到主页数字没变」 */
function onPostUpdated(post: CommunityPost) {
  const hit = userPosts.value.find((p) => p.id === post.id)
  if (hit) Object.assign(hit, { like_count: post.like_count, comment_count: post.comment_count, liked: post.liked })
}

/** 详情里删掉了帖子：直接从主页列表里摘掉，不整块重拉 */
function onPostDeleted(id: number) {
  userPosts.value = userPosts.value.filter((p) => p.id !== id)
}

function onPostDetailClosed() {
  activePostId.value = 0
  postDetailLeaving.value = false
}

// 换人：清空上一个人的动态，再按新 id 拉一次
watch(() => data.value?.id, (id) => {
  userPosts.value = []
  postsError.value = ''
  postsMore.value = false
  activePostId.value = 0
  postDetailLeaving.value = false
  if (id) void loadUserPosts()
}, { immediate: true })


const earnedBadges = computed(() => (data.value?.badges || []).filter((b) => b.earned))
const lockedBadges = computed(() => (data.value?.badges || []).filter((b) => !b.earned))
/** 勋章带：已点亮在前保持获得顺序，未点亮按进度倒序排在后面，一整排横向滑动 */
const allBadges = computed(() => [
  ...earnedBadges.value,
  ...[...lockedBadges.value].sort((a, b) => b.progress - a.progress),
])
/** 主页只留 3 条亮点，其余留给勋章墙，保证一屏多一点读完 */
const topHighlights = computed(() => (data.value?.highlights || []).slice(0, 3))

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
 *   · 教师端 → /teacher/messages，query 用裸 id（教师端会话键就是用户 id）
 *   · 学生端 → /student/messages，query 必须是 **s-<id>**（学生会话键带前缀）
 *
 * 学生端别再往 /student/workbench 跳：工作台里那套是消息中心的旧实现，
 * 会话页的返回是「收回到工作台首页」，从好友列表点进来再返回就莫名其妙到了工作台。
 * 底部导航的「消息」早就是 /student/messages 了，这里跟它对齐。
 */
function goChat(draft?: string) {
  const d = data.value
  if (!d) return
  if (d.role === 'admin' || auth.user?.role === 'admin') return
  const isTeacher = auth.user?.role === 'teacher'
  const query: Record<string, string> = isTeacher
    ? { chat: String(d.id), chatName: d.name }
    : { chat: `s-${d.id}`, chatName: d.name }
  if (draft) query.draft = draft
  const path = isTeacher ? '/teacher/messages' : '/student/messages'
  close()
  router.push({ path, query })
}

/**
 * 设置页末尾那个红色动作，按「有没有聊过」分两种：
 *   · 聊过 → 从消息列表移除（会话隐藏，关注关系保留，对方无感）；
 *   · 只关注没聊过 → 取消关注。不然这颗按钮点了什么都不发生，
 *     而这类人正是「好友 = 我关注的」名单里的大多数。
 */
function removeOrUnfollow() {
  return data.value?.mutual.has_conversation ? removeFriend() : unfollowTarget()
}

/** 取消关注：二次确认后删掉关注关系并收起主页（名单里这个人会消失） */
async function unfollowTarget() {
  const d = data.value
  if (!d) return
  const ok = await actionConfirm(
    `不再关注「${d.name}」？TA 会从好友列表里消失。`,
    '取消关注',
    { danger: true, confirmButtonText: '取消关注' },
  )
  if (!ok) return
  removing.value = true
  try {
    await unfollowUser(d.id)
    showSettings.value = false
    ElMessage.success(`已取消关注 ${d.name}`)
    close()
  } catch {
    ElMessage.error('取消关注失败，请稍后再试')
  } finally {
    removing.value = false
  }
}

/** 删除好友：二次确认后从我的会话列表移除该联系人（服务端记隐藏水位，对方不受影响） */
async function removeFriend() {
  const d = data.value
  if (!d) return
  const ok = await actionConfirm(
    `确定把「${d.name}」从消息列表移除？聊天记录保留、对方不受影响。`,
    '删除好友',
    { danger: true, confirmButtonText: '删除' },
  )
  if (!ok) return
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
.uh-badge:active { transform: scale(0.94); }
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

/* ===== 动态（TA 的帖子） =====
   与「资料」白组同构：一行一条，靠行内细线分隔。
   标题两行截断、元信息压到一行，保证一屏能看到 4~5 条。 */
.uh-posts-state {
  display: block;
  width: 100%;
  padding: 18px 16px;
  border: none;
  background: var(--tui-surface, #fff);
  font-family: inherit;
  font-size: 12.5px;
  line-height: 1.5;
  color: #98a2b3;
  text-align: center;
  cursor: default;
}
.uh-posts-state.is-error { color: #d92d20; cursor: pointer; }
.uh-posts-state.is-empty { color: #aeb6c2; }

.uh-post {
  align-items: flex-start;
  gap: 10px;
  padding-top: 11px;
  padding-bottom: 11px;
}
.uh-post-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.uh-post-title {
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.42;
  color: var(--tui-text, #344054);
  text-align: left;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.uh-post-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  font-size: 11px;
  color: #98a2b3;
  white-space: nowrap;
  overflow: hidden;
}
.uh-post-cat {
  flex-shrink: 0;
  padding: 0 5px;
  border-radius: 3px;
  background: #f2f4f7;
  color: #667085;
  font-style: normal;
  font-size: 10px;
  line-height: 15px;
}
.uh-post-thumb {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 6px;
  object-fit: cover;
  background: #f2f4f7;
}
.uh-post .uh-chev { margin-top: 2px; }

/* 「查看更多」：白底整行，与上面的行组连成一片（不额外做圆角按钮） */
.uh-post-more {
  display: block;
  width: 100%;
  padding: 13px 0;
  border: none;
  border-top: 1px solid #f2f4f7;
  background: var(--tui-surface, #fff);
  font-family: inherit;
  font-size: 12.5px;
  color: #667085;
  cursor: pointer;
}
.uh-post-more:disabled { opacity: 0.6; }
.uh-post-more:active { background: #f7f8fa; }

/* 近期亮点：与学生端个人主页成果卡一致的双列卡片 */
.uh-hl-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 0 16px 16px;
}
.uh-hl-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  padding: 12px;
  border: 1px solid #eef0f3;
  border-radius: 12px;
  background: var(--tui-surface, #fff);
  overflow: hidden;
}
.uh-hl-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: #f5f6f8;
  font-size: 15px;
  line-height: 1;
}
.uh-hl-title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  color: #344054;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.uh-hl-sub {
  font-size: 11px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-hl-date {
  margin-top: auto;
  padding-top: 4px;
  font-size: 10.5px;
  color: #b0b7c3;
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

/* ===== 封面上的关系标识（特别关心 / 亲密关系） ===== */
.uh-mark-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 5px;
}
.uh-care-chip {
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid rgba(253, 230, 138, 0.6);
  background: rgba(245, 158, 11, 0.24);
  color: #fde68a;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
.uh-intimacy-chip {
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.16);
  font-size: 10.5px;
  font-weight: 700;
  backdrop-filter: blur(4px);
}

/* 设置页行的补充说明：一句灰字，贴着白组下沿 */
.uh-cell-hint {
  margin: 0;
  padding: 10px 16px 12px;
  font-size: 11.5px;
  line-height: 1.6;
  color: #98a2b3;
}

/* ===== 三级：亲密关系（四宫格，QQ 关系标识那一套） ===== */
.uh-intimacy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 14px 12px 6px;
}
.uh-intimacy-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 86px;
  border: 1.5px solid #eef0f3;
  border-radius: 12px;
  background: var(--tui-surface, #fff);
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.uh-intimacy-card.on {
  border-color: var(--tone, #2563eb);
  background: color-mix(in srgb, var(--tone, #2563eb) 8%, #fff);
}
.uh-intimacy-icon { font-size: 22px; line-height: 1; }
.uh-intimacy-name { font-size: 13px; font-weight: 600; color: #344054; }
.uh-intimacy-on {
  position: absolute;
  top: 6px;
  right: 8px;
  font-size: 10px;
  color: var(--tone, #2563eb);
}
.uh-intimacy-hint { padding: 4px 16px 14px; }

/* ===== 三级：推荐给好友 ===== */
.uh-nested { z-index: 10; }
.uh-rec-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0 16px;
  scrollbar-width: none;
}
.uh-rec-body::-webkit-scrollbar { display: none; width: 0; }
.uh-rec-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 12px 12px;
  padding: 12px;
  border: 1px solid #eef0f3;
  border-radius: 12px;
  background: var(--tui-surface, #fff);
}
.uh-rec-card-main { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.uh-rec-name { font-size: 14px; font-weight: 700; color: #101828; }
.uh-rec-sub {
  font-size: 11.5px;
  color: #98a2b3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-rec-search { padding: 0 12px 10px; }
.uh-rec-search :deep(.el-input__wrapper) {
  border-radius: 10px;
  background: #f5f6f8;
  box-shadow: none;
}
.uh-rec-state {
  padding: 22px 16px;
  font-size: 12.5px;
  color: #98a2b3;
  text-align: center;
}
.uh-rec-row { gap: 10px; }
.uh-rec-row:disabled { opacity: 0.6; }
.uh-rec-row-name {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 13.5px;
  color: var(--tui-text, #344054);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uh-rec-row-name i { font-style: normal; font-size: 11px; color: #98a2b3; }
.uh-rec-send {
  flex-shrink: 0;
  padding: 3px 11px;
  border-radius: 999px;
  background: rgba(0, 153, 255, 0.1);
  color: #0099ff;
  font-size: 11.5px;
  font-weight: 600;
}

/* ===== 动效 =====
   主页本体的进出场交给全局 .subpage（styles/animations.css），这里只保留内层子页
   （设置页 / 勋章墙）自己的滑入规则。 */
.uh-sub-enter-active,
.uh-sub-leave-active { transition: transform 0.28s cubic-bezier(0.33, 1, 0.68, 1); }
.uh-sub-enter-from,
.uh-sub-leave-to { transform: translateX(100%); }
</style>