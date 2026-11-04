<template>
  <div class="tui-page schedule-page">
    <SubPageHeader title="我的课表" fallback="/teacher" />

    <!-- ============================================================
         移动端 · 定稿版「周网格」
         一屏读完：班级/学期 → 5 天网格 → 本周课时 → 今天
         ============================================================ -->
    <div v-if="isMobile" class="tm-page tm-m">
      <!-- 课表不是两套功能：默认直接看「我的授课」，需要时才切到「查课表」查班级/同事 -->
      <div class="tm-filter tm-filter-main">
        <TuiSegmented
          v-model="mobileTab"
          :options="mobileTabOptions"
          @update:model-value="onMobileTab"
        />
      </div>
      <div class="tm-filter">
        <TuiSegmented
          v-if="mobileTab === 'search'"
          v-model="mobileSearchMode"
          :options="mobileSearchOptions"
          class="tm-search-mode"
          @update:model-value="onMobileSearchMode"
        />
        <el-select
          v-if="mobileTab === 'search' && mobileSearchMode === 'class'"
          v-model="classGroupId"
          placeholder="搜索班级"
          filterable
          clearable
          size="small"
          style="flex: 1"
          @change="load"
        >
          <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select
          v-if="mobileTab === 'search' && mobileSearchMode === 'teacher'"
          v-model="teacherName"
          placeholder="选择任课教师"
          filterable
          clearable
          size="small"
          style="flex: 1"
          @change="load"
        >
          <el-option v-for="t in teacherList" :key="t.name" :label="t.is_me ? `${t.name}（我）` : t.name" :value="t.name" />
        </el-select>
        <el-select v-model="semester" size="small" style="width: 116px" @change="load">
          <el-option v-for="s in semesters" :key="s" :label="s" :value="s" />
        </el-select>
      </div>

      <p class="tm-sched-hint">
        课表用于确认今天 / 本周要上的课，点名和课程资料都从这里进入；「查课表」只是临时查班级或同事的安排。
      </p>

      <el-skeleton v-if="loading && !courses.length" :rows="6" animated style="padding: 0 14px" />

      <!-- 我的授课为空：说明真实情况，不假装用户漏选了班级 -->
      <div v-if="mobileTab === 'mine' && !loading && !courses.length" class="tm-empty">
        本学期暂无授课安排
      </div>

      <!-- 没选班级：给三张班卡，不要甩空网格 -->
      <template v-else-if="isEmptySelection">
        <div class="tm-sec">
          <span class="tm-sec-t">先选一个班级</span>
          <span class="tm-sec-m">共 {{ classOptions.length }} 个班有课</span>
        </div>
        <div class="tm-rows">
          <button
            v-for="c in pickClassCards.slice(0, 4)"
            :key="c.id"
            type="button"
            class="tm-row tm-row-tap"
            @click="pickClass(c.id)"
          >
            <span class="tm-r-ic">班</span>
            <div class="tm-r-bd">
              <div class="tm-r-t"><span>{{ c.name }}</span><span v-if="c.isMine" class="tm-tag tm-brand">我教的</span></div>
              <div class="tm-r-s">{{ c.courseCount }} 门课 · {{ c.studentCount }} 人{{ c.college ? ' · ' + c.college : '' }}</div>
            </div>
            <div class="tm-r-e"><span class="tm-ai-a">查看 ›</span></div>
          </button>
        </div>
      </template>

      <template v-else>
        <!-- 周网格（周一到周五） -->
        <div class="tm-gridwk">
          <div class="tm-gw-hd">
            <b></b>
            <b v-for="d in mDays" :key="d.value" :class="{ 'tm-on': d.value === todayWeekday }">
              周{{ d.label.slice(1) }}<i>{{ d.value === todayWeekday ? '今天' : '&nbsp;' }}</i>
            </b>
          </div>
          <div class="tm-gw-bd">
            <template v-for="p in mPeriods" :key="`p-${p}`">
              <div class="tm-gw-t">{{ p }}</div>
              <div
                v-for="d in mDays"
                :key="`${d.value}-${p}`"
                class="tm-gw-c"
                :class="cellKind(d.value, p)"
                @click="onCellTap(d.value, p)"
              >
                <template v-if="mCell(d.value, p)">
                  <b>{{ mCell(d.value, p)!.name.slice(0, 4) }}</b>
                  <span>{{ mCell(d.value, p)!.location?.slice(0, 4) }}</span>
                </template>
              </div>
            </template>
          </div>
          <div class="tm-gw-lg">
            <span><i style="background: #e9f0ff; border: 1px solid #d5e2fb"></i>我的课</span>
            <span><i style="background: #f5f7fc; border: 1px solid #e6ecf6"></i>其他教师</span>
          </div>
        </div>

        <!-- 本周课时 -->
        <div class="tm-sec" style="margin-top: 9px">
          <span class="tm-sec-t">本周课时</span>
          <span class="tm-sec-m">共 {{ courses.length }} 节</span>
        </div>
        <div class="tm-wk-les">
          <div v-for="d in mDays" :key="`w-${d.value}`" class="tm-wl" :class="{ 'tm-today': d.value === todayWeekday }">
            <em>周{{ d.label.slice(1) }}</em><b>{{ mWeekCount(d.value) }}</b>
          </div>
          <div v-if="mWeekendCount" class="tm-wl"><em>周末</em><b>{{ mWeekendCount }}</b></div>
        </div>

        <!-- 今天 -->
        <div v-if="mTodayList.length" class="tm-sec" style="margin-top: 9px">
          <span class="tm-sec-t">今天 · {{ weekdayLabel(todayWeekday) }}</span>
          <span class="tm-sec-m">{{ mTodayList.length }} 节</span>
        </div>
        <div v-if="mTodayList.length" class="tm-rows">
          <div v-for="c in mTodayList" :key="c.id" class="tm-row">
            <span class="tm-r-ic">{{ c.start_period }}</span>
            <div class="tm-r-bd" @click="openCourse(c)">
              <div class="tm-r-t"><span>{{ c.name }}</span></div>
              <div class="tm-r-s">{{ c.class_name }} · {{ c.location }} · {{ c.start_period }}-{{ c.end_period }} 节</div>
            </div>
            <div class="tm-r-e"><span class="tm-muted">{{ c.teacher }}</span></div>
          </div>
        </div>

        <div class="tm-tail">课表为教务公共数据，以教务排课为准</div>
      </template>
    </div>

    <div v-else class="tui-content">
      <TuiPageHero
        v-if="!isMobile"
        title="课表"
        sub="先看我的授课安排，需要时再按班级或教师查课；课表由教务排定，这里不排课"
        :icon="Calendar"
        tone="cyan"
      >
        <template v-if="overview">
          <div class="hero-pill">
            <b>{{ overview.week_course_count }}</b>
            <span>本周课时</span>
          </div>
          <div class="hero-pill">
            <b>{{ overview.total_student_count }}</b>
            <span>授课学生</span>
          </div>
          <div class="hero-pill">
            <b>{{ overview.today_course_count }}</b>
            <span>今日课程</span>
          </div>
        </template>
        <template #actions>
          <el-button :loading="loading" text @click="load">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </template>
      </TuiPageHero>

      <!-- ===== 筛选栏：视图切换 + 教师 + 学期 ===== -->
      <section class="filter-bar">
        <TuiSegmented
          :model-value="viewMode"
          :options="viewOptions"
          @update:model-value="onViewModeChange"
        />

        <div class="filter-right">
          <el-select
            v-if="viewMode === 'teacher'"
            v-model="teacherName"
            placeholder="选择任课教师"
            clearable
            filterable
            size="default"
            class="filter-teacher"
            @change="load"
          >
            <el-option
              v-for="t in teacherList"
              :key="t.name"
              :label="t.is_me ? `${t.name}（我）` : t.name"
              :value="t.name"
            >
              <div class="opt-row">
                <span class="opt-name">{{ t.name }}<span v-if="t.is_me" class="opt-me">我</span></span>
                <span class="opt-meta">{{ t.course_count }} 门 · {{ t.student_count }} 人</span>
              </div>
            </el-option>
          </el-select>

          <el-select
            v-if="viewMode === 'class'"
            v-model="classGroupId"
            placeholder="选择班级"
            clearable
            filterable
            size="default"
            class="filter-teacher"
            @change="load"
          >
            <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>

          <el-select
            v-model="semester"
            placeholder="学期"
            size="default"
            class="filter-semester"
            @change="load"
          >
            <el-option v-for="s in semesters" :key="s" :label="s" :value="s" />
          </el-select>

          <el-button v-if="viewMode === 'teacher' && teacherName" size="default" text @click="clearTeacher">
            回到我的授课
          </el-button>
        </div>
      </section>

      <!--
        刻意不在这里放 el-alert 提示：
        默认视图就是「班级课表」，一进来必然显示「正在查看（未选择班级）的完整课表」——
        一句没有信息量的废话，还占掉一整屏高度。当前在看谁，筛选栏里的下拉已经说明白了。
        只读这件事也不需要解释：页面上根本没有能改课表的按钮，用户不会误以为自己能排课。
      -->

      <el-skeleton v-if="loading && !courses.length" :rows="8" animated />

      <!--
        ===== 空选态 =====
        默认视图是「班级课表」，但没选班级时后端返回空 courses。
        原来的做法是不管有没有数据都渲染 8×7 的空网格 —— 一屏全是灰格子，
        用户看不出「是没排课」还是「我没选班」。这里改成明确的引导：
        列出我教的班，点一下就进课表，比让人去右上角找一个下拉框快得多。
      -->
      <template v-else-if="isEmptySelection">
        <section class="pick-panel">
          <div class="pick-head">
            <span class="pick-ico" aria-hidden="true">
              <el-icon :size="20"><School /></el-icon>
            </span>
            <div class="pick-head-text">
              <h2 class="pick-title">先选一个班级</h2>
              <p class="pick-sub">
                课表由教务排定，这里查看的是<b>某个班级被排成什么样</b>，
                或者<b>某位任课教师在哪几节有课</b>。选一个班级开始：
              </p>
            </div>
          </div>

          <div v-if="pickClassCards.length" class="pick-grid">
            <button
              v-for="c in pickClassCards"
              :key="c.id"
              type="button"
              class="pick-card"
              @click="pickClass(c.id)"
            >
              <span class="pick-card-top">
                <span class="pick-card-name">{{ c.name }}</span>
                <span v-if="c.isMine" class="pick-card-badge">我教的</span>
              </span>
              <span class="pick-card-meta">
                <template v-if="c.college">{{ c.college }} · </template>
                {{ c.courseCount }} 门课 · {{ c.studentCount }} 人
              </span>
              <span class="pick-card-go">查看课表 ›</span>
            </button>
          </div>
          <p v-else class="pick-empty">
            本学期还没有任何班级排课记录，可在右上角切换到「教师授课」查同事的安排。
          </p>

          <div v-if="classOptions.length > pickClassCards.length" class="pick-more">
            共 {{ classOptions.length }} 个班级有课，上面只列了 {{ pickClassCards.length }} 个 ——
            用下面的下拉搜索全部。
          </div>

          <div class="pick-alt">
            想查的是别的班？
            <el-select
              v-model="classGroupId"
              placeholder="搜索班级"
              filterable
              clearable
              class="pick-select"
              @change="load"
            >
              <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <span class="pick-alt-sep">或</span>
            <button type="button" class="pick-alt-btn" @click="onViewModeChange('mine')">
              直接看我的授课
            </button>
          </div>
        </section>
      </template>

      <template v-else>
        <!-- ===== 周课表网格 ===== -->
        <section class="tui-card grid-card">
          <div class="grid-head-row">
            <h2 class="card-title">{{ view?.label || '课表' }}</h2>
            <span class="card-hint">{{ courses.length }} 节课 / 周</span>
            <div class="grid-legend">
              <span class="grid-legend-item"><i class="lg-dot is-mine" />我的课</span>
              <span class="grid-legend-item"><i class="lg-dot is-other" />其他教师</span>
            </div>
          </div>
          <div class="grid-scroll">
            <div class="week-grid">
              <!--
                整个网格一律用「显式行列定位」，不依赖 DOM 顺序自动排版。
                原因：跨节次的课需要 span N 行，一旦某个元素多占了行，
                后面所有元素就会整体错位（节次标签跑到中间列、课程整体下移）。
                显式写 grid-column / grid-row 后，块跨几行都不影响别的元素。
              -->
              <div class="grid-corner" :style="{ gridColumn: 1, gridRow: 1 }" />
              <div
                v-for="d in weekdays"
                :key="`h-${d.value}`"
                class="grid-head"
                :class="{ today: d.value === todayWeekday }"
                :style="{ gridColumn: d.value + 1, gridRow: 1 }"
              >
                <span class="gh-label">{{ d.label }}</span>
                <i v-if="d.value === todayWeekday" class="gh-today">今天</i>
              </div>

              <!--
                节次行：跨节次的课合并成一个块。
                早期写法是「每个格子各自渲染一遍这门课」——一节 2 学时的课会变成两个
                紧挨着、内容相同的卡片，看起来像两门课。
                现在只在该课的起始节渲染，并让它跨过 end-start+1 行；
                被覆盖掉的下方格子直接跳过（不再渲染空壳，否则会和跨行块重叠）。
              -->
              <template v-for="p in periods" :key="`r-${p}`">
                <div class="grid-period" :style="{ gridColumn: 1, gridRow: p + 1 }">
                  第{{ p }}节
                </div>
                <template v-for="d in weekdays" :key="`c-${d.value}-${p}`">
                  <div
                    v-if="!coveredByAbove(d.value, p)"
                    class="grid-cell"
                    :class="{ occupied: cellCourse(d.value, p), today: d.value === todayWeekday }"
                    :style="{ gridColumn: d.value + 1, gridRow: `${p + 1} / span ${cellSpan(d.value, p)}` }"
                  >
                    <div
                      v-for="c in cellCourse(d.value, p)"
                      :key="c.id"
                      class="course-block"
                      :class="{ 'is-mine': isMyCourse(c) }"
                      :style="courseStyle(c)"
                      @click="openCourse(c)"
                    >
                      <div class="cb-name">{{ c.name }}</div>
                      <div class="cb-meta">{{ c.class_name }}</div>
                      <div class="cb-meta muted">{{ c.location }}</div>
                      <div v-if="viewMode !== 'mine'" class="cb-teacher">
                        <span class="cb-teacher-dot" :class="{ 'is-mine': isMyCourse(c) }" />
                        {{ c.teacher }}
                      </div>
                    </div>
                  </div>
                </template>
              </template>
            </div>
          </div>
        </section>

        <!-- ===== 今日课程（移动端优先）===== -->
        <section v-if="todayCourses.length" class="tui-card">
          <div class="card-head">
            <h2 class="card-title">今天（{{ weekdayLabel(todayWeekday) }}）</h2>
            <span class="card-hint">共 {{ todayCourses.length }} 节</span>
          </div>
          <div class="today-list">
            <div
              v-for="c in todayCourses"
              :key="c.id"
              class="today-item"
              @click="openCourse(c)"
            >
              <div class="ti-period">
                第{{ c.start_period }}-{{ c.end_period }}节
              </div>
              <div class="ti-body">
                <div class="ti-name">{{ c.name }}</div>
                <div class="ti-meta">
                  {{ c.class_name }} · {{ c.location }}
                </div>
                <div class="ti-meta quiet">任课教师：{{ c.teacher }}</div>
              </div>
            </div>
          </div>
        </section>

        <!-- ===== 全部课程列表 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">
              {{ view?.label || '本学期课程' }}
            </h2>
            <span class="card-hint">共 {{ courses.length }} 门/次</span>
          </div>

          <div v-if="courses.length" class="course-list">
            <div v-for="c in courses" :key="c.id" class="course-row" @click="openCourse(c)">
              <div class="cr-time">
                <span class="cr-day">{{ weekdayShort(c.day_of_week) }}</span>
                <span class="cr-period">{{ c.start_period }}-{{ c.end_period }}节</span>
              </div>
              <div class="cr-body">
                <div class="cr-name">
                  {{ c.name }}
                  <span v-if="isMyCourse(c)" class="cr-tag">我教的</span>
                </div>
                <div class="cr-meta">
                  {{ c.class_name }}
                  <template v-if="c.college_name"> · {{ c.college_name }}</template>
                </div>
                <div class="cr-meta quiet">
                  任课教师：{{ c.teacher }} · {{ c.location }}
                  <template v-if="c.credit"> · {{ c.credit }} 学分</template>
                </div>
              </div>
              <div class="cr-side">
                <span class="cr-count">{{ c.student_count }} 人</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="该条件下暂无课程" :image-size="80" />
        </section>

        <!-- ===== 育人 ∩ 教学 ===== -->
        <section v-if="viewMode === 'mine' && myClassCount > 0" class="tui-card">
          <div class="card-head">
            <h2 class="card-title">我的授课版图</h2>
            <span class="card-hint">本学期你覆盖的班级与学生</span>
          </div>
          <div class="overlap-body">
            <div class="overlap-num">{{ myClassCount }}</div>
            <div class="overlap-text">
              你在 <b>{{ myClassCount }}</b> 个班开设课程，覆盖 <b>{{ overview?.total_student_count ?? 0 }}</b> 人次学生。
              课堂上发现的学业问题，可以直接落到育人侧的关怀记录与跟进待办——
              这是教师端相比纯教务系统最有价值的一层。
              <el-button size="small" text type="primary" @click="goGrowth">看育人 ∩ 教学</el-button>
            </div>
          </div>
        </section>
      </template>
    </div>

    <!-- ===== 课程详情抽屉 ===== -->
    <el-drawer
      v-model="drawerVisible"
      :title="activeCourse?.name || '课程详情'"
      :size="isMobile ? '100%' : '440px'"
      direction="rtl"
    >
      <div v-if="activeCourse" class="drawer-body">
        <div class="drawer-row">
          <span class="dr-label">任课教师</span>
          <span class="dr-value">{{ activeCourse.teacher || '未指派' }}</span>
        </div>
        <div class="drawer-row">
          <span class="dr-label">班级</span>
          <span class="dr-value">{{ activeCourse.class_name }}</span>
        </div>
        <div class="drawer-row">
          <span class="dr-label">时间</span>
          <span class="dr-value">
            {{ weekdayLabel(activeCourse.day_of_week) }}
            第{{ activeCourse.start_period }}-{{ activeCourse.end_period }}节
          </span>
        </div>
        <div class="drawer-row">
          <span class="dr-label">地点</span>
          <span class="dr-value">{{ activeCourse.location || '待定' }}</span>
        </div>
        <div class="drawer-row">
          <span class="dr-label">学时</span>
          <span class="dr-value">
            第 {{ activeCourse.week_start }}-{{ activeCourse.week_end }} 周
          </span>
        </div>
        <div class="drawer-row">
          <span class="dr-label">学生</span>
          <span class="dr-value">{{ activeCourse.student_count }} 人</span>
        </div>
        <div class="drawer-row">
          <span class="dr-label">学分</span>
          <span class="dr-value">{{ activeCourse.credit ?? '-' }}</span>
        </div>

        <div v-if="!isMyCourse(activeCourse)" class="drawer-tip">
          这是 {{ activeCourse.teacher }} 老师任教的课程，你只有查看权限。
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, Refresh, School } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import {
  getScheduleView,
  getScheduleTeachers,
  getScheduleClasses,
  type TeachingCourse,
  type ScheduleView,
  type ScheduleTeacher,
} from '@/api/teaching'

