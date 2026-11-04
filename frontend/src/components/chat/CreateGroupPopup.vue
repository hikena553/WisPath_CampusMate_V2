<template>
  <!-- 发起群聊：移动端是整屏子页、桌面端是弹窗（ResponsivePopup 两端各自适配）。
       消息页的「＋」与「添加朋友」页共用这一份 —— 选人规则只有一处，
       不会出现「从消息页建的群能直接进群、从别处建的群却退回列表」这种两套行为。 -->
  <ResponsivePopup
    :model-value="modelValue"
    title="发起群聊"
    width="440px"
    transition="subpage"
    class="cg-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="cg-form">
      <!-- 群名：留空也能建（按成员昵称自动起名），提示写在输入框下方而不是塞进
           placeholder —— 既不会被字数计数挤断，也不用猜「留空到底会叫什么」 -->
      <div class="cg-name">
        <el-input
          v-model="groupName"
          placeholder="群名称（可选）"
          maxlength="20"
          show-word-limit
          size="large"
          @keyup.enter="submit"
        />
        <p v-if="!groupName.trim() && picked.length" class="cg-name-tip">
          留空则命名为「{{ autoName }}」
        </p>
      </div>

      <div class="cg-head">
        <span>选择成员</span>
        <div class="cg-head-right">
          <span v-if="picked.length" class="cg-count">{{ picked.length }} 人已选</span>
          <span v-else class="cg-count is-hint">至少选 1 人</span>
          <button
            v-if="filtered.length > 1"
            type="button"
            class="cg-text-btn"
            @click="toggleAll"
          >
            {{ allFilteredPicked ? '取消全选' : '全选' }}
          </button>
        </div>
      </div>

      <!-- 已选成员：头像 + 昵称 + 单个移除。比「已选 3 人」更能确认「选的是不是那个张三」；
           横向一条，不占列表高度，选得多也不会把名单挤没 -->
      <div v-if="picked.length" class="cg-picked-bar" role="list" aria-label="已选成员">
        <span v-for="m in picked" :key="m.id" class="cg-chip" role="listitem">
          <el-avatar :size="20" :src="m.avatar || undefined" class="cg-chip-avatar">
            {{ m.name.slice(0, 1) }}
          </el-avatar>
          <span class="cg-chip-name">{{ m.name }}</span>
          <button
            type="button"
            class="cg-chip-x"
            :aria-label="`移除 ${m.name}`"
            @click="removePicked(m.id)"
          >
            <el-icon :size="11"><Close /></el-icon>
          </button>
        </span>
      </div>

      <!-- 搜索放在名单上方（不在滚动区里），名单再长也不用滚回去找人 -->
      <label v-if="friends.length || kw" class="cg-search">
        <el-icon :size="15" class="cg-search-icon"><Search /></el-icon>
        <input
          v-model="keyword"
          class="cg-search-input"
          type="text"
          enterkeyhint="search"
          placeholder="搜索姓名 / 班级 / 学院"
          aria-label="搜索成员"
        />
        <button v-if="keyword" type="button" class="cg-search-clear" aria-label="清空搜索" @click="keyword = ''">
          <el-icon :size="14"><CircleCloseFilled /></el-icon>
        </button>
      </label>

      <!-- Ⅰ 首次加载：骨架屏，不要用一个转圈的图标把整块留白 -->
      <el-skeleton v-if="loading && !friends.length" :rows="5" animated class="cg-skeleton" />

      <!-- Ⅱ 请求失败 ≠ 没有好友。以前网络一抖就显示「还没有可拉的同学」，
             把接口的锅甩给用户，这里必须分开说 -->
      <div v-else-if="failed && !friends.length" class="cg-empty">
        <el-icon :size="26"><Warning /></el-icon>
        <p>名单没能加载出来</p>
        <span>检查一下网络，重试即可，不用重新选人</span>
        <button type="button" class="cg-retry" :disabled="loading" @click="loadFriends">
          {{ loading ? '重试中…' : '重新加载' }}
        </button>
      </div>

      <!-- Ⅲ 真的没关注过人 -->
      <div v-else-if="!friends.length" class="cg-empty">
        <el-icon :size="26"><User /></el-icon>
        <p>还没有可拉的同学</p>
        <span>先在「添加朋友」里关注同学，再回来建群</span>
      </div>

      <!-- Ⅳ 搜不到 -->
      <div v-else-if="!filtered.length" class="cg-empty">
        <el-icon :size="26"><Search /></el-icon>
        <p>没有匹配「{{ kw }}」的同学</p>
        <span>换个姓名、班级或学院的关键词试试</span>
        <button type="button" class="cg-retry" @click="keyword = ''">清空搜索</button>
      </div>

      <!-- Ⅴ 名单：按姓名首字母分节，节头吸顶；同姓名的人靠班级/学院一行区分 -->
      <div v-else ref="listRef" class="cg-list" :class="{ 'is-more': hasMore }" @scroll="measureList">
        <section v-for="sec in sections" :key="sec.letter" class="cg-sec">
          <h3 class="cg-sec-head">{{ sec.letter }}</h3>
          <button
            v-for="c in sec.items"
            :key="c.id"
            type="button"
            class="cg-row"
            :class="{ picked: isPicked(c.id) }"
            :aria-pressed="isPicked(c.id)"
            @click="togglePicked(c)"
          >
            <el-avatar :size="38" :src="c.avatar || undefined" class="cg-avatar">
              {{ c.name.slice(0, 1) }}
            </el-avatar>
            <span class="cg-row-main">
              <span class="cg-row-name">{{ c.name }}</span>
              <span v-if="subtitleOf(c)" class="cg-row-sub">{{ subtitleOf(c) }}</span>
            </span>
            <i class="cg-check" aria-hidden="true"><el-icon :size="13"><Check /></el-icon></i>
          </button>
        </section>
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button class="cg-submit" type="primary" :loading="creating" :disabled="!canCreate" @click="submit">
        {{ picked.length ? `创建群聊（${picked.length + 1} 人）` : '创建群聊' }}
      </el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Check,
  CircleCloseFilled,
  Close,
  Search,
  User,
  Warning,
} from '@element-plus/icons-vue'
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { createGroup } from '@/api/groups'
import { getContacts, type ContactUser } from '@/api/social'
import { indexOrder, initialOf } from '@/utils/pinyinInitial'

