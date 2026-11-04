<template>
  <!-- 发起群聊：移动端是整屏子页、桌面端是弹窗（ResponsivePopup 两端各自适配）。
       消息页的「＋」与「添加朋友」页共用这一份 —— 选人规则只有一处，
       不会出现「从消息页建的群能直接进群、从别处建的群却退回列表」这种两套行为。 -->
  <ResponsivePopup
    :model-value="modelValue"
    title="发起群聊"
    width="420px"
    transition="subpage"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="cg-form">
      <el-input
        v-model="groupName"
        placeholder="群名称，例如：期末复习搭子"
        maxlength="20"
        show-word-limit
        size="large"
      />
      <div class="cg-head">
        <span>选择成员</span>
        <span v-if="picked.length" class="cg-picked">已选 {{ picked.length }} 人</span>
      </div>
      <div v-if="loading" class="cg-empty">
        <el-icon :size="26"><User /></el-icon>
        <p>正在加载名单…</p>
      </div>
      <div v-else-if="!friends.length" class="cg-empty">
        <el-icon :size="26"><User /></el-icon>
        <p>还没有可拉的同学</p>
        <span>先在「添加朋友」里关注同学，再回来建群</span>
      </div>
      <div v-else class="cg-list">
        <button
          v-for="c in friends"
          :key="c.id"
          type="button"
          class="cg-row"
          :class="{ picked: isPicked(c.id) }"
          @click="togglePicked(c)"
        >
          <el-avatar :size="34" :src="c.avatar || undefined">{{ c.name.slice(0, 1) }}</el-avatar>
          <span class="cg-row-name">{{ c.name }}</span>
          <i class="cg-check" aria-hidden="true"><el-icon :size="13"><Check /></el-icon></i>
        </button>
      </div>
    </div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="creating" :disabled="!groupName.trim()" @click="submit">
        创建
      </el-button>
    </template>
  </ResponsivePopup>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, User } from '@element-plus/icons-vue'
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import { createGroup } from '@/api/groups'
import { getContacts, type ContactUser } from '@/api/social'

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
/** 可拉名单 = 我关注的人（本系统里好友即我关注的）。
 *  名单缓存在组件里：连开两次不必重复请求，也不会污染通讯录视图自己的那份。 */
const friends = ref<ContactUser[]>([])
const picked = ref<ContactUser[]>([])
const loading = ref(false)
const creating = ref(false)

function isPicked(id: number) {
  return picked.value.some((m) => m.id === id)
}

function togglePicked(c: ContactUser) {
  if (isPicked(c.id)) picked.value = picked.value.filter((m) => m.id !== c.id)
  else picked.value.push(c)
}

/** 每次打开都清空上次的草稿（群名 + 选中人），名单只拉一次 */
async function prepare() {
  groupName.value = ''
  picked.value = []
  if (friends.value.length || loading.value) return
  loading.value = true
  try {
    friends.value = await getContacts({ tab: 'following' })
  } catch {
    friends.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) void prepare()
  },
)

async function submit() {
  const name = groupName.value.trim()
  if (!name || creating.value) return
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
.cg-form { display: flex; flex-direction: column; gap: 14px; }
.cg-head { display: flex; align-items: baseline; justify-content: space-between; font-size: 13px; color: #6b7280; }
.cg-picked { color: #3b82f6; font-variant-numeric: tabular-nums; }
.cg-list { display: flex; flex-direction: column; gap: 2px; max-height: min(52vh, 460px); overflow-y: auto; }
.cg-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.cg-row:active { background: #f4f5f7; }
.cg-row-name { flex: 1; min-width: 0; font-size: 14.5px; color: #1d2129; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* el-avatar 默认是浅灰底 + 白字，选人列表里一排头像糊成一片；
   这里压深一档底色、字号收小，让姓名首字看得清 */
.cg-row .el-avatar { background: #e4e8ee; color: #5b6472; font-size: 13.5px; font-weight: 500; }
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
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}
.cg-row.picked .cg-check { background: #3b82f6; border-color: #3b82f6; color: #fff; }
.cg-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 34px 0; color: #9aa0a6; }
.cg-empty p { margin: 0; font-size: 14px; color: #6b7280; }
.cg-empty span { font-size: 12.5px; }
</style>
