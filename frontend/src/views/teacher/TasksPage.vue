<template>
  <div
    class="tui-page"
    :class="{ 'pull-enabled': isMobile }"
    @touchstart.passive="pull.onStart"
    @touchmove="pull.onMove"
    @touchend="pull.onEnd"
    @touchcancel="pull.onCancel"
  >
    <SubPageHeader title="今日重点" fallback="/teacher" />
    <PullRefreshIndicator :indicator-style="pull.indicatorStyle" :active="pull.active" />

    <div class="tui-content tr-content">
      <!-- ===================== 载入态：产品形象 + 智能体式反馈（打点 / 轮换文案 / 进度条） =====================
           文案轮换交给 TuiMascotLoader → AgentLoading 统一处理，页面不再自己养定时器。 -->
      <TuiMascotLoader v-if="loading && !report" state="loading" :tips="LOAD_TIPS" />

      <template v-else-if="report && !isMobile">
        <!-- ===================== 问候头部 =====================
             设计调整：原来这里是「渐变底 + 三张统计小卡 + 一个『重新整理』按钮」，
             一屏里先出现四张卡，每张都在抢注意力，反而看不出今天到底该先做什么。
             现在抬头只留三样：一行元信息（日期 · 时段 · 天气）、一句问候、一句当日基调。
             数字不再在抬头重复——它们本来就在下面的清单与正文里，重复一遍只是噪音。
             基调句完全由 summary 推导，不编造：没有数据就退回中性表述。 -->
        <section class="tr-hero">
          <div class="tr-hero-meta">
            <span class="tr-hero-date">{{ report.date_text }}</span>
            <div class="tr-hero-tools">
              <!-- 刷新中的即时反馈：沿用智能体那套「打点 + 一句话」，而不是让按钮独自转圈 -->
              <AgentLoading v-if="refreshing" size="sm" text="正在重新整理" class="tr-hero-status" />
              <button
                v-if="report.weather"
                type="button"
                class="tr-hero-weather"
                :title="`${report.weather.city} 实时天气 · 点击重新整理`"
                @click="refresh"
              >
                <span class="tr-hero-weather-emoji">{{ report.weather.emoji }}</span>
                <span>{{ report.weather.temp }}℃</span>
                <span class="tr-hero-weather-desc">{{ report.weather.desc }}</span>
              </button>
              <button
                type="button"
                class="tr-hero-refresh"
                :disabled="refreshing"
                :aria-label="refreshing ? '正在重新整理' : '重新整理'"
                :title="refreshing ? '正在重新整理' : '重新整理'"
                @click="refresh"
              >
                <el-icon :size="14" :class="{ 'is-spin': refreshing }"><Refresh /></el-icon>
              </button>
            </div>
          </div>
          <h1 class="tr-hero-greet">{{ report.greeting }}</h1>
          <p class="tr-hero-tone" :class="'is-' + toneKind">
            <i class="tr-hero-tone-bar" aria-hidden="true" />
            <span class="tr-hero-tone-txt">{{ toneText }}</span>
          </p>
        </section>

        <!-- ===================== 今日运势 =====================
             做成一条贴边的「签文」插页：有底色、无边框、无圆角、无投影。
             它和正文的层级本来就不同，用底色区分比再套一张白卡省眼睛。 -->
        <section class="tr-fortune" :class="'is-' + fortuneTone">
          <div class="tr-fortune-head">
            <span class="tr-fortune-label">今日运势</span>
            <span class="tr-fortune-level">{{ report.fortune.level }}</span>
            <span class="tr-fortune-key">{{ report.fortune.keyword }}</span>
            <span class="tr-fortune-score">{{ report.fortune.score }}<small>分</small></span>
          </div>
          <div class="tr-fortune-meter" aria-hidden="true">
            <i :style="{ width: report.fortune.score + '%' }"></i>
          </div>
          <p v-if="report.fortune.summary" class="tr-fortune-summary">
            <RichMarkText :text="report.fortune.summary" />
          </p>
          <div class="tr-fortune-meta">
            <span>幸运色 · {{ report.fortune.lucky_color }}</span>
            <span>幸运时段 · {{ report.fortune.lucky_time }}</span>
          </div>
        </section>

        <!-- ===================== 四段正文 =====================
             每段一个段号（01/02/03），整页读起来像一份当日简报，
             排序感由字阶和发丝线给出，不再靠一层层卡片把内容框起来。 -->
        <section v-for="(sec, si) in report.sections" :key="sec.key" class="tr-sec">
          <div class="tr-sec-head">
            <span class="tr-sec-no">{{ num(si + 1) }}</span>
            <h2 class="tr-sec-title">{{ sec.title }}</h2>
            <button
              v-if="sec.key === 'review' && overdueCount"
              type="button"
              class="tr-sec-more"
              @click="showOverdue = true"
            >
              看逾期任务
              <el-icon :size="11"><ArrowRight /></el-icon>
            </button>
            <button
              v-else-if="sec.key === 'student'"
              type="button"
              class="tr-sec-more"
              @click="go('/teacher/students')"
            >
              学生档案
              <el-icon :size="11"><ArrowRight /></el-icon>
            </button>
          </div>
          <ul class="tr-sec-list">
            <li v-for="(line, li) in sec.items" :key="li" class="tr-sec-line">
              <RichMarkText :text="line" />
            </li>
          </ul>
        </section>

        <!-- ===================== 今日可操作条目 =====================
             这一块直接复用设计系统的 .tui-list / .tui-row：教师端别的页面里
             「一条一个动作」的清单就是这个形状（左图标块 + 标题/说明 + 右侧操作），
             用现成组件比自己再造一套行样式更统一，也省得每页各长一副样子。
             分界很清楚：上面四段是「读」的，保持无壳的发丝线段落；
             这里、下面的建议、任务清单是「动手」的，才配卡片。 -->
        <section v-if="report.actions.length" class="tr-sec tr-actions">
          <div class="tr-sec-head">
            <span class="tr-sec-no">{{ num(actNo) }}</span>
            <h2 class="tr-sec-title">可以直接处理</h2>
            <!-- 只有当这一屏里真的存在「可一键完成」的条目时，计数才有意义；
                 全部都是跳转类条目时显示「0/0 已办结」纯属噪音，直接不显示。 -->
            <span v-if="completableTotal" class="tr-sec-count">{{ completedCount }}/{{ completableTotal }} 已办结</span>
          </div>

          <div class="tui-list tr-list">
            <div
              v-for="a in report.actions"
              :key="a.id"
              class="tui-row tr-act"
              :class="{ 'is-done': doneIds.has(a.id) }"
            >
              <span class="tui-row-icon tr-act-icon" :class="'is-' + a.group">
                <el-icon :size="17"><component :is="ACTION_ICON[a.group]" /></el-icon>
              </span>
              <button type="button" class="tui-row-main tr-act-main" @click="go(a.link)">
                <span class="tui-row-label tr-act-title">{{ a.title }}</span>
                <span class="tr-act-desc">
                  <span class="tui-tag" :class="TAG_TONE[a.group]">{{ a.label }}</span>
                  <span v-if="a.student_name" class="tr-act-sub">{{ a.student_name }}</span>
                  <span v-if="a.source_label" class="tr-act-sub">{{ a.source_label }}</span>
                </span>
              </button>
              <span class="tr-act-btns">
                <button
                  v-if="a.can_complete && !doneIds.has(a.id)"
                  type="button"
                  class="tr-pill is-primary"
                  :disabled="completingId === a.id"
                  @click.stop="completeTask(a)"
                >
                  {{ completingId === a.id ? '处理中' : '一键完成' }}
                </button>
                <span v-else-if="doneIds.has(a.id)" class="tr-pill is-done">已办结</span>
                <!-- 可一键完成的条目已给出主操作，不再重复挂一个同名按钮 -->
                <button v-else type="button" class="tr-pill" @click.stop="go(a.link)">{{ a.action_text || '去处理' }}</button>
              </span>
            </div>
          </div>
        </section>

        <!-- ===================== AI 建议 =====================
             建议是「一句话 + 一个动作」，塞进 tui-row 会被右操作挤成窄条，
             所以用同一张 tui-list 壳、内部改成「标题行 + 正文行」两段式。 -->
        <section v-if="report.suggestions.length" class="tr-sec tr-suggest">
          <div class="tr-sec-head">
            <span class="tr-sec-no">{{ num(sugNo) }}</span>
            <h2 class="tr-sec-title">可以让 AI 帮你排进去</h2>
            <span class="tr-sec-count">{{ report.suggestions.length }} 条</span>
          </div>

          <div class="tui-list tr-list">
            <div v-for="(s, i) in report.suggestions" :key="i" class="tr-sug">
              <div class="tr-sug-top">
                <p class="tr-sug-title">
                  <span v-if="s.when" class="tui-chip">{{ s.when }}</span>
                  <span class="tr-sug-name">{{ s.title }}</span>
                </p>
                <button
                  v-if="!addedSet.has(i)"
                  type="button"
                  class="tr-pill is-primary"
                  :disabled="addingIdx === i"
                  @click="addSuggestion(s, i)"
                >
                  {{ addingIdx === i ? '添加中' : '加入' }}
                </button>
                <span v-else class="tr-pill is-done">已加入</span>
              </div>
              <p class="tr-sug-text"><RichMarkText :text="s.content" /></p>
            </div>
          </div>
        </section>

        <!-- ===================== 今天的任务 =====================
             清单只留「今天」这一层：不再有按日期前后翻的日程条，也不再往里塞全部历史任务。
             全页只有这一处用卡片——它是唯一需要反复点开、反复勾选的东西；
             卡内仍是发丝线分组的行，不把每条任务再套一张小卡，否则又回到「一堆同样重的盒子」。
             分组按状态（待办 / 已办结）而不是按小时：后端 due_at 只有日期没有时刻，
             排成「上午/下午」的时刻表等于编造信息。逾期默认收成一行提示，点开才并到最前。 -->
        <section class="tr-sec tr-today">
          <div class="tr-sec-head">
            <span class="tr-sec-no">{{ num(listNo) }}</span>
            <h2 class="tr-sec-title">今天的任务</h2>
            <span class="td-head-right">
              <button type="button" class="td-add" @click="openCreate()">
                <el-icon :size="12"><Plus /></el-icon>新增
              </button>
            </span>
          </div>

          <div class="td-card">
            <!-- 完成度用设计系统的 .tui-progress：6px 圆角细条 + 右侧数字，
                 比贴在卡片顶端那条 3px 边线更像「进度」，也不会被圆角裁成一道缺口。 -->
            <div v-if="todayTotal" class="td-progrow">
              <div class="tui-progress">
                <div class="tui-progress-track">
                  <span
                    class="tui-progress-fill is-success"
                    :style="{ '--pct': (todayRate || 0) / 100 }"
                  />
                </div>
                <span class="tui-progress-text">已办结 {{ todayDone }}/{{ todayTotal }}</span>
              </div>
            </div>

            <section v-for="g in boardGroups" :key="g.key" class="td-group">
              <div class="td-group-head" :class="'is-' + g.tone">
                <span>{{ g.title }}</span>
                <span class="td-group-n">{{ g.items.length }}</span>
              </div>

              <div
                v-for="t in g.items"
                :key="g.key + '-' + t.id"
                class="td-row"
                :class="{ 'is-done': t.status === 'done', 'is-overdue': t.overdue }"
              >
                <span v-if="t.status === 'done'" class="td-check is-on" aria-hidden="true">
                  <el-icon :size="10"><Select /></el-icon>
                </span>
                <button
                  v-else
                  type="button"
                  class="td-check"
                  :disabled="busyRowId === t.id"
                  :aria-label="`办结：${t.title}`"
                  @click.stop="finishTask(t)"
                />

                <button type="button" class="td-row-main" @click="openEditTask(t)">
                  <span class="td-row-title">{{ t.title }}</span>
                  <span class="td-row-meta">
                    <span class="td-pri" :class="'is-' + (t.priority || 'mid')">{{ PRIORITY_SHORT[t.priority || 'mid'] }}</span>
                    <span v-if="g.key === 'overdue'" class="td-meta is-danger">{{ overdueText(t) }}</span>
                    <span v-if="t.student_name" class="td-meta">{{ t.student_name }}</span>
                    <span class="td-meta">{{ TASK_SOURCE_LABEL[t.source_type] }}</span>
                  </span>
                </button>

                <el-icon class="td-go" :size="12" aria-hidden="true"><ArrowRight /></el-icon>
              </div>
            </section>

            <div v-if="!boardGroups.length" class="td-empty">
              <p class="td-empty-t">今天还没有安排任务</p>
              <p class="td-empty-d">当天的事当天清，比攒到周末再补省力</p>
              <button type="button" class="td-empty-btn" @click="openCreate()">
                <el-icon :size="12"><Plus /></el-icon>加一条今天的任务
              </button>
            </div>

            <button
              v-if="overdueCount"
              type="button"
              class="td-ovd"
              :class="{ 'is-open': showOverdue }"
              @click="showOverdue = !showOverdue"
            >
              <i class="td-ovd-dot" aria-hidden="true" />
              <span class="td-ovd-t">
                {{ showOverdue ? '逾期任务已并到上面' : `另有 ${overdueCount} 项逾期未办` }}
              </span>
              <span class="td-ovd-act">{{ showOverdue ? '收起' : '一起看' }}</span>
              <el-icon :size="11" :class="{ 'is-open': showOverdue }"><ArrowRight /></el-icon>
            </button>
          </div>
        </section>

        <p class="tr-footnote">
          今日重点由绵小城根据你的任务、预警、请假与成长记录生成<template v-if="generatedText"> · {{ generatedText }}</template>
        </p>
      </template>

      <!-- ============================================================
           移动端 · 报告式「今日工作简报」
           一级标题 + 导语 + 形象图构成封面；二级章节按「必须今天 / 可推到明天 / 可一键办结」分档，
           每条只留一个办理入口，读起来是一份可执行的报告，而不是一墙卡片。
           ============================================================ -->
      <template v-else-if="report && isMobile">
        <div class="tm-page rp-report">
          <!-- ============ 报告封面：一级标题 + 导语 + 形象图 + 关键数字 ============ -->
          <header class="rp-cover">
            <div class="rp-cover-top">
              <img class="rp-logo" :src="siteLogo" alt="站点标识" />
              <span class="rp-kicker">今日工作简报</span>
              <span class="rp-date">{{ report.date_text }}</span>
            </div>

            <h1 class="rp-h1">今日重点</h1>

            <div class="rp-cover-body">
              <div class="rp-cover-text">
                <p class="rp-lead"><RichMarkText :text="aiSummaryText" /></p>
                <p class="rp-sign">
                  {{ report.greeting }}
                  <template v-if="report.weather">
                    · {{ report.weather.emoji }} {{ report.weather.temp }}℃ {{ report.weather.desc }}
                  </template>
                  <template v-if="generatedText"> · {{ generatedText }}</template>
                </p>
              </div>
              <img class="rp-cover-img" :src="siteMascot" alt="绵小城" />
            </div>

            <div class="rp-stats">
              <div class="rp-stat">
                <b>{{ summary.open }}</b>
                <span>未办事项</span>
              </div>
              <div class="rp-stat is-hot">
                <b>{{ mustToday.length }}</b>
                <span>必须今天</span>
              </div>
              <div class="rp-stat is-ok">
                <b>{{ autoList.length }}</b>
                <span>可一键办结</span>
              </div>
            </div>
          </header>

          <!-- ============ 二级章节：按处理时限分档，每条只留一个办理入口 ============ -->
          <section v-for="(g, gi) in focusGroups" :key="g.key" class="rp-sec">
            <div class="rp-sec-head">
              <span class="rp-sec-no">{{ num(gi + 1) }}</span>
              <h2 class="rp-h2">{{ g.title }}</h2>
              <span class="rp-sec-count">{{ g.items.length }} 件</span>
            </div>
            <p class="rp-sec-desc">{{ g.desc }}</p>

            <div class="rp-list">
              <article
                v-for="(a, ai) in g.items"
                :key="a.id"
                class="rp-item"
                :class="{ 'is-done': doneIds.has(a.id) }"
              >
                <span class="rp-item-no">{{ num(ai + 1) }}</span>
                <div class="rp-item-bd">
                  <div class="rp-item-top">
                    <span class="rp-kind" :class="noteTagCls(a)">{{ groupLabel(a.group) }}</span>
                    <span class="rp-item-src">{{ a.student_name || a.source_label }}</span>
                    <span v-if="doneIds.has(a.id)" class="rp-item-done">已办结</span>
                  </div>
                  <p class="rp-item-t">{{ actionContent(a) }}</p>
                  <p class="rp-item-sub">{{ actionHint(a) }}</p>
                </div>
                <button
                  v-if="a.kind === 'task' && a.task_id"
                  type="button"
                  class="rp-btn rp-btn-main"
                  :class="{ 'is-done': doneIds.has(a.id) }"
                  :disabled="doneIds.has(a.id) || completingId === a.id"
                  @click.stop="completeTask(a)"
                >
                  {{
                    doneIds.has(a.id)
                      ? '已办结'
                      : completingId === a.id
                        ? '办结中…'
                        : '一键完成'
                  }}
                </button>
                <button v-else-if="a.link" type="button" class="rp-btn" @click.stop="go(a.link)">
                  {{ linkLabel(a) }}
                  <el-icon :size="11"><ArrowRight /></el-icon>
                </button>
              </article>
            </div>

            <div v-if="g.key === 'auto'" class="rp-batch">
              <span>均为后端判定低风险，办结后仍可在任务清单查到记录</span>
              <button
                type="button"
                class="rp-batch-btn"
                :disabled="bulkCompleting"
                @click="completeAllAuto"
              >
                {{ bulkCompleting ? '正在办结…' : '全部办结' }}
              </button>
            </div>
          </section>

          <div v-if="!mustToday.length" class="rp-empty">
            今天没有必须处理的事，可继续看下方 AI 建议。
          </div>

          <!-- ============ 二级章节：AI 建议（可一键加入今天的清单） ============ -->
          <section v-if="report.suggestions.length" class="rp-sec">
            <div class="rp-sec-head">
              <span class="rp-sec-no">{{ num(focusGroups.length + 1) }}</span>
              <h2 class="rp-h2">AI 建议</h2>
              <span class="rp-sec-count">{{ report.suggestions.length }} 条</span>
            </div>
            <p class="rp-sec-desc">可一键加入今天，加入后进入上面的办理清单</p>

            <div class="rp-list">
              <article v-for="(s, i) in report.suggestions" :key="i" class="rp-item rp-sug">
                <img class="rp-sug-img" :src="siteMascot" alt="绵小城" />
                <div class="rp-item-bd">
                  <div class="rp-item-top">
                    <span class="rp-flag">{{ suggestionFlag(s) }}</span>
                    <b class="rp-sug-title">{{ s.title }}</b>
                  </div>
                  <p class="rp-sug-desc">{{ s.content }}</p>
                </div>
                <button
                  type="button"
                  class="rp-btn"
                  :disabled="addingIdx === i"
                  @click="addSuggestion(s, i)"
                >
                  {{ addingIdx === i ? '加入中' : '加入今天' }}
                </button>
              </article>
            </div>
          </section>

          <footer class="rp-foot-note">
            <img class="rp-foot-logo" :src="siteLogo" alt="" />
            <span>依据：优先级 · 是否逾期 · 来源（任务 / 预警 / 请假）· 可办结由后端判定</span>
          </footer>
        </div>
      </template>

      <!-- ===================== 失败态：产品形象 + 真实原因 + 重试（无卡片） ===================== -->
      <template v-else>
        <TuiMascotLoader
          state="error"
          :desc="errorText"
          retry-text="重新整理"
          :busy="refreshing"
          retry-busy-text="正在重新整理"
          @retry="manualRetry"
        />
        <div class="tr-error-actions">
          <!-- 接口 404 = 后端版本旧：光重试永远好不了，必须让用户换条路 -->
          <button v-if="endpointMissing" type="button" class="tr-error-link" @click="seeTasksAnyway">
            先看任务清单
            <el-icon :size="12"><ArrowRight /></el-icon>
          </button>
          <button v-if="endpointMissing" type="button" class="tr-error-link" @click="reloadPage">
            重新加载页面
          </button>
        </div>
      </template>
    </div>

    <TeacherTaskDialog
      v-model="createVisible"
      :task="editingTask"
      :preset-due-at="presetDueAt"
      :preset-title="presetTitle"
      :preset-student-id="presetStudent?.id ?? null"
      :preset-student-name="presetStudent?.name"
      @saved="refreshAll"
    />

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { onDataChange, emitDataChange } from '@/utils/dataSync'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Calendar,
  Clock,
  Plus,
  Refresh,
  Select,
  Timer,
  WarningFilled,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import PullRefreshIndicator from '@/components/common/PullRefreshIndicator.vue'
