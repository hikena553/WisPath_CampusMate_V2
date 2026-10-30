<template>
  <div class="portfolio-page"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="作品集" sub="项目 · 证书 · 简历" accent="#b45309" fallback="/student">
      <!-- 移动端：AI 建议压成 Head 右侧图标按钮，避免正文顶部再顶一个蓝色大按钮 -->
      <template #right>
        <button class="pf-ai-btn" type="button" aria-label="AI 优化建议" :disabled="aiLoading" @click="openAISuggest">
          <el-icon :size="17"><MagicStick /></el-icon>
        </button>
      </template>
    </SubPageHeader>
    <!-- 移动端下拉刷新：吉祥物指示器（与学业中心 / 工作台共用同一模块） -->
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />
    <!-- 顶部标题（桌面端） -->
    <div class="portfolio-header">
      <div>
        <h2 class="portfolio-title">我的作品集</h2>
        <p class="portfolio-sub">项目经历 · 证书荣誉 · 个人简历</p>
      </div>
      <el-button type="primary" round :loading="aiLoading" @click="openAISuggest">
        <el-icon style="margin-right:4px"><MagicStick /></el-icon>AI 优化建议
      </el-button>
    </div>

    <!-- 项目经历 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">项目经历</span>
        <el-badge :value="projects.length" :max="99" class="head-badge">
          <el-button size="small" text type="primary" @click="openProjectDialog()">添加项目</el-button>
        </el-badge>
      </div>
      <div v-if="!projects.length" class="empty-tip">还没有项目经历，点击「添加项目」记录你的第一个项目吧</div>
      <div class="projects-wall">
        <div v-for="p in projects" :key="p.id" class="project-card" :class="{ 'has-cover': !!projectCover(p) }">
          <!-- 移动端作品墙封面（桌面端隐藏，桌面保持原列表卡样式） -->
          <div class="project-cover">
            <el-image
              v-if="projectCover(p)"
              :src="projectCover(p)" fit="cover" class="project-cover-img"
              :preview-src-list="p.images && p.images.length ? p.images : [projectCover(p)]"
              preview-teleported
            />
            <div v-else class="project-cover-fallback"><span>{{ (p.project_name || '#').slice(0, 1) }}</span></div>
            <div class="project-cover-grad" aria-hidden="true"></div>
            <span v-if="(p.images?.length || 0) > 1" class="project-cover-badge">{{ p.images!.length }} 图</span>
            <div class="project-cover-txt">
              <b>{{ p.project_name }}</b>
              <i>{{ [p.my_role, p.is_team ? '团队' : ''].filter(Boolean).join(' · ') || formatDate(p.start_date) }}</i>
            </div>
            <span class="project-cover-acts">
              <button type="button" @click.stop="openProjectDialog(p)">编辑</button>
              <button type="button" @click.stop="removeProject(p)">删除</button>
            </span>
          </div>
          <div class="project-head">
          <div class="project-title">
            {{ p.project_name }}
            <el-tag v-if="p.is_team" size="small" type="primary" effect="light" round>团队</el-tag>
          </div>
          <div class="project-actions">
            <el-button size="small" text type="primary" @click="openProjectDialog(p)">编辑</el-button>
            <el-button size="small" text type="danger" @click="removeProject(p)">删除</el-button>
          </div>
        </div>
        <div class="project-meta">
          <span class="meta-item">{{ formatDate(p.start_date) }} ~ {{ p.end_date ? formatDate(p.end_date) : '至今' }}</span>
          <span v-if="p.my_role" class="meta-item">角色: {{ p.my_role }}</span>
          <span v-if="p.team_members" class="meta-item">成员: {{ p.team_members }}</span>
        </div>
        <div v-if="p.tech_stack" class="project-tags">
          <el-tag v-for="t in splitTags(p.tech_stack)" :key="t" size="small" effect="plain" round class="tag-item">{{ t }}</el-tag>
        </div>
        <p v-if="p.description" class="project-desc">{{ p.description }}</p>
        <div v-if="p.project_link || p.attachment_url" class="project-links">
          <el-link v-if="p.project_link" type="primary" :href="p.project_link" target="_blank" :underline="false">
            <el-icon style="margin-right:3px"><Link /></el-icon>项目链接
          </el-link>
          <el-link v-if="p.attachment_url" type="primary" :href="p.attachment_url" target="_blank" :underline="false" style="margin-left:16px">
            <el-icon style="margin-right:3px"><Paperclip /></el-icon>附件
          </el-link>
        </div>
      </div>
      </div><!-- /.projects-wall -->
    </div>

    <!-- 证书荣誉 -->
    <div class="card">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">证书荣誉</span>
        <el-badge :value="certificates.length" :max="99" class="head-badge">
          <el-button size="small" text type="primary" @click="openCertDialog()">添加证书</el-button>
        </el-badge>
      </div>
      <div v-if="!certificates.length" class="empty-tip">还没有证书荣誉，把获得的奖项记录下来吧</div>
      <div v-for="c in certificates" :key="c.id" class="cert-card">
        <div class="cert-head">
          <div class="cert-title">
            {{ c.title }}
            <el-tag v-if="c.award_level" size="small" type="warning" effect="light" round>{{ awardLevelLabel(c.award_level) }}</el-tag>
          </div>
          <div class="cert-actions">
            <el-button size="small" text type="primary" @click="openCertDialog(c)">编辑</el-button>
            <el-button size="small" text type="danger" @click="removeCert(c)">删除</el-button>
          </div>
        </div>
        <div class="cert-meta">
          <span v-if="c.competition_name" class="meta-item">{{ c.competition_name }}</span>
          <span v-if="c.date" class="meta-item">{{ c.date }}</span>
          <el-tag size="small" :type="c.status === 'APPROVED' ? 'success' : c.status === 'REJECTED' ? 'danger' : 'info'" effect="light" round>
            {{ certStatusLabel(c.status) }}
          </el-tag>
        </div>
        <p v-if="c.description" class="cert-desc">{{ c.description }}</p>
        <div v-if="c.image_url" class="cert-img-box">
          <el-image :src="c.image_url" fit="cover" class="cert-img" :preview-src-list="[c.image_url]" preview-teleported />
          <span class="cert-img-label">佐证图片</span>
        </div>
      </div>
    </div>

    <!-- 个人简历（移动端已抽至「我的资料」页管理，此处桌面端保留） -->
    <div class="card resume-section">
      <div class="card-head">
        <span class="head-bar"></span>
        <span class="head-title">个人简历</span>
        <div>
          <el-upload :show-file-list="false" :before-upload="beforeUpload" accept=".pdf,.doc,.docx">
            <el-button size="small" type="primary" plain>上传简历</el-button>
          </el-upload>
        </div>
      </div>
      <div v-if="!resumes.length" class="empty-tip">还没有简历，点击「上传简历」上传 PDF 简历，随时可以预览和下载</div>
      <div v-for="r in resumes" :key="r.id" class="resume-card" :class="{ 'resume-current': !!r.is_current }">
        <el-icon :size="22" :color="r.is_current ? '#409eff' : '#999'"><Document /></el-icon>
        <div class="resume-info">
          <div class="resume-name">
            {{ r.filename }}
            <el-tag v-if="r.is_current" size="small" type="primary" effect="light" round>当前版本</el-tag>
          </div>
          <div class="resume-meta">{{ formatSize(r.file_size) }} · {{ formatTime(r.created_at) }}</div>
        </div>
        <div class="resume-actions">
          <el-button size="small" text type="primary" @click="previewResume(r)">预览/下载</el-button>
          <el-button v-if="!r.is_current" size="small" text type="primary" @click="makeCurrent(r)">设为当前</el-button>
          <el-button size="small" text type="danger" @click="removeResume(r)">删除</el-button>
        </div>
      </div>
    </div>

    <!-- 项目弹窗（多字段重表单：移动端=全屏子页 / 桌面端=弹窗） -->
    <ResponsivePopup v-model="projectDialogVisible" :title="projectForm.id ? '编辑项目' : '添加项目'" width="520px">
      <el-form label-width="72px">
        <el-form-item label="项目名称" required>
          <el-input v-model="projectForm.project_name" placeholder="例如：校园二手交易小程序" maxlength="60" />
        </el-form-item>
        <el-form-item label="我的角色">
          <el-input v-model="projectForm.my_role" placeholder="例如：前端开发 / 项目负责人" maxlength="30" />
        </el-form-item>
        <el-form-item label="技术栈">
          <el-input v-model="projectForm.tech_stack" placeholder="逗号分隔，例如：Vue3, FastAPI, MySQL" maxlength="100" />
        </el-form-item>
        <el-form-item label="开始时间" required>
          <el-date-picker v-model="projectForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="projectForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="选填，不填则至今" style="width:100%" />
        </el-form-item>
        <el-form-item label="是否团队">
          <el-switch v-model="projectForm.is_team" active-text="团队项目" />
        </el-form-item>
        <el-form-item v-if="projectForm.is_team" label="团队成员">
          <el-input v-model="projectForm.team_members" placeholder="逗号分隔成员姓名" maxlength="100" />
        </el-form-item>
        <el-form-item label="项目链接">
          <el-input v-model="projectForm.project_link" placeholder="https:// 项目地址 / GitHub / 演示链接" maxlength="200" />
        </el-form-item>
        <el-form-item label="附件地址">
          <el-input v-model="projectForm.attachment_url" placeholder="https:// 附件 / 截图地址，选填" maxlength="200" />
        </el-form-item>
        <el-form-item label="项目图片">
          <div class="img-upload-wrap">
            <div class="img-upload-row">
              <div v-for="(img, i) in projectForm.images" :key="img + i" class="img-thumb">
                <el-image :src="img" fit="cover" class="img-thumb-img" :preview-src-list="projectForm.images" :initial-index="i" preview-teleported />
                <button type="button" class="img-thumb-del" aria-label="移除图片" @click="projectForm.images.splice(i, 1)">✕</button>
                <span v-if="i === 0" class="img-thumb-cover">封面</span>
              </div>
              <el-upload
                v-if="projectForm.images.length < 6"
                :show-file-list="false"
                :before-upload="uploadProjectImage"
                accept="image/*"
              >
                <button type="button" class="img-add-btn" aria-label="添加图片"><el-icon :size="18"><Plus /></el-icon></button>
              </el-upload>
            </div>
            <p class="img-upload-hint">最多 6 张，第一张将作为作品墙封面展示</p>
          </div>
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="projectForm.description" type="textarea" :rows="3" placeholder="项目背景、职责与成果（可点击右上角 AI 优化建议生成）" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingProject" @click="saveProject">保存</el-button>
      </template>
    </ResponsivePopup>

    <!-- 证书弹窗（多字段表单：移动端=全屏子页 / 桌面端=弹窗） -->
    <ResponsivePopup v-model="certDialogVisible" :title="certForm.id ? '编辑证书' : '添加证书'" width="520px">
      <el-form label-width="72px">
        <el-form-item label="证书名称" required>
          <el-input v-model="certForm.title" placeholder="例如：蓝桥杯省赛一等奖" maxlength="60" />
        </el-form-item>
        <el-form-item label="比赛/机构">
          <el-input v-model="certForm.competition_name" placeholder="颁发机构，例如：工业和信息化部人才交流中心" maxlength="60" />
        </el-form-item>
        <el-form-item label="荣誉等级">
          <el-select v-model="certForm.award_level" placeholder="选择等级" style="width:100%">
            <el-option v-for="lv in awardLevels" :key="lv.value" :label="lv.label" :value="lv.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="获取日期">
          <el-date-picker v-model="certForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="佐证图片">
          <div class="cert-upload-row">
            <el-upload :show-file-list="false" :before-upload="uploadCertImage" accept="image/*">
              <el-button size="small" plain>上传图片</el-button>
            </el-upload>
            <span v-if="uploadingImg" class="uploading-tip">上传中...</span>
            <el-image v-if="certForm.image_url" :src="certForm.image_url" fit="cover" class="cert-upload-preview" :preview-src-list="[certForm.image_url]" preview-teleported />
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="certForm.description" type="textarea" :rows="2" placeholder="选填" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="certDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingCert" @click="saveCert">保存</el-button>
      </template>
    </ResponsivePopup>

    <!-- AI 优化建议弹窗（轻内容：移动端=底部动作面板） -->
    <ActionSheet v-model="aiDialogVisible" title="AI 优化建议" width="540px">
      <div class="ai-tip">选择项目后，AI 将基于 STAR 法则生成一段结构化项目描述，并给出简历优化建议。生成的描述可直接填入项目编辑弹窗。</div>
      <el-select v-model="aiProjectId" placeholder="选择项目" style="width:100%" @change="genAISuggest">
        <el-option v-for="p in projects" :key="p.id" :label="p.project_name" :value="p.id" />
      </el-select>
      <div v-if="aiResult" class="ai-result">
        <div class="ai-result-label">项目描述建议</div>
        <div class="ai-result-text">{{ aiResult.description }}</div>
        <el-button size="small" type="primary" plain @click="copyToProjectForm">填入项目编辑</el-button>
        <div class="ai-result-label ai-result-label2">简历优化建议</div>
        <div class="ai-result-text">{{ aiResult.resume_tips }}</div>
      </div>
    </ActionSheet>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Link, Paperclip, MagicStick } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import { useResponsive } from '@/composables/useResponsive'
