<template>
  <div class="students-page">
    <div class="page-header">
      <div class="header-left">
        <h2>学生成长档案</h2>
        <p class="page-sub">共 <strong>{{ students.length }}</strong> 名学生</p>
      </div>
      <el-input v-model="search" placeholder="搜索姓名/学号/学院" style="width:280px" clearable @input="loadStudents">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <el-empty v-if="!students.length && loaded" description="暂无学生记录" :image-size="100">
      <template #image>
        <el-icon :size="64" color="#ddd"><User /></el-icon>
      </template>
      <p style="color:#999;margin-top:8px">当前名下暂无学生</p>
    </el-empty>

    <div v-else class="student-grid">
      <div v-for="s in students" :key="s.id" class="student-card" :class="s.crisis_level ? `level-${s.crisis_level}` : ''">
        <div class="card-head">
          <el-avatar :size="48" :src="s.avatar || undefined" class="card-avatar">{{ s.name[0] }}</el-avatar>
          <div class="card-info">
            <strong class="card-name">{{ s.name }}</strong>
            <span class="card-college">{{ s.college || '未分配' }}</span>
          </div>
          <el-tag v-if="s.crisis_level" :type="crisisType(s.crisis_level)" size="small" effect="dark" class="crisis-tag">
            {{ crisisLabel(s.crisis_level) }}
          </el-tag>
        </div>

        <div class="card-stats">
          <div class="stat-item">
            <span class="stat-num">{{ s.growth_count }}</span>
            <span class="stat-text">成果</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ s.leave_count }}</span>
            <span class="stat-text">请假</span>
          </div>
          <div class="stat-item" v-if="s.score !== undefined">
            <span :class="['stat-num', scoreClass(s.score)]">{{ s.score }}</span>
            <span class="stat-text">综合分</span>
          </div>
        </div>

        <div v-if="s.skills_json?.skills?.length" class="card-skills">
          <el-tag v-for="sk in s.skills_json.skills.slice(0, 3)" :key="sk.name" size="small" round effect="plain">{{ sk.name }}</el-tag>
        </div>

        <div class="card-actions">
          <el-button size="small" type="primary" @click="openDetail(s)">
            <el-icon><View /></el-icon> 详情
          </el-button>
          <el-button size="small" type="success" plain @click="openContact(s)">
            <el-icon><ChatDotRound /></el-icon> 联系
          </el-button>
        </div>
      </div>
    </div>

    <!-- Detail Drawer -->
    <el-drawer v-model="detailVisible" size="600px">
      <template v-if="detail">
        <div class="drawer-profile">
          <el-avatar :size="56" :src="detail.avatar || undefined">{{ detail.name[0] }}</el-avatar>
          <div class="drawer-profile-info">
            <strong>{{ detail.name }}</strong>
            <small>{{ detail.college || '未分配' }}</small>
            <small>学号: {{ detail.username }}</small>
          </div>
        </div>
        <el-tabs v-model="detailTab">
          <el-tab-pane label="技能画像" name="skills">
            <div v-if="detail.skills_json?.skills?.length">
              <h4>技能</h4>
              <div class="skill-list">
                <div v-for="sk in detail.skills_json.skills" :key="sk.name" class="skill-item">
                  <el-tag>{{ sk.name }}</el-tag>
                  <small>{{ sk.context }}</small>
                </div>
              </div>
            </div>
            <div v-if="detail.skills_json?.interests?.length">
              <h4>兴趣</h4>
              <div>
                <el-tag v-for="i in detail.skills_json.interests" :key="i" round style="margin:4px">{{ i }}</el-tag>
              </div>
            </div>
            <el-empty v-if="!detail.skills_json?.skills?.length && !detail.skills_json?.interests?.length" description="暂无技能画像数据" />
          </el-tab-pane>
          <el-tab-pane label="成长记录" name="growth">
            <el-timeline>
              <el-timeline-item v-for="r in detail.growth_records" :key="r.id" :timestamp="r.date">
                <el-tag size="small" :type="growthType(r.type)">{{ growthLabel(r.type) }}</el-tag>
                <p style="margin:4px 0"><strong>{{ r.title }}</strong></p>
                <p v-if="r.description" style="color:#666;font-size:13px">{{ r.description }}</p>
                <template v-if="r.type === 'honor' && r.honor_level">
                  <el-tag size="small" hit effect="plain" style="margin-top:4px">{{ r.honor_level }}</el-tag>
                </template>
                <template v-else-if="r.type === 'competition'">
                  <div style="margin-top:4px;font-size:13px;color:#666">
                    <span v-if="r.organizer">主办方: {{ r.organizer }}</span>
                    <span v-if="r.competition_level" style="margin-left:8px">等级: {{ r.competition_level }}</span>
                  </div>
                </template>
                <template v-else-if="r.type === 'practice'">
                  <div style="margin-top:4px;font-size:13px;color:#666">
                    <span v-if="r.practice_type">{{ r.practice_type }}</span>
                    <span v-if="r.practice_certificate" style="margin-left:8px">证书: {{ r.practice_certificate }}</span>
                  </div>
                </template>
                <template v-else-if="r.type === 'paper'">
                  <div style="margin-top:4px;font-size:13px;color:#666">
                    <div v-if="r.paper_name">{{ r.paper_name }} <span v-if="r.paper_type">[{{ r.paper_type }}]</span></div>
                    <div v-if="r.first_author">作者: {{ r.first_author }}{{ r.second_author ? ', ' + r.second_author : '' }}{{ r.third_author ? ', ' + r.third_author : '' }}</div>
                  </div>
                </template>
                <template v-else-if="r.type === 'achievement'">
                  <div style="margin-top:4px;font-size:13px;color:#666">
                    <span v-if="r.achievement_name">{{ r.achievement_name }}</span>
                    <span v-if="r.achievement_type" style="margin-left:8px">[{{ r.achievement_type }}]</span>
                  </div>
                </template>
                <el-link v-if="r.attachment_url" type="primary" :href="r.attachment_url" target="_blank" style="margin-top:4px;font-size:13px">查看附件</el-link>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!detail.growth_records.length" description="暂无成长记录" />
          </el-tab-pane>
          <el-tab-pane label="危机预警" name="crisis">
            <el-timeline>
              <el-timeline-item v-for="a in detail.crisis_alerts" :key="a.id" :timestamp="formatTime(a.created_at)">
                <el-alert
                  :title="crisisLabel(a.level)"
                  :type="crisisType(a.level)"
                  :description="a.summary"
                  :closable="false"
                  show-icon
                />
                <small v-if="a.keywords_matched" style="color:#999">匹配关键词：{{ a.keywords_matched }}</small>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!detail.crisis_alerts.length" description="暂无预警记录" />
          </el-tab-pane>
          <el-tab-pane label="项目展示" name="projects">
            <div v-if="detail.projects?.length">
              <el-timeline>
                <el-timeline-item v-for="p in detail.projects" :key="p.id" :timestamp="`${p.start_date} ~ ${p.end_date || '至今'}`">
                  <p style="margin:4px 0"><strong>{{ p.project_name }}</strong></p>
                  <el-tag v-if="p.is_team" size="small" type="primary" round>团队</el-tag>
                  <el-tag v-else size="small" type="info" round>个人</el-tag>
                  <p v-if="p.is_team && p.team_members" style="color:#666;font-size:13px;margin-top:4px">成员：{{ p.team_members }}</p>
                  <p v-if="p.attachment_url" style="margin-top:4px">
                    <el-link type="primary" :href="p.attachment_url" target="_blank">查看附件</el-link>
                  </p>
                </el-timeline-item>
              </el-timeline>
            </div>
            <el-empty v-else description="暂无项目数据" />
          </el-tab-pane>
          <el-tab-pane label="请假记录" name="leave">
            <el-table :data="detail.leave_requests" size="small" style="width:100%"
              :header-cell-style="{ background: '#f8faff', color: '#333', fontWeight: 600 }">
              <el-table-column prop="start_date" label="日期" width="100" />
              <el-table-column prop="leave_type" label="类型" width="70">
                <template #default="{ row }">{{ leaveTypeLabel(row.leave_type) }}</template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="140" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
                    {{ row.status === 'approved' ? '通过' : row.status === 'rejected' ? '拒绝' : '待批' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!detail.leave_requests.length" description="无请假记录" />
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>

    <!-- Contact Dialog -->
    <el-dialog v-model="contactVisible" :title="`发送消息给 ${contactStudent?.name || ''}`" width="420px" :close-on-click-modal="false">
      <el-input v-model="contactMsg" type="textarea" :rows="4" placeholder="输入消息内容..." />
      <template #footer>
        <el-button @click="contactVisible = false">取消</el-button>
        <el-button type="primary" @click="sendContactMsg" :loading="sending">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, User, View, ChatDotRound } from '@element-plus/icons-vue'
import { getStudents, getStudentDetail, type StudentSummary, type StudentDetail } from '@/api/teacher'
import { sendMessage } from '@/api/messages'
import { ElMessage } from 'element-plus'

const search = ref('')
const students = ref<(StudentSummary & { score?: number })[]>([])
const loaded = ref(false)
const detailVisible = ref(false)
const detail = ref<StudentDetail | null>(null)
const detailTab = ref('skills')

const router = useRouter()

const contactVisible = ref(false)
const contactStudent = ref<StudentSummary | null>(null)
const contactMsg = ref('')
const sending = ref(false)

async function loadStudents() {
  try {
    students.value = await getStudents(search.value || undefined)
    loaded.value = true
  } catch {}
}

function crisisType(level: string) {
  const map: Record<string, string> = { severe: 'danger', moderate: 'warning', mild: 'info' }
  return map[level] || 'info'
}

function crisisLabel(level: string) {
  const map: Record<string, string> = { severe: '高危', moderate: '中度', mild: '轻度' }
  return map[level] || level
}

function growthType(t: string) {
  const map: Record<string, string> = { honor: 'primary', competition: 'success', award: 'warning', practice: 'info' }
  return map[t] || 'info'
}

function growthLabel(t: string) {
  const map: Record<string, string> = { honor: '荣誉', competition: '竞赛', award: '奖项', practice: '实践', paper: '论文', achievement: '成果' }
  return map[t] || t
}

function leaveTypeLabel(t: string) {
  const map: Record<string, string> = { competition: '比赛', sick: '病假', personal: '事假', other: '其他' }
  return map[t] || t
}

function formatTime(t: string) {
  try { return new Date(t).toLocaleString('zh-CN') } catch { return t }
}

function scoreClass(score: number) {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-average'
  return 'score-poor'
}

async function openDetail(s: StudentSummary) {
  try {
    detail.value = await getStudentDetail(s.id)
    detailVisible.value = true
    detailTab.value = 'skills'
  } catch {}
}

function openContact(s: StudentSummary) {
  router.push({ path: '/teacher/messages', query: { studentId: String(s.id), studentName: s.name } })
}

async function sendContactMsg() {
  if (!contactMsg.value.trim() || !contactStudent.value) return
  sending.value = true
  try {
    await sendMessage(contactStudent.value.id, contactMsg.value.trim())
    ElMessage.success('消息已发送')
    contactVisible.value = false
  } catch {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

onMounted(loadStudents)
</script>

<style scoped>
.students-page { height: 100%; overflow-y: auto; overflow-x: hidden; padding: 8px 4px; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-end;
  margin-bottom: 20px; padding: 0 4px;
}
.header-left h2 {
  font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0;
}
.page-sub { font-size: 14px; color: #888; margin: 4px 0 0; }
.page-sub strong { color: #5b8def; }

/* ===== Student Grid ===== */
.student-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.student-card {
  background: #fff;
  border-radius: 14px;
  padding: 20px;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  transition: all 0.2s ease;
  cursor: default;
}
.student-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}
.student-card.level-severe { border-left: 3px solid #f56c6c; }
.student-card.level-moderate { border-left: 3px solid #e6a23c; }
.student-card.level-mild { border-left: 3px solid #909399; }

.card-head {
  display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
}
.card-avatar { flex-shrink: 0; }
.card-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.card-name { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.card-college { font-size: 12px; color: #999; margin-top: 2px; }
.crisis-tag { flex-shrink: 0; }

/* ===== Stats ===== */
.card-stats {
  display: flex; gap: 16px; margin-bottom: 12px;
  padding: 10px 0; border-top: 1px solid #f5f5f5; border-bottom: 1px solid #f5f5f5;
}
.stat-item { display: flex; flex-direction: column; align-items: center; flex: 1; }
.stat-num { font-size: 18px; font-weight: 700; color: #333; line-height: 1.2; }
.stat-text { font-size: 11px; color: #999; margin-top: 2px; }
.score-excellent .stat-num, .score-excellent { color: #67c23a; }
.score-good .stat-num, .score-good { color: #409eff; }
.score-average .stat-num, .score-average { color: #e6a23c; }
.score-poor .stat-num, .score-poor { color: #f56c6c; }

/* ===== Skills ===== */
.card-skills {
  display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px;
}

/* ===== Actions ===== */
.card-actions {
  display: flex; gap: 8px;
}

/* ===== Drawer ===== */
.drawer-profile {
  display: flex; align-items: center; gap: 16px;
  padding: 0 0 16px 0; border-bottom: 1px solid #f0f0f0; margin-bottom: 16px;
}
.drawer-profile-info { display: flex; flex-direction: column; }
.drawer-profile-info strong { font-size: 16px; }
.drawer-profile-info small { font-size: 13px; color: #999; }

:deep(.el-drawer__header) { padding: 8px 16px 0 !important; margin-bottom: 0 !important; }

.skill-list { display: flex; flex-direction: column; gap: 8px; }
.skill-item { display: flex; align-items: center; gap: 8px; }
</style>