import AgentLoading from '@/components/common/AgentLoading.vue'
import RichMarkText from '@/components/common/RichMarkText.vue'
import TuiMascotLoader from '@/components/teacher/ui/TuiMascotLoader.vue'
import { usePullRefresh } from '@/composables/usePullRefresh'
import TeacherTaskDialog from '@/components/teacher/task/TeacherTaskDialog.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import {
  createTeacherTask,
  getTeacherTasks,
  TASK_SOURCE_LABEL,
  updateTeacherTask,
  type TeacherTask,
} from '@/api/teacherTask'
import {
  getTeacherDailyReport,
  type TeacherDailyReport,
  type TeacherReportAction,
  type TeacherReportSuggestion,
} from '@/api/teacherDailyReport'

defineOptions({ name: 'teacher-tasks' })

const { isMobile } = useResponsive()
const { siteMascot, siteLogo } = useSiteConfig()
const route = useRoute()
const router = useRouter()

/* ================= 日报 ================= */
/**
 * 可操作条目的图标与标签配色：服务端 group 只有四个值，
 * 这里一次性映射到 element-plus 图标 + 设计系统的 tui-tag 色调，
 * 模板里就不用写一长串 v-if。
 */
const ACTION_ICON: Record<string, Component> = {
  alert: WarningFilled,
  leave: Calendar,
  overdue: Clock,
  due: Timer,
}
const TAG_TONE: Record<string, string> = {
  alert: 'tui-tag-danger',
  leave: 'tui-tag-warn',
  overdue: 'tui-tag-danger',
  due: 'tui-tag-brand',
}