// v6.1 弹窗减负：重表单走全屏子页，轻内容走底部动作面板，删除确认用 actionConfirm（简历相关弹窗保持原样）
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import ActionSheet from '@/components/common/ActionSheet.vue'
import { actionConfirm } from '@/composables/useActionSheet'
import {
  getProjects, createProject, updateProject, deleteProject,
  type StudentProject,
} from '@/api/growth'
import {
  getCertificates, createCertificate, updateCertificate, deleteCertificate,
  getResumes, createResume, setCurrentResume, deleteResume,
  type Certificate, type Resume,
} from '@/api/portfolio'
import { uploadFile } from '@/api/upload'

// ---------- 状态 ----------
const projects = ref<StudentProject[]>([])
const certificates = ref<Certificate[]>([])
const resumes = ref<Resume[]>([])

const awardLevels = [
  { value: 'school', label: '校级' },
  { value: 'city', label: '市级' },
  { value: 'province', label: '省级' },
  { value: 'national', label: '国家级' },
  { value: 'international', label: '国际级' },
]
const awardLevelLabel = (v: string) => awardLevels.find(a => a.value === v)?.label || v
const certStatusLabel = (v: string) =>
  v === 'APPROVED' ? '已认证' : v === 'REJECTED' ? '未通过' : v === 'PENDING' ? '待认证' : v