const router = useRouter()
const { isMobile } = useResponsive()
const auth = useAuthStore()

const loading = ref(false)
const view = ref<ScheduleView | null>(null)
const semester = ref('')
const semesters = ref<string[]>([])

/**
 * 课表页的定位（重要，别按「学生那种课表」理解）：
 *
 * 教师没有「被排课」的概念，但有「我今天要去上哪几节课」的真实需求。三个视图是：
 *   mine    = 我的授课安排（我教哪几门、在哪几节、在哪个教室）—— 默认视图
 *   class   = 查某个班级的课表（教务系统怎么给这个班排的）
 *   teacher = 查某个任课教师的授课安排（找同事 / 排课协调 / 代课找空档）
 *
 * 默认落到「我的授课」：教师打开课表最先关心的是自己今天上什么；
 * 「查课表」不再作为并列入口，而是页内的二级切换（班级 / 教师两种查法）。
 */
const viewMode = ref<'class' | 'teacher' | 'mine'>('mine')

/** 移动端：课表只有一个入口，默认「我的授课」；「查课表」是二级场景 */
const mobileTab = ref<'mine' | 'search'>('mine')
const mobileSearchMode = ref<'class' | 'teacher'>('class')
const mobileTabOptions = [
  { label: '我的授课', value: 'mine' },
  { label: '查课表', value: 'search' },
]
const mobileSearchOptions = [
  { label: '班级', value: 'class' },
  { label: '教师', value: 'teacher' },
]

