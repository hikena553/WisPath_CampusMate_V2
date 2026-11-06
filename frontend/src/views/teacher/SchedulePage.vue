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
        <el-select
          v-model="activeWeek"
          size="small"
          placeholder="整学期"
          style="width: 92px"
          @change="() => {}"
        >
          <el-option v-for="w in weekOptions" :key="w" :label="`第${w}周`" :value="w" />
        </el-select>
      </div>

      <p class="tm-sched-hint">
        课表用于确认今天 / 本周要上的课，点名和课程资料都从这里进入；「查课表」只是临时查班级或同事的安排。
      </p>

      <!-- 排课调整入口：手机上抽屉里的按钮点不到，这里给一条明确的常驻入口 -->
      <div class="tm-sched-ops">
        <button type="button" class="tm-op-btn" @click="openChangeDialog('add')">
          <span>＋ 申请增课</span>
        </button>
        <button type="button" class="tm-op-btn" @click="openMyChanges">
          <span>我的申请</span>
          <em v-if="pendingChangeCount">{{ pendingChangeCount }}</em>
        </button>
      </div>

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
        <!-- 周网格（周一~周日，7 列全显示） -->
        <div class="tm-gridwk">
          <div class="tm-gw-hd">
            <b></b>
            <b
              v-for="d in mDays"
              :key="d.value"
              :class="{ 'tm-on': d.value === todayWeekday, 'tm-wk': isWeekendDay(d.value) }"
            >
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
                :class="[cellKind(d.value, p), { 'tm-gw-wk': isWeekendDay(d.value) && !mCell(d.value, p) }]"
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
          <span class="tm-sec-m">
            共 {{ weekCourses.length }} 节<template v-if="mWeekendCount"> · 周末 {{ mWeekendCount }} 节</template>
          </span>
        </div>
        <div class="tm-wk-les">
          <div v-for="d in mDays" :key="`w-${d.value}`" class="tm-wl" :class="{ 'tm-today': d.value === todayWeekday }">
            <em>周{{ d.label.slice(1) }}</em><b>{{ mWeekCount(d.value) }}</b>
          </div>
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
          <el-button text @click="openMyChanges">
            我的申请
            <el-badge v-if="pendingChangeCount" :value="pendingChangeCount" class="hero-badge" />
          </el-button>
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
            v-model="activeWeek"
            placeholder="教学周"
            clearable
            size="default"
            class="filter-week"
          >
            <el-option v-for="w in weekOptions" :key="w" :label="`第${w}周`" :value="w" />
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
            <span class="card-hint">{{ activeWeek ? `第${activeWeek}周 ` : "" }}{{ weekCourses.length }} 节课 / 周</span>
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

        <!-- 排课调整：只有自己的课才能发起调课；增课与调课都走管理员审批 -->
        <div class="drawer-actions">
          <el-button
            v-if="isMyCourse(activeCourse)"
            type="primary"
            :icon="Switch"
            @click="openChangeDialog('swap', activeCourse)"
          >
            申请调课
          </el-button>
          <el-button :icon="Plus" @click="openChangeDialog('add')">申请增课</el-button>
        </div>
        <p class="drawer-hint">
          调课 / 增课提交后由教务审批，通过后自动写入课表并通知班级学生。
        </p>
      </div>
    </el-drawer>

    <!-- ===== 调课 / 增课申请弹窗 =====
         位置实现与学生端「导出简历」弹窗（components/resume/ResumeExportWizard.vue）同款：
         Teleport 到 body + fixed 全屏遮罩 + align-items:flex-end 底部面板 + 上滑过渡。
         不用 el-dialog——它的 top 居中定位做不出真正的底部抽屉。 -->
    <Teleport to="body">
      <transition name="chg-fade">
        <div v-if="changeVisible" class="chg-mask" @click.self="changeVisible = false">
          <div class="chg-panel" role="dialog" aria-modal="true">
        <header class="chg-hd">
          <div class="chg-hd-tx">
            <h3>{{ changeForm.kind === 'swap' ? '申请调课' : '申请增课' }}</h3>
            <p>{{ changeForm.kind === 'swap' ? '把某一周的课调到以后某一周的某天上课' : '在课表之外新增一次或一段课' }}</p>
          </div>
          <button type="button" class="chg-x" aria-label="关闭" @click="changeVisible = false">✕</button>
        </header>

        <div class="chg-body">
          <!-- 原课信息：调课时展示，明确「挪的是哪一周」 -->
          <template v-if="changeForm.kind === 'swap'">
            <p class="chg-cap">要调走的课</p>
            <div class="chg-origin">
              <b>{{ changeOrigin?.name || '未选课程' }}</b>
              <span>
                {{ changeOrigin ? `${weekdayLabel(changeOrigin.day_of_week)} 第${changeOrigin.start_period}-${changeOrigin.end_period}节 · ${changeOrigin.location || '地点待定'}` : '' }}
              </span>
            </div>

            <p class="chg-cap">调走第几周</p>
            <div class="chg-chips">
              <button
                v-for="w in originWeekOptions"
                :key="w"
                type="button"
                class="chg-chip"
                :class="{ on: changeForm.origin_week_no === w, skipped: isWeekSkipped(w) }"
                @click="changeForm.origin_week_no = w"
              >{{ w }}</button>
            </div>
            <p class="chg-tip">灰色的周已被调走，再选会叠加调整</p>

            <p class="chg-cap">补到第几周</p>
            <div class="chg-chips chg-chips-scroll">
              <button
                v-for="w in targetWeekOptions"
                :key="`t${w}`"
                type="button"
                class="chg-chip"
                :class="{ on: changeForm.target_week === w }"
                @click="changeForm.target_week = w"
              >{{ w }}</button>
            </div>
          </template>

          <template v-else>
            <div class="chg-two">
              <label class="chg-field">
                <span>班级</span>
                <el-select v-model="changeForm.class_group_id" placeholder="选择班级" filterable size="small" popper-class="chg-popper">
                  <el-option v-for="c in classOptions" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
              </label>
              <label class="chg-field">
                <span>课程名称</span>
                <el-input v-model="changeForm.course_name" placeholder="如：算法竞赛实训" maxlength="100" size="small" />
              </label>
            </div>
            <p class="chg-cap">教学周</p>
            <div class="chg-two">
              <label class="chg-field">
                <span>开始周</span>
                <el-input-number v-model="changeForm.week_start" :min="1" :max="30" controls-position="right" size="small" style="width: 100%" />
              </label>
              <label class="chg-field">
                <span>结束周</span>
                <el-input-number v-model="changeForm.week_end" :min="1" :max="30" controls-position="right" size="small" style="width: 100%" />
              </label>
            </div>
          </template>

          <p class="chg-cap">{{ changeForm.kind === 'swap' ? '补课时间' : '上课时间' }}</p>
          <div class="chg-chips">
            <button
              v-for="d in weekdays"
              :key="d.value"
              type="button"
              class="chg-chip"
              :class="{ on: changeForm.day_of_week === d.value }"
              @click="changeForm.day_of_week = d.value"
            >{{ d.label }}</button>
          </div>

          <div class="chg-chips">
            <button
              v-for="p in periodOptions"
              :key="`s${p}`"
              type="button"
              class="chg-chip"
              :class="{ on: changeForm.start_period === p }"
              @click="onPickStartPeriod(p)"
            >{{ p }}</button>
          </div>
          <p class="chg-tip">点起始节，再点结束节（当前：第{{ changeForm.start_period }}-{{ changeForm.end_period }}节）</p>

          <label class="chg-field">
            <span>地点</span>
            <el-input v-model="changeForm.location" placeholder="如：教学楼B-203（留空沿用原教室）" maxlength="100" size="small" />
          </label>

          <label class="chg-field">
            <span>申请理由</span>
            <el-input
              v-model="changeForm.reason"
              type="textarea"
              :rows="2"
              maxlength="500"
              placeholder="如：学院统一安排会议，申请顺延至周六同节次"
            />
          </label>
        </div>

        <footer class="chg-ft">
          <button
            type="button"
            class="chg-submit"
            :disabled="changeSubmitting"
            @click="submitChange"
          >{{ changeSubmitting ? '提交中…' : '提交审批' }}</button>
        </footer>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- ===== 我的申请（调课 / 增课进度）===== -->
    <el-drawer
      v-model="myChangesVisible"
      title="我的调课 / 增课申请"
      :size="isMobile ? '100%' : '480px'"
      direction="rtl"
    >
      <el-skeleton v-if="myChangesLoading" :rows="4" animated />
      <el-empty v-else-if="!myChanges.length" description="还没有提交过调课或增课申请" :image-size="80" />
      <div v-else class="mc-list">
        <article v-for="r in myChanges" :key="r.id" class="mc-item" :class="`is-${r.status}`">
          <div class="mc-hd">
            <span class="mc-kind">{{ r.kind_label }}</span>
            <span class="mc-name">{{ r.course_name }}</span>
            <el-tag size="small" :type="changeStatusType(r.status)" effect="light">{{ r.status_label }}</el-tag>
          </div>
          <div class="mc-when">
            <template v-if="r.kind === 'swap' && r.origin_day_of_week">
              <span class="mc-origin">第{{ r.origin_week_no || r.origin_week_start }}周 {{ weekdayLabel(r.origin_day_of_week) }} 第{{ r.origin_start_period }}-{{ r.origin_end_period }}节</span>
              <span class="mc-arrow">→</span>
              <span class="mc-target">第{{ r.week_start }}周 {{ weekdayLabel(r.day_of_week) }} 第{{ r.start_period }}-{{ r.end_period }}节</span>
            </template>
            <template v-else>
              <span class="mc-target">{{ weekdayLabel(r.day_of_week) }} 第{{ r.start_period }}-{{ r.end_period }}节（第{{ r.week_start }}-{{ r.week_end }}周）</span>
            </template>
            <span v-if="r.location" class="mc-loc">{{ r.location }}</span>
          </div>
          <div class="mc-meta">{{ r.class_name }} · {{ r.applicant_name }} · {{ r.created_at.slice(0, 16).replace('T', ' ') }}</div>
          <div v-if="r.reason" class="mc-reason">理由：{{ r.reason }}</div>
          <div v-if="r.status === 'rejected' && r.reject_reason" class="mc-reject">驳回原因：{{ r.reject_reason }}</div>
          <div v-if="r.status === 'pending'" class="mc-ops">
            <el-button size="small" text type="danger" @click="cancelMyChange(r.id)">撤回申请</el-button>
          </div>
        </article>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, Refresh, School, Plus, Switch } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import TuiSegmented from '@/components/teacher/ui/TuiSegmented.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import {
  cancelScheduleChange,
  createScheduleChange,
  getMyScheduleChanges,
  type ScheduleChangeCreatePayload,
  type ScheduleChangeItem,
} from '@/api/scheduleChange'
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