const report = ref<TeacherDailyReport | null>(null)
const loading = ref(true)
const refreshing = ref(false)
/** 失败原因：null 表示没有错误；有值时渲染失败态 */
const loadError = ref<string | null>(null)
/** 模板用的失败文案：错误优先，其次兜底，保证失败态永远有话说 */
const errorText = computed(() => loadError.value || '暂时没能整理出今日重点')
const EMPTY_BODY_TIP = '没有拿到今日重点内容，重试一次试试'

/** 加载态文案轮换：让等待有进展感，而不是干等（轮换由 TuiMascotLoader → AgentLoading 执行） */
const LOAD_TIPS = [
  '正在为你整理今日重点',
  '看看昨天还有什么没办完',
  '查一下哪些学生需要多留意',
  '把今天该做的事排个序',
]

/**
 * 加载态最短可见时长（毫秒）。
 * 取值依据：形象呼吸周期 2.8s、文案轮换 2.2s，800ms 足够看清「东西在动」，
 * 又不会让本来就很快的接口显得卡。若要更快，改成 500 也不会闪一下就没。
 */
const MIN_LOADING_MS = 800
/** 已一键办结的条目（按 action.id 记，避免重新拉取前的视觉回退） */
const doneIds = reactive(new Set<string>())
const completedCount = computed(() => report.value?.actions.filter((a) => doneIds.has(a.id)).length ?? 0)
const completableTotal = computed(
  () => report.value?.actions.filter((a) => a.can_complete || doneIds.has(a.id)).length ?? 0
)
const summary = computed(
  () =>
    report.value?.summary ?? {
      open: 0,
      due_today: 0,
      overdue: 0,
      high: 0,
      done_yesterday: 0,
      alert_total: 0,
      severe_total: 0,
      leave_total: 0,
      student_total: 0,
    }
)

/**
 * 当日基调：只从真实 summary 推导，不写死文案、不随机。
 * 优先级是「有人可能出事」>「有活没干完」>「一切正常」，
 * 因为辅导员真正需要被提醒的是前两者。
 */
const toneKind = computed<'danger' | 'warn' | 'calm'>(() => {
  const s = summary.value
  if (s.severe_total > 0 || s.overdue > 0) return 'danger'
  if (s.leave_total > 0 || s.due_today > 0) return 'warn'
  return 'calm'
})
const toneText = computed(() => {
  const s = summary.value
  const bits: string[] = []
  if (s.severe_total > 0) bits.push(`${s.severe_total} 名学生处于高风险，建议今天逐个谈话`)
  if (s.overdue > 0) bits.push(`${s.overdue} 项待办已逾期，先清掉`)
  if (s.leave_total > 0) bits.push(`${s.leave_total} 条请假等你批复`)
  if (!bits.length && s.due_today > 0) bits.push(`今天有 ${s.due_today} 项要办结，节奏还算宽裕`)
  if (!bits.length) bits.push('没有逾期、没有高危，可以按自己的节奏安排')
  return bits.join('；')
})

/** 运势档位 → 配色（上签喜庆、平签稳重、缓行签柔和，不用红色渲染负向） */
const fortuneTone = computed(() => {
  const score = report.value?.fortune.score ?? 70
  if (score >= 85) return 'great'
  if (score >= 75) return 'good'
  if (score >= 65) return 'mid'
  return 'soft'
})

/**
 * 段号：整页按 01 / 02 / 03 排成一份「当日简报」。
 * 用数字而不是图标，是因为数字天然给出阅读顺序——老师扫一眼就知道这份重点有几段、读到第几段了。
 */
function num(n: number) {
  return String(n).padStart(2, '0')
}
/** 「可以直接处理」紧接四段正文，编号随段落数滚动 */
const actNo = computed(() => (report.value?.sections.length ?? 0) + 1)
const sugNo = computed(() => actNo.value + (report.value?.actions.length ? 1 : 0))
const listNo = computed(() => sugNo.value + (report.value?.suggestions.length ? 1 : 0))
const generatedText = computed(() => {
  const at = report.value?.generated_at
  if (!at) return ''
  const d = new Date(at)
  if (Number.isNaN(d.getTime())) return ''
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')} 生成`
})

