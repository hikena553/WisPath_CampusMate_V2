<template>
  <div class="cd">
    <!-- 三个数字 = 三个列表页签：关注 / 粉丝 / 好友（互关） -->
    <div class="cd-stats">
      <button
        v-for="s in statItems"
        :key="s.key"
        type="button"
        class="cd-stat"
        :class="{ active: tab === s.key }"
        @click="switchTab(s.key)"
      >
        <b>{{ s.value }}</b>
        <span>{{ s.label }}</span>
      </button>
    </div>

    <div class="cd-search">
      <DtIcon name="search" :size="16" class="cd-search-icon" />
      <input
        v-model="keyword"
        type="search"
        class="cd-search-input"
        placeholder="搜索同学姓名 / 学号"
        @input="onSearchInput"
      />
      <button v-if="keyword" type="button" class="cd-search-clear" aria-label="清空" @click="clearSearch">
        <DtIcon name="close" :size="12" />
      </button>
    </div>

    <div class="cd-scroll">
      <!-- 搜索结果 -->
      <template v-if="searchMode">
        <div v-if="searching" class="cd-tip">搜索中…</div>
        <template v-else-if="searchResults.length">
          <div class="cd-section-title">搜索结果</div>
          <div class="cd-list">
            <div v-for="u in searchResults" :key="u.id" class="cd-row">
              <el-avatar
                :size="44"
                :src="u.avatar || undefined"
                class="cd-avatar"
                title="查看个人主页"
                @click="emit('open-profile', u.id)"
              >{{ u.name?.[0] }}</el-avatar>
              <div class="cd-main" @click="emit('open-profile', u.id)">
                <div class="cd-name-line">
                  <span class="cd-name">{{ u.name }}</span>
                  <span v-if="u.is_friend" class="cd-tag is-friend">互关</span>
                  <span v-else-if="u.is_follower" class="cd-tag is-fans">关注了你</span>
                </div>
                <div class="cd-meta">{{ metaOf(u) }}</div>
              </div>
              <div class="cd-actions">
                <button
                  type="button"
                  class="cd-btn"
                  :class="u.is_following ? 'is-ghost' : 'is-primary'"
                  @click="toggleFollow(u)"
                >{{ u.is_following ? '已关注' : (u.is_follower ? '回关' : '关注') }}</button>
                <button v-if="u.is_friend" type="button" class="cd-btn is-ghost" @click="emit('open-chat', u)">私信</button>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="cd-empty">
          <DtIcon name="search" :size="42" style="color: var(--dt-text-quiet)" />
          <span>没有找到「{{ keyword.trim() }}」</span>
          <span class="cd-empty-hint">试试姓名或学号，关注后可互相互关成为好友</span>
        </div>
      </template>

      <!-- 关注 / 粉丝 / 好友列表 -->
      <template v-else>
        <div class="cd-hint">{{ tabHint }}</div>
        <div v-if="loading" class="cd-tip">加载中…</div>
        <template v-else-if="currentList.length">
          <div class="cd-list">
            <div v-for="u in currentList" :key="u.id" class="cd-row">
              <el-avatar
                :size="44"
                :src="u.avatar || undefined"
                class="cd-avatar"
                title="查看个人主页"
                @click="emit('open-profile', u.id)"
              >{{ u.name?.[0] }}</el-avatar>
              <div class="cd-main" @click="emit('open-profile', u.id)">
                <div class="cd-name-line">
                  <span class="cd-name">{{ u.name }}</span>
                  <span v-if="u.is_friend" class="cd-tag is-friend">互关</span>
                </div>
                <div class="cd-meta">{{ metaOf(u) }}</div>
              </div>
              <div class="cd-actions">
                <button
                  v-if="tab === 'followers' && !u.is_following"
                  type="button"
                  class="cd-btn is-primary"
                  @click="toggleFollow(u)"
                >回关</button>
                <button
                  v-else
                  type="button"
                  class="cd-btn"
                  :class="u.is_following ? 'is-ghost' : 'is-primary'"
                  @click="toggleFollow(u)"
                >{{ u.is_following ? '已关注' : '关注' }}</button>
                <button v-if="u.is_friend" type="button" class="cd-btn is-ghost" @click="emit('open-chat', u)">私信</button>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="cd-empty">
          <DtIcon :name="tab === 'friends' ? 'contacts' : 'user'" :size="42" style="color: var(--dt-text-quiet)" />
          <span>{{ emptyText }}</span>
          <span class="cd-empty-hint">{{ tab === 'followers' ? '别的同学关注你后会出现在这里' : '互相关注即好友，可直接发起聊天与群聊' }}</span>
        </div>

        <!-- 关注 / 好友为空时给推荐，避免「关注页一片空白、无从下手」 -->
        <template v-if="suggestions.length && tab !== 'followers'">
          <div class="cd-section-title">可能认识的人</div>
          <div class="cd-list">
            <div v-for="u in suggestions" :key="'s' + u.id" class="cd-row">
              <el-avatar
                :size="44"
                :src="u.avatar || undefined"
                class="cd-avatar"
                title="查看个人主页"
                @click="emit('open-profile', u.id)"
              >{{ u.name?.[0] }}</el-avatar>
              <div class="cd-main" @click="emit('open-profile', u.id)">
                <div class="cd-name-line"><span class="cd-name">{{ u.name }}</span></div>
                <div class="cd-meta">{{ metaOf(u) }}</div>
              </div>
              <div class="cd-actions">
                <button type="button" class="cd-btn is-primary" @click="toggleFollow(u)">关注</button>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 通讯录：关注 / 粉丝 / 好友（互关）
 *
 * 好友不是独立实体——互相关注即好友。三个数字就是三个列表的入口，
 * 行内操作只做「关注 / 回关 / 已关注」，互关后才出现「私信」按钮，
 * 与个人主页、论坛共用同一套关注关系（/api/social）。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DtIcon from '@/components/common/DtIcon.vue'