/* ---------- 按教学周查看 ----------
 * 课表接口返回的是整学期的课，但「单次调课」是按周生效的：
 * 第 5 周的课挪到第 8 周，网格必须能切到某一周去看——否则挪走的那周看起来还在。
 * activeWeek 默认取后端算好的当前教学周；学期外（null）退化为整学期视图。
 */
const activeWeek = ref<number | null>(null)

/** 学期最大教学周（周次选择器范围） */
const maxWeek = computed(() =>
  courses.value.length ? Math.max(16, ...courses.value.map((c) => c.week_end)) : 20
)

/** 第 activeWeek 周真正要上的课：学期范围内 + 跳过被调走的周 */
const weekCourses = computed<TeachingCourse[]>(() => {
  const wk = activeWeek.value
  if (!wk) return courses.value
  return courses.value.filter(
    (c) => c.week_start <= wk && wk <= c.week_end && !(c.skip_weeks ?? []).includes(wk)
  )
})

const weekOptions = computed(() =>
  Array.from({ length: maxWeek.value }, (_, i) => i + 1)
)

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
  const max = Math.max(8, ...weekCourses.value.map((c) => c.end_period || 0))
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
  const wk = activeWeek.value
  const list = wk
    ? weekCourses.value.filter((c) => c.day_of_week === todayWeekday.value)
    : (view.value?.today_courses ?? [])
  return list.slice().sort((a, b) => a.start_period - b.start_period)
})

