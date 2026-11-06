<template>
  <Teleport to="body">
    <transition name="rw-fade">
      <div v-if="modelValue" class="rw-mask" @click.self="close">
        <div class="rw-panel" role="dialog" aria-modal="true" aria-label="导出简历">
          <!-- ── 顶部：返回 / 标题 / 关闭 ── -->
          <header class="rw-head">
            <button v-if="step > 1" class="rw-back" type="button" aria-label="上一步" @click="goBack">‹</button>
            <div class="rw-head-txt">
              <h2 class="rw-title">{{ stepTitle }}</h2>
              <p class="rw-sub">{{ stepSub }}</p>
            </div>
            <button class="rw-close" type="button" aria-label="关闭" @click="close">✕</button>
          </header>

          <div class="rw-progress" aria-hidden="true">
            <span v-for="s in 3" :key="s" :class="{ on: s <= step }"></span>
          </div>

          <div class="rw-body">
            <p v-if="loadingOptions" class="rw-loading">正在读取岗位库…</p>

            <!-- ══════ 第 1 步：目标 ══════ -->
            <template v-else-if="step === 1">
              <div class="rw-block">
                <p class="rw-label">你想进入哪个行业？</p>
                <div class="rw-chips">
                  <button
                    v-for="ind in options.industries" :key="ind.key" type="button"
                    class="rw-chip" :class="{ on: form.industry === ind.key }"
                    @click="pickIndustry(ind.key)"
                  >{{ ind.label }}</button>
                </div>
              </div>

              <div class="rw-block">
                <p class="rw-label">具体投哪个岗位？</p>
                <div class="rw-chips">
                  <button
                    v-for="j in currentJobs" :key="j.key" type="button"
                    class="rw-chip" :class="{ on: form.job_key === j.key }"
                    @click="form.job_key = j.key"
                  >{{ j.label }}</button>
                  <button
                    type="button"
                    class="rw-chip is-custom" :class="{ on: form.job_key === 'custom' }"
                    @click="pickCustomJob"
                  >✎ 自定义岗位</button>
                </div>
                <input
                  v-if="form.job_key === 'custom'"
                  v-model="form.custom_job"
                  class="rw-input rw-input-job"
                  maxlength="20"
                  placeholder="手动输入岗位名，例如：无人机飞手 / 新媒体运营"
                />
                <p v-if="form.job_key === 'custom'" class="rw-hint">按你输入的岗位名做匹配，行业仍用于划分简历侧重</p>
                <p v-else-if="!currentJobs.length" class="rw-hint">先选一个行业，岗位会跟着变</p>
              </div>

              <div class="rw-block">
                <p class="rw-label">求职类型</p>
                <div class="rw-chips">
                  <button
                    v-for="t in options.job_types" :key="t" type="button"
                    class="rw-chip" :class="{ on: form.job_type === t }"
                    @click="form.job_type = t"
                  >{{ t }}</button>
                </div>
              </div>

              <div class="rw-block">
                <p class="rw-label">意向城市 <em>选填</em></p>
                <input v-model="form.city" class="rw-input" maxlength="20" placeholder="例如：成都 / 一线城市 / 不限" />
              </div>
            </template>

            <!-- ══════ 第 2 步：匹配度 ══════ -->
            <template v-else-if="step === 2">
              <p v-if="matching" class="rw-loading">正在比对你的档案…</p>
              <template v-else-if="match">
                <div class="rw-score">
                  <svg class="rw-ring" viewBox="0 0 100 100" aria-hidden="true">
                    <circle class="rw-ring-bg" cx="50" cy="50" r="42" />
                    <circle
                      class="rw-ring-fg" cx="50" cy="50" r="42"
                      :stroke="ringColor"
                      :stroke-dasharray="`${(match.score / 100) * 264} 264`"
                    />
                  </svg>
                  <div class="rw-score-txt">
                    <b>{{ Math.round(match.score) }}</b>
                    <i>{{ match.level }}匹配</i>
                  </div>
                </div>
                <p class="rw-score-job">
                  <span>{{ match.job.industry_label }}</span>
                  <i>·</i>
                  <span>{{ match.job.label }}</span>
                </p>

                <div class="rw-dims">
                  <div v-for="d in match.dims" :key="d.key" class="rw-dim">
                    <div class="rw-dim-top">
                      <span>{{ d.label }}</span>
                      <b>{{ Math.round(d.score) }}</b>
                    </div>
                    <div class="rw-dim-bar"><i :style="{ width: d.score + '%' }"></i></div>
                    <p class="rw-dim-note">{{ d.note }}</p>
                  </div>
                </div>

                <div v-if="match.hits.length || match.gaps.length" class="rw-two">
                  <div v-if="match.hits.length" class="rw-tags">
                    <p class="rw-label">已经对得上</p>
                    <div class="rw-chips is-static">
                      <span v-for="h in match.hits.slice(0, 8)" :key="h" class="rw-chip is-hit">{{ h }}</span>
                    </div>
                  </div>
                  <div v-if="match.gaps.length" class="rw-tags">
                    <p class="rw-label">还缺这些</p>
                    <div class="rw-chips is-static">
                      <span v-for="g in match.gaps.slice(0, 8)" :key="g" class="rw-chip is-gap">{{ g }}</span>
                    </div>
                  </div>
                </div>

                <section v-if="match.suggest.length" class="rw-suggest">
                  <p class="rw-label">建议投递</p>
                  <button
                    v-for="(s, i) in match.suggest" :key="s.job_key" type="button"
                    class="rw-suggest-row" :class="{ on: s.job_key === form.job_key }"
                    @click="switchJob(s.job_key)"
                  >
                    <span class="rw-suggest-rank">{{ i + 1 }}</span>
                    <span class="rw-suggest-main">
                      <b>{{ s.label }}</b>
                      <em>{{ s.why }}</em>
                    </span>
                    <span class="rw-suggest-score">{{ Math.round(s.score) }}</span>
                  </button>
                </section>

                <ul v-if="match.tips.length" class="rw-tips">
                  <li v-for="t in match.tips" :key="t">{{ t }}</li>
                </ul>
              </template>
            </template>

            <!-- ══════ 第 3 步：证件照 + 模板 + 导出 ══════ -->
            <template v-else>
              <!-- 证件照采集：与头像无关，仅供简历使用；比例不适合会要求重传 -->
              <div class="rw-photo">
                <p class="rw-label">简历证件照 <em>建议上传 · 与头像相互独立</em></p>
                <div class="rw-photo-row">
                  <div class="rw-photo-box">
                    <img
                      v-if="photoUrl && !photoBroken" :src="photoUrl" class="rw-photo-img" alt="简历证件照"
                      @error="photoBroken = true"
                    />
                    <span v-else-if="photoBroken" class="rw-photo-empty">照片<br />丢失</span>
                    <span v-else class="rw-photo-empty">一寸<br />3:4</span>
                  </div>
                  <div class="rw-photo-ops">
                    <template v-if="!photoUrl || photoBroken">
                      <button type="button" class="rw-photo-btn" @click="pickPhoto">选择照片</button>
                      <p class="rw-hint">JPG / PNG，系统按一寸照比例自动裁剪；比例不合适会提醒重传</p>
                    </template>
                    <template v-else>
                      <div class="rw-photo-btns">
                        <button type="button" class="rw-photo-btn" @click="pickPhoto">更换</button>
                        <button type="button" class="rw-photo-btn is-ghost" @click="removePhoto">不使用</button>
                      </div>
                      <p class="rw-hint">已按 3:4 自动裁剪，将放在简历抬头右侧</p>
                    </template>
                    <p v-if="photoError" class="rw-photo-err">{{ photoError }}</p>
                  </div>
                </div>
                <input ref="photoInputRef" type="file" accept="image/*" style="display:none" @change="onPhotoFile" />
              </div>

              <p class="rw-label rw-tpl-label">
                挑一套版式
                <em v-if="tplLoading" class="rw-tpl-loading">正在用你的档案生成真实预览…</em>
              </p>
              <div class="rw-tpl">
                <button
                  v-for="t in options.templates" :key="t.key" type="button"
                  class="rw-tpl-card" :class="{ on: form.template_key === t.key }"
                  @click="form.template_key = t.key"
                >
                  <span class="rw-tpl-shot">
                    <!-- 真实预览：后端用你的档案按该模板渲染出的 PDF 首页，所见即所得 -->
                    <img v-if="tplShots[t.key]" :src="tplShots[t.key]" alt="" />
                    <span v-else class="rw-tpl-skeleton" :class="{ spin: tplLoading }"></span>
                  </span>
                  <span class="rw-tpl-main">
                    <b>{{ t.name }}<em>{{ t.tag }}</em></b>
                    <i>{{ t.desc }}</i>
                  </span>
                </button>
              </div>
              <p class="rw-hint rw-tpl-note">
                缩略图是用你自己的档案实时渲染的导出效果，不是示意图；换岗位或照片会重新生成。
              </p>

              <div class="rw-preview">
                <p class="rw-label">这份简历会包含</p>
                <div class="rw-chips is-static">
                  <span v-for="s in (result?.sections || defaultSections)" :key="s.key || s.title" class="rw-chip is-plain">
                    {{ s.title }}<template v-if="s.count"> {{ s.count }}</template>
                  </span>
                </div>
                <p class="rw-hint">内容取自你的作品集、成绩、证书与成长档案，空小节会自动省略。</p>
              </div>

              <div v-if="result" class="rw-done">
                已生成「{{ result.filename }}」· {{ sizeText }} · 已存入我的简历
              </div>
              <p v-if="errorMsg" class="rw-error">{{ errorMsg }}</p>
            </template>
          </div>

          <!-- ── 底部操作 ── -->
          <footer class="rw-foot">
            <template v-if="step === 1">
              <button class="rw-btn primary" type="button" :disabled="!canNext" @click="goMatch">看看匹配度</button>
            </template>
            <template v-else-if="step === 2">
              <button class="rw-btn" type="button" @click="step = 1">改目标</button>
              <button class="rw-btn primary" type="button" :disabled="!match" @click="step = 3">挑模板</button>
            </template>
            <template v-else>
              <button class="rw-btn" type="button" :disabled="busyDocx" @click="exportAs('docx')">
                {{ busyDocx ? '生成中…' : '导出 DOCX' }}
              </button>
              <button class="rw-btn primary" type="button" :disabled="busyPdf" @click="exportAs('pdf')">
                {{ busyPdf ? '生成中…' : '导出 PDF' }}
              </button>
            </template>
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadFile } from '@/api/upload'
import {
  getResumeOptions, getTemplatePreview, matchResume, generateResume,
  type ResumeMatch, type ResumeOptions, type ResumeFile,
} from '@/api/portfolio'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'generated'): void }>()