const props = defineProps<{
  /** 显隐（v-model） */
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  /** 建群成功：调用方决定是直接开会话、还是回列表刷新 */
  (e: 'created', group: { id: number; name: string }): void
}>()

const groupName = ref('')
const keyword = ref('')
/** 可拉名单 = 我关注的人（本系统里好友即我关注的）。
 *  名单缓存在组件里：连开两次不必重复请求，也不会污染通讯录视图自己的那份。 */
const friends = ref<ContactUser[]>([])
const picked = ref<ContactUser[]>([])
const loading = ref(false)
const failed = ref(false)
const creating = ref(false)
/** 上次拉名单的时间：缓存超过 1 分钟就静默刷新，刚关注的人不至于看不到 */
const loadedAt = ref(0)

const CACHE_TTL = 60_000

const kw = computed(() => keyword.value.trim())

/** 过滤：姓名 / 学号 / 班级 / 学院都参与匹配；单个字母还能按拼音首字母筛（打 z 出「张」） */
const filtered = computed(() => {
  const k = kw.value.toLowerCase()
  if (!k) return friends.value
  const byLetter = k.length === 1 && /[a-z]/.test(k) ? k.toUpperCase() : ''
  return friends.value.filter((c) => {
    if (byLetter && initialOf(c.name) === byLetter) return true
    return (
      c.name.toLowerCase().includes(k) ||
      (c.username || '').toLowerCase().includes(k) ||
      (c.class_name || '').toLowerCase().includes(k) ||
      (c.college || '').toLowerCase().includes(k)
    )
  })
})