function onMobileTab(v: string | number) {
  mobileTab.value = v === 'search' ? 'search' : 'mine'
  if (mobileTab.value === 'mine') {
    viewMode.value = 'mine'
    teacherName.value = ''
    classGroupId.value = null
  } else {
    viewMode.value = mobileSearchMode.value
  }
  load()
}

function onMobileSearchMode(v: string | number) {
  mobileSearchMode.value = v === 'teacher' ? 'teacher' : 'class'
  viewMode.value = mobileSearchMode.value
  if (viewMode.value === 'class') teacherName.value = ''
  else classGroupId.value = null
  load()
}

const viewOptions = [
  { label: '我的授课', value: 'mine' },
  { label: '班级课表', value: 'class' },
  { label: '教师授课', value: 'teacher' },
]

const teacherName = ref('')
const teacherList = ref<ScheduleTeacher[]>([])
const classGroupId = ref<number | null>(null)
const classOptions = ref<
  { id: number; name: string; college: string; courseCount: number; studentCount: number; isMine: boolean }[]
>([])

const drawerVisible = ref(false)
const activeCourse = ref<TeachingCourse | null>(null)

const weekdays = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
  { value: 7, label: '周日' },
]

/** 兼容模板里旧名 overview（改用 view 后统一） */
const overview = computed(() => view.value)