const step = ref(1)
const loadingOptions = ref(false)
const matching = ref(false)
const busyDocx = ref(false)
const busyPdf = ref(false)
const errorMsg = ref('')

const options = ref<ResumeOptions>({ industries: [], job_types: [], templates: [] })
const match = ref<ResumeMatch | null>(null)
const result = ref<ResumeFile | null>(null)

const form = reactive({
  industry: '' as string,
  job_key: '' as string,
  custom_job: '',
  job_type: '',
  city: '',
  template_key: 'classic',
})

/** 简历证件照（与头像无关）：只存在于导出流程，上传成功后记住 url 方便下次带出 */
const photoInputRef = ref<HTMLInputElement>()
const photoUrl = ref('')
const photoError = ref('')
// 历史照片可能已被清理，加载失败时退回「选择照片」态，别显示裂图
const photoBroken = ref(false)

const defaultSections = [
  { key: 'edu', title: '教育背景', count: 0 },
  { key: 'skill', title: '专业技能', count: 0 },
  { key: 'project', title: '项目经历', count: 0 },
  { key: 'cert', title: '荣誉证书', count: 0 },
  { key: 'self', title: '自我评价', count: 0 },
]

const stepTitle = computed(() => ['', '先说你想要什么工作', '你的档案离它有多远', '挑一套版式导出'][step.value])
const stepSub = computed(() => [
  '',
  '这几项决定了简历的侧重，也会影响匹配度的算法',
  '分数由技能、项目、学业、证书四个维度加权得出',
  '三种模板内容一致，只是排版和侧重点不同',
][step.value])