/** 按姓名首字母分节（中文用 ICU 拼音序推首字母，与通讯录同一套规则） */
const sections = computed(() => {
  const buckets = new Map<string, ContactUser[]>()
  for (const c of filtered.value) {
    const key = initialOf(c.name)
    const bucket = buckets.get(key)
    if (bucket) bucket.push(c)
    else buckets.set(key, [c])
  }
  return [...buckets.entries()]
    .sort((a, b) => indexOrder(a[0]) - indexOrder(b[0]))
    .map(([letter, items]) => ({
      letter,
      items: [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN')),
    }))
})

const allFilteredPicked = computed(
  () => filtered.value.length > 0 && filtered.value.every((c) => isPicked(c.id)),
)

/** 留空时的群名：取已选成员的昵称。微信群也是这么起的，比逼用户想名字顺手 */
const autoName = computed(() => {
  const joined = picked.value.map((m) => m.name).join('、')
  return joined.length > 20 ? `${joined.slice(0, 19)}…` : joined
})

const canCreate = computed(() => picked.value.length > 0 && !creating.value)

/** 名单底部还有没有没露出来的人：有就给末尾那道硬切口加一层渐隐，
 *  不然半行姓名被截断看起来像排版崩了，而不是「还能往下滚」 */
const listRef = ref<HTMLElement | null>(null)
const hasMore = ref(false)

function measureList() {
  const el = listRef.value
  hasMore.value = !!el && el.scrollHeight - el.scrollTop - el.clientHeight > 4
}

function isPicked(id: number) {
  return picked.value.some((m) => m.id === id)
}

function togglePicked(c: ContactUser) {
  if (isPicked(c.id)) picked.value = picked.value.filter((m) => m.id !== c.id)
  else picked.value.push(c)
}

function removePicked(id: number) {
  picked.value = picked.value.filter((m) => m.id !== id)
}

/** 全选只作用于「当前筛选结果」：先搜「软件 2101」再全选，就是整班拉群 */
function toggleAll() {
  if (allFilteredPicked.value) {
    const ids = new Set(filtered.value.map((c) => c.id))
    picked.value = picked.value.filter((m) => !ids.has(m.id))
    return
  }
  const have = new Set(picked.value.map((m) => m.id))
  picked.value = [...picked.value, ...filtered.value.filter((c) => !have.has(c.id))]
}

/** 同名的人不少，班级 / 学院一行是唯一能区分的信息 */
function subtitleOf(c: ContactUser) {
  return c.class_name || c.college || ''
}

async function loadFriends() {
  if (loading.value) return
  loading.value = true
  failed.value = false
  try {
    friends.value = await getContacts({ tab: 'following' })
    loadedAt.value = Date.now()
  } catch {
    // 有旧名单就继续用，只有「一片空白」才需要把错误摆到台面上
    if (!friends.value.length) failed.value = true
  } finally {
    loading.value = false
  }
}

/** 每次打开都清空上次的草稿（群名 + 搜索词 + 选中人），名单按缓存策略复用 */
async function prepare() {
  groupName.value = ''
  keyword.value = ''
  picked.value = []
  if (!friends.value.length || Date.now() - loadedAt.value > CACHE_TTL) await loadFriends()
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) void prepare().then(() => nextTick(measureList))
  },
)

/** 搜索 / 名单变化后重新判断「还能不能往下滚」 */
watch(filtered, () => nextTick(measureList), { flush: 'post' })

async function submit() {
  if (!canCreate.value) return
  // 群名留空时用成员昵称兜底，绝不把空串丢给后端
  const name = groupName.value.trim() || autoName.value
  if (!name) return
  creating.value = true
  try {
    const res = await createGroup({ name, member_ids: picked.value.map((m) => m.id) })
    ElMessage.success('群聊已创建')
    emit('update:modelValue', false)
    emit('created', res)
  } catch {
    ElMessage.error('创建失败，请稍后再试')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.cg-form {
  --cg-accent: #3b82f6;
  --cg-text: #1d2129;
  --cg-sub: #6b7280;
  --cg-muted: #9aa0a6;
  --cg-line: #eef0f4;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ===== 群名 ===== */
.cg-name { display: flex; flex-direction: column; gap: 6px; }
.cg-name-tip {
  margin: 0 2px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--cg-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 分组标题行 ===== */
.cg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 2px;
  font-size: 13px;
  color: var(--cg-sub);
}
.cg-head-right { display: flex; align-items: center; gap: 10px; }
.cg-count { color: var(--cg-accent); font-variant-numeric: tabular-nums; }
.cg-count.is-hint { color: var(--cg-muted); }
.cg-text-btn {
  padding: 2px 4px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  font-family: inherit;
  font-size: 12.5px;
  color: var(--cg-accent);
  cursor: pointer;
}
.cg-text-btn:active { background: rgba(59, 130, 246, 0.1); }

/* ===== 已选成员 ===== */
.cg-picked-bar {
  display: flex;
  gap: 8px;
  margin-top: -2px;
  padding-bottom: 2px;
  overflow-x: auto;
  scrollbar-width: none;
}
.cg-picked-bar::-webkit-scrollbar { display: none; }
.cg-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  max-width: 168px;
  padding: 3px 4px 3px 3px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.09);
}
.cg-chip-avatar {
  flex-shrink: 0;
  background: #fff;
  color: var(--cg-accent);
  font-size: 11px;
  font-weight: 600;
}
.cg-chip-name {
  min-width: 0;
  font-size: 12.5px;
  color: #2f5fd0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cg-chip-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #7f9cd8;
  cursor: pointer;
}
.cg-chip-x:active { background: rgba(59, 130, 246, 0.18); color: #2f5fd0; }

/* ===== 搜索 ===== */
.cg-search {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  border-radius: 10px;
  background: #f3f4f6;
  color: var(--cg-muted);
  transition: background 0.16s ease, box-shadow 0.16s ease;
}
.cg-search:focus-within {
  background: #fff;
  box-shadow: inset 0 0 0 1.5px rgba(59, 130, 246, 0.45);
}
.cg-search-icon { flex-shrink: 0; }
.cg-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: var(--cg-text);
}
.cg-search-input::placeholder { color: var(--cg-muted); }
.cg-search-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #c3c8cf;
  cursor: pointer;
}