const courses = computed<TeachingCourse[]>(() => view.value?.courses ?? [])

/**
 * 「选了视图但还没落实到具体对象」——需要引导用户选班，而不是甩一个 8×7 的空网格。
 * 只有 class 视图会落到这里：teacher 视图没选人时后端会退回「全部教师」，
 * mine 视图为空是真实情况（我确实没课），不该假装用户漏选了点什么。
 */
const isEmptySelection = computed(() => {
  if (loading.value) return false
  if (viewMode.value !== 'class') return false
  return courses.value.length === 0
})

function pickClass(id: number) {
  classGroupId.value = id
  load()
}


/** 节次行：按实际最大节次动态生成，至少 8 节 */
const periods = computed(() => {
  const max = Math.max(8, ...courses.value.map((c) => c.end_period || 0))
  return Array.from({ length: Math.min(max, 12) }, (_, i) => i + 1)
})

const todayWeekday = computed(() => {
  // JS getDay(): 0=周日 → 课表口径 7=周日
  const d = new Date().getDay()
  return d === 0 ? 7 : d
})

/** 今天有课：只有"我的授课"视图才值得单独列，别人的课表今天有课与我无关 */
const todayCourses = computed(() => {
  if (viewMode.value !== 'mine') return []
  return (view.value?.today_courses ?? []).slice().sort((a, b) => a.start_period - b.start_period)
})