const currentJobs = computed(() => {
  const ind = options.value.industries.find(i => i.key === form.industry)
  return ind?.jobs ?? []
})

const canNext = computed(() => !!form.industry && (form.job_key === 'custom' ? !!form.custom_job.trim() : !!form.job_key))

const ringColor = computed(() => {
  const s = match.value?.score ?? 0
  if (s >= 80) return '#0f7a58'
  if (s >= 65) return '#3f8f6b'
  if (s >= 50) return '#b0761c'
  return '#b0483c'
})

const sizeText = computed(() => {
  const n = result.value?.size ?? 0
  if (!n) return ''
  return n >= 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'
})

function close() {
  emit('update:modelValue', false)
}

function goBack() {
  if (step.value > 1) step.value -= 1
}

function pickIndustry(key: string) {
  form.industry = key
  const jobs = options.value.industries.find(i => i.key === key)?.jobs ?? []
  // 换行业必须重置岗位，否则会拿「前端」去投「银行」这种错配；
  // 自定义岗位是用户手填的，跟行业列表无关，保留
  if (form.job_key !== 'custom') form.job_key = jobs[0]?.key ?? ''
  match.value = null
  result.value = null
}

function pickCustomJob() {
  form.job_key = 'custom'
  match.value = null
  result.value = null
}

