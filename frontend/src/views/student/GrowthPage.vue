<template>
  <div class="growth-page">
    <div class="score-header">
      <div class="score-ring">
        <svg viewBox="0 0 120 120" class="score-svg">
          <circle cx="60" cy="60" r="52" fill="none" stroke="#f0f2f5" stroke-width="8" />
          <circle cx="60" cy="60" r="52" fill="none" stroke="url(#scoreGrad)" stroke-width="8"
            :stroke-dasharray="circleLen" :stroke-dashoffset="circleOffset" stroke-linecap="round"
            transform="rotate(-90, 60, 60)" />
          <defs><linearGradient id="scoreGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#409eff" /><stop offset="100%" stop-color="#67c23a" />
          </linearGradient></defs>
        </svg>
        <div class="score-center">
          <div class="score-value">{{ profile?.total_score ?? '--' }}</div>
          <div class="score-label">综合评分</div>
        </div>
      </div>
      <div class="score-stats">
        <div class="stat-item" v-for="s in statsCards" :key="s.label">
          <span class="stat-num">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-card-header"><el-icon style="margin-right:6px"><DataAnalysis /></el-icon> 综合能力雷达</div>
        <v-chart :option="radarOption" class="chart" autoresize />
      </div>
      <div class="chart-card">
        <div class="chart-card-header"><el-icon style="margin-right:6px"><Histogram /></el-icon> 成长类型分布</div>
        <v-chart :option="barOption" class="chart" autoresize />
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card wide">
        <div class="chart-card-header"><el-icon style="margin-right:6px"><TrendCharts /></el-icon> 成长趋势</div>
        <v-chart :option="lineOption" class="chart" autoresize />
      </div>
      <div class="chart-card wide">
        <div class="chart-card-header"><el-icon style="margin-right:6px"><DataLine /></el-icon> 学习绩点轨迹</div>
        <v-chart :option="gpaOption" class="chart" autoresize />
      </div>
    </div>

    <div class="split-row">
      <div class="tag-card">
        <div class="tag-card-header">
          <span><el-icon style="margin-right:6px"><Coin /></el-icon> 技能标签</span>
          <el-button size="small" type="primary" plain @click="saveSkills">保存</el-button>
        </div>
        <div class="preset-tags">
          <el-tag v-for="p in skillPresets" :key="p"
            :type="localSkills.includes(p) ? 'primary' : 'info'"
            :effect="localSkills.includes(p) ? 'dark' : 'plain'"
            class="preset-tag" @click="toggleSkill(p)">
            {{ p }}
          </el-tag>
        </div>
        <div class="tag-cloud">
          <el-tag v-for="s in localSkills" :key="s" closable :type="skillPresets.includes(s) ? 'primary' : 'warning'"
            @close="removeSkill(s)" class="skill-tag">{{ s }}</el-tag>
        </div>
        <div class="tag-input-row">
          <el-input v-model="newSkill" placeholder="自定义技能" size="small" @keyup.enter="addCustomSkill" />
          <el-button size="small" type="primary" @click="addCustomSkill">添加</el-button>
        </div>
      </div>
      <div class="tag-card">
        <div class="tag-card-header">
          <span><el-icon style="margin-right:6px"><Star /></el-icon> 兴趣领域</span>
          <el-button size="small" type="primary" plain @click="saveSkills">保存</el-button>
        </div>
        <div class="preset-tags">
          <el-tag v-for="p in interestPresets" :key="p"
            :type="localInterests.includes(p) ? 'success' : 'info'"
            :effect="localInterests.includes(p) ? 'dark' : 'plain'"
            class="preset-tag" @click="toggleInterest(p)">
            {{ p }}
          </el-tag>
        </div>
        <div class="tag-cloud">
          <el-tag v-for="s in localInterests" :key="s" closable :type="interestPresets.includes(s) ? 'success' : 'warning'"
            @close="removeInterest(s)" class="skill-tag">{{ s }}</el-tag>
        </div>
        <div class="tag-input-row">
          <el-input v-model="newInterest" placeholder="自定义兴趣" size="small" @keyup.enter="addCustomInterest" />
          <el-button size="small" type="primary" @click="addCustomInterest">添加</el-button>
        </div>
      </div>
    </div>

    <div class="records-section">
      <div class="section-header clickable" @click="recordsExpanded = !recordsExpanded">
        <span class="header-left">
          <el-icon class="collapse-icon" :class="{ collapsed: !recordsExpanded }"><ArrowRight /></el-icon>
          <el-icon style="margin-right:6px"><Collection /></el-icon>
          成长记录
          <el-tag v-if="records.length" size="small" type="info" effect="plain" style="margin-left:8px">{{ records.length }}</el-tag>
        </span>
        <el-button type="primary" size="small" @click.stop="openDialog">添加记录</el-button>
      </div>
      <Transition name="collapse">
        <div v-show="recordsExpanded">
          <div v-if="records.length" class="records-list">
        <div v-for="r in records" :key="r.id" class="record-card">
          <div class="record-left">
            <div class="record-dot" :style="{ background: dotColor(r.type) }"></div>
            <div class="record-line"></div>
          </div>
          <div class="record-body">
            <div class="record-top">
              <el-tag :type="typeTagType(r.type)" size="small" effect="dark" round>{{ typeLabel(r.type) }}</el-tag>
              <span class="record-date">{{ formatDate(r.date) }}</span>
            </div>
            <div class="record-title">{{ r.title }}</div>
            <div class="record-meta" v-if="r.description">{{ r.description }}</div>
            <div class="record-details" v-if="r.type === 'honor' && r.honor_level">
              <el-tag size="small" hit effect="plain">{{ r.honor_level }}</el-tag>
            </div>
            <div class="record-details" v-else-if="r.type === 'competition'">
              <span v-if="r.organizer" class="detail-item">主办方: {{ r.organizer }}</span>
              <span v-if="r.competition_level" class="detail-item">等级: {{ r.competition_level }}</span>
            </div>
            <div class="record-details" v-else-if="r.type === 'practice' && r.practice_type">
              <span class="detail-item">{{ r.practice_type }}</span>
            </div>
            <div class="record-details" v-else-if="r.type === 'paper'">
              <span v-if="r.paper_name" class="detail-item">{{ r.paper_name }}</span>
              <span v-if="r.paper_type" class="detail-item">[{{ r.paper_type }}]</span>
            </div>
            <div class="record-details" v-else-if="r.type === 'achievement'">
              <span v-if="r.achievement_name" class="detail-item">{{ r.achievement_name }}</span>
              <span v-if="r.achievement_type" class="detail-item">[{{ r.achievement_type }}]</span>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无成长记录" />
        </div>
      </Transition>
    </div>

    <div class="projects-section">
      <div class="section-header clickable" @click="projectsExpanded = !projectsExpanded">
        <span class="header-left">
          <el-icon class="collapse-icon" :class="{ collapsed: !projectsExpanded }"><ArrowRight /></el-icon>
          <el-icon style="margin-right:6px"><FolderOpened /></el-icon>
          项目展示
          <el-tag v-if="projects.length" size="small" type="info" effect="plain" style="margin-left:8px">{{ projects.length }}</el-tag>
        </span>
        <el-button type="primary" size="small" @click.stop="openProjectDialog">添加项目</el-button>
      </div>
      <Transition name="collapse">
        <div v-show="projectsExpanded">
          <div v-if="projects.length" class="project-grid">
        <div v-for="p in projects" :key="p.id" class="project-card">
          <div class="project-top">
            <div class="project-icon" :class="p.is_team ? 'team' : 'solo'">
              <el-icon :size="22"><UserFilled v-if="p.is_team" /><User v-else /></el-icon>
            </div>
            <div class="project-info">
              <div class="project-name">{{ p.project_name }}</div>
              <div class="project-date">{{ p.start_date }} ~ {{ p.end_date || '至今' }}</div>
            </div>
          </div>
          <div v-if="p.is_team && p.team_members" class="project-members">成员: {{ p.team_members }}</div>
          <div v-if="p.attachment_url" class="project-attach">
            <el-link type="primary" :href="p.attachment_url" target="_blank" :icon="Link">查看附件</el-link>
          </div>
          <div class="project-actions">
            <el-button size="small" text type="primary" @click="editProject(p)">编辑</el-button>
            <el-button size="small" text type="danger" @click="handleDeleteProject(p.id)">删除</el-button>
          </div>
        </div>
      </div>
      <el-empty v-else-if="loaded" description="暂无项目" :image-size="60" />
        </div>
      </Transition>
    </div>

    <el-dialog v-model="projectDialogVisible" :title="editingProject ? '编辑项目' : '添加项目'" width="500px">
      <el-form :model="projectForm" label-width="100px">
        <el-form-item label="项目名称">
          <el-input v-model="projectForm.project_name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始日期">
              <el-date-picker v-model="projectForm.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="projectForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" clearable />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="是否团队">
          <el-switch v-model="projectForm.is_team" />
        </el-form-item>
        <el-form-item v-if="projectForm.is_team" label="团队成员">
          <el-input v-model="projectForm.team_members" placeholder="逗号分隔，如：张三, 李四, 王五" />
        </el-form-item>
        <el-form-item label="项目成果">
          <UploadBtn v-model="projectForm.attachment_url" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveProject">{{ editingProject ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="'添加成长记录 — ' + typeLabel(form.type)" width="600px" class="growth-dialog">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="类型">
              <el-select v-model="form.type" @change="onTypeChange">
                <el-option label="荣誉" value="honor" />
                <el-option label="竞赛" value="competition" />
                <el-option label="实践" value="practice" />
                <el-option label="论文" value="paper" />
                <el-option label="成果" value="achievement" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="日期">
              <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <template v-if="form.type === 'honor'">
          <el-form-item label="荣誉等级">
            <el-select v-model="form.honor_level" style="width:100%">
              <el-option label="校级" value="校级" />
              <el-option label="省级" value="省级" />
              <el-option label="国家级" value="国家级" />
              <el-option label="国际级" value="国际级" />
            </el-select>
          </el-form-item>
          <el-form-item label="荣誉名称">
            <el-input v-model="form.title" placeholder="例如：国家奖学金" />
          </el-form-item>
          <el-form-item label="荣誉描述">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="颁发单位、获奖时间等" />
          </el-form-item>
          <el-form-item label="证明材料">
            <UploadBtn v-model="form.attachment_url" />
          </el-form-item>
        </template>

        <template v-if="form.type === 'competition'">
          <el-form-item label="竞赛名称">
            <el-input v-model="form.title" placeholder="例如：ACM-ICPC国际大学生程序设计竞赛" />
          </el-form-item>
          <el-form-item label="主办方">
            <el-input v-model="form.organizer" placeholder="例如：ACM/ICPC组委会" />
          </el-form-item>
          <el-form-item label="竞赛等级">
            <el-select v-model="form.competition_level" style="width:100%">
              <el-option label="校级" value="校级" />
              <el-option label="省级" value="省级" />
              <el-option label="国家级" value="国家级" />
              <el-option label="国际级" value="国际级" />
            </el-select>
          </el-form-item>
          <el-form-item label="获奖情况">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="金奖/银奖/铜奖/一等奖等" />
          </el-form-item>
          <el-form-item label="证明材料">
            <UploadBtn v-model="form.attachment_url" />
          </el-form-item>
        </template>

        <template v-if="form.type === 'practice'">
          <el-form-item label="实践类型">
            <el-select v-model="form.practice_type" style="width:100%">
              <el-option label="社会志愿活动" value="社会志愿活动" />
              <el-option label="三下乡" value="三下乡" />
              <el-option label="支教" value="支教" />
              <el-option label="西部计划" value="西部计划" />
              <el-option label="筑梦扬帆计划" value="筑梦扬帆计划" />
              <el-option label="其他社会实践" value="其他社会实践" />
            </el-select>
          </el-form-item>
          <el-form-item label="实践名称">
            <el-input v-model="form.title" placeholder="例如：暑期三下乡支教活动" />
          </el-form-item>
          <el-form-item label="实践描述">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="实践内容、服务时长等" />
          </el-form-item>
          <el-form-item label="荣誉证明">
            <el-input v-model="form.practice_certificate" type="textarea" :rows="2" placeholder="优秀志愿者证书/表彰文件等" />
          </el-form-item>
          <el-form-item label="证明材料">
            <UploadBtn v-model="form.attachment_url" />
          </el-form-item>
        </template>

        <template v-if="form.type === 'paper'">
          <el-form-item label="论文题目">
            <el-input v-model="form.paper_name" placeholder="论文完整标题" />
          </el-form-item>
          <el-form-item label="期刊类型">
            <el-select v-model="form.paper_type" style="width:100%">
              <el-option label="普刊" value="普刊" />
              <el-option label="核心期刊" value="核心期刊" />
              <el-option label="SCI" value="SCI" />
              <el-option label="EI" value="EI" />
              <el-option label="顶刊" value="顶刊" />
              <el-option label="会议论文" value="会议论文" />
            </el-select>
          </el-form-item>
          <el-form-item label="第一作者">
            <el-input v-model="form.first_author" placeholder="姓名" />
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="第二作者">
                <el-input v-model="form.second_author" placeholder="姓名（选填）" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="第三作者">
                <el-input v-model="form.third_author" placeholder="姓名（选填）" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="备注">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="发表时间、期刊名称等" />
          </el-form-item>
          <el-form-item label="证明材料">
            <UploadBtn v-model="form.attachment_url" />
          </el-form-item>
        </template>

        <template v-if="form.type === 'achievement'">
          <el-form-item label="成果类型">
            <el-select v-model="form.achievement_type" style="width:100%">
              <el-option label="发明专利" value="发明专利" />
              <el-option label="实用新型专利" value="实用新型专利" />
              <el-option label="外观设计专利" value="外观设计专利" />
              <el-option label="软件著作权" value="软件著作权" />
              <el-option label="作品著作权" value="作品著作权" />
            </el-select>
          </el-form-item>
          <el-form-item label="成果名称">
            <el-input v-model="form.achievement_name" placeholder="专利/软著名称" />
          </el-form-item>
          <el-form-item label="成果标题">
            <el-input v-model="form.title" placeholder="简短标题（可选）" />
          </el-form-item>
          <el-form-item label="成果描述">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="授权号、申请日等信息" />
          </el-form-item>
          <el-form-item label="证明材料">
            <UploadBtn v-model="form.attachment_url" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { DataAnalysis, Histogram, TrendCharts, DataLine, Coin, Star, Collection, FolderOpened, Link, User, UserFilled, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { RadarChart, BarChart, LineChart } from 'echarts/charts'
import { GridComponent, RadarComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getGrowthRecords, createGrowthRecord, getGrowthProfile, updateSkills, getProjects, createProject, updateProject, deleteProject } from '@/api/growth'
import type { GrowthProfile, StudentProject } from '@/api/growth'
import type { GrowthRecord } from '@/types'
import UploadBtn from '@/components/upload/UploadBtn.vue'

use([RadarChart, BarChart, LineChart, GridComponent, RadarComponent, TooltipComponent, LegendComponent, CanvasRenderer])

// 预设选项
const skillPresets = ['编程开发', 'UI/UX设计', '数据分析', '人工智能', '项目管理', '产品设计', '视频剪辑', '摄影', '写作', '翻译', '演讲', '团队协作', '领导力']
const interestPresets = ['音乐', '运动', '阅读', '游戏', '旅行', '美食', '电影', '摄影', '绘画', '舞蹈', '编程', '创业', '公益']

// 个人档案
const profile = ref<GrowthProfile | null>(null)
const records = ref<GrowthRecord[]>([])
const recordsExpanded = ref(false)
const projectsExpanded = ref(false)
const dialogVisible = ref(false)
const form = ref<Record<string, any>>({ type: 'honor', title: '', description: '', date: '' })

// 技能编辑
const localSkills = ref<string[]>([])
const localInterests = ref<string[]>([])
const newSkill = ref('')
const newInterest = ref('')

function toggleSkill(s: string) {
  const idx = localSkills.value.indexOf(s)
  if (idx >= 0) localSkills.value.splice(idx, 1)
  else localSkills.value.push(s)
}

function removeSkill(s: string) {
  localSkills.value = localSkills.value.filter(x => x !== s)
}

function addCustomSkill() {
  const s = newSkill.value.trim()
  if (!s) return
  if (!localSkills.value.includes(s)) localSkills.value.push(s)
  newSkill.value = ''
}

function toggleInterest(s: string) {
  const idx = localInterests.value.indexOf(s)
  if (idx >= 0) localInterests.value.splice(idx, 1)
  else localInterests.value.push(s)
}

function removeInterest(s: string) {
  localInterests.value = localInterests.value.filter(x => x !== s)
}

function addCustomInterest() {
  const s = newInterest.value.trim()
  if (!s) return
  if (!localInterests.value.includes(s)) localInterests.value.push(s)
  newInterest.value = ''
}

async function saveSkills() {
  try {
    await updateSkills({ skills: localSkills.value, interests: localInterests.value })
    ElMessage.success('技能/兴趣已保存')
    profile.value = await getGrowthProfile()
  } catch { ElMessage.error('保存失败') }
}

// 项目
const projects = ref<StudentProject[]>([])
const loaded = ref(false)
const projectDialogVisible = ref(false)
const editingProject = ref<StudentProject | null>(null)
const projectForm = ref<Record<string, any>>({
  project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '',
})

function openProjectDialog() {
  editingProject.value = null
  projectForm.value = { project_name: '', start_date: '', end_date: null, is_team: false, team_members: '', attachment_url: '' }
  projectDialogVisible.value = true
}

function editProject(p: StudentProject) {
  editingProject.value = p
  projectForm.value = { ...p }
  projectDialogVisible.value = true
}

async function handleSaveProject() {
  try {
    if (editingProject.value) {
      await updateProject(editingProject.value.id, projectForm.value as any)
      ElMessage.success('项目已更新')
    } else {
      await createProject(projectForm.value as any)
      ElMessage.success('项目已添加')
    }
    projectDialogVisible.value = false
    projects.value = await getProjects()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function handleDeleteProject(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该项目？', '确认')
    await deleteProject(id)
    ElMessage.success('已删除')
    projects.value = await getProjects()
  } catch {}
}

// 成长记录表单
function typeLabel(t: string) {
  const labels: Record<string, string> = { honor: '荣誉', competition: '竞赛', practice: '实践', paper: '论文', achievement: '成果' }
  return labels[t] || t
}

function typeTagType(t: string) {
  const types: Record<string, string> = { honor: 'warning', competition: 'primary', practice: 'success', paper: 'danger', achievement: 'info' }
  return types[t] || 'default'
}

function dotColor(t: string) {
  const colors: Record<string, string> = { honor: '#e6a23c', competition: '#409eff', practice: '#67c23a', paper: '#f56c6c', achievement: '#909399' }
  return colors[t] || '#bbb'
}

function formatDate(d: string) {
  if (!d) return ''
  return d.slice(0, 10)
}

function onTypeChange() {
  form.value.title = ''
  form.value.description = ''
  form.value.honor_level = ''
  form.value.organizer = ''
  form.value.competition_level = ''
  form.value.practice_type = ''
  form.value.practice_certificate = ''
  form.value.paper_type = ''
  form.value.paper_name = ''
  form.value.first_author = ''
  form.value.second_author = ''
  form.value.third_author = ''
  form.value.achievement_type = ''
  form.value.achievement_name = ''
}

function openDialog() {
  onTypeChange()
  dialogVisible.value = true
}

const circleLen = 2 * Math.PI * 52

const circleOffset = computed(() => {
  if (!profile.value) return circleLen
  return circleLen - (circleLen * Math.min(100, profile.value.total_score) / 100)
})

const statsCards = computed(() => [
  { label: '成长记录', value: profile.value?.total_records ?? 0 },
  { label: '技能数量', value: profile.value?.total_skills ?? 0 },
  { label: '荣誉', value: profile.value?.stats_by_type.find(s => s.name === '荣誉')?.value ?? 0 },
  { label: '竞赛', value: profile.value?.stats_by_type.find(s => s.name === '竞赛')?.value ?? 0 },
  { label: '实践', value: profile.value?.stats_by_type.find(s => s.name === '实践')?.value ?? 0 },
  { label: '论文', value: profile.value?.stats_by_type.find(s => s.name === '论文')?.value ?? 0 },
  { label: '成果', value: profile.value?.stats_by_type.find(s => s.name === '成果')?.value ?? 0 },
])

const radarOption = computed(() => ({
  radar: {
    indicator: (profile.value?.radar ?? []).map(d => ({ name: d.name, max: 100 })),
    shape: 'circle',
    center: ['50%', '50%'],
    radius: '65%',
    axisName: { color: '#333', fontSize: 12 },
    splitArea: { areaStyle: { color: ['rgba(64,158,255,.03)', 'rgba(64,158,255,.06)'] } },
  },
  series: [{
    type: 'radar',
    data: [{ value: profile.value?.radar.map(d => d.value) ?? [0, 0, 0, 0, 0] }],
    areaStyle: { color: 'rgba(64,158,255,.2)' },
    lineStyle: { color: '#409eff', width: 2 },
    itemStyle: { color: '#409eff' },
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
    animationDelay: function(idx: number) {
      return idx * 100;
    }
  }],
  animationDuration: 2000,
  animationEasing: 'cubicOut' as const,
}))

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 55, right: 20, top: 20, bottom: 40 },
  xAxis: {
    type: 'category',
    data: (profile.value?.stats_by_type ?? []).map(s => s.name),
    name: '成长类型',
    nameLocation: 'center',
    nameGap: 25,
    axisLabel: { color: '#666' },
  },
  yAxis: { type: 'value', name: '数量', nameLocation: 'center', nameGap: 35, minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
  series: [{
    type: 'bar',
    data: (profile.value?.stats_by_type ?? []).map(s => s.value),
    barWidth: '40%',
    itemStyle: {
      borderRadius: [6, 6, 0, 0],
      color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#409eff' }, { offset: 1, color: '#67c23a' }] },
    },
    animationDuration: 1500,
    animationEasing: 'elasticOut' as const,
    animationDelay: function(idx: number) {
      return idx * 200;
    }
  }],
  animationDuration: 1500,
  animationEasing: 'cubicOut' as const,
}))