function go(link: string) {
  if (!link) return
  router.push(link)
}

/* ── 移动端便签墙：只读后端字段分档，不在前端判断风险 ──
   mustToday = 预警来源 / 已逾期 / 高优先级；
   autoList  = 后端判定 can_complete 的低风险项；其余进「可推到明天」。 */
const GROUP_LABEL: Record<string, string> = {
  alert: '预警',
  leave: '请假',
  overdue: '逾期',
  due: '今天到期',
}
function groupLabel(g: string) {
  return GROUP_LABEL[g] || '待办'
}
const mustToday = computed(
  () =>
    report.value?.actions.filter(
      (a) => a.group === 'alert' || a.group === 'overdue' || a.priority === 'high'
    ) ?? []
)
const autoList = computed(
  () =>
    report.value?.actions.filter(
      (a) => a.can_complete && !mustToday.value.some((m) => m.id === a.id)
    ) ?? []
)
const laterList = computed(
  () =>
    report.value?.actions.filter(
      (a) =>
        !mustToday.value.some((m) => m.id === a.id) && !autoList.value.some((m) => m.id === a.id)
    ) ?? []
)
/** 统一分组：同一套「事项简报」卡片，按处理时限分档展示 */
const focusGroups = computed(() => [
  {
    key: 'must',
    title: '必须今天',
    desc: `${mustToday.value.length} 件 · 逾期 ${summary.value.overdue}`,
    items: mustToday.value,
  },
  {
    key: 'later',
    title: '可推到明天',
    desc: `${laterList.value.length} 件 · 不紧急但不能忘`,
    items: laterList.value,
  },
  {
    key: 'auto',
    title: '可以一键办结',
    desc: `低风险 ${autoList.value.length} 件`,
    items: autoList.value,
  },
].filter((g) => g.items.length))

/** AI 今日总结：用富标记生成下划线高亮与黄色标签，避免又堆成一张信息卡 */
const aiSummaryText = computed(() => {
  const open = summary.value.open
  const must = mustToday.value.length
  const auto = autoList.value.length
  const first = mustToday.value[0]
  const who = first?.student_name || first?.source_label
  const lead = who ? `建议先处理 __${who}__ 相关事项，` : '今天没有高风险事项，'
  return `今天 **${open}** 件未办，其中 ==${must} 件必须今天==、==${auto} 件可一键办结==。${lead}其余按「必须今天 → 可推明天」顺序推进即可。`
})

/** 历史数据里的 emoji 可能落成连续问号，先清掉再展示 */
function cleanTaskTitle(raw: string) {
  return (raw || '')
    .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu, '')
    .replace(/[?？]{2,}/g, '')
    .trim()
}

/** 条目正文：写清具体要办什么，而不是一句通用分类名 */
function actionContent(a: TeacherReportAction) {
  const raw = cleanTaskTitle(a.title)
  if (a.group === 'alert') {
    return raw ? `${a.student_name ? `${a.student_name} · ` : ''}${raw}` : `${a.student_name || '学生'} 的心理预警需要核实`
  }
  if (a.group === 'leave') {
    return raw || `${a.student_name || '学生'} 的请假申请待审批`
  }
  return raw || `${a.student_name || '本班'} 有事项待处理`
}

/** 条目补充说明：一句话交代为什么要办、办到什么程度 */
function actionHint(a: TeacherReportAction) {
  if (a.group === 'alert') return '需人工核实并登记干预；涉及安全风险请同步上报'
  if (a.group === 'leave') return '核对事由与起止时间后通过或驳回'
  if (a.group === 'overdue') return '已超过计划时间；今天内办结，做不完就改期并记录原因'
  return '今天到期；可在任务清单中改期或直接办结'
}

/** 建议条目的黄色标记：与下划线一起构成「AI 批注」视觉 */
function suggestionFlag(s: TeacherReportSuggestion) {
  if (s.priority === 'high') return '优先处理'
  if (s.when) return s.when
  return 'AI 建议'
}

/** 跳转按钮文案：按事项来源说清进去能做什么 */
function linkLabel(a: TeacherReportAction) {
  if (a.group === 'alert') return '去跟进'
  if (a.group === 'leave') return '去审批'
  if (a.group === 'overdue') return '去处理'
  return '打开详情'
}

function noteTagCls(a: TeacherReportAction) {
  if (a.group === 'alert' || a.group === 'overdue') return 'tm-bad'
  if (a.priority === 'high') return 'tm-warn'
  return 'tm-brand'
}
const bulkCompleting = ref(false)

/**
 * 一键办结全部低风险项：
 * 原来的实现逐条 await completeTask，每完成一条都会重新拉一次日报与任务清单，
 * N 条就要发 2N 次请求，且中途失败会让后面的条目状态错乱。
 * 现在先批量提交，最后只刷新一次；部分失败也保留已成功的结果。
 */
async function completeAllAuto() {
  if (bulkCompleting.value) return
  const targets = autoList.value.filter((a) => a.task_id && !doneIds.has(a.id))
  if (!targets.length) return
  bulkCompleting.value = true
  let ok = 0
  try {
    for (const a of targets) {
      try {
        await updateTeacherTask(a.task_id!, { status: 'done' })
        doneIds.add(a.id)
        ok++
      } catch {
        /* 单条失败不打断其余条目 */
      }
    }
    if (ok === targets.length) ElMessage.success(`已办结 ${ok} 件`)
    else ElMessage.warning(`已办结 ${ok} 件，${targets.length - ok} 件失败，请重试`)
  } finally {
    bulkCompleting.value = false
    await Promise.all([load(true), loadTasks()])
    emitDataChange(['teacher-tasks', 'teacher-students'])
  }
}

/** 拉取今日重点：失败时记录真实原因（HTTP 状态 / 业务 detail），
 *  并区分「首次载入失败」与「刷新失败但已有旧数据」——后者保留旧内容只提示，不清空页面。 */
async function load(silent = false, forceRefresh = false) {
  const startedAt = performance.now()
  if (!silent) loading.value = true
  loadError.value = null

  /*
    关键：结果先存在局部变量里，等满最短可见时长再落到 report 上。
    加载态的渲染条件是 `loading && !report` —— 一旦 report 先被赋值，
    即使 loading 还是 true，加载动画也已经卸载了，等于没有加载过程。
    （早期写法就是在这里直接 `report.value = await ...`，所以接口 30ms 返回时
    整段动画只存在 0.2 秒，肉眼看就是「白屏一下，内容突然出现」。）
  */
  let next: TeacherDailyReport | null = null
  try {
    const data = await getTeacherDailyReport(forceRefresh)
    if (data) {
      next = data
    } else {
      // 后端返回空体（极少见）：当成一次失败，避免页面停在空白
      loadError.value = EMPTY_BODY_TIP
    }
  } catch (e) {
    loadError.value = describeError(e)
  }

  // 首次载入等够 800ms：形象浮动周期 3.4s、光圈呼吸 2.6s，短于 0.5s 根本看不出在动。
  // 静默刷新（下拉 / 换一批）不拖着用户，直接出结果。
  if (!silent) {
    const rest = MIN_LOADING_MS - (performance.now() - startedAt)
    if (rest > 0) await new Promise((resolve) => setTimeout(resolve, rest))
  }

  if (next) {
    report.value = next
  } else if (!silent) {
    report.value = null
  } else if (report.value) {
    // 已有内容时（下拉刷新 / 换一批）不清空，改成轻提示，用户手上的内容不消失
    ElMessage.warning('刷新没成功，先显示上一次的重点')
  }

  loading.value = false
}

/** 把各种失败形态翻译成用户能看懂的一句话 */
function describeError(e: unknown): string {
  const err = e as { response?: { status?: number; data?: { detail?: unknown } }; message?: string }
  const status = err?.response?.status
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (status === 401) return '登录已过期，请重新登录后再试'
  if (status === 403) return '当前账号没有查看今日重点的权限'
  // 404 单独说清楚：这不是「今天没内容」，是服务端根本没有这个接口。
  // 最常见的原因是后端进程还是旧的（代码改了但没重启），必须点明，否则用户只会反复点重试。
  if (status === 404) return '后端还没加载这个功能，重启后端服务后再试'
  if (status === 429) return '请求太频繁了，缓一分钟再试'
  if (status && status >= 500) return '服务临时出了点状况，稍后再试一次'
  if (!status) return '网络连接不上，检查一下网络后再试'
  return '生成过程中断了，重试一次通常就能好'
}

/** 接口不存在（404）时的额外动作：光提示没用，要能带用户绕过去 */
const endpointMissing = computed(() => loadError.value?.includes('重启后端服务') ?? false)