const isMine = (c: TeachingCourse) => c.teacher_id === auth.user?.id || c.teacher === auth.user?.name

/** 是否是我的课（前端只做 UI 提示，真实权限由后端裁决） */
function isMyCourse(c: TeachingCourse) {
  return isMine(c)
}

/* ---------- 移动端（定稿版·周网格） ---------- */
/** 手机上只铺周一到周五，周末的课另计一行 */
const mDays = computed(() => weekdays.slice(0, 5))

/** 网格行：按真实最大节次，最多 10 行 */
const mPeriods = computed(() => {
  const max = Math.max(8, ...courses.value.map((c) => c.end_period || 0))
  return Array.from({ length: Math.min(max, 10) }, (_, i) => i + 1)
})

/** 该格起始的课（跨节的课只在起始节显示，避免重复） */
function mCell(day: number, p: number): TeachingCourse | null {
  return courses.value.find((c) => c.day_of_week === day && c.start_period === p) || null
}

/** 该格颜色：只在「课程起始节」上色；被上方跨节覆盖的格子保持透明 */
function cellKind(day: number, p: number) {
  const start = mCell(day, p)
  if (!start) return ''
  return isMyCourse(start) ? 'tm-cls' : 'tm-other'
}

/** 今天课程（按起始节排序） */
const mTodayList = computed(() =>
  courses.value
    .filter((c) => c.day_of_week === todayWeekday.value)
    .slice()
    .sort((a, b) => a.start_period - b.start_period)
)