/* ===== 名单 ===== */
.cg-list {
  display: flex;
  flex-direction: column;
  max-height: min(52vh, 440px);
  margin: 0 -6px;
  padding: 0 6px;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
/* 名单底部还有没露出来的人时，末尾 22px 渐隐 —— 半行姓名被硬切看着像版式坏了，
   渐隐一眼就能传达「还能往下滚」 */
.cg-list.is-more {
  -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 22px), transparent);
  mask-image: linear-gradient(to bottom, #000 calc(100% - 22px), transparent);
}
.cg-sec-head {
  position: sticky;
  top: 0;
  z-index: 1;
  margin: 0;
  padding: 6px 8px 4px;
  background: #fff;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--cg-muted);
}
.cg-row {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 7px 8px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.14s ease;
}
.cg-row:hover { background: #f6f7f9; }
.cg-row:active { background: #eef0f3; }
.cg-row.picked { background: rgba(59, 130, 246, 0.07); }
/* el-avatar 默认是浅灰底 + 白字，选人列表里一排头像糊成一片；
   这里压深一档底色、字号收小，让姓名首字看得清 */
.cg-avatar {
  flex-shrink: 0;
  background: #e4e8ee;
  color: #5b6472;
  font-size: 14px;
  font-weight: 500;
}
.cg-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cg-row-name {
  font-size: 14.5px;
  color: var(--cg-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cg-row-sub {
  font-size: 11.5px;
  color: var(--cg-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 勾选框常显成一个空心圆，选中填成主色 —— 比只在选中时才出现的对勾更早给出「可点」信号 */
.cg-check {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1.5px solid #dcdfe3;
  border-radius: 50%;
  color: transparent;
  background: #fff;
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease, transform 0.16s ease;
}
.cg-row.picked .cg-check {
  background: var(--cg-accent);
  border-color: var(--cg-accent);
  color: #fff;
  transform: scale(1.04);
}

/* 主按钮在 .main-area 下被灌了一层蓝色渐变，而 Element 的禁用态只改
   background-color，渐变照旧 —— 「没选人」和「可以建」看着一模一样。
   这里把禁用态压平成一档淡蓝，先给出「还差点什么」的信号。
   !important 是被迫的：那条渐变选择器挂了三个 :not()，权重压不过它。 */
.cg-submit.is-disabled,
.cg-submit.is-disabled:hover,
.cg-submit.is-disabled:focus {
  background: #a9c7fb !important;
  border-color: transparent !important;
  box-shadow: none !important;
  color: #fff !important;
}

/* ===== 空态 / 失败态 ===== */
.cg-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 30px 12px;
  color: var(--cg-muted);
  text-align: center;
}
.cg-empty p { margin: 0; font-size: 14px; color: var(--cg-sub); }
.cg-empty span { font-size: 12.5px; line-height: 1.5; }
.cg-retry {
  margin-top: 6px;
  padding: 5px 14px;
  border: 1px solid #e3e6eb;
  border-radius: 999px;
  background: #fff;
  font-family: inherit;
  font-size: 12.5px;
  color: #4b5563;
  cursor: pointer;
}
.cg-retry:active { background: #f4f5f7; }
.cg-retry:disabled { color: var(--cg-muted); cursor: default; }
.cg-skeleton { padding: 4px 8px; }

/* 桌面端弹窗比手机高得多，名单可以再长一点；
   上限跟着弹窗的 84dvh 走（下面 .cg-dialog），保证「输入框 + 已选 + 搜索 + 名单 + 按钮」
   刚好装在框内，只留名单这一处滚动，不会出现「外框一层、名单再一层」的两道滚动条 */
@media (min-width: 768px) {
  .cg-list { max-height: min(44dvh, 440px); }
}
/* 移动端整屏子页：让名单吃掉剩余的竖向空间，页面本身不滚动，
   「取消 / 创建」就不会被推到屏外还得再滚一段 */
@media (max-width: 767px) {
  .cg-list { max-height: max(200px, calc(100vh - 340px)); }
}
</style>

<!-- 非 scoped：class 透传到 el-dialog 根节点，作用域选择器命不中；
     同时要盖掉全局 .el-dialog 的 66dvh 高度上限（那是给一行输入的确认框定的，
     选人页要纵向空间，放宽到 84dvh 才不会把名单截在半行上）。 -->
<style>
@media (min-width: 768px) {
  .el-dialog.cg-dialog {
    max-height: min(84dvh, 760px);
  }
}
</style>