// ---------- 工具 ----------
function formatDate(d: string) {
  return d ? String(d).slice(0, 10) : ''
}
function formatTime(t: string | null) {
  return t ? String(t).slice(0, 10) : ''
}
function formatSize(n: number | null) {
  if (!n) return '未知大小'
  return n >= 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'
}
function splitTags(s: string) {
  return String(s || '').split(/[,，、;；]/).map(t => t.trim()).filter(Boolean)
}

// ---------- 数据加载 ----------
async function refreshAll() {
  const [ps, cs, rs] = await Promise.all([getProjects(), getCertificates(), getResumes()])
  projects.value = ps
  certificates.value = cs
  resumes.value = rs
}
onMounted(refreshAll)

// 下拉刷新（移动端）：复用 refreshAll 重拉项目 / 证书 / 简历，桌面端不响应手势
const { isMobile } = useResponsive()
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

// ---------- 项目 ----------
const projectDialogVisible = ref(false)
const savingProject = ref(false)
const projectForm = reactive<any>({
  id: null, project_name: '', my_role: '', tech_stack: '', start_date: '', end_date: null,
  is_team: false, team_members: '', project_link: '', attachment_url: '', description: '',
  images: [] as string[],
})

/** 作品墙封面：后端 cover_url 优先，其次第一张图 */
function projectCover(p: StudentProject): string {
  return p.cover_url || (p.images && p.images[0]) || ''
}