function mWeekCount(day: number) {
  return courses.value.filter((c) => c.day_of_week === day).length
}
const mWeekendCount = computed(() => courses.value.filter((c) => c.day_of_week > 5).length)

/** 点格子：有课直接开详情 */
function onCellTap(day: number, p: number) {
  const c = mCell(day, p)
  if (c) openCourse(c)
}

/** 单元格内该节次的课程 */
function cellCourse(day: number, period: number): TeachingCourse[] {
  return courses.value.filter(
    (c) => c.day_of_week === day && period >= c.start_period && period <= c.end_period
  )
}

/**
 * 该格是否已被「从上方跨行下来」的课程覆盖 —— 是的话本格不渲染任何卡片，
 * 否则会和跨行块叠在一起（同一门课出现两次）。
 */
function coveredByAbove(day: number, period: number): boolean {
  return courses.value.some(
    (c) => c.day_of_week === day && c.start_period < period && period <= c.end_period
  )
}

/**
 * 该格需要跨几行：只在课程的起始节返回 N，其它情况返回 1。
 * 配合显式的 grid-row: `${p+1} / span N`，一门 2 学时的课就是一个占两行高的块。
 */
function cellSpan(day: number, period: number): number {
  const start = cellCourse(day, period).find((c) => c.start_period === period)
  if (!start) return 1
  return Math.max(1, (start.end_period || start.start_period) - start.start_period + 1)
}

const PALETTE = [
  'linear-gradient(135deg,#eef4ff,#dbe7ff)',
  'linear-gradient(135deg,#eefaf3,#d7f3e5)',
  'linear-gradient(135deg,#fff5ea,#ffe8cf)',
  'linear-gradient(135deg,#f3efff,#e5dbff)',
  'linear-gradient(135deg,#eefaff,#d6f0fa)',
  'linear-gradient(135deg,#fdeef2,#fbdce4)',
]

function courseStyle(c: TeachingCourse) {
  // 用课程 id 做稳定取色，保证同一门课每次颜色一致
  return { background: PALETTE[c.id % PALETTE.length] }
}

function weekdayLabel(d: number) {
  return weekdays.find((w) => w.value === d)?.label || `周${d}`
}
function weekdayShort(d: number) {
  return weekdayLabel(d).replace('周', '')
}

function openCourse(c: TeachingCourse) {
  activeCourse.value = c
  drawerVisible.value = true
}

/** 我授课覆盖的班级数（去重） */
const myClassCount = computed(() => {
  const set = new Set<number>()
  for (const c of courses.value) if (c.class_group_id) set.add(c.class_group_id)
  return set.size
})

function goGrowth() {
  router.push('/teacher/growth')
}

function clearTeacher() {
  teacherName.value = ''
  classGroupId.value = null
  viewMode.value = 'mine'
  load()
}
async function load() {
  loading.value = true
  try {
    // 「其他教师/班级」两个视图与"我的"同构，后端统一返回 ScheduleView，前端一套渲染
    view.value = await getScheduleView({
      semester: semester.value || undefined,
      teacher_name: viewMode.value === 'teacher' && teacherName.value ? teacherName.value : undefined,
      class_group_id: viewMode.value === 'class' && classGroupId.value ? classGroupId.value : undefined,
    })
    if (view.value.semesters?.length) {
      semesters.value = view.value.semesters
      if (!semester.value) semester.value = view.value.semester || semesters.value[0]
    }
    // 班级下拉 / 教师下拉的数据源必须无条件准备：
    // 默认视图是「我的授课」，但用户随时可能切到「查课表」，下拉不能等到切换时才空着。
    await ensureFilterSources()
  } catch {
    ElMessage.error('课表加载失败')
  } finally {
    loading.value = false
  }
}

/**
 * 准备两个筛选下拉的数据源（只准备一次，切换视图不重复拉）。
 *   classOptions  ← /teaching/classes（本学期有课的班级）
 *   teacherList   ← /teaching/teachers
 *
 * 早期是从「我的授课」的 courses 里反推班级 —— 那是错的：
 * 课表是教务排定的公共数据，一个本学期没排课的教师会拿到空清单，
 * 整页既没有卡片也没有下拉选项，用户以为功能坏了。
 */
let filterSourcesReady = false
async function ensureFilterSources(force = false) {
  if (filterSourcesReady && !force) return
  try {
    const rows = await getScheduleClasses({ semester: semester.value || undefined })
    classOptions.value = rows.map((r) => ({
      id: r.class_group_id,
      name: r.name,
      college: r.college_name || '',
      courseCount: r.course_count,
      studentCount: r.student_count,
      isMine: r.is_mine,
    }))
  } catch {
    classOptions.value = []
  }
  try {
    teacherList.value = await getScheduleTeachers({ semester: semester.value || undefined })
  } catch {
    teacherList.value = []
  }
  filterSourcesReady = true
}

/**
 * 空选态里铺出来的班级卡片：最多 12 个。
 * 全校一百多个班全铺开就成了「班级目录」，反而没有引导作用 ——
 * 引导的目标是「点一下就进去」，不是「让你浏览全校」。
 * 我任教的班优先，其次按课程数多的（更可能是你想看的），其余靠搜索下拉。
 */