import {
  getFollowers, getFollowing, getFriends, getSocialStats, getFollowSuggestions,
  followUser, unfollowUser, searchSocialUsers,
  type FollowState, type SocialUser,
} from '@/api/social'

type TabKey = 'friends' | 'following' | 'followers'

const emit = defineEmits<{
  (e: 'open-chat', user: SocialUser): void
  (e: 'open-profile', userId: number): void
}>()

const tab = ref<TabKey>('friends')
const stats = ref<FollowState | null>(null)
const friends = ref<SocialUser[]>([])
const following = ref<SocialUser[]>([])
const followers = ref<SocialUser[]>([])
const suggestions = ref<SocialUser[]>([])
const loading = ref(false)

const keyword = ref('')
const searchMode = computed(() => !!keyword.value.trim())
const searching = ref(false)
const searchResults = ref<SocialUser[]>([])

const statItems = computed(() => [
  { key: 'friends' as const, label: '好友', value: stats.value?.friends ?? friends.value.length },
  { key: 'following' as const, label: '关注', value: stats.value?.following ?? following.value.length },
  { key: 'followers' as const, label: '粉丝', value: stats.value?.followers ?? followers.value.length },
])

const currentList = computed(() =>
  tab.value === 'friends' ? friends.value : tab.value === 'following' ? following.value : followers.value,
)

const tabHint = computed(() =>
  tab.value === 'friends'
    ? '互相关注即好友，可直接发起聊天'
    : tab.value === 'following'
      ? '你关注的人；对方回关后成为好友'
      : '关注你的人；回关后成为好友',
)

const emptyText = computed(() =>
  tab.value === 'friends' ? '还没有互关好友' : tab.value === 'following' ? '还没有关注任何人' : '还没有粉丝',
)

function metaOf(u: SocialUser) {
  const role = u.role === 'teacher' ? '教师' : u.role === 'admin' ? '管理员' : '学生'
  const extra = u.role === 'student' ? (u.class_name || u.college || '') : (u.title || u.college || '')
  return extra ? `${role} · ${extra}` : role
}

function switchTab(key: TabKey) {
  tab.value = key
  keyword.value = ''
  searchResults.value = []
}

async function loadAll() {
  loading.value = true
  try {
    const [f, ing, ers, st] = await Promise.all([
      getFriends(), getFollowing(), getFollowers(), getSocialStats(),
    ])
    friends.value = f
    following.value = ing
    followers.value = ers
    stats.value = st
  } catch {
    /* 网络异常保留上一次数据 */
  } finally {
    loading.value = false
  }
}

async function loadSuggestions() {
  try {
    suggestions.value = await getFollowSuggestions(6)
  } catch {
    suggestions.value = []
  }
}