/** 请求里带的岗位参数：自定义时把手输名字一起送后端 */
function targetPayload() {
  return {
    job_key: form.job_key,
    industry: form.industry,
    custom_job: form.job_key === 'custom' ? form.custom_job.trim() : null,
    job_type: form.job_type,
    city: form.city,
  }
}

async function loadOptions() {
  loadingOptions.value = true
  try {
    options.value = await getResumeOptions()
    if (!form.industry && options.value.industries.length) {
      pickIndustry(options.value.industries[0].key)
    }
    if (!form.job_type && options.value.job_types.length) {
      form.job_type = options.value.job_types[1] || options.value.job_types[0]
    }
  } catch {
    ElMessage.error('岗位库加载失败，请重试')
  } finally {
    loadingOptions.value = false
  }
}

async function goMatch() {
  if (!canNext.value) return
  step.value = 2
  await runMatch()
}

async function runMatch() {
  matching.value = true
  match.value = null
  errorMsg.value = ''
  try {
    match.value = await matchResume({ ...targetPayload() })
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '匹配度计算失败'
    ElMessage.error(errorMsg.value)
  } finally {
    matching.value = false
  }
}

/** 点「建议投递」里的岗位：直接换目标并重算，省得退回第 1 步 */
async function switchJob(jobKey: string) {
  form.job_key = jobKey
  result.value = null
  await runMatch()
}