async function uploadProjectImage(file: File) {
  if (projectForm.images.length >= 6) { ElMessage.warning('最多上传 6 张图片'); return false }
  try {
    const res = await uploadFile(file)
    projectForm.images.push(res.url)
    ElMessage.success('图片已上传')
  } catch { ElMessage.error('图片上传失败') }
  return false
}

function openProjectDialog(p?: StudentProject) {
  Object.assign(projectForm, p
    ? { ...p, images: Array.isArray(p.images) ? [...p.images] : [] }
    : { id: null, project_name: '', my_role: '', tech_stack: '', start_date: '', end_date: null, is_team: false, team_members: '', project_link: '', attachment_url: '', description: '', images: [] })
  projectDialogVisible.value = true
}

function openProjectDialogForCopy() {
  const p = projects.value.find(x => x.id === aiProjectId.value)
  openProjectDialog(p)
}

async function saveProject() {
  if (!projectForm.project_name.trim()) return ElMessage.warning('请填写项目名称')
  if (!projectForm.start_date) return ElMessage.warning('请选择开始时间')
  savingProject.value = true
  try {
    const payload: any = {
      project_name: projectForm.project_name.trim(),
      start_date: projectForm.start_date,
      end_date: projectForm.end_date || null,
      is_team: !!projectForm.is_team,
      team_members: projectForm.is_team ? projectForm.team_members : null,
      tech_stack: projectForm.tech_stack || null,
      my_role: projectForm.my_role || null,
      project_link: projectForm.project_link || null,
      attachment_url: projectForm.attachment_url || null,
      description: projectForm.description || null,
      images: projectForm.images?.length ? [...projectForm.images] : null,
    }
    if (projectForm.id) await updateProject(projectForm.id, payload)
    else await createProject(payload)
    ElMessage.success('保存成功')
    projectDialogVisible.value = false
    await refreshAll()
  } finally { savingProject.value = false }
}