const pickClassCards = computed(() => {
  const list = classOptions.value
  if (list.length <= 12) return list
  const sorted = list.slice().sort((a, b) => {
    if (a.isMine !== b.isMine) return a.isMine ? -1 : 1
    return b.courseCount - a.courseCount
  })
  return sorted.slice(0, 12)
})

// TuiSegmented 的 modelValue 是 string|number，这里收敛成有限字面量联合类型
function onViewModeChange(v: string | number) {
  if (v !== 'mine' && v !== 'teacher' && v !== 'class') return
  viewMode.value = v
  // 清空另一维度的筛选，避免「选了教师又选班级」的歧义
  if (v !== 'teacher') teacherName.value = ''
  if (v !== 'class') classGroupId.value = null
  load()
}

onMounted(() => {
  // 移动端默认落到「我的授课」：教师打开课表最先关心的是自己今天要上什么
  if (isMobile.value) viewMode.value = 'mine'
  load()
})
</script>

<style scoped>
/* ---------- 移动端（定稿版·周网格）私有件 ---------- */
.tm-filter {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 14px 9px;
}
.tm-filter-main {
  padding: 12px 14px 8px;
}
.tm-filter-main :deep(.tui-seg) {
  width: 100%;
}
.tm-search-mode {
  flex: 0 0 auto;
}
.tm-sched-hint {
  margin: -2px 14px 10px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--tm-ink3, #8a91a0);
}
.tm-row-tap {
  width: 100%;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}
.tm-row-tap:active { background: var(--tm-surf2); }
.tm-gw-c.tm-other { background: #f5f7fc; border-color: #e6ecf6; }
.tm-gw-c.tm-other b { color: #5b6b85; font-size: 8.2px; }
.tm-muted { font-size: 9.4px; color: var(--tm-ink3); font-weight: 650; }
.tui-content {
  padding: 0 16px 32px;
  max-width: 1280px;
  margin: 0 auto;
}

.hero-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.3;
}
.hero-pill b {
  font-size: 15px;
  color: var(--tui-text);
}
.hero-pill span {
  font-size: 11px;
  color: var(--tui-text-tertiary);
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin: 14px 0 12px;
}
.filter-right {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.filter-teacher {
  width: 200px;
}
.opt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.opt-name {
  display: flex;
  align-items: center;
  gap: 5px;
}
.opt-me {
  font-size: 10px;
  color: var(--tui-brand-strong);
  background: var(--tui-brand-soft);
  border-radius: 3px;
  padding: 0 4px;
}
.opt-meta {
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.filter-semester {
  width: 150px;
}

/* 卡片 */
.tui-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-lg);
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: var(--tui-shadow-1);
}
.card-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.card-title {
  font-size: 15.5px;
  font-weight: 650;
  color: var(--tui-text);
  margin: 0;
}
.card-hint {
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.quiet {
  color: var(--tui-text-quiet);
}

/* ===== 空选态：引导选班 ===== */
.pick-panel {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-lg);
  padding: 26px 24px 22px;
  margin-bottom: 14px;
  box-shadow: var(--tui-shadow-1);
}
.pick-head {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 20px;
}
.pick-ico {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
}
.pick-head-text {
  min-width: 0;
}
.pick-title {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 650;
  color: var(--tui-text);
  letter-spacing: -0.01em;
}
.pick-sub {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--tui-text-secondary);
}
.pick-sub b {
  font-weight: 600;
  color: var(--tui-text);
}
.pick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 10px;
}
.pick-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  padding: 12px 14px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius);
  background: var(--tui-surface-page);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s var(--tui-ease), background 0.16s var(--tui-ease),
    transform 0.16s var(--tui-ease);
}
.pick-card:hover {
  border-color: var(--tui-brand);
  background: var(--tui-brand-soft);
  transform: translateY(-1px);
}
.pick-card-top {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}
.pick-card-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pick-card-badge {
  flex: 0 0 auto;
  font-size: 9.5px;
  font-weight: 600;
  line-height: 1;
  padding: 2px 5px;
  border-radius: 4px;
  background: var(--tui-brand);
  color: #fff;
}
.pick-card-meta {
  font-size: 11px;
  color: var(--tui-text-quiet);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.pick-card-go {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  transition: color 0.16s var(--tui-ease);
}
.pick-card:hover .pick-card-go {
  color: var(--tui-brand-strong);
}
.pick-more {
  margin-top: 12px;
  font-size: 12px;
  color: var(--tui-text-quiet);
}
.pick-empty {
  margin: 0;
  padding: 16px 18px;
  border-radius: var(--tui-radius);
  background: var(--tui-surface-muted);
  font-size: 13px;
  line-height: 1.7;
  color: var(--tui-text-secondary);
}
.pick-alt {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed var(--tui-border);
  font-size: 12.5px;
  color: var(--tui-text-quiet);
}
.pick-select {
  width: 200px;
}
.pick-alt-sep {
  color: var(--tui-text-quiet);
}
.pick-alt-btn {
  border: none;
  background: none;
  padding: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-brand-strong);
  cursor: pointer;
}
.pick-alt-btn:hover {
  text-decoration: underline;
}