const isMine = (c: TeachingCourse) => c.teacher_id === auth.user?.id || c.teacher === auth.user?.name

/** 是否是我的课（前端只做 UI 提示，真实权限由后端裁决） */
function isMyCourse(c: TeachingCourse) {
  return isMine(c)
}

/* ---------- 移动端（定稿版·周网格） ---------- */
/**
 * 移动端固定铺满周一~周日七列。
 *
 * 旧版只铺周一到周五，周末的课折成「周末 N 节」一行——这是错的：
 * 用户看不到周末，就没法确认周末到底有没有课，还会以为课表漏了数据。
 * 学生端课表早就因为同样的原因改成 7 列（见 student/SchedulePage.vue 的注释），
 * 教师端与管理员端必须同口径。390px 下节次列压到 22px，每列仍有 ~44px，
 * 足够放下 4 字课程名；周末两列加一层极浅灰底与工作日区分。
 */
const mDays = computed(() => weekdays)

/** 是否周末列（只用于底色区分，不参与任何过滤） */
const isWeekendDay = (d: number) => d === 6 || d === 7

/** 网格行：按真实最大节次，最多 10 行 */
const mPeriods = computed(() => {
  const max = Math.max(8, ...weekCourses.value.map((c) => c.end_period || 0))
  return Array.from({ length: Math.min(max, 10) }, (_, i) => i + 1)
})