/** 手动重试：清空上一次的错误再拉，按钮期间显示「正在重新整理」 */
async function manualRetry() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await load(true)
    if (!loadError.value) ElMessage.success('今日重点已重新整理')
  } finally {
    refreshing.value = false
  }
}

/** 失败兜底：与其让人卡在报错页，不如直接带去任务清单（同一批数据的原始列表） */
function seeTasksAnyway() {
  router.push({ path: '/teacher/tasks', query: { view: 'list' } })
}

/** 后端版本旧时的终极手段：整页重载，让前端重新拉一次最新构建 */
function reloadPage() {
  window.location.reload()
}

/** 重新生成：带 refresh 让服务端跳过 10 分钟缓存，真的重跑一遍文案 */
async function refresh() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await load(true, true)
    if (!loadError.value) ElMessage.success('已按最新数据重新生成')
  } finally {
    refreshing.value = false
  }
}

/** 一键办结：只对服务端标记为低风险的任务开放 */
const completingId = ref('')
async function completeTask(a: TeacherReportAction) {
  if (!a.task_id || completingId.value) return
  completingId.value = a.id
  try {
    await updateTeacherTask(a.task_id, { status: 'done' })
    doneIds.add(a.id)
    ElMessage.success('已办结')
    await Promise.all([load(true), loadTasks()])
    emitDataChange(['teacher-tasks', 'teacher-students'])
  } catch {
    ElMessage.error('办结失败，请稍后重试')
  } finally {
    completingId.value = ''
  }
}

/** AI 建议 → 直接建一条今天到期的任务 */
const addedSet = reactive(new Set<number>())
const addingIdx = ref(-1)
async function addSuggestion(s: TeacherReportSuggestion, i: number) {
  if (addingIdx.value >= 0) return
  addingIdx.value = i
  try {
    await createTeacherTask({
      title: s.task_title || s.title,
      detail: s.content.replace(/==|__|\*\*/g, ''),
      student_id: s.student_id ?? undefined,
      priority: s.priority,
      due_at: toDateStr(new Date()),
      source_type: 'ai_suggest',
    })
    addedSet.add(i)
    ElMessage.success('已加入今日任务')
    await Promise.all([load(true), loadTasks()])
    emitDataChange(['teacher-tasks', 'teacher-students'])
  } catch {
    ElMessage.error('添加失败，请稍后重试')
  } finally {
    addingIdx.value = -1
  }
}

/* ================= 今天的任务 =================
   本页只承担「今天要做什么」：不再提供前后翻日期的日程条，也不再内嵌全部历史任务。
   取数仍是一次列表请求（100 条上限内），再按截止日切出今天与逾期——
   后端 due=today 只返回未办结的，会把今天已经勾掉的任务藏起来，
   而这里要显示「2/7 已办结」，所以必须自己按日期分。 */
const allTasks = ref<TeacherTask[]>([])
/** 逾期未办默认收起：今天才是主线，逾期按需并进来 */
const showOverdue = ref(false)
/** 正在办结的那一行，避免连点 */
const busyRowId = ref(0)

const todayStr = toDateStr(new Date())
/** 清单行里用单字标签：圆点已经表示「优先级」，再写三个字会把元信息挤成一片 */
const PRIORITY_SHORT: Record<string, string> = { high: '高', mid: '中', low: '低' }
function taskDue(t: TeacherTask): Date | null {
  if (!t.due_at) return null
  const d = new Date(t.due_at)
  return Number.isNaN(d.getTime()) ? null : d
}
function taskDueDate(t: TeacherTask): string | null {
  const d = taskDue(t)
  return d ? toDateStr(d) : null
}
/** 逾期文案：后端只存日期，所以给「逾期几天 + 哪一天」，比「几点」有用 */
function overdueText(t: TeacherTask): string {
  const d = taskDue(t)
  if (!d) return '逾期'
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(d)
  due.setHours(0, 0, 0, 0)
  const days = Math.round((today.getTime() - due.getTime()) / 86400000)
  const md = `${due.getMonth() + 1}月${due.getDate()}日`
  return days > 0 ? `逾期 ${days} 天 · ${md}` : md
}

// 今天到期的 + 没定时间的（浮在池子里的待办，也属于今天该看到的）
const todayTasks = computed(() =>
  allTasks.value.filter((t) => {
    const d = taskDueDate(t)
    return d === todayStr || d === null
  })
)
const overdueTasks = computed(() => allTasks.value.filter((t) => t.overdue && t.status !== 'done'))
const overdueCount = computed(() => overdueTasks.value.length)
const todayTotal = computed(() => todayTasks.value.length)
const todayDone = computed(() => todayTasks.value.filter((t) => t.status === 'done').length)
const todayRate = computed(() =>
  todayTotal.value ? Math.round((todayDone.value / todayTotal.value) * 100) : 0
)

const PRIORITY_RANK: Record<string, number> = { high: 0, mid: 1, low: 2 }

/** 三组：逾期未办（按需） / 待办 / 已办结。按状态分组是因为这一页回答的是「还剩什么没做」。 */
const boardGroups = computed(() => {
  const buckets: { key: string; title: string; tone: string; items: TeacherTask[] }[] = [
    { key: 'overdue', title: '逾期未办', tone: 'danger', items: [] },
    { key: 'todo', title: '待办', tone: '', items: [] },
    { key: 'done', title: '已办结', tone: 'quiet', items: [] },
  ]
  if (showOverdue.value) buckets[0].items = overdueTasks.value.slice()
  const inOverdue = new Set(buckets[0].items.map((t) => t.id))

  for (const t of todayTasks.value) {
    if (inOverdue.has(t.id)) continue
    if (t.status === 'done') buckets[2].items.push(t)
    else buckets[1].items.push(t)
  }

  // 待办：高优先级在前，同档按截止日（没定日期的排最后）
  buckets[1].items.sort((a, c) => {
    const pr = (PRIORITY_RANK[a.priority || 'mid'] ?? 1) - (PRIORITY_RANK[c.priority || 'mid'] ?? 1)
    if (pr !== 0) return pr
    return (a.due_at || '9999').localeCompare(c.due_at || '9999')
  })
  buckets[0].items.sort((a, c) => (a.due_at || '').localeCompare(c.due_at || ''))

  return buckets.filter((b) => b.items.length)
})

async function loadTasks() {
  try {
    allTasks.value = await getTeacherTasks({ limit: 100, offset: 0 } as never)
  } catch {
    /* 清单拉取失败保持空态，日报本体不受影响 */
  }
}

/** 行内直接勾掉：先本地置位给即时反馈，再用服务端结果校准 */
async function finishTask(t: TeacherTask) {
  if (busyRowId.value) return
  busyRowId.value = t.id
  const prev = t.status
  t.status = 'done'
  try {
    await updateTeacherTask(t.id, { status: 'done' })
    ElMessage.success('已办结')
    await Promise.all([load(true), loadTasks()])
    emitDataChange(['teacher-tasks', 'teacher-students'])
  } catch {
    t.status = prev
    ElMessage.error('办结失败，请稍后重试')
  } finally {
    busyRowId.value = 0
  }
}

const createVisible = ref(false)
const editingTask = ref<TeacherTask | null>(null)
const presetDueAt = ref<string | null>(null)
const presetTitle = ref('')
const presetStudent = ref<{ id: number; name: string } | null>(null)