async function removeProject(p: StudentProject) {
  const ok = await actionConfirm(`确定删除项目「${p.project_name}」吗？`, '删除确认', { danger: true, confirmButtonText: '删除' })
  if (!ok) return
  await deleteProject(p.id)
  ElMessage.success('已删除')
  await refreshAll()
}

// ---------- 证书 ----------
const certDialogVisible = ref(false)
const savingCert = ref(false)
const uploadingImg = ref(false)
const certForm = reactive<any>({
  id: null, title: '', competition_name: '', award_level: '', date: null, description: '', image_url: '',
})

function openCertDialog(c?: Certificate) {
  Object.assign(certForm, c
    ? { ...c }
    : { id: null, title: '', competition_name: '', award_level: '', date: null, description: '', image_url: '' })
  certDialogVisible.value = true
}

async function uploadCertImage(file: File) {
  uploadingImg.value = true
  try {
    const res = await uploadFile(file)
    certForm.image_url = res.url
    ElMessage.success('图片已上传')
  } catch { ElMessage.error('图片上传失败') }
  finally { uploadingImg.value = false }
  return false
}

async function saveCert() {
  if (!certForm.title.trim()) return ElMessage.warning('请填写证书名称')
  savingCert.value = true
  try {
    const payload: any = {
      title: certForm.title.trim(),
      competition_name: certForm.competition_name || null,
      award_level: certForm.award_level || null,
      date: certForm.date || null,
      description: certForm.description || null,
      image_url: certForm.image_url || null,
    }
    if (certForm.id) await updateCertificate(certForm.id, payload)
    else await createCertificate(payload)
    ElMessage.success('保存成功')
    certDialogVisible.value = false
    await refreshAll()
  } finally { savingCert.value = false }
}

async function removeCert(c: Certificate) {
  const ok = await actionConfirm(`确定删除证书「${c.title}」吗？`, '删除确认', { danger: true, confirmButtonText: '删除' })
  if (!ok) return
  await deleteCertificate(c.id)
  ElMessage.success('已删除')
  await refreshAll()
}

// ---------- 简历 ----------
async function beforeUpload(file: File) {
  const ok = await uploadFile(file)
  const payload: any = { filename: ok.filename || file.name, url: ok.url }
  if (file.size) payload.file_size = file.size
  try {
    await createResume(payload)
    ElMessage.success('简历上传成功')
    await refreshAll()
  } catch { ElMessage.error('简历上传失败') }
  return false
}

function previewResume(r: Resume) {
  if (r.url) window.open(r.url, '_blank')
}

async function makeCurrent(r: Resume) {
  await setCurrentResume(r.id)
  ElMessage.success('已设为当前版本')
  await refreshAll()
}

async function removeResume(r: Resume) {
  await ElMessageBox.confirm(`确定删除简历「${r.filename}」吗？`, '删除确认', { type: 'warning' })
  await deleteResume(r.id)
  ElMessage.success('已删除')
  await refreshAll()
}

// ---------- AI 优化建议 ----------
const aiDialogVisible = ref(false)
const aiLoading = ref(false)
const aiProjectId = ref<number | null>(null)
const aiResult = ref<{ description: string; resume_tips: string } | null>(null)

async function openAISuggest() {
  if (!projects.value.length) {
    ElMessage.info('请先添加项目经历，AI 才能基于项目生成优化建议')
    return
  }
  aiDialogVisible.value = true
  aiResult.value = null
  aiProjectId.value = projects.value[0].id
  await genAISuggest()
}

