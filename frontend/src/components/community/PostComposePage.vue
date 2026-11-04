<template>
  <Teleport to="body">
    <!-- 全屏发帖编辑器：从校园资讯页的悬浮按钮 / 桌面「发帖」入口打开 -->
    <Transition name="subpage" :duration="320" @after-leave="onAfterLeave">
      <div v-if="visible" class="pc-root" role="dialog" aria-modal="true" aria-label="发布帖子">
        <header class="pc-head">
          <button type="button" class="pc-icon-btn" aria-label="返回" @click="requestClose">
            <el-icon :size="20"><ArrowLeft /></el-icon>
          </button>
          <div class="pc-head-title">发布帖子</div>
          <button
            type="button"
            class="pc-publish"
            :disabled="!canPublish"
            @click="publish"
          >{{ publishing ? '发布中' : '发布' }}</button>
        </header>

        <div class="pc-scroll">
          <section class="pc-section">
            <div class="pc-label">选择分区</div>
            <div class="pc-cats">
              <button
                v-for="c in COMMUNITY_CATEGORIES"
                :key="c"
                type="button"
                class="pc-cat"
                :class="{ 'is-active': category === c }"
                @click="category = c"
              >{{ c }}</button>
            </div>
          </section>

          <section class="pc-section">
            <div class="pc-field">
              <input
                v-model="title"
                class="pc-title-input"
                type="text"
                maxlength="60"
                placeholder="标题：一句话说清主题"
              />
              <span class="pc-counter">{{ title.length }}/60</span>
            </div>

            <div class="pc-field is-textarea">
              <textarea
                v-model="content"
                class="pc-content-input"
                maxlength="2000"
                placeholder="详细描述你的问题或分享内容…"
              />
              <span class="pc-counter">{{ content.length }}/2000</span>
            </div>
          </section>

          <section class="pc-section">
            <div class="pc-label">配图（{{ images.length }}/9）</div>
            <div class="pc-imgs">
              <div v-for="(img, i) in images" :key="img + i" class="pc-thumb">
                <img :src="img" alt="" />
                <button
                  type="button"
                  class="pc-thumb-del"
                  aria-label="移除图片"
                  @click="removeImage(i)"
                >
                  <el-icon :size="12"><Close /></el-icon>
                </button>
              </div>
              <button
                v-if="images.length + uploadingCount < 9"
                type="button"
                class="pc-thumb pc-add"
                :disabled="uploadingCount > 0"
                aria-label="添加图片"
                @click="pickFile"
              >
                <el-icon :size="20"><Plus /></el-icon>
                <span>{{ uploadingCount > 0 ? '上传中…' : '添加图片' }}</span>
              </button>
            </div>
            <p class="pc-hint">支持最多 9 张图片，单张不超过 10MB</p>
          </section>
        </div>

        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          multiple
          class="pc-file"
          @change="onFiles"
        />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 发布帖子（全屏编辑器）
 *
 * 旧独立社区页的发帖只是三字段轻表单；并入校园资讯页后发帖入口常驻，
 * 这里给正文与配图留出整页空间。发布成功先 emit published（父页刷新帖子流），
 * 再播退场动画，结束后 emit closed 由父页卸载。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Close, Plus } from '@element-plus/icons-vue'
import { COMMUNITY_CATEGORIES, createPost, type CommunityPost } from '@/api/community'
import { uploadFile } from '@/api/upload'
import { actionConfirm } from '@/composables/useActionSheet'

const emit = defineEmits<{
  /** 发布成功：父页刷新帖子流 */
  (e: 'published', post: CommunityPost): void
  /** 退场动画播完：父页收到后才卸载本组件 */
  (e: 'closed'): void
}>()

const visible = ref(false)
const category = ref('分享')
const title = ref('')
const content = ref('')
const images = ref<string[]>([])
const uploadingCount = ref(0)
const publishing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const MAX_IMAGES = 9
const MAX_SIZE = 10 * 1024 * 1024

const canPublish = computed(
  () => !publishing.value && !uploadingCount.value && title.value.trim().length > 0 && content.value.trim().length > 0,
)
const dirty = computed(() => !!title.value.trim() || !!content.value.trim() || images.value.length > 0)

function pickFile() {
  fileInput.value?.click()
}

async function onFiles(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return

  const remain = MAX_IMAGES - images.value.length - uploadingCount.value
  for (const file of files.slice(0, Math.max(0, remain))) {
    if (!file.type.startsWith('image/')) {
      ElMessage.warning('只能上传图片文件')
      continue
    }
    if (file.size > MAX_SIZE) {
      ElMessage.warning('单张图片不能超过 10MB')
      continue
    }
    uploadingCount.value += 1
    try {
      const { url } = await uploadFile(file)
      if (url) images.value.push(url)
    } catch {
      ElMessage.error('图片上传失败，请重试')
    } finally {
      uploadingCount.value -= 1
    }
  }
}