function downloadB64(b64: string, filename: string, mime: string) {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  const url = URL.createObjectURL(new Blob([bytes], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  setTimeout(() => { URL.revokeObjectURL(url); a.remove() }, 1500)
}

async function exportAs(fmt: 'docx' | 'pdf') {
  const busy = fmt === 'docx' ? busyDocx : busyPdf
  if (busy.value) return
  busy.value = true
  errorMsg.value = ''
  try {
    const file = await generateResume({
      ...targetPayload(),
      template_key: form.template_key, fmt, save: true,
      photo_url: photoUrl.value || null,
    })
    result.value = file
    downloadB64(file.b64, file.filename, file.mime)
    ElMessage.success(`已导出 ${file.filename}`)
    emit('generated')
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '生成失败，请换一种格式或稍后重试'
    ElMessage.error(errorMsg.value)
  } finally {
    busy.value = false
  }
}

watch(() => props.modelValue, (v) => {
  if (!v) return
  // 每次都从第 1 步开始，但保留上次选的目标（多数人是一次投一个方向反复导）
  step.value = 1
  match.value = null
  result.value = null
  errorMsg.value = ''
  photoError.value = ''
  photoUrl.value = localStorage.getItem('resume_photo_url') || ''
  photoBroken.value = false
  if (!options.value.industries.length) loadOptions()
})

// ── 证件照采集 ──
function pickPhoto() { photoInputRef.value?.click() }

function removePhoto() {
  photoUrl.value = ''
  photoError.value = ''
  photoBroken.value = false
  localStorage.removeItem('resume_photo_url')
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

/**
 * 按一寸照比例（295:413 ≈ 3:4）居中「cover」裁剪，输出 590×826 的 JPEG。
 * 严谨性靠两道前置校验兜底：分辨率太低会糊、比例太偏裁出来构图不对——
 * 这两种都不裁，直接提示重新上传。
 */
async function onPhotoFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  photoError.value = ''
  const objUrl = URL.createObjectURL(file)
  try {
    const img = await loadImage(objUrl)
    const w = img.naturalWidth, h = img.naturalHeight
    if (w < 200 || h < 260) {
      photoError.value = '这张照片分辨率太低，印出来会模糊，请换一张更清晰的'
      return
    }
    const ratio = w / h
    if (ratio < 0.5 || ratio > 0.95) {
      photoError.value = '照片比例不适合做证件照（建议竖版、接近 3:4），请重新上传'
      return
    }
    // cover 居中裁剪到 295:413
    const tw = 590, th = 826
    const canvas = document.createElement('canvas')
    canvas.width = tw
    canvas.height = th
    const ctx = canvas.getContext('2d')
    if (!ctx) { photoError.value = '照片处理失败，请换一张试试'; return }
    const srcRatio = w / h
    let sw: number, sh: number, sx: number, sy: number
    if (srcRatio > 295 / 413) { sh = h; sw = sh * (295 / 413); sx = (w - sw) / 2; sy = 0 }
    else { sw = w; sh = sw / (295 / 413); sx = 0; sy = (h - sh) / 2 }
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, tw, th)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
    const blob = await (await fetch(dataUrl)).blob()
    const up = await uploadFile(new File([blob], `idphoto_${Date.now()}.jpg`, { type: 'image/jpeg' }))
    photoUrl.value = up.url
    photoBroken.value = false
    localStorage.setItem('resume_photo_url', up.url)
    ElMessage.success('已按一寸照比例自动裁剪')
  } catch {
    photoError.value = '照片读取失败，请换一张试试'
  } finally {
    URL.revokeObjectURL(objUrl)
  }
}

// ── 模板预览：后端用学生自己的档案按该模板真实渲染一页 PDF 转 PNG ──
// 与导出走同一渲染管线，缩略图即导出效果（含证件照），不会再对不上。
const tplShots = reactive<Record<string, string>>({})
const tplLoading = ref(false)

async function loadTplShots() {
  if (tplLoading.value || !options.value.templates.length) return
  tplLoading.value = true
  try {
    await Promise.all(options.value.templates.map(async (t) => {
      try {
        const r = await getTemplatePreview(t.key, photoUrl.value || null, {
          industry: form.industry, job_key: form.job_key, custom_job: form.custom_job,
          job_type: form.job_type, city: form.city,
        })
        // 后端按当前选择的行业/岗位渲染，预览的求职意向与导出一致
        tplShots[t.key] = r.image
      } catch { /* 拉取失败保留骨架，不挡导出 */ }
    }))
  } finally {
    tplLoading.value = false
  }
}

// 打开向导即清缓存：行业/岗位可能换了，预览要跟着重渲染
watch(() => props.modelValue, (v) => {
  if (v) Object.keys(tplShots).forEach(k => delete tplShots[k])
})

// 进入第 3 步、或照片更换后都重拉（照片会出现在预览里）
watch(step, (s) => { if (s === 3 && props.modelValue) loadTplShots() })
watch(photoUrl, () => {
  Object.keys(tplShots).forEach(k => delete tplShots[k])
  if (step.value === 3 && props.modelValue) loadTplShots()
})
</script>

<style scoped>
.rw-mask {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(20, 24, 22, .42);
  backdrop-filter: blur(2px);
}
.rw-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-height: 92vh;
  background: #fff;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -10px 30px rgba(16, 30, 24, .16);
  overflow: hidden;
}