function genAISuggest() {
  aiLoading.value = true
  aiResult.value = null
  const p = projects.value.find(x => x.id === aiProjectId.value)
  if (!p) { aiLoading.value = false; return }
  // 规则式本地生成（STAR 法则），后端无独立 AI 接口时保持可用
  const desc = [
    `围绕「${p.project_name}」完成项目实践`,
    p.my_role ? `，担任${p.my_role}角色` : '',
    p.tech_stack ? `，负责基于 ${splitTags(p.tech_stack).join(' / ')} 的核心功能开发与落地` : '',
    p.is_team && p.team_members ? `（团队协作成员：${p.team_members}）` : '',
    `；项目周期 ${formatDate(p.start_date)} 至 ${p.end_date ? formatDate(p.end_date) : '至今'}`,
    p.description ? `。项目要点：${p.description}` : '。通过需求分析、方案设计与迭代打磨，交付了完整可用的成果，显著提升了工程实践与协作能力。',
  ].join('')
  const tips = [
    '1. 简历中突出「量化成果」：补充项目上线后的用户量、性能提升、代码规模等可量化数据；',
    '2. 使用 STAR 结构描述每段经历（情境-任务-行动-结果），让面试官 30 秒内抓住重点；',
    '3. 技术栈按熟练度排序，与目标岗位 JD 关键词对齐，提升简历筛选命中率；',
    '4. 附上项目链接与演示截图，增强可信度。',
  ].join('\n')
  setTimeout(() => {
    aiResult.value = { description: desc, resume_tips: tips }
    aiLoading.value = false
  }, 400)
}

function copyToProjectForm() {
  if (!aiResult.value) return
  projectDialogVisible.value = true
  if (!projectForm.id) openProjectDialogForCopy()
  projectForm.description = aiResult.value.description
  nextTick(() => {
    ElMessage.success('已填入项目描述，可继续编辑后保存')
  })
}
</script>

<style scoped>
.portfolio-page {
  padding: 16px;
  background: #f8f9fc;
  min-height: 100vh;
  color: #1a1a2e;
}

/* 移动端：整屏覆盖子页（与资讯搜索/详情子页同一形式）——
   滑入/滑出时连顶栏与底部导航一起盖住，返回走页面顶部的 SubPageHeader。
   z-index 1500：盖过顶栏(100)/底部导航(1000)，低于 Element Plus 弹层基准(2000+)，
   页内的下拉/上传等弹出层不受影响。根元素自成滚动容器（原来靠外层裁剪，改后自滚）。 */
@media (max-width: 767px) {
  .portfolio-page {
    position: fixed;
    inset: 0;
    z-index: 1500;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    /* 下拉刷新接管顶部下拉手势，需屏蔽浏览器原生下拉刷新 */
    overscroll-behavior-y: contain;
  }
  .portfolio-page > .tui-appbar {
    position: sticky;
    top: 0;
    left: auto; right: auto;
    z-index: 5;
    margin: 0 -14px 2px;   /* 横向铺满，抵掉页面内边距 */
    padding: 0 14px;
  }
}