function removeImage(index: number) {
  images.value.splice(index, 1)
}

async function requestClose() {
  if (publishing.value) return
  if (dirty.value) {
    const ok = await actionConfirm('退出后本次编辑不会保存，确定退出吗？', '退出编辑', {
      confirmButtonText: '退出',
    })
    if (!ok) return
  }
  close()
}

function close() {
  if (!visible.value) return
  visible.value = false
}

async function publish() {
  if (!canPublish.value) {
    if (!title.value.trim()) ElMessage.warning('请填写标题')
    else if (!content.value.trim()) ElMessage.warning('请填写内容')
    else if (uploadingCount.value) ElMessage.warning('图片还在上传，请稍候')
    return
  }
  publishing.value = true
  try {
    const post = await createPost({
      category: category.value,
      title: title.value.trim(),
      content: content.value.trim(),
      images: images.value.slice(),
    })
    ElMessage.success('发布成功')
    emit('published', post)
    close()
  } catch (e: any) {
    const status = e?.response?.status as number | undefined
    if (!status || status < 500) ElMessage.error(e?.response?.data?.detail || '发布失败，请稍后重试')
  } finally {
    publishing.value = false
  }
}

function onAfterLeave() {
  document.body.style.overflow = ''
  emit('closed')
}

function onKeydown(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && visible.value) void requestClose()
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  document.body.style.overflow = 'hidden'
  visible.value = true
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* ---------- 根容器 ---------- */
.pc-root {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  flex-direction: column;
  background: #fff;
  color: #1d2129;
  overflow: hidden;
  -webkit-tap-highlight-color: transparent;
}

/* ---------- 顶栏 ---------- */
.pc-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 52px;
  padding: 6px 10px;
  padding-top: calc(6px + env(safe-area-inset-top, 0px));
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
}
.pc-icon-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #4e5969;
  cursor: pointer;
}
.pc-icon-btn:active { background: #f2f3f5; opacity: 0.62; }
.pc-head-title {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}
.pc-publish {
  flex-shrink: 0;
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: 17px;
  background: #1d2129;
  color: #fff;
  font-size: 13.5px;
  cursor: pointer;
}
.pc-publish:disabled { background: #e5e6eb; color: #b2b2b2; cursor: not-allowed; }

/* ---------- 编辑区 ---------- */
.pc-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  background: #fff;
  padding: 6px 16px calc(24px + env(safe-area-inset-bottom, 0px));
}
.pc-section { padding: 12px 0; }
.pc-label {
  font-size: 12.5px;
  font-weight: 600;
  color: #86909c;
  margin-bottom: 8px;
}
.pc-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.pc-cat {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #e5e6eb;
  border-radius: 16px;
  background: #fff;
  color: #4e5969;
  font-size: 13px;
  cursor: pointer;
}
.pc-cat.is-active {
  border-color: #1d2129;
  background: #1d2129;
  color: #fff;
}

.pc-field { position: relative; }
.pc-field + .pc-field { margin-top: 14px; }
.pc-title-input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 0 14px;
  border: none;
  border-bottom: 1px solid #f0f0f0;
  outline: none;
  background: transparent;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.45;
  color: #1d2129;
  font-family: inherit;
}
.pc-title-input::placeholder { color: #c9cdd4; font-weight: 500; }
.pc-field.is-textarea { margin-top: 4px; }
.pc-content-input {
  width: 100%;
  box-sizing: border-box;
  min-height: 200px;
  padding: 12px 0 18px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-size: 15px;
  line-height: 1.75;
  color: #26282c;
  font-family: inherit;
}
.pc-content-input::placeholder { color: #b2b2b2; }
.pc-counter {
  position: absolute;
  right: 0;
  bottom: 4px;
  font-size: 10.5px;
  color: #b2b2b2;
  font-variant-numeric: tabular-nums;
}

/* ---------- 配图 ---------- */
.pc-imgs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.pc-thumb {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  overflow: hidden;
  background: #f7f8fa;
}
.pc-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.pc-thumb-del {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(17, 20, 24, 0.55);
  color: #fff;
  cursor: pointer;
}
.pc-add {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: 1px dashed #d9dde3;
  background: #fff;
  color: #86909c;
  font-size: 11.5px;
  cursor: pointer;
}
.pc-add:disabled { opacity: 0.6; cursor: default; }
.pc-hint {
  margin: 8px 0 0;
  font-size: 11.5px;
  color: #b2b2b2;
}
.pc-file { display: none; }

/* ---------- 桌面端：与详情一致的 760px 居中整页 ---------- */
@media (min-width: 768px) {
  .pc-root { align-items: center; background: #f2f3f5; }
  .pc-head,
  .pc-scroll { width: 100%; max-width: 760px; }
}

@media (prefers-reduced-motion: reduce) {
  .pc-root { animation: none !important; }
}
</style>