const lineOption = computed(() => {
  const trend = profile.value?.monthly_trend ?? []
  const months = [...new Set(trend.map(t => t.month))].sort()
  const types = [...new Set(trend.map(t => t.type))]
  const colors: Record<string, string> = { honor: '#e6a23c', competition: '#409eff', practice: '#67c23a', paper: '#f56c6c', achievement: '#909399' }
  const typeLabels: Record<string, string> = { honor: '荣誉', competition: '竞赛', practice: '实践', paper: '论文', achievement: '成果' }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: types.map(t => typeLabels[t] || t), bottom: 0 },
    grid: { left: 55, right: 20, top: 20, bottom: 65 },
    xAxis: { type: 'category', data: months, name: '月份', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666' } },
    yAxis: { type: 'value', name: '记录数', nameLocation: 'center', nameGap: 35, minInterval: 1, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: types.map(t => ({
      name: typeLabels[t] || t,
      type: 'line',
      smooth: true,
      data: months.map(m => trend.find(item => item.month === m && item.type === t)?.count ?? 0),
      itemStyle: { color: colors[t] || '#909399' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: (colors[t] || '#909399') + '40' }, { offset: 1, color: (colors[t] || '#909399') + '05' }] } },
      animationDuration: 2000,
      animationEasing: 'cubicOut' as const,
      animationDelay: function(idx: number) {
        return idx * 100;
      }
    })),
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
  }
})