.portfolio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.portfolio-title { margin: 0; font-size: 20px; font-weight: 600; color: #1a1a2e; }

.card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.head-bar { width: 3px; height: 14px; background: #409eff; border-radius: 2px; }
.head-title { font-size: 15px; font-weight: 600; color: #1a1a2e; flex: 1; }
.head-badge { margin-right: 4px; }

.empty-tip { color: #999; font-size: 13px; text-align: center; padding: 22px 0; }

/* 项目 */
.project-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.project-head { display: flex; align-items: flex-start; justify-content: space-between; }
.project-title { font-size: 14px; font-weight: 600; color: #1a1a2e; display: flex; align-items: center; gap: 6px; }
.project-actions { display: flex; gap: 0; }
.project-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 6px; font-size: 12px; color: #666; }
.meta-item { display: inline-flex; align-items: center; }
.project-tags { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.tag-item { color: #409eff; }
.project-desc { margin: 8px 0 0; font-size: 13px; color: #444; line-height: 1.6; white-space: pre-wrap; }
.project-links { margin-top: 8px; display: flex; align-items: center; }

/* 证书 */
.cert-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.cert-head { display: flex; align-items: flex-start; justify-content: space-between; }
.cert-title { font-size: 14px; font-weight: 600; color: #1a1a2e; display: flex; align-items: center; gap: 6px; }
.cert-actions { display: flex; gap: 0; }
.cert-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; margin-top: 6px; font-size: 12px; color: #666; }
.cert-desc { margin: 8px 0 0; font-size: 13px; color: #444; line-height: 1.6; }
.cert-img-box { margin-top: 10px; display: flex; align-items: center; gap: 8px; }
.cert-img { width: 96px; height: 68px; border-radius: 8px; border: 1px solid rgba(0, 0, 0, 0.06); }
.cert-img-label { font-size: 12px; color: #999; }

/* 简历 */
.resume-card {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 10px;
}
.resume-current { border-color: rgba(64, 158, 255, 0.5); background: rgba(64, 158, 255, 0.04); }
.resume-info { flex: 1; min-width: 0; }
.resume-name { font-size: 13px; font-weight: 600; color: #1a1a2e; display: flex; align-items: center; gap: 6px; }
.resume-meta { font-size: 12px; color: #999; margin-top: 2px; }
.resume-actions { display: flex; gap: 0; flex-shrink: 0; }

/* 上传 */
.cert-upload-row { display: flex; align-items: center; gap: 10px; }
.uploading-tip { font-size: 12px; color: #999; }
.cert-upload-preview { width: 80px; height: 56px; border-radius: 8px; border: 1px solid rgba(0, 0, 0, 0.06); }

/* 项目多图上传（编辑弹窗，桌面/移动共用） */
.img-upload-wrap { width: 100%; }
.img-upload-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.img-thumb { position: relative; width: 72px; height: 54px; }
.img-thumb-img { width: 100%; height: 100%; border-radius: 8px; border: 1px solid rgba(0, 0, 0, 0.08); }
.img-thumb-del {
  position: absolute; top: -6px; right: -6px;
  width: 18px; height: 18px; border-radius: 50%;
  border: 0; background: rgba(0, 0, 0, 0.55); color: #fff;
  font-size: 10px; line-height: 18px; padding: 0; cursor: pointer;
}
.img-thumb-cover {
  position: absolute; left: 0; right: 0; bottom: 0;
  background: rgba(31, 122, 77, 0.85); color: #fff;
  font-size: 9px; line-height: 15px; text-align: center;
  border-radius: 0 0 8px 8px;
}
.img-add-btn {
  width: 72px; height: 54px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px dashed #c0c4cc; border-radius: 8px;
  background: #fafafa; color: #909399; cursor: pointer;
}
.img-upload-hint { margin: 6px 0 0; font-size: 11px; color: #999; }

/* 作品墙封面（仅移动端渲染，桌面隐藏） */
.project-cover { display: none; }

/* AI 建议 */
.ai-tip { font-size: 12px; color: #999; margin-bottom: 12px; line-height: 1.6; }
.ai-result { margin-top: 14px; }
.ai-result-label { font-size: 13px; font-weight: 600; color: #1a1a2e; margin-bottom: 6px; }
.ai-result-label2 { margin-top: 14px; }
.ai-result-text {
  font-size: 13px; color: #444; line-height: 1.7;
  background: #f5f7fb; border-radius: 8px; padding: 10px 12px;
  margin-bottom: 8px; white-space: pre-wrap;
}

/* ===== 作品集 v5（仅移动端）：GitHub Profile Pinned 仓库卡风 =====
   参考：GitHub 个人主页置顶仓库卡 —— 蓝色仓库名 + 空心 repo 图标 + 描述 +
   语言色点/star/更新时间 元信息行。扁平分区，无大标题重复（顶部 Head 已有标题）。 */
@media (max-width: 767px) {
  .portfolio-page {
    background: var(--sp-bg, #f5f6f7);
    /* Head 是 sticky 且在文档流内，自己占 48px；这里不再额外让位，否则顶部会多出一条白带 */
    padding: 0 14px 24px;
    min-height: 100vh;
    box-sizing: border-box;
  }

  /* 顶部操作行：整块隐藏 —— 标题归 Head，AI 按钮已移到 Head 右侧 */
  .portfolio-header { display: none; }

  /* Head 右侧 AI 图标按钮：与 Head 同色系的幽灵按钮，不抢视觉 */
  .pf-ai-btn {
    width: 30px; height: 30px;
    display: inline-flex; align-items: center; justify-content: center;
    border: 0; border-radius: 8px; padding: 0;
    background: transparent; color: var(--sp-ink-2, #5b6470);
    cursor: pointer; -webkit-tap-highlight-color: transparent;
    transition: background .18s ease;
  }
  .pf-ai-btn:active { background: rgba(20, 23, 26, .06); }
  .pf-ai-btn:focus-visible { outline: 2px solid #b45309; outline-offset: 1px; }
  .pf-ai-btn:disabled { opacity: .5; }

  /* 分区：全部透明，靠发丝线与小标题分区 */
  .portfolio-page .card {
    background: transparent;
    border: 0;
    box-shadow: none;
    border-radius: 0;
    padding: 0;
    margin: 0;
  }
  .portfolio-page .card + .card { margin-top: 6px; }
  .portfolio-page .card-head {
    padding: 14px 2px 8px;
    margin: 0;
  }
  .portfolio-page .card-head .head-bar { display: none; }
  .portfolio-page .card-head .head-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--sp-ink-2, #5b6472);
  }
  /* 计数徽标在扁平分区里会顶着标题行浮出来，移动端隐藏（条数看列表即可） */
  .portfolio-page .card-head :deep(.el-badge__content) { display: none; }
  .portfolio-page .card-head :deep(.el-badge) { display: inline-flex; }
  .portfolio-page .card-head .el-button--primary.is-text {
    font-size: 12.5px;
    padding: 0;
    height: auto;
  }

  /* ===== Behance 风作品墙：两列封面网格，标题压在封面底部渐变上 ===== */
  .portfolio-page .projects-wall {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 9px;
  }
  .portfolio-page .project-card {
    background: transparent;
    border: 0;
    border-radius: 0;
    padding: 0;
    margin: 0;
  }
  /* 桌面列表卡内容整体让位给封面 */
  .portfolio-page .project-card > .project-head,
  .portfolio-page .project-card > .project-meta,
  .portfolio-page .project-card > .project-tags,
  .portfolio-page .project-card > .project-desc,
  .portfolio-page .project-card > .project-links { display: none; }

  .portfolio-page .project-cover {
    display: block;
    position: relative;
    aspect-ratio: 4 / 5;
    border-radius: 14px;
    overflow: hidden;
    background: #eef1f4;
  }
  .portfolio-page .project-cover-img { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  .portfolio-page .project-cover-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
  /* 无图项目：同比例浅绿渐变 + 首字占位，保证墙面对齐 */
  .portfolio-page .project-cover-fallback {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #e3f1ea 0%, #c9e4d7 100%);
  }
  .portfolio-page .project-cover-fallback span { font-size: 30px; font-weight: 700; color: rgba(31, 122, 77, 0.45); }
  .portfolio-page .project-cover-grad {
    position: absolute; left: 0; right: 0; bottom: 0; height: 46%;
    background: linear-gradient(180deg, rgba(10, 14, 12, 0) 0%, rgba(10, 14, 12, 0.62) 100%);
  }
  .portfolio-page .project-cover-badge {
    position: absolute; top: 8px; left: 8px;
    padding: 2px 7px; border-radius: 999px;
    background: rgba(12, 16, 14, 0.55); color: #fff;
    font-size: 10px; line-height: 14px;
    backdrop-filter: blur(4px);
  }
  .portfolio-page .project-cover-txt { position: absolute; left: 10px; right: 10px; bottom: 9px; color: #fff; }
  .portfolio-page .project-cover-txt b {
    display: block; font-size: 12.5px; font-weight: 600; line-height: 17px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .portfolio-page .project-cover-txt i {
    display: block; margin-top: 2px; font-style: normal; font-size: 10px; line-height: 14px;
    color: rgba(255, 255, 255, 0.78);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .portfolio-page .project-cover-acts { position: absolute; top: 6px; right: 6px; display: flex; gap: 4px; }
  .portfolio-page .project-cover-acts button {
    padding: 3px 8px;
    border: 0; border-radius: 999px;
    background: rgba(255, 255, 255, 0.92); color: #1f7a4d;
    font-size: 10.5px; font-weight: 600; line-height: 14px;
    cursor: pointer; -webkit-tap-highlight-color: transparent;
  }
  .portfolio-page .project-cover-acts button:active { opacity: 0.75; }

  /* 证书卡：同语言，标题不用蓝色（非仓库） */
  .portfolio-page .cert-card {
    background: var(--sp-surface, #fff);
    border: 1px solid #e4e7eb;
    border-radius: 12px;
    box-shadow: none;
    padding: 12px 14px 13px;
    margin: 0 0 8px;
  }
  .portfolio-page .cert-title { font-size: 13.5px; font-weight: 600; color: var(--sp-ink, #14171a); }
  .portfolio-page .cert-meta { margin-top: 5px; font-size: 11px; color: #9aa0a8; }

  /* 简历管理已抽至「我的资料」页（ProfilePage），移动端整块隐藏 */
  .portfolio-page .card.resume-section { display: none; }

  .portfolio-page .empty-tip {
    padding: 16px 2px;
    font-size: 12px;
    color: #9aa0a8;
  }
}
</style>