function pad(n: number) {
  return String(n).padStart(2, '0')
}
function toDateStr(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

async function refreshAll() {
  await Promise.all([load(true), loadTasks()])
  // 任务已变更：通知工作台等页面同步刷新
  emitDataChange(['teacher-tasks', 'teacher-students'])
}

function openCreate() {
  editingTask.value = null
  // 入口就在「今天的任务」里，默认把截止日定成今天，省一次选择
  presetDueAt.value = todayStr
  presetTitle.value = ''
  presetStudent.value = null
  createVisible.value = true
}
function openEditTask(task: TeacherTask) {
  editingTask.value = task
  presetDueAt.value = null
  createVisible.value = true
}

/** 移动端下拉刷新 */
const pull = usePullRefresh(refreshAll, { enabled: () => isMobile.value })

/**
 * 「去处理」链接形如 /teacher/tasks?open-task=12（今日重点卡片用 ?task=12）：
 * 先展开清单，再按 id 取到任务并打开编辑弹窗，老师不用自己再找一遍。
 */
async function openTaskFromQuery() {
  const raw = route.query['open-task'] ?? route.query.task
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  if (!id) return
  if (route.query.filter === 'overdue') showOverdue.value = true
  try {
    // 优先从已加载的列表里拿，避免多一次请求
    let target = allTasks.value.find((t) => t.id === id)
    if (!target) {
      const list = await getTeacherTasks({ limit: 100, offset: 0 } as never)
      target = list.find((t) => t.id === id)
    }
    if (target) openEditTask(target)
  } catch {
    /* 打不开就保持在清单页，用户仍可手动找到该任务 */
  }
}

// 智能体 / 其他页面变更了任务或学生：立即刷新任务清单
// （AI 日报重算较慢，这里只刷清单，日报仍由页面自身的刷新入口触发）
const offDataChange = onDataChange(['teacher-tasks', 'teacher-students'], () => {
  loadTasks()
})
onUnmounted(() => {
  offDataChange()
})

onMounted(async () => {
  // ?filter=overdue 仍然认：老链接直接把逾期那组展开，而不是跳到不存在的筛选页
  if (route.query.filter === 'overdue') showOverdue.value = true
  await Promise.all([load(), loadTasks()])

  // 消息页「加入任务」跳转：?student_id=&student_name=&title=
  const sid = route.query.student_id
  const title = route.query.title
  if (sid || title) {
    editingTask.value = null
    presetDueAt.value = toDateStr(new Date())
    if (typeof title === 'string') presetTitle.value = title
    if (sid) presetStudent.value = { id: Number(sid), name: String(route.query.student_name || '') }
    createVisible.value = true
    return
  }
  await openTaskFromQuery()
})

/** 日报里点「去处理」跳到本页时，路由已挂载不会重新 onMounted，靠 watch 补一次 */
watch(
  () => route.query['open-task'] ?? route.query.task,
  (v) => {
    if (v) openTaskFromQuery()
  }
)
</script>

<style scoped>
.tui-page.pull-enabled { overscroll-behavior-y: contain; }

/* ================= 整页骨架：去卡片化 =================
   原来整页是「卡 + 卡 + 卡 + 卡」：抬头一张、运势一张、每段正文一张、清单再一张。
   边框 + 投影把页面切成一堆同样重要的小块，反而看不出哪里最该看。
   现在全页只有两层结构：发丝线切分段落，字阶区分层级。
   卡片只留给真正「可点的一整条」——也就是任务条目本身不铺底，靠时间列和留白读成清单。 */
.tr-content {
  display: flex;
  flex-direction: column;
}

/*
  载入态 → 内容的衔接：加载动画结束后不要「啪」地换成满屏卡片。
  给内容区各区块加一段很短的上浮淡入（0.32s / 逐块 40ms 错峰），
  让用户的视线自然从形象落到第一个区块上，读起来像一个加载过程而不是页面跳变。
*/
.tr-content > section {
  animation: tr-rise 0.32s var(--tui-ease) both;
}
.tr-content > section:nth-child(2) { animation-delay: 40ms; }
.tr-content > section:nth-child(3) { animation-delay: 80ms; }
.tr-content > section:nth-child(n + 4) { animation-delay: 110ms; }

@keyframes tr-rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tr-content > section { animation: none; }
}

/* ================= 载入 / 失败态（产品形象，无卡片） ================= */
.tr-error-actions {
  display: flex;
  justify-content: center;
  gap: 18px;
  padding: 0 0 28px;
  flex-wrap: wrap;
}
.tr-error-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: 0;
  background: transparent;
  padding: 4px 6px;
  font-size: 12.5px;
  color: var(--tui-text-tertiary);
  cursor: pointer;
  transition: color 0.16s var(--tui-ease);
}
.tr-error-link:hover { color: var(--tui-brand); }

/* ================= 抬头 =================
   一行元信息 + 一句问候 + 一句当日基调，不加任何底色盒子。
   天气与「重新整理」都收进右上角的小控件里：刷新是低频动作，不该占一个卡片位。 */
.tr-hero { padding: 4px 2px 16px; }

.tr-hero-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  min-height: 30px;
  font-size: 11.5px;
  line-height: 1.4;
  color: var(--tui-text-tertiary);
}
.tr-hero-date { font-weight: 600; color: var(--tui-text-secondary); font-variant-numeric: tabular-nums; }
.tr-hero-tools { margin-left: auto; display: flex; align-items: center; gap: 1px; }

/* 刷新中的状态行：只在刷新期间出现，最多占一半宽度，避免把天气/按钮挤到换行 */
.tr-hero-status {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 132px;
  margin-right: 4px;
  font-size: 11.5px;
}
.tr-hero-status :deep(.al-text) { white-space: nowrap; }

.tr-hero-weather {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 5px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-text-secondary);
  cursor: pointer;
  transition: background 0.16s var(--tui-ease);
}
.tr-hero-weather:hover { background: rgba(15, 17, 21, 0.05); }
.tr-hero-weather-emoji { font-size: 13px; line-height: 1; }
.tr-hero-weather-desc { color: var(--tui-text-quiet); }

.tr-hero-refresh {
  width: 30px;
  height: 30px;
  margin-right: -5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--tui-text-quiet);
  cursor: pointer;
  transition: color 0.16s var(--tui-ease), background 0.16s var(--tui-ease);
}
.tr-hero-refresh:hover:not(:disabled) { color: var(--tui-text); background: rgba(15, 17, 21, 0.05); }
.tr-hero-refresh:disabled { cursor: default; opacity: 0.5; }
.tr-hero-refresh .is-spin { animation: tr-spin 0.9s linear infinite; }
@keyframes tr-spin { to { transform: rotate(360deg); } }

.tr-hero-greet {
  margin: 8px 0 0;
  font-size: var(--tui-fs-title);
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.3px;
  color: var(--tui-text);
}