/** 该格起始的课（跨节的课只在起始节显示，避免重复） */
function mCell(day: number, p: number): TeachingCourse | null {
  return weekCourses.value.find((c) => c.day_of_week === day && c.start_period === p) || null
}

/** 该格颜色：只在「课程起始节」上色；被上方跨节覆盖的格子保持透明 */
function cellKind(day: number, p: number) {
  const start = mCell(day, p)
  if (!start) return ''
  return isMyCourse(start) ? 'tm-cls' : 'tm-other'
}

/** 今天课程（按起始节排序） */
const mTodayList = computed(() =>
  weekCourses.value
    .filter((c) => c.day_of_week === todayWeekday.value)
    .slice()
    .sort((a, b) => a.start_period - b.start_period)
)

function mWeekCount(day: number) {
  return weekCourses.value.filter((c) => c.day_of_week === day).length
}
const mWeekendCount = computed(() => weekCourses.value.filter((c) => c.day_of_week > 5).length)
// 周末的课现在直接画进网格第 6/7 列，不再单独折叠成一行；
// 这个计数只用于「本周课时」标题里的补充说明（周末有课时才提一句）。

/** 点格子：有课直接开详情 */
function onCellTap(day: number, p: number) {
  const c = mCell(day, p)
  if (c) openCourse(c)
}

/** 单元格内该节次的课程 */
function cellCourse(day: number, period: number): TeachingCourse[] {
  return weekCourses.value.filter(
    (c) => c.day_of_week === day && period >= c.start_period && period <= c.end_period
  )
}

/**
 * 该格是否已被「从上方跨行下来」的课程覆盖 —— 是的话本格不渲染任何卡片，
 * 否则会和跨行块叠在一起（同一门课出现两次）。
 */