const gpaOption = computed(() => {
  const data = profile.value?.gpa_trend ?? []
  if (!data.length) return {}
  const semLabels = data.map(d => d.semester.replace('2023-2024-1', '23-24 上').replace('2023-2024-2', '23-24 下').replace('2024-2025-1', '24-25 上').replace('2024-2025-2', '24-25 下'))
  const values = data.map(d => d.gpa)
  const minGpa = Math.max(0, Math.floor(Math.min(...values) * 10) / 10 - 0.3)
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>平均绩点: ${p[0].value}` },
    grid: { left: 55, right: 60, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: semLabels, name: '学期', nameLocation: 'center', nameGap: 25, axisLabel: { color: '#666', fontSize: 13 } },
    yAxis: { type: 'value', min: minGpa, max: 4.0, name: '绩点', nameLocation: 'center', nameGap: 35, axisLabel: { color: '#666' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series: [{
      type: 'line', data: values, smooth: true,
      symbol: 'circle', symbolSize: 10,
      lineStyle: { color: '#e6a23c', width: 3 },
      itemStyle: { color: '#e6a23c' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#e6a23c40' }, { offset: 1, color: '#e6a23c05' }] } },
      markLine: { data: [{ yAxis: 3.5, label: { formatter: '优秀线 3.5', color: '#67c23a' } }, { yAxis: 2.5, label: { formatter: '警戒线 2.5', color: '#f56c6c' } }], silent: true, lineStyle: { type: 'dashed' } },
      animationDuration: 2000,
      animationEasing: 'cubicOut' as const,
      animationDelay: function(idx: number) {
        return idx * 200;
      }
    }],
    animationDuration: 2000,
    animationEasing: 'cubicOut' as const,
  }
})

onMounted(async () => {
  try {
    const p = await getGrowthProfile()
    profile.value = p
    localSkills.value = [...(p.skills || [])]
    localInterests.value = [...(p.interests || [])]
  } catch { /* ignore */ }
  records.value = await getGrowthRecords() as any
  try { projects.value = await getProjects(); loaded.value = true } catch { /* ignore */ }
})

async function handleAdd() {
  const payload: Record<string, any> = {}
  for (const k of Object.keys(form.value)) {
    if (form.value[k] !== '' && form.value[k] !== undefined) {
      payload[k] = form.value[k]
    }
  }
  try {
    await createGrowthRecord(payload as any)
    ElMessage.success('添加成功')
    dialogVisible.value = false
    records.value = await getGrowthRecords() as any
    profile.value = await getGrowthProfile() as any
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  }
}
</script>

<style scoped>
.growth-page { 
  max-width: 1200px; 
  margin: 0 auto; 
  padding: 4px 0 24px; 
  height: 100%; 
  overflow-y: auto; 
  box-sizing: border-box; 
  scrollbar-width: none; 
  -ms-overflow-style: none;
  animation: fadeInUp 0.35s ease-out;
}
.growth-page::-webkit-scrollbar { display: none; }

/* 动画工具类 (fadeInUp/scaleIn/pulse 等) 已统一在全局 styles/animations.css 中定义，此处直接引用 */
.score-header {
  display: flex; align-items: center; gap: 36px;
  padding: 20px 28px; margin-bottom: 20px;
  background: var(--gradient-card);
  border-radius: 16px; border: 1px solid var(--border-color);
  animation: fadeInUp 0.35s ease-out;
}
.score-ring { 
  position: relative; 
  width: 110px; 
  height: 110px; 
  flex-shrink: 0;
  animation: scaleIn 0.8s ease-out;
}
.score-svg { 
  width: 110px; 
  height: 110px;
  display: block;
}
.score-center {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.score-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent-blue);
  animation: pulse 2s ease-in-out infinite;
  line-height: 1;
}
.score-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}
.score-stats { display: flex; gap: 28px; flex: 1; flex-wrap: wrap; }
.stat-item { 
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  min-width: 56px;
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.3s ease-out forwards;
}
.stat-item:nth-child(1) { animation-delay: 0.05s; }
.stat-item:nth-child(2) { animation-delay: 0.1s; }
.stat-item:nth-child(3) { animation-delay: 0.15s; }
.stat-item:nth-child(4) { animation-delay: 0.2s; }
.stat-item:nth-child(5) { animation-delay: 0.25s; }
.stat-item:nth-child(6) { animation-delay: 0.3s; }
.stat-item:nth-child(7) { animation-delay: 0.35s; }
.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  transition: all 0.15s ease;
}
.stat-item:hover .stat-num {
  transform: scale(1.1);
  color: var(--accent-blue);
}
.stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* ===== Charts Row ===== */
.charts-row { display: flex; gap: 16px; margin-bottom: 16px; }
.chart-card {
  flex: 1; background: var(--bg-card); border-radius: 14px; padding: 18px 20px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-md);
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.35s ease-out forwards;
}
.chart-card:nth-child(1) { animation-delay: 0.1s; }
.chart-card:nth-child(2) { animation-delay: 0.15s; }
.chart-card.wide { flex: 1; }
.chart-card-header {
  font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px;
  display: flex; align-items: center;
}
.chart { 
  width: 100%; 
  height: 250px;
  animation: scaleIn 0.8s ease-out;
  animation-delay: 0.4s;
  animation-fill-mode: both;
}
.chart-card.wide .chart { height: 200px; }

/* ===== Split Row (Skills + Interests) ===== */
.split-row { display: flex; gap: 16px; margin-bottom: 20px; }
.tag-card {
  flex: 1; background: var(--bg-card); border-radius: 14px; padding: 18px 20px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-md);
  opacity: 0;
  transform: translateX(-20px);
  animation: fadeInLeft 0.35s ease-out forwards;
}
.tag-card:nth-child(1) { animation-delay: 0.15s; }
.tag-card:nth-child(2) { 
  animation-name: fadeInRight;
  animation-delay: 0.2s;
}
.tag-card-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px; font-size: 14px; font-weight: 600; color: var(--text-primary);
}
.preset-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.preset-tag { 
  cursor: pointer; 
  font-size: 12px;
  transition: all 0.2s ease;
}
.preset-tag:hover {
  transform: scale(1.05);
}
.preset-tag:active {
  transform: scale(0.95);
}
.tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.skill-tag { 
  font-size: 12px; 
  padding: 3px 12px; 
  border-radius: 16px;
  transition: all 0.2s ease;
}
.skill-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.tag-input-row { display: flex; gap: 8px; }

/* ===== Section ===== */
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; font-size: 15px; font-weight: 600; color: var(--text-primary);
}
.section-header.clickable {
  cursor: pointer;
  padding: 10px 16px;
  border-radius: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
  margin-bottom: 12px;
}
.section-header.clickable:hover {
  background: var(--hover-bg, #f5f7fa);
  border-color: var(--accent-blue, #409eff);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 2px;
}
.collapse-icon {
  transition: transform 0.15s ease;
  font-size: 14px;
  margin-right: 4px;
}
.collapse-icon.collapsed {
  transform: rotate(0deg);
}
.collapse-icon:not(.collapsed) {
  transform: rotate(90deg);
}

/* Collapse transition */
.collapse-enter-active, .collapse-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.collapse-enter-from, .collapse-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-8px);
}
.collapse-enter-to, .collapse-leave-from {
  opacity: 1;
  max-height: 2000px;
  transform: translateY(0);
}

/* ===== Records (Timeline Style) ===== */
.records-section { margin-bottom: 24px; }
.records-list { display: flex; flex-direction: column; gap: 0; position: relative; }
.record-card {
  display: flex; gap: 16px; padding: 14px 18px;
  background: var(--bg-card); border-radius: 12px; margin-bottom: 8px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-sm);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0;
  transform: translateY(20px);
  animation: fadeInUp 0.35s ease-out forwards;
}
.record-card:nth-child(1) { animation-delay: 0.05s; }
.record-card:nth-child(2) { animation-delay: 0.1s; }
.record-card:nth-child(3) { animation-delay: 0.15s; }
.record-card:nth-child(4) { animation-delay: 0.2s; }
.record-card:nth-child(5) { animation-delay: 0.25s; }
.record-card:hover { 
  transform: translateY(-4px); 
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.record-left {
  display: flex; flex-direction: column; align-items: center;
  width: 12px; flex-shrink: 0; padding-top: 6px;
}
.record-dot { 
  width: 10px; 
  height: 10px; 
  border-radius: 50%; 
  flex-shrink: 0;
  transition: all 0.15s ease;
}
.record-card:hover .record-dot {
  transform: scale(1.3);
  box-shadow: 0 0 8px rgba(0,0,0,0.2);
}
.record-body { flex: 1; min-width: 0; }
.record-top { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.record-date { font-size: 11px; color: var(--text-placeholder); }
.record-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
  transition: color 0.2s ease;
}
.record-card:hover .record-title {
  color: var(--accent-blue);
}
.record-meta { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 4px; }
.record-details { display: flex; gap: 8px; flex-wrap: wrap; }
.detail-item {
  font-size: 12px;
  color: var(--text-muted);
  transition: color 0.2s ease;
}
.record-card:hover .detail-item {
  color: var(--text-secondary);
}

/* ===== Projects ===== */
.projects-section { margin-bottom: 24px; }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.project-card {
  background: var(--bg-card); border-radius: 14px; padding: 18px 20px;
  border: 1px solid var(--border-color); box-shadow: var(--shadow-md);
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  opacity: 0;
  transform: scale(0.9);
  animation: scaleIn 0.3s ease-out forwards;
}
.project-card:nth-child(1) { animation-delay: 0.05s; }
.project-card:nth-child(2) { animation-delay: 0.1s; }
.project-card:nth-child(3) { animation-delay: 0.15s; }
.project-card:nth-child(4) { animation-delay: 0.2s; }
.project-card:hover { 
  transform: translateY(-6px) scale(1.02); 
  box-shadow: 0 12px 32px rgba(0,0,0,0.15);
}
.project-top { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.project-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  transition: all 0.15s ease;
}
.project-card:hover .project-icon {
  transform: rotate(10deg) scale(1.1);
}
.project-icon.team { background: rgba(64,158,255,.1); color: var(--accent-blue); }
.project-icon.solo { background: rgba(103,194,58,.1); color: var(--accent-green); }
.project-info { flex: 1; min-width: 0; }
.project-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.2s ease;
}
.project-card:hover .project-name {
  color: var(--accent-blue);
}
.project-date { font-size: 11px; color: var(--text-placeholder); margin-top: 2px; }
.project-members { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
.project-attach { margin-bottom: 8px; }
.project-actions { 
  display: flex; 
  gap: 4px; 
  margin-top: 6px; 
  padding-top: 8px; 
  border-top: 1px solid var(--border-light);
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.15s ease;
}
.project-card:hover .project-actions {
  opacity: 1;
  transform: translateY(0);
}

/* ===== Dialog overrides ===== */
:deep(.el-dialog__body) { padding: 20px 24px; }

/* ===== Mobile ===== */
@media (max-width: 767px) {
  .growth-page { padding: 8px 12px 24px; }
  .score-header { flex-direction: column; align-items: center; gap: 16px; padding: 16px; }
  .score-stats { gap: 16px; justify-content: center; }
  .stat-num { font-size: 20px; }
  .charts-row { flex-direction: column; }
  .chart { height: 200px; }
  .chart-card.wide .chart { height: 180px; }
  .split-row { flex-direction: column; }
  .project-grid { grid-template-columns: 1fr; }
  .record-card { padding: 12px; }
  .record-title { font-size: 13px; }
}
</style>