/* 当日基调：左侧一根语义色竖线。比小圆点安静，也不会和正文的圆点抢注意力。 */
.tr-hero-tone {
  display: flex;
  align-items: stretch;
  gap: 9px;
  margin: 9px 0 0;
  max-width: 54ch;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--tui-text-secondary);
}
.tr-hero-tone-bar { flex: 0 0 2px; width: 2px; border-radius: 2px; background: var(--tui-text-quiet); }
.tr-hero-tone.is-danger .tr-hero-tone-bar { background: var(--tui-danger); }
.tr-hero-tone.is-warn .tr-hero-tone-bar { background: #d9871a; }
.tr-hero-tone.is-calm .tr-hero-tone-bar { background: var(--tui-success); }
.tr-hero-tone-txt { min-width: 0; }

/* ================= 今日运势（贴边签文，不是卡片） =================
   它和正文的层级本来就不同：正文是「要做的事」，运势是一句题外话。
   用一条通栏的浅底色把这一小段隔出来，比再套一张白卡更省眼睛。 */
.tr-fortune {
  margin: 0 -14px;
  padding: 15px 14px 17px;
  border-top: 1px solid var(--tui-hairline);
  border-bottom: 1px solid var(--tui-hairline);
  background: #f8faff;
}
.tr-fortune.is-great { background: #fffcf2; }
.tr-fortune.is-good { background: #fffdf6; }
.tr-fortune.is-soft { background: #f8f9fb; }

.tr-fortune-head { display: flex; align-items: baseline; gap: 8px; }
.tr-fortune-label { font-size: 11.5px; font-weight: 600; letter-spacing: 0.04em; color: var(--tui-text-tertiary); }
.tr-fortune-level { font-size: 13px; font-weight: 700; color: var(--tui-brand-strong); }
.tr-fortune.is-great .tr-fortune-level,
.tr-fortune.is-good .tr-fortune-level { color: #b45309; }
.tr-fortune.is-soft .tr-fortune-level { color: var(--tui-text-secondary); }
.tr-fortune-key { font-size: 11.5px; color: var(--tui-text-quiet); }
.tr-fortune-key::before { content: '·'; margin-right: 6px; }
.tr-fortune-score {
  margin-left: auto;
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.tr-fortune-score small { margin-left: 1px; font-size: 10.5px; font-weight: 400; color: var(--tui-text-quiet); }
.tr-fortune-meter {
  height: 2px;
  margin: 10px 0 12px;
  border-radius: 2px;
  background: rgba(15, 17, 21, 0.07);
  overflow: hidden;
}
.tr-fortune-meter i {
  display: block;
  height: 100%;
  border-radius: 2px;
  background: var(--tui-text-quiet);
  transition: width 0.5s var(--tui-ease);
}
.tr-fortune.is-great .tr-fortune-meter i,
.tr-fortune.is-good .tr-fortune-meter i { background: #d9a13c; }
.tr-fortune.is-mid .tr-fortune-meter i { background: var(--tui-brand); }
.tr-fortune-summary { margin: 0 0 10px; font-size: 12.5px; line-height: 1.7; color: var(--tui-text-secondary); }
.tr-fortune-meta { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 11px; color: var(--tui-text-quiet); }

/* ================= 正文段落 ================= */
.tr-sec { padding: 15px 2px 17px; border-bottom: 1px solid var(--tui-hairline); }
.tr-sec-head { display: flex; align-items: baseline; gap: 9px; margin-bottom: 9px; }
.tr-sec-no {
  flex-shrink: 0;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.tr-sec-title { margin: 0; font-size: 14px; font-weight: 600; letter-spacing: -0.1px; color: var(--tui-text); }
.tr-sec-more {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  cursor: pointer;
}
.tr-sec-more:hover { color: var(--tui-brand); }
.tr-sec-count { margin-left: auto; font-size: 11.5px; color: var(--tui-text-quiet); font-variant-numeric: tabular-nums; }

.tr-sec-list { display: flex; flex-direction: column; gap: 7px; margin: 0; padding: 0; list-style: none; }
.tr-sec-line { position: relative; padding-left: 12px; font-size: 13px; line-height: 1.75; color: var(--tui-text-secondary); }
.tr-sec-line::before {
  content: '';
  position: absolute;
  left: 1px;
  top: 10px;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #ccd1d9;
}

/* ================= 可操作条目 / AI 建议 =================
   卡片外壳交给设计系统的 .tui-list（白底 + 1px 边 + 14 圆角 + shadow-1），
   这里只补本页特有的三样：图标底色、右操作胶囊、说明行。 */
.tr-list { margin-top: 10px; }

/* 图标块按来源着色：预警 / 逾期=红、请假=橙、今日到期=蓝 */
.tr-act-icon.is-alert,
.tr-act-icon.is-overdue { background: var(--tui-danger-soft); color: var(--tui-danger); }
.tr-act-icon.is-leave { background: var(--tui-warn-soft); color: var(--tui-warn); }
.tr-act-icon.is-due { background: var(--tui-brand-soft); color: var(--tui-brand-strong); }

.tr-act-main {
  align-items: flex-start;
  padding: 0;
  border: 0;
  background: none;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.tr-act-title {
  display: block;
  max-width: 100%;
  font-size: 13.5px;
  font-weight: 500;
  line-height: 1.45;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tr-act.is-done .tr-act-title { text-decoration: line-through; color: var(--tui-text-quiet); }
.tr-act-desc {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  min-width: 0;
}
.tr-act-sub { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* 学生名与来源之间补一个「·」，否则两段文字会读成一句话 */
.tr-act-sub + .tr-act-sub::before { content: '·'; margin-right: 6px; color: var(--tui-text-quiet); }
.tr-act-btns { display: flex; flex-shrink: 0; align-items: center; }

/* 右操作胶囊：比 el-button 小一档，跟行高对齐；只有主操作才上品牌色 */
.tr-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--tui-border-strong);
  border-radius: 999px;
  background: var(--tui-surface);
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), border-color 0.15s var(--tui-ease);
}
.tr-pill:hover:not(:disabled) { background: var(--tui-surface-muted); border-color: #d8dbe0; }
.tr-pill:disabled { opacity: 0.6; cursor: default; }
.tr-pill.is-primary { border-color: transparent; background: var(--tui-brand-soft); color: var(--tui-brand-strong); }
.tr-pill.is-primary:hover:not(:disabled) { background: #e2ebff; }
.tr-pill.is-done { border-color: transparent; background: var(--tui-success-soft); color: var(--tui-success); }

/* AI 建议：一条一段，标题行右侧「＋加入」，正文单独铺满一行 */
.tr-sug { padding: 12px 16px; }
.tr-sug + .tr-sug { border-top: 1px solid var(--tui-hairline); }
.tr-sug-top { display: flex; align-items: flex-start; gap: 10px; }
.tr-sug-title {
  flex: 1;
  min-width: 0;
  margin: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
  color: var(--tui-text);
}
.tr-sug-name { min-width: 0; }
.tr-sug-text { margin: 5px 0 0; font-size: 12px; line-height: 1.65; color: var(--tui-text-secondary); }

/* ================= 今天的任务 =================
   全页唯一的卡片。理由：这里是唯一「要反复点、反复勾」的地方，
   给它一点体积不会和正文抢，反而能一眼认出「这块可以动」；
   卡内仍是发丝线分组的行，不把每条任务再套一张小卡。 */
.tr-today { padding-bottom: 20px; }
/* 标题行右侧：计数 + 新增，放在同一个组里，没数据时按钮自然贴到最右 */
.tr-today .tr-sec-head { align-items: center; }
.td-head-right { margin-left: auto; display: inline-flex; align-items: center; gap: 10px; }
.td-add {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 26px;
  padding: 0 10px 0 8px;
  border: 1px solid #d3e0fb;
  border-radius: 8px;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease), border-color 0.15s var(--tui-ease), transform 0.12s var(--tui-ease);
}
.td-add:hover { background: #e2ebff; border-color: #bfd4fa; }
.td-add:active { transform: scale(0.97); }

.td-card {
  margin-top: 10px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  background: var(--tui-surface);
  box-shadow: var(--tui-shadow-1);
  overflow: hidden;
}

/* 完成度：细进度条一行，数字贴在右边（.tui-progress 自带 6px 轨道） */
.td-progrow { padding: 12px 14px 6px; }

/* 分组头：浅色窄条，比彩色胶囊安静，但能切出「上午/下午/晚上」 */
.td-group-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 6px 14px;
  background: var(--tui-surface-muted);
  border-top: 1px solid var(--tui-hairline);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--tui-text-tertiary);
}
/* 第一组紧贴完成度那一行，不再补顶线，否则卡片顶端会多出一道短横线 */
.td-group:first-of-type .td-group-head { border-top: 0; }
.td-group-head.is-danger { background: var(--tui-danger-soft); color: var(--tui-danger); }
.td-group-head.is-quiet { color: var(--tui-text-quiet); }
.td-group-n { font-variant-numeric: tabular-nums; color: var(--tui-text-quiet); }
.td-group-head.is-danger .td-group-n { color: var(--tui-danger); }

/* 一行 = 时刻 + 标题/元信息 + 勾选；行与行之间只有一条发丝线 */
.td-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 12px;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  transition: background 0.15s var(--tui-ease);
}
.td-row + .td-row { border-top: 1px solid var(--tui-hairline); }
.td-row:hover { background: #fafbfc; }

/* 左侧勾选：视觉 22px，用伪元素把热区撑到 38px，移动端点得准又不撑高行 */
.td-check {
  position: relative;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid var(--tui-border-strong);
  border-radius: 50%;
  background: var(--tui-surface);
  color: #fff;
  cursor: pointer;
  transition: border-color 0.15s var(--tui-ease), background 0.15s var(--tui-ease);
}
.td-check::after { content: ''; position: absolute; inset: -8px; }
.td-check:hover { border-color: var(--tui-success); background: var(--tui-success-soft); }
.td-check:disabled { opacity: 0.5; cursor: default; }
.td-check.is-on {
  border-color: var(--tui-success);
  background: var(--tui-success);
  cursor: default;
}
.td-check.is-on::after { display: none; }

.td-row-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.td-row-title {
  font-size: 13.5px;
  font-weight: 500;
  line-height: 1.45;
  color: var(--tui-text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.td-row-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--tui-text-quiet);
  overflow: hidden;
}
.td-meta { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.td-meta.is-danger { flex-shrink: 0; color: var(--tui-danger); }
.td-pri + .td-meta::before,
.td-meta + .td-meta::before { content: '·'; margin-right: 6px; color: var(--tui-text-quiet); }
.td-meta.is-danger + .td-meta::before { color: rgba(217, 45, 32, 0.4); }

/* 优先级：小圆点 + 单字，只有「高」用红色 */
.td-pri {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--tui-text-tertiary);
}
.td-pri::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--tui-text-quiet); }
.td-pri.is-high { color: var(--tui-danger); }
.td-pri.is-high::before { background: var(--tui-danger); }
.td-pri.is-mid::before { background: var(--tui-brand); }
.td-pri.is-low::before { background: #c3c8d0; }

/* 行尾的箭头只是「可以点开」的提示，不参与点击 */
.td-go { color: #c8ccd3; }

.td-row.is-done .td-row-title { text-decoration: line-through; color: var(--tui-text-quiet); }
.td-row.is-done .td-row-meta { opacity: 0.5; }
.td-row.is-done .td-go { opacity: 0; }

/* 逾期：默认收成卡片底部一行，点开才并入上面同一套行 */
.td-ovd {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 14px;
  border: 0;
  border-top: 1px solid var(--tui-hairline);
  background: transparent;
  font-family: inherit;
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s var(--tui-ease);
}
.td-ovd:hover { background: var(--tui-surface-muted); }
.td-ovd-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--tui-danger); flex-shrink: 0; }
.td-ovd-t { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-ovd-act { margin-left: auto; flex-shrink: 0; color: var(--tui-text-quiet); }
.td-ovd .el-icon { flex-shrink: 0; color: var(--tui-text-quiet); transition: transform 0.2s var(--tui-ease); }
.td-ovd .el-icon.is-open { transform: rotate(90deg); }

/* 空态：一句话 + 一个虚线按钮，不用插画占掉半屏 */
.td-empty { padding: 28px 18px 26px; text-align: center; }
.td-empty-t { margin: 0; font-size: 13px; font-weight: 600; color: var(--tui-text-secondary); }
.td-empty-d { margin: 5px 0 14px; font-size: 11.5px; color: var(--tui-text-quiet); }
.td-empty-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 14px;
  border: 1px dashed var(--tui-border-strong);
  border-radius: 9px;
  background: transparent;
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s var(--tui-ease), color 0.15s var(--tui-ease), background 0.15s var(--tui-ease);
}
.td-empty-btn:hover {
  border-color: var(--tui-brand);
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
}

/* ================= 页脚 ================= */
.tr-footnote { margin: 14px 0 6px; font-size: 11px; line-height: 1.6; color: var(--tui-text-quiet); text-align: center; }

@media (min-width: 768px) {
  .tr-hero { padding: 6px 2px 18px; }
  /* 桌面端页边距是 28px，贴边签文要跟着改 */
  .tr-fortune { margin: 0 -28px; padding: 16px 28px 18px; }
  /* 这是一份「简报」而不是仪表盘：桌面端不铺满整屏。
     用 :global 前缀是为了压过 teacher-ui.css 里给 .tui-content 写的 max-width:none，
     否则 1440 屏下每行文字会被拉到 1200px 宽，行尾的按钮也会飘到离正文很远的地方。 */
  :global(.main-area.teacher-scope) .tr-content { width: 100%; max-width: 920px; margin-left: auto; margin-right: auto; }
  /* 桌面端行宽 920，两行式会把标题和元信息拉得很散；
     改成「标题在左、元信息贴右」的单行，读起来像表格，也不浪费横向空间。 */
  .td-row { grid-template-columns: 22px minmax(0, 1fr) 12px; gap: 12px; padding: 11px 16px; }
  .td-row-main { flex-direction: row; align-items: center; gap: 12px; }
  .td-row-title { flex: 1 1 auto; min-width: 0; display: block; white-space: nowrap; text-overflow: ellipsis; }
  .td-row-meta { flex: 0 1 auto; justify-content: flex-end; margin-left: auto; }
  .td-group-head { padding: 7px 16px; }
  .td-ovd { padding: 11px 16px; }
}

@media (max-width: 767px) {
  /* 移动端卡片贴边到 14px，把两侧留白还给内容 */
  .td-row { padding: 12px 12px; }
  .td-group-head { padding: 6px 12px; }
  .td-ovd { padding: 11px 12px; }
}

/* ================= 今日待办条目：描述 + 快捷动作 =================
   原来的副标题只有学生名/来源，看不出「到底要处理什么」；
   现在第一行是对象，第二行是说清事项与处理方式的描述。 */
.tm-pc-s { display: flex; flex-direction: column; gap: 1px; margin-top: 4px; }
.tm-pc-who { font-size: 11px; font-weight: 650; color: var(--tm-ink2); }
.tm-pc-desc { font-size: 11px; line-height: 1.5; color: var(--tm-ink3); }
.tm-pc-go {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px 9px;
  border-radius: 8px;
  border: 1px solid var(--tm-line);
  background: var(--tm-surf2, #f6f7f9);
  font-family: inherit;
  font-size: 11px;
  font-weight: 650;
  color: var(--tm-brand-deep, #1f2430);
  cursor: pointer;
}
.tm-pp-tip-ic {
  display: inline-flex;
  align-items: center;
  color: #4a6fa5;
  flex: 0 0 auto;
}

/* ================= 今日重点：报告式版面 =================
   封面（一级标题 / 导语 / 形象图 / 三个关键数字）→ 分档章节（二级标题）
   → 条目（编号 + 标签 + 短标题 + 唯一入口）→ 页脚依据。
   整页沿用页面底色、无外框，靠字号与编号建立层级，不再堆卡片。 */
.rp-report {
  /* 不铺底、不描边：完全沿用页面底色，底部与移动端其它内容自然衔接 */
  background: transparent;
  padding: 0 16px calc(22px + env(safe-area-inset-bottom));
}

/* 封面 */
.rp-cover { padding: 18px 0 16px; }
.rp-cover-top { display: flex; align-items: center; gap: 8px; }
.rp-logo { width: 22px; height: 22px; flex: 0 0 22px; object-fit: contain; }
.rp-kicker {
  display: inline-flex;
  align-items: center;
  color: #8b93a1;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.rp-date { margin-left: auto; font-size: 11.5px; color: #8b93a1; }
.rp-h1 {
  margin: 10px 0 0;
  font-size: 27px;
  line-height: 1.15;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: #15181e;
}
.rp-cover-body { display: flex; align-items: flex-start; gap: 12px; margin-top: 10px; }
.rp-cover-text { flex: 1; min-width: 0; }
.rp-lead { margin: 0; font-size: 13px; line-height: 1.75; color: #4b5563; }
.rp-sign { margin: 8px 0 0; font-size: 11px; color: #9aa1ad; }
.rp-cover-img { width: 84px; height: 84px; flex: 0 0 84px; object-fit: contain; }
.rp-stats { display: flex; gap: 16px; margin-top: 12px; }
.rp-stat {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.rp-stat b {
  font-size: 19px;
  font-weight: 800;
  line-height: 1.2;
  color: #171a20;
  font-variant-numeric: tabular-nums;
}
.rp-stat span { font-size: 10.5px; color: #7c8494; }

/* 二级章节：编号 + 标题 + 数量，章节之间用发丝分割线区分 */
.rp-sec {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid #cfd4dd;
}
.rp-sec-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.rp-sec-no {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #9aa1ad;
  font-variant-numeric: tabular-nums;
}
.rp-h2 { margin: 0; font-size: 18px; font-weight: 800; color: #15181e; }
.rp-sec-count { margin-left: auto; font-size: 11px; color: #8b93a1; }
.rp-sec-desc { margin: 6px 0 0; font-size: 11.5px; color: #8b93a1; }

/* 条目：编号 + 标签/标题 + 唯一入口 */
.rp-list { margin-top: 8px; display: flex; flex-direction: column; }
.rp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 0;
}
/* 同组事项之间加一条发丝线，条目多时也能看清边界 */
.rp-item + .rp-item {
  border-top: 1px solid #dde1e8;
}
.rp-item-no {
  flex: 0 0 22px;
  width: 22px;
  font-size: 11px;
  font-weight: 800;
  color: #b3b9c5;
  font-variant-numeric: tabular-nums;
}
.rp-item-bd { flex: 1; min-width: 0; }
.rp-item-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.rp-kind { font-size: 10px; font-weight: 700; color: #8b93a1; }
.rp-flag {
  display: inline-flex;
  align-items: center;
  color: #6b7280;
  font-size: 10.5px;
  font-weight: 700;
  white-space: nowrap;
}
.rp-item-src { font-size: 11px; color: #6b7280; }
.rp-item-done { margin-left: auto; font-size: 10.5px; font-weight: 700; color: #8b93a1; }
.rp-item-t {
  margin: 4px 0 0;
  font-size: 13.5px;
  font-weight: 700;
  line-height: 1.45;
  color: #171a20;
}
.rp-item-sub {
  margin: 3px 0 0;
  font-size: 11.5px;
  line-height: 1.55;
  color: #7c8494;
}
.rp-item.is-done .rp-item-t { color: #9aa1ad; text-decoration: line-through; }

.rp-btn {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 7px 12px;
  border: 0;
  border-radius: 8px;
  background: #f1f2f5;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  color: #2b3140;
  cursor: pointer;
}
.rp-btn-main { background: #171a20; color: #fff; }
.rp-btn-main.is-done {
  background: #eef0f3;
  color: #8a91a0;
  cursor: default;
}

/* 批量办结：章节尾注，不另起一张卡 */
.rp-batch {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  padding: 4px 0;
  font-size: 11.5px;
  line-height: 1.55;
  color: #7c8494;
}
.rp-batch-btn {
  flex: 0 0 auto;
  margin-left: auto;
  padding: 5px 10px;
  border: 0;
  border-radius: 8px;
  background: #f1f2f5;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 700;
  color: #2b3140;
  cursor: pointer;
}
.rp-empty {
  margin-top: 14px;
  padding: 4px 0;
  text-align: left;
  font-size: 12px;
  color: #8b93a1;
}

/* AI 建议：形象图 + 建议正文 + 加入按钮 */
.rp-sug-img { width: 44px; height: 44px; flex: 0 0 44px; object-fit: contain; }
.rp-sug-title { font-size: 12.5px; font-weight: 700; color: #171a20; }
.rp-sug-desc { margin: 4px 0 0; font-size: 11.5px; line-height: 1.6; color: #6b7280; }

/* 页脚依据 */
.rp-foot-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 24px;
  padding-top: 12px;
  font-size: 11px;
  line-height: 1.6;
  color: #9aa1ad;
}
.rp-foot-logo { width: 16px; height: 16px; flex: 0 0 16px; object-fit: contain; margin-top: 1px; }
</style>