function coveredByAbove(day: number, period: number): boolean {
  return weekCourses.value.some(
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

/* ---------- 调课 / 增课申请 ----------
 * 课表是教务口径的公共数据，教师端不直接改课，只能发起申请；
 * 审批通过后由后端写回 courses，课表刷新即生效，学生端同步看到。
 */
const changeVisible = ref(false)
const changeSubmitting = ref(false)
const changeOrigin = ref<TeachingCourse | null>(null)
const changeForm = ref<{
  kind: 'swap' | 'add'
  course_id: number | null
  class_group_id: number | null
  course_name: string
  location: string
  day_of_week: number
  start_period: number
  end_period: number
  week_start: number
  week_end: number
  /** 单次调课：挪走的是第几教学周 */
  origin_week_no: number | null
  /** 单次调课：补到第几教学周 */
  target_week: number | null
  reason: string
}>({
  kind: 'swap',
  course_id: null,
  class_group_id: null,
  course_name: '',
  location: '',
  day_of_week: 1,
  start_period: 1,
  end_period: 2,
  week_start: 1,
  week_end: 16,
  origin_week_no: null,
  target_week: null,
  reason: '',
})

/** 弹窗里的节次胶囊：最多 12 节（与网格一致） */
const periodOptions = Array.from({ length: 12 }, (_, i) => i + 1)

/**
 * 起始/结束节共用一排胶囊：点的节比当前起始节大且当前已跨节 → 改结束节；
 * 点的节比当前起始节小 → 重设起始节；其余情况设为单节。
 */
function onPickStartPeriod(p: number) {
  const f = changeForm.value
  if (f.start_period !== f.end_period && p > f.start_period && p !== f.end_period) {
    f.end_period = p
  } else if (f.start_period !== f.end_period && p < f.start_period) {
    f.start_period = p
  } else {
    f.start_period = p
    f.end_period = p
  }
}

/** 原课学期范围内的可选周（调走哪一周） */
const originWeekOptions = computed(() => {
  const c = changeOrigin.value
  if (!c) return []
  const weeks: number[] = []
  for (let w = c.week_start; w <= c.week_end; w++) weeks.push(w)
  return weeks
})

/** 目标周：被调走那周之后到学期末（补到以后的某一周） */
const targetWeekOptions = computed(() => {
  const c = changeOrigin.value
  const from = (changeForm.value.origin_week_no || c?.week_start || 1) + 1
  const end = Math.max(30, c?.week_end || 16)
  const weeks: number[] = []
  for (let w = from; w <= end; w++) weeks.push(w)
  return weeks
})

/** 该周是否已被调走过（灰显提示会叠加调整） */
function isWeekSkipped(w: number) {
  return !!changeOrigin.value?.skip_weeks?.includes(w)
}

function openChangeDialog(kind: 'swap' | 'add', course?: TeachingCourse) {
  changeOrigin.value = kind === 'swap' ? course ?? null : null
  const today = todayWeekday.value
  changeForm.value = {
    kind,
    course_id: course?.id ?? null,
    class_group_id: course?.class_group_id ?? classGroupId.value ?? null,
    course_name: '',
    location: course?.location ?? '',
    day_of_week: course?.day_of_week ?? today,
    start_period: course?.start_period ?? 1,
    end_period: course?.end_period ?? 2,
    week_start: course?.week_start ?? 1,
    week_end: course?.week_end ?? 16,
    // 单次调课默认：挪当前正在看的教学周（不在原课范围则取起始周），补到下一周
    origin_week_no: null,
    target_week: null,
    reason: '',
  }
  if (kind === 'swap' && course) {
    const wk = activeWeek.value && course.week_start <= activeWeek.value && activeWeek.value <= course.week_end
      ? activeWeek.value
      : course.week_start
    changeForm.value.origin_week_no = wk
    changeForm.value.target_week = wk + 1
  }
  changeVisible.value = true
}

async function submitChange() {
  const f = changeForm.value
  if (f.end_period < f.start_period) return ElMessage.warning('结束节次不能早于开始节次')
  if (f.week_end < f.week_start) return ElMessage.warning('结束周不能早于开始周')
  if (!f.reason.trim()) return ElMessage.warning('请填写申请理由')
  if (f.kind === 'add') {
    if (!f.class_group_id) return ElMessage.warning('请选择班级')
    if (!f.course_name.trim()) return ElMessage.warning('请填写课程名称')
  } else {
    if (!f.origin_week_no) return ElMessage.warning('请选择要调走的是第几周')
    if (!f.target_week) return ElMessage.warning('请选择补到第几周')
    if (f.target_week <= f.origin_week_no) return ElMessage.warning('补课周必须晚于被调走的那一周')
  }
  const payload: ScheduleChangeCreatePayload = {
    kind: f.kind,
    course_id: f.course_id,
    day_of_week: f.day_of_week,
    start_period: f.start_period,
    end_period: f.end_period,
    location: f.location.trim(),
    reason: f.reason.trim(),
    semester: semester.value || null,
  }
  if (f.kind === 'add') {
    payload.class_group_id = f.class_group_id
    payload.course_name = f.course_name.trim()
    payload.week_start = f.week_start
    payload.week_end = f.week_end
  } else {
    // 单次调课：把第 origin_week_no 周的课挪到第 target_week 周
    payload.origin_week_no = f.origin_week_no
    payload.target_week = f.target_week
  }
  changeSubmitting.value = true
  try {
    await createScheduleChange(payload)
    ElMessage.success('已提交，等待教务审批')
    changeVisible.value = false
    drawerVisible.value = false
    loadMyChanges()
  } catch (e: any) {
    // 冲突、归属等业务校验由后端给出具体原因，这里原样展示
    ElMessage.error(e?.response?.data?.detail || '提交失败，请稍后重试')
  } finally {
    changeSubmitting.value = false
  }
}

/* ---------- 我的申请（留痕与进度）---------- */
const myChangesVisible = ref(false)
const myChangesLoading = ref(false)
const myChanges = ref<ScheduleChangeItem[]>([])

const pendingChangeCount = computed(() => myChanges.value.filter((r) => r.status === 'pending').length)

function changeStatusType(s: string): 'warning' | 'success' | 'danger' | 'info' {
  if (s === 'approved') return 'success'
  if (s === 'rejected') return 'danger'
  if (s === 'pending') return 'warning'
  return 'info'
}

async function loadMyChanges() {
  myChangesLoading.value = true
  try {
    myChanges.value = await getMyScheduleChanges()
  } catch {
    myChanges.value = []
  } finally {
    myChangesLoading.value = false
  }
}

async function openMyChanges() {
  myChangesVisible.value = true
  await loadMyChanges()
}

async function cancelMyChange(id: number) {
  try {
    await cancelScheduleChange(id)
    ElMessage.success('已撤回')
    await loadMyChanges()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '撤回失败')
  }
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
    // 周次选择器默认落在当前教学周（后端统一口径）；换学期时重算
    if (activeWeek.value == null || view.value.semester !== semester.value) {
      activeWeek.value = view.value.current_week ?? null
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
  // 申请进度不阻塞课表首屏，静默拿一次用于徽标计数
  void loadMyChanges()
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
/* 移动端排课调整入口：两个等宽小按钮，常驻在课表上方 */
.tm-sched-ops {
  display: flex;
  gap: 8px;
  padding: 0 14px 10px;
}
.tm-op-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 32px;
  border-radius: 9px;
  border: 1px solid var(--tm-line);
  background: var(--tm-surf);
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  color: var(--tm-ink2);
  cursor: pointer;
}
.tm-op-btn:active { background: var(--tm-surf2); }
.tm-op-btn em {
  font-style: normal;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 99px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
.filter-week {
  width: 110px;
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
/* 排课调整入口：固定在详情底部，避免详情一长就找不到 */
.drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--tui-border);
}
.drawer-actions .el-button {
  flex: 1;
  margin-left: 0;
}
.drawer-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
}
.change-origin {
  margin-bottom: 14px;
}
.change-when {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}
.change-sep {
  color: var(--tui-text-tertiary);
  flex: 0 0 auto;
}
/* 「我的申请」列表 */
.mc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mc-item {
  border: 1px solid var(--tui-border);
  border-radius: 10px;
  padding: 12px 14px;
  background: var(--tui-surface);
}
.mc-item.is-rejected {
  background: var(--tui-surface-muted);
}
.mc-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.mc-kind {
  font-size: 11px;
  font-weight: 700;
  color: var(--tui-accent, #2563eb);
  background: rgba(37, 99, 235, 0.1);
  border-radius: 4px;
  padding: 1px 6px;
}
.mc-name {
  font-size: 14px;
  font-weight: 650;
  color: var(--tui-text);
  flex: 1;
  min-width: 0;
}
.mc-when {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--tui-text-secondary);
}
.mc-origin {
  text-decoration: line-through;
  color: var(--tui-text-quiet);
}
.mc-arrow {
  color: var(--tui-text-quiet);
}
.mc-target {
  font-weight: 650;
  color: var(--tui-text);
}
.mc-loc {
  color: var(--tui-text-tertiary);
}
.mc-meta {
  margin-top: 5px;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.mc-reason,
.mc-reject {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--tui-text-secondary);
}
.mc-reject {
  color: #c02f45;
}
.mc-ops {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}
.hero-badge {
  margin-left: 4px;
  vertical-align: middle;
}

/* ===== 调课/增课弹窗（与学生端简历导出弹窗同款底部抽屉） ===== */
.chg-mask {
  position: fixed;
  inset: 0;
  z-index: 2600;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(20, 24, 22, 0.42);
  backdrop-filter: blur(2px);
}
.chg-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-height: 92vh;
  background: var(--tui-surface, #fff);
  border-radius: 18px 18px 0 0;
  box-shadow: 0 -10px 30px rgba(16, 30, 24, 0.16);
  overflow: hidden;
}
/* 桌面端不铺满整行：居中一块窄面板，贴底弹出 */
@media (min-width: 768px) {
  .chg-panel {
    width: 460px;
    border-radius: 18px;
    margin-bottom: 6vh;
    max-height: 86vh;
  }
}
.chg-fade-enter-active,
.chg-fade-leave-active {
  transition: opacity 0.2s ease;
}
.chg-fade-enter-active .chg-panel,
.chg-fade-leave-active .chg-panel {
  transition: transform 0.26s cubic-bezier(0.32, 0.72, 0, 1);
}
.chg-fade-enter-from,
.chg-fade-leave-to {
  opacity: 0;
}
.chg-fade-enter-from .chg-panel,
.chg-fade-leave-to .chg-panel {
  transform: translateY(24px);
}
.chg-hd {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 16px 18px 10px;
  border-bottom: 1px solid var(--tui-border);
}
.chg-hd-tx {
  flex: 1;
  min-width: 0;
}
.chg-hd h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--tui-text);
}
.chg-hd p {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.chg-x {
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 50%;
  background: var(--tui-surface-muted);
  color: var(--tui-text-tertiary);
  font-size: 12px;
  cursor: pointer;
  line-height: 1;
}
.chg-x:hover {
  background: var(--tui-surface-page);
  color: var(--tui-text);
}
.chg-body {
  padding: 12px 18px 4px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chg-cap {
  margin: 2px 0 -2px;
  font-size: 11px;
  font-weight: 650;
  color: var(--tui-text-tertiary);
}
.chg-origin {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 11px;
  border-radius: 10px;
  background: var(--tui-surface-muted);
  font-size: 12px;
}
.chg-origin b {
  font-size: 13px;
  color: var(--tui-text);
}
.chg-origin span {
  color: var(--tui-text-tertiary);
}
.chg-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chg-chips-scroll {
  flex-wrap: nowrap;
  overflow-x: auto;
  padding-bottom: 2px;
}
.chg-chip {
  min-width: 34px;
  height: 28px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid var(--tui-border);
  background: var(--tui-surface);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-secondary);
  cursor: pointer;
  transition: all 0.14s var(--tui-ease);
}
.chg-chip:hover {
  border-color: var(--tui-brand);
  color: var(--tui-brand-strong);
}
.chg-chip.on {
  background: var(--tui-brand);
  border-color: var(--tui-brand);
  color: #fff;
}
.chg-chip.skipped:not(.on) {
  background: var(--tui-surface-muted);
  color: var(--tui-text-quiet);
  text-decoration: line-through;
}
.chg-tip {
  margin: -3px 0 0;
  font-size: 10.5px;
  color: var(--tui-text-quiet);
}
.chg-two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.chg-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 11px;
  color: var(--tui-text-tertiary);
}
.chg-field :deep(.el-select),
.chg-field :deep(.el-input),
.chg-field :deep(.el-input-number) {
  width: 100%;
}
/* ── 输入控件美化：浅灰底、圆角 10、聚焦亮边，与胶囊按钮同一观感 ── */
.chg-field :deep(.el-input__wrapper),
.chg-field :deep(.el-textarea__inner),
.chg-field :deep(.el-select__wrapper) {
  border-radius: 10px;
  background: var(--tui-surface-muted);
  box-shadow: 0 0 0 1px var(--tui-border-strong) inset;
  transition: box-shadow 0.15s var(--tui-ease), background 0.15s var(--tui-ease);
}
.chg-field :deep(.el-input__wrapper.is-focus),
.chg-field :deep(.el-select__wrapper.is-focused),
.chg-field :deep(.el-textarea__inner:focus) {
  background: var(--tui-surface);
  box-shadow: 0 0 0 1.5px var(--tui-brand) inset;
}
.chg-field :deep(.el-input__wrapper:hover:not(.is-focus)),
.chg-field :deep(.el-select__wrapper:hover:not(.is-focused)),
.chg-field :deep(.el-textarea__inner:hover:not(:focus)) {
  box-shadow: 0 0 0 1px var(--tui-text-quiet) inset;
}
.chg-field :deep(.el-input__inner) {
  height: 32px;
  font-size: 13px;
  color: var(--tui-text);
}
.chg-field :deep(.el-input__inner::placeholder),
.chg-field :deep(.el-textarea__inner::placeholder) {
  color: var(--tui-text-quiet);
}
.chg-field :deep(.el-textarea__inner) {
  padding: 8px 10px;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--tui-text);
  resize: none;
}
/* 下拉 / 步进器：紧凑高度 + 细箭头 */
.chg-field :deep(.el-select__selected-item),
.chg-field :deep(.el-select__placeholder) {
  font-size: 13px;
  color: var(--tui-text);
}
.chg-field :deep(.el-input-number) .el-input__inner {
  text-align: left;
}
.chg-field :deep(.el-input-number__decrease),
.chg-field :deep(.el-input-number__increase) {
  background: transparent;
  color: var(--tui-text-tertiary);
  border-radius: 8px;
  width: 26px;
}
.chg-field :deep(.el-input-number__decrease:hover),
.chg-field :deep(.el-input-number__increase:hover) {
  color: var(--tui-brand);
}
/* 下拉面板 append-to-body，浮层里的选项也要跟手 */
:global(.el-select-dropdown.chg-popper) .el-select-dropdown__item {
  border-radius: 8px;
  font-size: 13px;
}
:global(.el-select-dropdown.chg-popper) .el-select-dropdown__item.is-selected {
  color: var(--tui-brand);
  font-weight: 600;
}
.chg-ft {
  padding: 10px 18px calc(12px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--tui-border);
}
.chg-submit {
  width: 100%;
  height: 42px;
  border: none;
  border-radius: 12px;
  background: var(--tui-brand);
  color: #fff;
  font: inherit;
  font-size: 14.5px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.14s var(--tui-ease);
}
.chg-submit:hover {
  opacity: 0.92;
}
.chg-submit:disabled {
  opacity: 0.6;
  cursor: default;
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