/* ── 头部 ── */
.rw-head {
  flex: none;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 16px 16px 8px;
}
.rw-back {
  flex: none;
  width: 28px; height: 28px;
  margin-top: 1px;
  display: flex; align-items: center; justify-content: center;
  border: 0; border-radius: 9px;
  background: #f3f5f4; color: #3c453f;
  font-size: 20px; line-height: 1; font-family: inherit;
  cursor: pointer;
}
.rw-head-txt { flex: 1; min-width: 0; }
.rw-title { margin: 0; font-size: 17px; font-weight: 700; color: #14171a; letter-spacing: -.3px; }
.rw-sub { margin: 4px 0 0; font-size: 11.5px; line-height: 1.5; color: #8b939b; }
.rw-close {
  flex: none;
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border: 0; border-radius: 9px;
  background: transparent; color: #98a1a8;
  font-size: 13px; font-family: inherit;
  cursor: pointer;
}
.rw-close:active { background: rgba(20, 24, 22, .06); }

.rw-progress { flex: none; display: flex; gap: 5px; padding: 0 16px 10px; }
.rw-progress span {
  flex: 1; height: 3px; border-radius: 2px; background: #e9eeeb;
  transition: background .25s ease;
}
.rw-progress span.on { background: #0f7a58; }

/* ── 主体 ── */
.rw-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 2px 16px 14px;
}
.rw-loading { margin: 24px 0; text-align: center; font-size: 12.5px; color: #98a1a8; }

.rw-block { margin-bottom: 16px; }
.rw-label {
  margin: 0 0 8px;
  font-size: 12px; font-weight: 600; color: #5b6470;
}
.rw-label em { font-style: normal; font-weight: 400; color: #b3b9bf; }
.rw-hint { margin: 7px 0 0; font-size: 10.5px; line-height: 1.5; color: #a2aab1; }

.rw-chips { display: flex; flex-wrap: wrap; gap: 7px; }
.rw-chips.is-static { gap: 6px; }
.rw-chip {
  height: 32px;
  padding: 0 12px;
  display: inline-flex; align-items: center;
  border: 1px solid #e3e8e5;
  border-radius: 9px;
  background: #fbfcfb;
  color: #4a535b;
  font-size: 12.5px; font-family: inherit;
  cursor: pointer;
  transition: border-color .16s, background .16s, color .16s;
}
.rw-chip.on {
  border-color: #0f7a58;
  background: #eef7f2;
  color: #0b5c42;
  font-weight: 600;
}
.rw-chip.is-static { height: 26px; padding: 0 9px; font-size: 11px; cursor: default; }
.rw-chip.is-hit { border-color: #cbe6d8; background: #f2faf5; color: #14674a; }
.rw-chip.is-gap { border-color: #eddfd0; background: #fdf8f2; color: #94611f; }
.rw-chip.is-plain { border-color: #e7ebe9; background: #f7f9f8; color: #5b6470; }

.rw-input {
  width: 100%; height: 40px; padding: 0 12px;
  border: 1px solid #e3e8e5; border-radius: 10px;
  background: #fafcfb; color: #14171a;
  font-size: 13px; font-family: inherit;
}
.rw-input:focus { outline: none; border-color: #8ec9ae; background: #fff; }
.rw-input-job { margin-top: 9px; height: 38px; }
.rw-chip.is-custom { border-style: dashed; color: #6b747c; }

/* ── 证件照采集 ── */
.rw-photo { margin-bottom: 16px; }
.rw-photo-row { display: flex; gap: 12px; align-items: flex-start; }
.rw-photo-box {
  flex: none;
  width: 72px; height: 96px;
  border-radius: 9px;
  border: 1.5px dashed #c8d4cd;
  background: #f7faf8;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.rw-photo-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rw-photo-empty {
  font-size: 10.5px; line-height: 1.5; text-align: center;
  color: #a7b0a9; font-style: normal;
}
.rw-photo-ops { flex: 1; min-width: 0; padding-top: 2px; }
.rw-photo-btns { display: flex; gap: 7px; }
.rw-photo-btn {
  height: 30px; padding: 0 13px;
  border: 1px solid #0f7a58; border-radius: 9px;
  background: #0f7a58; color: #fff;
  font-size: 12px; font-weight: 600; font-family: inherit;
  cursor: pointer;
}
.rw-photo-btn.is-ghost { background: #fff; color: #6b747c; border-color: #dde3df; font-weight: 500; }
.rw-photo-btn:active { opacity: .8; }
.rw-photo-ops .rw-hint { margin-top: 8px; }
.rw-photo-err {
  margin: 8px 0 0; padding: 7px 9px;
  border-radius: 8px; background: #fdf3f2;
  font-size: 11px; line-height: 1.5; color: #a5382c;
}

/* ── 匹配度 ── */
.rw-score { position: relative; width: 108px; height: 108px; margin: 4px auto 0; }
.rw-ring { width: 108px; height: 108px; transform: rotate(-90deg); }
.rw-ring-bg { fill: none; stroke: #eef2f0; stroke-width: 8; }
.rw-ring-fg {
  fill: none; stroke-width: 8; stroke-linecap: round;
  transition: stroke-dasharray .8s cubic-bezier(.4, 0, .2, 1), stroke .3s;
}
.rw-score-txt {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px;
}
.rw-score-txt b { font-size: 30px; font-weight: 700; line-height: 1; color: #14171a; font-variant-numeric: tabular-nums; }
.rw-score-txt i { font-style: normal; font-size: 10px; color: #8b939b; }
.rw-score-job {
  margin: 10px 0 0; text-align: center;
  font-size: 12.5px; font-weight: 600; color: #3c453f;
}
.rw-score-job i { margin: 0 5px; font-style: normal; color: #c8cfcb; }

.rw-dims { margin-top: 16px; display: flex; flex-direction: column; gap: 11px; }
.rw-dim-top {
  display: flex; align-items: baseline; justify-content: space-between;
  font-size: 12px; color: #5b6470;
}
.rw-dim-top b { font-size: 13px; font-weight: 700; color: #14171a; font-variant-numeric: tabular-nums; }
.rw-dim-bar { margin-top: 5px; height: 5px; border-radius: 3px; background: #eef2f0; overflow: hidden; }
.rw-dim-bar i {
  display: block; height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, #7fc7a5, #0f7a58);
  transition: width .6s cubic-bezier(.4, 0, .2, 1);
}
.rw-dim-note { margin: 5px 0 0; font-size: 10.5px; line-height: 1.45; color: #9aa3ab; }

.rw-two { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.rw-tags .rw-label { margin-bottom: 7px; }

.rw-suggest { margin-top: 16px; }
.rw-suggest-row {
  width: 100%;
  display: flex; align-items: center; gap: 9px;
  padding: 9px 10px; margin-bottom: 6px;
  border: 1px solid #e9edea; border-radius: 11px;
  background: #fff; text-align: left; font-family: inherit;
  cursor: pointer;
}
.rw-suggest-row.on { border-color: #b8ddc9; background: #f5fbf7; }
.rw-suggest-rank {
  flex: none; width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; background: #f0f4f1;
  font-size: 10px; font-weight: 700; color: #7b848c;
}
.rw-suggest-row.on .rw-suggest-rank { background: #0f7a58; color: #fff; }
.rw-suggest-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.rw-suggest-main b { font-size: 12.5px; font-weight: 600; color: #1b2024; }
.rw-suggest-main em {
  font-style: normal; font-size: 10.5px; color: #98a1a8;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rw-suggest-score {
  flex: none; font-size: 13px; font-weight: 700; color: #0f7a58;
  font-variant-numeric: tabular-nums;
}

.rw-tips {
  margin: 16px 0 0; padding: 11px 12px 11px 26px;
  border-radius: 11px; background: #fafbfa;
  font-size: 11.5px; line-height: 1.65; color: #6b747c;
}
.rw-tips li + li { margin-top: 5px; }

/* ── 模板：迷你版式示意图 ── */
.rw-tpl-label { margin-top: 2px; display: flex; align-items: baseline; gap: 8px; }
.rw-tpl-note { margin: -2px 0 2px; font-size: 11px; line-height: 1.55; color: #8a938d; }
.rw-tpl-loading {
  font-style: normal; font-size: 10.5px; font-weight: 400;
  color: #0f7a58; animation: rw-pulse 1.2s ease-in-out infinite;
}
@keyframes rw-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
.rw-tpl { display: flex; flex-direction: column; gap: 8px; }
.rw-tpl-card {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e6ebe8; border-radius: 12px;
  background: #fff; text-align: left; font-family: inherit;
  cursor: pointer;
  transition: border-color .16s, background .16s, box-shadow .16s;
}
.rw-tpl-card.on {
  border-color: #0f7a58; background: #f6fbf8;
  box-shadow: 0 0 0 2.5px rgba(15, 122, 88, .12);
}
/* 真实渲染预览（A4 首页缩略图，与导出同管线） */
.rw-tpl-shot {
  flex: none;
  width: 68px; height: 93px;
  border-radius: 5px;
  overflow: hidden;
  background: #f4f7f5;
  box-shadow: 0 1px 5px rgba(20, 24, 22, .10);
  display: flex;
}
.rw-tpl-shot img {
  width: 100%; height: 100%;
  object-fit: cover; object-position: top center;
  display: block;
}
.rw-tpl-skeleton {
  flex: 1; margin: 6px;
  border-radius: 3px;
  background: linear-gradient(100deg, #e7ece9 40%, #f3f6f4 50%, #e7ece9 60%) no-repeat;
  background-size: 200% 100%;
  animation: rw-skeleton 1.1s linear infinite;
}
.rw-tpl-skeleton.spin { animation: rw-skeleton 1.1s linear infinite; }
@keyframes rw-skeleton { from { background-position: 120% 0; } to { background-position: -80% 0; } }
.rw-tpl-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.rw-tpl-main b {
  display: flex; align-items: center; gap: 7px;
  font-size: 13px; font-weight: 600; color: #14171a;
}
.rw-tpl-main b em {
  font-style: normal; font-size: 9.5px; font-weight: 500;
  padding: 1px 6px; border-radius: 999px;
  background: #f1f4f2; color: #7b848c;
}
.rw-tpl-card.on .rw-tpl-main b em { background: #e3f2ea; color: #0b5c42; }
.rw-tpl-main i { font-style: normal; font-size: 11px; line-height: 1.45; color: #98a1a8; }

.rw-preview { margin-top: 18px; }
.rw-done {
  margin-top: 14px; padding: 9px 11px;
  border-radius: 10px; background: #f2faf5;
  font-size: 11.5px; line-height: 1.5; color: #14674a;
}
.rw-error {
  margin-top: 10px; padding: 9px 11px;
  border-radius: 10px; background: #fdf3f2;
  font-size: 11.5px; line-height: 1.5; color: #a5382c;
}

/* ── 底部 ── */
.rw-foot {
  flex: none;
  display: flex; gap: 9px;
  padding: 10px 16px calc(12px + env(safe-area-inset-bottom));
  border-top: 1px solid #f0f3f1;
  background: #fff;
}
.rw-btn {
  flex: 1; height: 44px;
  border: 1px solid #e3e8e5; border-radius: 12px;
  background: #f7f9f8; color: #3c453f;
  font-size: 14px; font-weight: 600; font-family: inherit;
  cursor: pointer;
}
.rw-btn.primary { flex: 1.4; border-color: #0f7a58; background: #0f7a58; color: #fff; }
.rw-btn:disabled { opacity: .55; }
.rw-btn:active:not(:disabled) { transform: scale(.985); }

/* 桌面端：居中弹层，别铺满整屏 */
@media (min-width: 768px) {
  .rw-mask { align-items: center; padding: 24px; }
  .rw-panel {
    max-width: 520px;
    max-height: 88vh;
    border-radius: 18px;
  }
}

.rw-fade-enter-active, .rw-fade-leave-active { transition: opacity .22s ease; }
.rw-fade-enter-from, .rw-fade-leave-to { opacity: 0; }
.rw-fade-enter-active .rw-panel, .rw-fade-leave-active .rw-panel {
  transition: transform .26s cubic-bezier(.32, .72, 0, 1);
}
.rw-fade-enter-from .rw-panel, .rw-fade-leave-to .rw-panel { transform: translateY(24px); }

@media (prefers-reduced-motion: reduce) {
  .rw-fade-enter-active, .rw-fade-leave-active,
  .rw-fade-enter-active .rw-panel, .rw-fade-leave-active .rw-panel { transition: none; }
  .rw-ring-fg, .rw-dim-bar i { transition: none; }
}
</style>