/** 关注 / 取消关注：成功后同步三张列表里该用户的状态，并刷新计数 */
async function toggleFollow(u: SocialUser) {
  const willFollow = !u.is_following
  if (!willFollow) {
    // 取消关注会解除互关，误触代价不小，先确认一次
    try {
      await ElMessageBox.confirm(`取消关注「${u.name}」？互关关系会一并解除。`, '取消关注', {
        confirmButtonText: '取消关注',
        cancelButtonText: '再想想',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  try {
    const state = willFollow ? await followUser(u.id) : await unfollowUser(u.id)
    patchUser(u.id, { is_following: state.is_following, is_follower: state.is_follower, is_friend: state.is_friend })
    stats.value = await getSocialStats()
    // 关注后该用户应从「推荐」里消失；取消关注后可重新推荐
    if (willFollow) suggestions.value = suggestions.value.filter((s) => s.id !== u.id)
    else void loadSuggestions()
    ElMessage.success(willFollow ? (state.is_friend ? '已互关，成为好友' : '已关注') : '已取消关注')
  } catch {
    ElMessage.error('操作失败，请稍后重试')
  }
}

function patchUser(userId: number, patch: Partial<SocialUser>) {
  const apply = (list: SocialUser[]) => list.map((x) => (x.id === userId ? { ...x, ...patch } : x))
  friends.value = apply(friends.value)
  following.value = apply(following.value)
  followers.value = apply(followers.value)
  searchResults.value = apply(searchResults.value)
  suggestions.value = apply(suggestions.value)
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  const kw = keyword.value.trim()
  if (!kw) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    searching.value = true
    try {
      searchResults.value = await searchSocialUsers(kw)
    } catch {
      searchResults.value = []
    } finally {
      searching.value = false
    }
  }, 280)
}

function clearSearch() {
  keyword.value = ''
  searchResults.value = []
}

/** 从消息页切回来时重新拉一次：对方可能在别处回关了我 */
onMounted(() => {
  void loadAll()
  void loadSuggestions()
})

defineExpose({ reload: loadAll })
</script>

<style scoped>
.cd {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  /* 与页头、会话流同宽（桌面端 880 居中），否则列表会横贯整个视口 */
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
}

/* ===== 三个数字：关注 / 粉丝 / 好友 ===== */
.cd-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 4px 16px 10px;
}
.cd-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 4px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: var(--dt-surface, #fff);
  color: var(--dt-text-secondary);
  cursor: pointer;
  transition: background .18s ease, color .18s ease, border-color .18s ease;
}
.cd-stat b { font-size: 18px; font-weight: 650; color: var(--dt-text); line-height: 1.1; }
.cd-stat span { font-size: 11px; letter-spacing: .02em; }
.cd-stat.active {
  background: var(--dt-primary-soft, #e8f3ff);
  border-color: rgba(0, 137, 255, .22);
}
.cd-stat.active b, .cd-stat.active span { color: var(--dt-primary-strong, #0070d9); }

/* ===== 搜索 ===== */
.cd-search {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 16px 10px;
  padding: 0 12px;
  height: 38px;
  border-radius: 10px;
  background: var(--dt-surface, #fff);
  border: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.cd-search-icon { color: var(--dt-text-quiet); flex-shrink: 0; }
.cd-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 13px;
  color: var(--dt-text);
}
.cd-search-input::placeholder { color: var(--dt-text-quiet); }
.cd-search-clear {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  border: 0; background: var(--dt-surface-press, #eaebed);
  color: var(--dt-text-tertiary); cursor: pointer;
}

/* ===== 列表 ===== */
.cd-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 16px 24px;
  scrollbar-width: none;
}
.cd-scroll::-webkit-scrollbar { display: none; }

.cd-hint {
  padding: 2px 2px 8px;
  font-size: 12px;
  color: var(--dt-text-tertiary);
}
.cd-section-title {
  padding: 14px 2px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--dt-text-tertiary);
  letter-spacing: .04em;
}
.cd-list {
  border-radius: 12px;
  background: var(--dt-surface, #fff);
  overflow: hidden;
}
.cd-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--dt-divider, rgba(0, 0, 0, .06));
}
.cd-row:last-child { border-bottom: 0; }
.cd-avatar { flex-shrink: 0; cursor: pointer; }
.cd-main {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}
.cd-name-line { display: flex; align-items: center; gap: 6px; min-width: 0; }
.cd-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--dt-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cd-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1.5;
}
.cd-tag.is-friend { background: var(--dt-success-soft, #e8ffea); color: var(--dt-success, #00b42a); }
.cd-tag.is-fans { background: var(--dt-primary-soft, #e8f3ff); color: var(--dt-primary-strong, #0070d9); }
.cd-meta {
  margin-top: 3px;
  font-size: 12px;
  color: var(--dt-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cd-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.cd-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity .18s ease, background .18s ease;
}
.cd-btn.is-primary { background: var(--dt-primary, #0089ff); color: #fff; }
.cd-btn.is-primary:active { opacity: .82; }
.cd-btn.is-ghost {
  background: var(--dt-surface-z1, #fafbfc);
  border-color: var(--dt-divider-strong, rgba(0, 0, 0, .1));
  color: var(--dt-text-secondary);
}

.cd-tip { padding: 18px 0; text-align: center; font-size: 12px; color: var(--dt-text-tertiary); }
.cd-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 46px 12px 24px;
  font-size: 13px;
  color: var(--dt-text-tertiary);
  text-align: center;
}
.cd-empty-hint { font-size: 12px; color: var(--dt-text-quiet); }

@media (max-width: 767px) {
  .cd-stats { padding: 0 12px 8px; }
  .cd-search { margin: 0 12px 8px; }
  .cd-scroll { padding: 0 12px 16px; }
}
</style>