/* 周网格 */
.grid-head-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.grid-legend {
  display: flex;
  gap: 12px;
  margin-left: auto;
}
.grid-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.lg-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
}
.lg-dot.is-mine {
  background: var(--tui-brand);
}
.grid-scroll {
  overflow-x: auto;
}
.week-grid {
  display: grid;
  grid-template-columns: 56px repeat(7, minmax(96px, 1fr));
  /* 行高固定 56px：跨行块的高度 = 56 * N + gap * (N-1)，可预测。
     用 auto 时跨行块会把行撑高，反过来挤压相邻格，网格会抖。 */
  grid-auto-rows: 56px;
  gap: 6px;
  min-width: 740px;
}
.grid-corner {
  min-height: 32px;
}
.grid-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  text-align: center;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  padding: 6px 0;
  border-radius: var(--tui-radius-xs);
  background: var(--tui-surface-muted);
}
.grid-head.today {
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
}
.gh-today {
  font-style: normal;
  font-size: 9.5px;
  font-weight: 600;
  line-height: 1;
  padding: 2px 4px;
  border-radius: 4px;
  background: var(--tui-brand);
  color: #fff;
}
.grid-period {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-xs);
  min-height: 56px;
}
.grid-cell {
  min-height: 56px;
  border-radius: var(--tui-radius-xs);
  background: var(--tui-surface-muted);
  padding: 2px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.grid-cell.today {
  background: var(--tui-brand-soft);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.14);
}
.course-block {
  position: relative;
  border-radius: 6px;
  padding: 5px 6px;
  cursor: pointer;
  transition: transform 0.14s var(--tui-ease);
  overflow: hidden;
  flex: 1;
}
.course-block.is-mine {
  box-shadow: inset 3px 0 0 var(--tui-brand);
  padding-left: 8px;
}
.course-block:hover {
  transform: translateY(-1px);
  box-shadow: var(--tui-shadow-2);
}
.cb-name {
  font-size: 11.5px;
  font-weight: 650;
  color: #0f1115;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cb-meta {
  font-size: 10px;
  color: #374151;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cb-meta.muted {
  opacity: 0.72;
}
.cb-teacher {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 600;
  color: #1d4ed8;
  margin-top: 1px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cb-teacher-dot {
  flex: 0 0 auto;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
}
.cb-teacher-dot.is-mine {
  background: var(--tui-brand);
}

/* 今日课程 */
.today-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.today-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  cursor: pointer;
}
.today-item:hover {
  background: var(--tui-brand-soft);
}
.ti-period {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--tui-brand-strong);
  flex: 0 0 auto;
  min-width: 78px;
}
.ti-body {
  flex: 1;
  min-width: 0;
}
.ti-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
}
.ti-meta {
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
  margin-top: 1px;
}
/* 课程列表 */
.course-list {
  display: flex;
  flex-direction: column;
}
.course-row {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 11px 4px;
  border-bottom: 1px solid var(--tui-border);
  cursor: pointer;
}
.course-row:last-child {
  border-bottom: none;
}
.course-row:hover {
  background: var(--tui-surface-muted);
}
.cr-time {
  flex: 0 0 66px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.cr-day {
  font-size: 12.5px;
  font-weight: 650;
  color: var(--tui-text);
}
.cr-period {
  font-size: 10.5px;
  color: var(--tui-text-quiet);
}
.cr-body {
  flex: 1;
  min-width: 0;
}
.cr-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
  display: flex;
  align-items: center;
  gap: 6px;
}
.cr-tag {
  font-size: 10px;
  font-weight: 500;
  color: var(--tui-brand-strong);
  background: var(--tui-brand-soft);
  border-radius: 4px;
  padding: 0 5px;
}
.cr-meta {
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cr-side {
  flex: 0 0 auto;
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cr-count {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
/* 育人∩教学 */
.overlap-body {
  display: flex;
  gap: 16px;
  align-items: center;
}
.overlap-num {
  font-size: 34px;
  font-weight: 700;
  color: var(--tui-brand-strong);
  font-variant-numeric: tabular-nums;
  flex: 0 0 auto;
}
.overlap-text {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--tui-text-secondary);
}

/* 抽屉 */
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.drawer-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--tui-border);
  font-size: 13px;
}
.dr-label {
  color: var(--tui-text-tertiary);
  flex: 0 0 auto;
}
.dr-value {
  color: var(--tui-text);
  text-align: right;
}
.drawer-tip {
  margin-top: 20px;
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 12px;
  line-height: 1.7;
}

@media (max-width: 767px) {
  .tui-content {
    padding: 12px 12px 90px;
  }
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
  .filter-right {
    flex-direction: column;
    align-items: stretch;
  }
  .filter-teacher,
  .filter-semester {
    width: 100%;
  }
  .week-grid {
    min-width: 620px;
    grid-template-columns: 44px repeat(7, minmax(78px, 1fr));
  }
  .tui-card {
    padding: 14px;
  }
}
</style>
