<template>
  <div class="tui-page growth-page">
    <SubPageHeader title="我的成长" fallback="/teacher" />

    <!-- ============================================================
         移动端 · 定稿版「大环 + 徽章墙」
         一屏读完：成长值环 → 徽章墙 → 最快加分项 → 近 6 周影响 → 履职 → 最近痕迹 → AI 观察
         ============================================================ -->
    <div v-if="isMobile" class="tm-page tm-m">
      <el-skeleton v-if="loading && !data" :rows="6" animated style="padding: 0 14px" />

      <template v-else-if="data">
        <!-- ① 成长值大环 -->
        <div class="tm-gr-head">
          <div class="tm-bigring">
            <svg width="82" height="82" viewBox="0 0 82 82">
              <defs>
                <linearGradient id="tmGrowGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stop-color="#2f6df6" />
                  <stop offset=".6" stop-color="#5b5bd6" />
                  <stop offset="1" stop-color="#7c5cf0" />
                </linearGradient>
              </defs>
              <circle class="tm-bgc" cx="41" cy="41" r="34" />
              <circle class="tm-fgc" cx="41" cy="41" r="34" :stroke-dasharray="`${growDash} ${growCirc}`" />
            </svg>
            <div class="tm-gv">
              <b>{{ data.level.points }}</b>
              <span>成长值</span>
            </div>
          </div>
          <div class="tm-gr-bd">
            <div class="tm-gr-lv">
              {{ data.level.name }}
              <em>{{ data.badges.earned_count }}/{{ data.badges.total_count }} 徽章</em>
            </div>
            <div class="tm-gr-s">{{ data.teacher.college || '未知学院' }} · {{ data.level.desc }}</div>
            <div class="tm-gr-nx">
              <template v-if="data.level.next_points">
                距下一级还差 <b>{{ data.level.next_points - data.level.points }}</b> 分 · 已完成
                {{ data.level.progress }}%
              </template>
              <template v-else>已是最高等级</template>
            </div>
          </div>
        </div>

        <!-- ①-A 成长分析：把雷达、履职、影响力合成一份诊断 -->
        <div v-if="growthAnalysis" class="tm-anal">
          <div class="tm-anal-hd">
            <span class="tm-anal-t">成长分析</span>
            <span class="tm-tag tm-ai">综合 {{ growthAnalysis.score }} 分</span>
          </div>
          <p class="tm-anal-sum">{{ growthAnalysis.summary }}</p>
          <div class="tm-anal-list">
            <div v-for="l in growthAnalysis.lines" :key="l.key" class="tm-anal-row">
              <span class="tm-anal-k">{{ l.title }}</span>
              <span class="tm-anal-v" :class="'is-' + l.tone">{{ l.value }}</span>
              <span class="tm-anal-n">{{ l.note }}</span>
            </div>
          </div>
        </div>

        <!-- ①-B AI 成长建议：把雷达短板、履职缺口、最近可达成的徽章翻译成可执行的三条建议 -->
        <div class="tm-ai-card">
          <div class="tm-ai-hd">
            <span class="tm-ai-t">AI 成长建议</span>
            <span class="tm-tag tm-ai">基于能力雷达与履职</span>
          </div>
          <div class="tm-ai-list">
            <div v-for="(s, i) in growthAdvice" :key="i" class="tm-ai-item">
              <span class="tm-ai-idx">{{ i + 1 }}</span>
              <div class="tm-ai-bd">
                <div class="tm-ai-name">{{ s.title }}</div>
                <p class="tm-ai-desc">{{ s.desc }}</p>
                <button v-if="s.link" class="tm-ai-go" type="button" @click="go(s.link)">
                  {{ s.action }}
                  <el-icon :size="12"><ArrowRight /></el-icon>
                </button>
              </div>
            </div>
          </div>
          <button class="tm-ai-evidence" type="button" @click="showAdviceEvidence = !showAdviceEvidence">
            {{ showAdviceEvidence ? '收起依据' : '查看依据' }}
            <el-icon :size="12"><component :is="showAdviceEvidence ? ArrowUp : ArrowDown" /></el-icon>
          </button>
          <div v-if="showAdviceEvidence" class="tm-ai-evidence-bd">
            {{ adviceEvidence }}
          </div>
        </div>

        <!-- ①-C 我的育人档案：案例 / 荣誉 / 培训 / 研究成果 + 成长报告导出 -->
        <div class="tm-archive">
          <div class="tm-archive-hd">
            <b>我的育人档案</b>
            <em>{{ archiveCount }} 条</em>
          </div>
          <div class="tm-archive-sub">课例、论文、获奖、公开课都可沉淀进来，并推动徽章进度</div>
          <div class="tm-archive-act">
            <button type="button" class="tm-upload-btn" @click="openItemDialog()">新增档案</button>
            <button type="button" class="tm-archive-ghost" @click="openArchiveReport">成长报告</button>
          </div>
        </div>

        <!-- ② 徽章墙 -->
        <div class="tm-sec">
          <span class="tm-sec-t">徽章墙</span>
          <span class="tm-sec-m">{{ data.badges.earned_count }} / {{ data.badges.total_count }} 已点亮</span>
        </div>
        <div class="tm-badges">
          <div
            v-for="b in mobileBadges"
            :key="b.code"
            class="tm-bdg"
            :class="{ 'tm-lock': !b.earned }"
            @click="showBadge(b)"
          >
            <div class="tm-bi">{{ b.icon || b.name.slice(0, 1) }}</div>
            <b>{{ b.name }}</b>
            <span>{{ b.earned ? '已获得' : b.progress + '%' }}</span>
          </div>
        </div>

        <!-- ③ 最快的加分项（未获得徽章里进度最高的三个） -->
        <div class="tm-sec" style="margin-top: 11px">
          <span class="tm-sec-t">最快的三个加分项</span>
          <span class="tm-sec-m">按进度排序</span>
        </div>
        <div v-if="nextBadges.length" class="tm-plus">
          <div v-for="b in nextBadges" :key="b.code" class="tm-plus-i">
            <span class="tm-pi-c">+</span>
            <div class="tm-pi-n">
              <div class="tm-pi-t">{{ b.name }}</div>
              <div class="tm-pi-s">{{ b.target_label }}</div>
            </div>
            <span class="tm-pi-p">{{ b.progress }}%</span>
          </div>
        </div>
        <div v-else class="tm-plus-empty">全部徽章已点亮</div>

        <!-- ④ 近 6 周影响力（真实曲线数据） -->
        <div class="tm-card">
          <div class="tm-card-hd">
            <span class="tm-ct">近 6 周影响力</span>
            <span class="tm-cm">均值 {{ data.impact.avg }}</span>
          </div>
          <div class="tm-bars">
            <div v-for="(p, i) in impactBars" :key="p.week" class="tm-bcol" :class="{ 'tm-hi': i === impactBars.length - 1 }">
              <i :style="{ height: p.h + 'px' }"></i>
              <em>{{ shortDate(p.week) }}</em>
            </div>
          </div>
        </div>

        <!-- ⑤ 履职四指标 -->
        <div class="tm-sec" style="margin-top: 11px">
          <span class="tm-sec-t">本月履职</span>
          <span class="tm-sec-m">{{ data.duty.period.care_month }}</span>
        </div>
        <div class="tm-kpis">
          <div v-for="m in data.duty.metrics.slice(0, 3)" :key="m.key" class="tm-kpi">
            <b>{{ m.value }}</b>
            <span>{{ m.label }}</span>
          </div>
          <div class="tm-kpi tm-ok">
            <b>{{ data.duty.coverage_rate }}%</b>
            <span>覆盖率</span>
          </div>
        </div>

        <!-- ⑥ 最近痕迹 -->
        <div class="tm-sec" style="margin-top: 11px">
          <span class="tm-sec-t">最近痕迹</span>
          <span class="tm-sec-m">{{ data.timeline.length }} 条</span>
        </div>
        <div class="tm-rows">
          <div v-for="(t, i) in data.timeline.slice(0, 3)" :key="i" class="tm-row">
            <span class="tm-r-ic">{{ t.icon || '·' }}</span>
            <div class="tm-r-bd">
              <div class="tm-r-t"><span>{{ t.title }}</span></div>
              <div class="tm-r-s">{{ t.desc || t.type }}</div>
            </div>
            <div class="tm-r-e"><span class="tm-r-num">{{ shortDate(t.date) }}</span></div>
          </div>
        </div>

        <div class="tm-tail">成长值 = 教学 + 育人 + 研究三部分加权，每月 1 日更新</div>
      </template>
    </div>

    <div v-else class="tui-content">
      <!-- ===== 桌面端页头（统一走 TuiPageHero，与其它教师页一致）===== -->
      <TuiPageHero
        v-if="!isMobile"
        title="我的成长"
        sub="育人先育己：职业能力、履职影响与成长痕迹都在这里"
        :icon="TrendCharts"
        tone="violet"
      >
        <template v-if="data">
          <div class="hero-pill">
            <b>{{ data.level.name }}</b>
            <span>{{ data.level.points }} 分</span>
          </div>
          <div class="hero-pill">
            <b>{{ data.badges.earned_count }}/{{ data.badges.total_count }}</b>
            <span>徽章</span>
          </div>
        </template>
        <template #actions>
          <el-button :loading="loading" text @click="load">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </template>
      </TuiPageHero>

      <el-skeleton v-if="loading && !data" :rows="8" animated />

      <template v-else-if="data">
        <!-- ===== 1. 身份 + 等级 ===== -->
        <section class="growth-hero">
          <div class="hero-left">
            <el-avatar :size="isMobile ? 52 : 64" :src="data.teacher.avatar || ''">
              {{ data.teacher.name?.[0] }}
            </el-avatar>
            <div class="hero-meta">
              <div class="hero-name">
                {{ data.teacher.name }}
                <span class="hero-level">{{ data.level.name }}</span>
              </div>
              <div class="hero-sub">
                {{ data.teacher.college || '未知学院' }}
                <template v-if="data.teacher.title"> · {{ data.teacher.title }}</template>
              </div>
              <div v-if="data.teacher.signature" class="hero-sign">{{ data.teacher.signature }}</div>
            </div>
          </div>

          <div class="hero-right">
            <div class="hero-points">
              <span class="num">{{ data.level.points }}</span>
              <span class="unit">成长值</span>
            </div>
            <div class="hero-progress">
              <el-progress
                :percentage="data.level.progress"
                :stroke-width="8"
                :show-text="false"
                color="#2563eb"
              />
              <span class="hero-progress-text">
                <template v-if="data.level.next_points">
                  距下一级还需 {{ data.level.next_points - data.level.points }} 分
                </template>
                <template v-else>已达最高等级</template>
              </span>
            </div>
            <div class="hero-badges">
              <span>徽章 {{ data.badges.earned_count }} / {{ data.badges.total_count }}</span>
              <span class="dot">·</span>
              <span>{{ data.level.desc }}</span>
            </div>
          </div>
        </section>

        <!-- ===== 2. 成长分析 ===== -->
        <section v-if="growthAnalysis" class="tui-card">
          <div class="card-head">
            <h2 class="card-title">成长分析</h2>
            <span class="card-hint">能力画像 · 履职趋势 · 育人影响力的综合诊断</span>
          </div>

          <div class="anal-top">
            <div class="anal-score">
              <b>{{ growthAnalysis.score }}</b>
              <span>综合健康度</span>
            </div>
            <p class="anal-sum">{{ growthAnalysis.summary }}</p>
          </div>

          <div class="anal-rows">
            <div v-for="l in growthAnalysis.lines" :key="l.key" class="anal-row">
              <span class="anal-k">{{ l.title }}</span>
              <span class="anal-v" :class="'is-' + l.tone">{{ l.value }}</span>
              <span class="anal-n">{{ l.note }}</span>
            </div>
          </div>
        </section>

        <!-- ===== 3. 九项职业能力雷达 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">职业能力画像</h2>
            <span class="card-hint">对标《高等学校辅导员职业能力标准（暂行）》九项能力</span>
          </div>

          <div class="radar-wrap">
            <!--
              纯 SVG 雷达：不引第三方图表库，避免包体增大。
              viewBox 边距必须是 PAD 而不是固定 30：标签画在 1.18*R 处，
              最左/最右的标签是 6 个中文字（约 60px 宽），30px 边距会把「班级管理」「学业指导」裁掉半截。
            -->
            <svg class="radar-svg" :viewBox="`0 0 ${R * 2 + PAD * 2} ${R * 2 + PAD * 2}`">
              <g :transform="`translate(${R + PAD}, ${R + PAD})`">
                <!-- 网格 -->
                <polygon
                  v-for="ring in [0.25, 0.5, 0.75, 1]"
                  :key="`ring-${ring}`"
                  :points="ringPoints(ring)"
                  class="radar-ring"
                />
                <!-- 轴线 -->
                <line
                  v-for="(_, i) in data.radar.items"
                  :key="`axis-${i}`"
                  x1="0"
                  y1="0"
                  :x2="axisPoint(i, 1).x"
                  :y2="axisPoint(i, 1).y"
                  class="radar-axis"
                />
                <!-- 数据面 -->
                <polygon :points="dataPolygon" class="radar-area" />
                <!-- 顶点 -->
                <circle
                  v-for="(pt, i) in dataPoints"
                  :key="`pt-${i}`"
                  :cx="pt.x"
                  :cy="pt.y"
                  r="3.5"
                  class="radar-dot"
                />
                <!-- 标签 -->
                <text
                  v-for="(item, i) in data.radar.items"
                  :key="`lb-${i}`"
                  :x="axisPoint(i, 1.18).x"
                  :y="axisPoint(i, 1.18).y"
                  class="radar-label"
                  :text-anchor="labelAnchor(i)"
                  dominant-baseline="middle"
                >
                  {{ item.name }}
                </text>
              </g>
            </svg>

            <div class="radar-side">
              <div class="radar-stat">
                <span class="radar-stat-num">{{ data.radar.avg.toFixed(1) }}</span>
                <span class="radar-stat-label">综合均分</span>
              </div>
              <div v-if="data.radar.top" class="radar-note">
                <span class="tag tag-success">优势</span>
                {{ data.radar.top[0] }}
                <b>{{ data.radar.top[1].toFixed(1) }}</b>
              </div>
              <div v-if="data.radar.weak" class="radar-note">
                <span class="tag tag-warn">待提升</span>
                {{ data.radar.weak[0] }}
                <b>{{ data.radar.weak[1].toFixed(1) }}</b>
              </div>
              <div class="radar-peer">
                互评覆盖 {{ data.radar.peer_coverage }} / {{ data.radar.items.length }} 项
                <span v-if="!data.radar.peer_coverage" class="quiet">（暂无学生互评样本）</span>
              </div>
            </div>
          </div>

          <!-- 能力明细 -->
          <div class="cap-list">
            <div v-for="cap in data.radar.items" :key="cap.key" class="cap-item">
              <span class="cap-icon">{{ cap.icon }}</span>
              <div class="cap-body">
                <div class="cap-name">
                  {{ cap.name }}
                  <span v-if="cap.has_peer" class="cap-peer" title="含学生互评分">互评</span>
                </div>
                <div class="cap-desc">{{ cap.desc }}</div>
                <el-progress
                  :percentage="Math.min(100, Math.round(cap.score))"
                  :stroke-width="5"
                  :show-text="false"
                  :color="scoreColor(cap.score)"
                />
              </div>
              <span class="cap-score">{{ cap.score.toFixed(1) }}</span>
            </div>
          </div>
        </section>

        <!-- ===== 3. 本月履职画像 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">本月履职</h2>
            <span class="card-hint">与上月对比，看的是"我做了什么"，不是"系统里有什么"</span>
          </div>

          <div class="duty-grid">
            <div v-for="m in data.duty.metrics" :key="m.key" class="duty-cell">
              <div class="duty-top">
                <span class="duty-icon">{{ m.icon }}</span>
                <span class="duty-label">{{ m.label }}</span>
              </div>
              <div class="duty-num">
                {{ m.value }}<span class="duty-unit">{{ m.unit }}</span>
              </div>
              <div class="duty-trend" :class="trendClass(m.trend)">
                <template v-if="m.trend === null">上月 {{ m.previous }}</template>
                <template v-else>
                  {{ m.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(m.trend).toFixed(0) }}%
                  <span class="quiet">（上月 {{ m.previous }}）</span>
                </template>
              </div>
            </div>
          </div>

          <div class="duty-sub">
            <div class="duty-sub-item">
              <span class="quiet">待办办结率</span>
              <b>{{ data.duty.tasks.done_rate.toFixed(0) }}%</b>
              <span class="quiet">（{{ data.duty.tasks.done }}/{{ data.duty.tasks.total }}）</span>
            </div>
            <div class="duty-sub-item">
              <span class="quiet">学生覆盖率</span>
              <b>{{ data.duty.coverage_rate.toFixed(0) }}%</b>
              <span class="quiet">（{{ data.duty.cared_students_month }}/{{ data.duty.student_total }}）</span>
            </div>
            <div class="duty-sub-item" :class="{ warn: data.duty.pending_visits > 0 }">
              <span class="quiet">悬空家访</span>
              <b>{{ data.duty.pending_visits }}</b>
              <span v-if="data.duty.pending_visits > 0" class="quiet"> 项未留痕</span>
            </div>
            <div class="duty-sub-item">
              <span class="quiet">教学工作量</span>
              <b>{{ data.duty.teaching.courses }}</b>
              <span class="quiet"> 门 · 本月点名 {{ data.duty.teaching.sessions_month }} 次</span>
            </div>
          </div>

          <div v-if="data.duty.tasks.overdue > 0" class="duty-alert">
            <el-icon><WarningFilled /></el-icon>
            有 {{ data.duty.tasks.overdue }} 条待办已逾期
            <el-button size="small" text type="primary" @click="go('/teacher/tasks')">去处理</el-button>
          </div>
        </section>

        <!-- ===== 4. 育人影响力曲线 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">育人影响力</h2>
            <span class="card-hint">近 12 周「关怀 + 家访 + 家校 + 表扬」行为总量</span>
          </div>

          <div class="impact-wrap">
            <!-- 纯 SVG 折线：宽高比固定，靠 CSS 自适应 -->
            <svg class="impact-svg" viewBox="0 0 640 160" preserveAspectRatio="none">
              <polyline :points="impactAxisLine" class="impact-axis" />
              <polygon :points="impactArea" class="impact-area" />
              <polyline :points="impactLine" class="impact-line" />
              <circle
                v-for="(pt, i) in impactDots"
                :key="`idot-${i}`"
                :cx="pt.x"
                :cy="pt.y"
                r="3"
                class="impact-dot"
              />
            </svg>
            <div class="impact-labels">
              <span v-for="(p, i) in data.impact.points" :key="`il-${i}`">
                {{ shortDate(p.week) }}
              </span>
            </div>
          </div>

          <div class="impact-foot">
            <span>累计 <b>{{ data.impact.total }}</b> 次育人行为</span>
            <span class="dot">·</span>
            <span>周均 <b>{{ data.impact.avg.toFixed(1) }}</b> 次</span>
            <span class="dot">·</span>
            <span>最高一周 {{ shortDate(data.impact.best_week) }}</span>
          </div>

          <div v-if="data.impact.total === 0" class="empty-tip">
            还没有育人行为记录。去「关怀与家校」写一条谈话记录，曲线就会开始生长。
            <el-button size="small" text type="primary" @click="go('/teacher/care-center')">
              去记录
            </el-button>
          </div>
        </section>

        <!-- ===== 5. 教学规模 + 育人∩教学 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">我的教学规模</h2>
            <span class="card-hint">「育人 ∩ 教学」是教师端独有的交叉视角</span>
          </div>

          <div class="scale-grid">
            <div class="scale-cell">
              <span class="scale-num">{{ data.teaching.course_count }}</span>
              <span class="scale-label">授课门/次</span>
            </div>
            <div class="scale-cell">
              <span class="scale-num">{{ data.teaching.class_count }}</span>
              <span class="scale-label">覆盖班级</span>
            </div>
            <div class="scale-cell">
              <span class="scale-num">{{ data.teaching.student_count }}</span>
              <span class="scale-label">授课学生</span>
            </div>
            <div class="scale-cell highlight">
              <span class="scale-num">{{ data.teaching.overlap_count }}</span>
              <span class="scale-label">既教又带</span>
            </div>
            <div class="scale-cell">
              <span class="scale-num">{{ data.teaching.attendance_sessions }}</span>
              <span class="scale-label">点名课次</span>
            </div>
            <div class="scale-cell">
              <span class="scale-num">{{ data.teaching.homework_count }}</span>
              <span class="scale-label">布置作业</span>
            </div>
          </div>

          <div v-if="data.teaching.overlap_count > 0" class="overlap-tip">
            有 {{ data.teaching.overlap_count }} 位学生既在你的课堂上、也在你带的班里——
            这是最容易发现学业与心理联动信号的人群，建议优先关注。
          </div>
        </section>

        <!-- ===== 6. 徽章墙 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">育人徽章</h2>
            <span class="card-hint">已获得 {{ data.badges.earned_count }} / {{ data.badges.total_count }}</span>
          </div>

          <div class="badge-grid">
            <div
              v-for="b in displayBadges"
              :key="b.code"
              class="badge-cell"
              :class="{ locked: !b.earned }"
              :title="b.desc"
            >
              <span class="badge-icon">{{ b.icon }}</span>
              <span class="badge-name">{{ b.name }}</span>
              <span v-if="!b.earned" class="badge-progress">{{ b.progress }}%</span>
            </div>
          </div>

          <div v-if="data.badges.locked.length" class="badge-more">
            还有 {{ data.badges.locked.length }} 枚待解锁，
            <el-button size="small" text type="primary" @click="showAllBadges = !showAllBadges">
              {{ showAllBadges ? '收起' : '查看全部' }}
            </el-button>
          </div>
        </section>

        <!-- ===== 6.5 我的育人档案（原「学生成长档案」页里的教师维度内容） ===== -->
        <section class="tui-card" ref="archiveRef">
          <div class="card-head">
            <h2 class="card-title">我的育人档案</h2>
            <span class="card-hint">案例 / 荣誉 / 培训研修 / 研究成果，共 {{ archiveCount }} 条</span>
          </div>

          <div v-if="archiveLoading" class="empty-tip">正在读取育人档案…</div>
          <div v-else-if="!archiveItems.length" class="empty-tip">
            还没有育人档案。添加一条案例或荣誉，它会同时进入成长时间线与成长报告。
          </div>
          <template v-else>
            <!-- 可见性筛选：让「公开 / 仅自己」在列表上真正可感知 -->
            <div class="arch-tabs">
              <button
                v-for="t in ARCHIVE_TABS"
                :key="t.value"
                type="button"
                class="arch-tab"
                :class="{ active: archiveTab === t.value }"
                @click="archiveTab = t.value"
              >
                {{ t.label }}
                <em>{{ archiveTabCount(t.value) }}</em>
              </button>
            </div>

            <div v-if="archiveFiltered.length" class="arch-list">
              <div v-for="it in archiveFiltered.slice(0, 20)" :key="it.id" class="arch-item">
                <span class="arch-dot" :style="{ background: PORTFOLIO_TYPE_COLOR[it.item_type] }"></span>
                <span class="arch-title">{{ it.title }}</span>
                <span class="arch-type">{{ PORTFOLIO_TYPE_LABEL[it.item_type] }}</span>
                <span class="arch-date">{{ it.occurred_on || '—' }}</span>
                <span class="arch-vis" :class="{ 'is-public': it.visibility === 'public' }">
                  {{ it.visibility === 'public' ? '公开展示' : '仅自己可见' }}
                </span>
                <el-button text size="small" :icon="Edit" @click="openItemDialog(it)" />
              </div>
            </div>
            <div v-else class="empty-tip">
              该分类下还没有档案。
            </div>

            <!-- 同行公开展示区：只有标记「公开展示」的档案会出现在这里 -->
            <div v-if="publicItems.length" class="arch-public">
              <div class="arch-public-hd">
                <span>同行公开展示</span>
                <em>其他教师公开的 {{ publicItems.length }} 条</em>
              </div>
              <div v-for="it in publicItems.slice(0, 5)" :key="`p-${it.id}`" class="arch-public-item">
                <span class="arch-dot" :style="{ background: PORTFOLIO_TYPE_COLOR[it.item_type] }"></span>
                <span class="arch-title">{{ it.title }}</span>
                <span class="arch-type">{{ it.teacher_name || '—' }}</span>
              </div>
            </div>
          </template>

          <div class="arch-act">
            <el-button round :icon="Plus" @click="openItemDialog()">新增档案</el-button>
            <el-button round :icon="Printer" :loading="reportLoading" @click="openArchiveReport">
              成长报告
            </el-button>
          </div>
          <div class="arch-note">
            成长报告汇总的是你自己的育人档案，与学生无关；学生的成长记录请看「学生成长档案」。
          </div>
        </section>

        <!-- ===== 7. 成长时间线 ===== -->
        <section class="tui-card">
          <div class="card-head">
            <h2 class="card-title">成长时间线</h2>
            <span class="card-hint">作品集 + 徽章 + 育人行为的合并轨迹</span>
          </div>

          <div v-if="data.timeline.length" class="timeline">
            <div v-for="(t, i) in data.timeline" :key="`tl-${i}`" class="tl-item">
              <div class="tl-dot">{{ t.icon }}</div>
              <div class="tl-body">
                <div class="tl-title">{{ t.title }}</div>
                <div v-if="t.desc" class="tl-desc">{{ t.desc }}</div>
                <div class="tl-meta">
                  {{ t.date }}
                  <span v-if="t.type" class="tl-type">{{ t.type }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-tip">
            还没有成长记录。在上面「我的育人档案」里添加一条案例或荣誉，这里会按时间串联你的职业轨迹。
          </div>
        </section>
      </template>

      <el-empty v-else description="成长数据加载失败">
        <el-button type="primary" @click="load">重试</el-button>
      </el-empty>
    </div>

    <!-- 育人档案：新增 / 编辑（桌面端 el-dialog，移动端全屏子页） -->
    <PortfolioItemDialog
      v-model="itemDialogVisible"
      :item="editingItem"
      @saved="reloadArchive"
    />

    <!-- 成长报告：教师本人育档案的汇总导出，与学生无关 -->
    <ResponsivePopup
      v-model="reportVisible"
      title="成长报告"
      width="420px"
      align-center
      :close-on-click-modal="false"
      class="tui-dialog"
      destroy-on-close
    >
      <div v-if="report" class="rpt">
        <div class="rpt-cover">
          <img v-if="siteMascot" class="rpt-mascot" :src="siteMascot" :alt="siteName" />
          <div class="rpt-cover-bd">
            <h3>{{ report.teacher_name }} · 教师成长报告</h3>
            <span>生成于 {{ (report.generated_at || '').slice(0, 10) }} · 共 {{ report.total }} 条育人档案</span>
          </div>
          <el-button class="rpt-print" size="small" :icon="Printer" @click="printReport">打印 / PDF</el-button>
        </div>

        <div class="rpt-types">
          <div v-for="t in report.by_type" :key="t.type" class="rpt-type">
            <div class="rpt-type-hd">
              <span class="rpt-lb">{{ t.label }}</span>
              <span class="rpt-num">{{ t.count }}</span>
            </div>
            <div class="rpt-bar">
              <i
                :style="{
                  width: (report.total ? Math.round((t.count / report.total) * 100) : 0) + '%',
                  background: PORTFOLIO_TYPE_COLOR[t.type],
                }"
              ></i>
            </div>
          </div>
        </div>

        <template v-if="report.items.length">
          <div class="rpt-sec">
            <span>档案明细</span>
            <span>{{ report.items.length }} 条</span>
          </div>
          <div class="rpt-list">
            <div v-for="(it, i) in report.items" :key="it.id" class="rpt-item">
              <span class="rpt-idx">{{ i + 1 }}</span>
              <span class="rpt-dot" :style="{ background: PORTFOLIO_TYPE_COLOR[it.item_type] }"></span>
              <span class="rpt-title">{{ it.title }}</span>
              <span class="rpt-meta">
                {{ PORTFOLIO_TYPE_LABEL[it.item_type] }}<template v-if="it.occurred_on"> · {{ it.occurred_on }}</template>
              </span>
            </div>
          </div>
        </template>

        <div v-else class="rpt-empty">
          <b>还没有可汇总的育人档案</b>
          <span>工作案例、荣誉表彰、培训研修与研究成果会自动归入成长报告。</span>
        </div>

        <div class="rpt-note">数据来自你的育人档案，补充档案后重新打开即可生成最新报告。</div>
      </div>
    </ResponsivePopup>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, WarningFilled, TrendCharts, ArrowRight, ArrowUp, ArrowDown, Plus, Printer, Edit } from '@element-plus/icons-vue'
import SubPageHeader from '@/components/common/SubPageHeader.vue'
import TuiPageHero from '@/components/common/TuiPageHero.vue'
import ResponsivePopup from '@/components/common/ResponsivePopup.vue'
import PortfolioItemDialog from '@/components/teacher/portfolio/PortfolioItemDialog.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useSiteConfig } from '@/composables/useSiteConfig'
import { getMyGrowth, type TeacherGrowth, type GrowthBadge } from '@/api/teacherMe'
import {
  getPortfolioItems,
  getPortfolioReport,
  getPublicPortfolioItems,
  PORTFOLIO_TYPE_COLOR,
  PORTFOLIO_TYPE_LABEL,
  type PortfolioItem,
  type PortfolioReport,
} from '@/api/teacherPortfolio'

const router = useRouter()
const route = useRoute()
const { isMobile } = useResponsive()
const { siteMascot, siteName } = useSiteConfig()

const loading = ref(false)
const data = ref<TeacherGrowth | null>(null)
const showAllBadges = ref(false)
const showAdviceEvidence = ref(false)

/* ── 我的育人档案：原「学生成长档案」页的教师维度能力，迁到本人成长页 ── */
const archiveRef = ref<HTMLElement | null>(null)
const archiveItems = ref<PortfolioItem[]>([])
const publicItems = ref<PortfolioItem[]>([])
const archiveLoading = ref(false)
const itemDialogVisible = ref(false)
const editingItem = ref<PortfolioItem | null>(null)
const report = ref<PortfolioReport | null>(null)
const reportVisible = ref(false)
const reportLoading = ref(false)
const archiveCount = computed(() => archiveItems.value.length)

/* 可见性筛选：让「公开 / 仅自己」成为页面上可感知的状态 */
type ArchiveTab = 'all' | 'private' | 'public'
const ARCHIVE_TABS: { value: ArchiveTab; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'private', label: '仅自己可见' },
  { value: 'public', label: '公开展示' },
]
const archiveTab = ref<ArchiveTab>('all')
const archiveFiltered = computed(() =>
  archiveTab.value === 'all'
    ? archiveItems.value
    : archiveItems.value.filter((it) => it.visibility === archiveTab.value)
)
function archiveTabCount(tab: ArchiveTab) {
  return tab === 'all'
    ? archiveItems.value.length
    : archiveItems.value.filter((it) => it.visibility === tab).length
}

function openItemDialog(item: PortfolioItem | null = null) {
  editingItem.value = item
  itemDialogVisible.value = true
}

async function loadArchive() {
  archiveLoading.value = true
  try {
    const [mine, pub] = await Promise.all([
      getPortfolioItems({ limit: 200 }),
      // 公开区失败不该拖垮本人的档案列表
      getPublicPortfolioItems({ limit: 10 }).catch(() => []),
    ])
    archiveItems.value = mine
    publicItems.value = pub.filter((p) => p.visibility === 'public')
  } catch {
    archiveItems.value = []
    publicItems.value = []
  } finally {
    archiveLoading.value = false
  }
}

/** 保存后同时刷新档案列表与成长数据（徽章 / 时间线依赖档案条数） */
async function reloadArchive() {
  await Promise.all([loadArchive(), load()])
}

async function openArchiveReport() {
  reportLoading.value = true
  try {
    report.value = await getPortfolioReport()
    reportVisible.value = true
  } catch {
    ElMessage.error('成长报告生成失败')
  } finally {
    reportLoading.value = false
  }
}

/** 打印 / 导出 PDF：打开独立打印窗口，避免页面样式干扰 */
function printReport() {
  const r = report.value
  if (!r) return
  const rows = r.items
    .map(
      (it, i) =>
        `<tr><td>${i + 1}</td><td>${escapeHtml(it.title)}</td><td>${PORTFOLIO_TYPE_LABEL[it.item_type]}</td><td>${it.occurred_on || '-'}</td></tr>`
    )
    .join('')
  const cards = r.by_type
    .map((t) => `<span class="chip">${t.label} <b>${t.count}</b></span>`)
    .join('')
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" />
<title>${escapeHtml(r.teacher_name)} · 教师成长报告</title>
<style>
  body{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",system-ui,sans-serif;color:#101828;padding:32px;}
  h1{font-size:20px;margin:0 0 4px;}
  .meta{color:#98a2b3;font-size:12px;margin-bottom:18px;}
  .chips{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px;}
  .chip{border:1px solid #eaecf0;border-radius:999px;padding:4px 12px;font-size:12px;color:#475467;}
  table{width:100%;border-collapse:collapse;font-size:13px;}
  th,td{border-bottom:1px solid #eaecf0;padding:8px 6px;text-align:left;}
  th{color:#667085;font-weight:600;font-size:12px;}
  td:first-child,th:first-child{width:40px;color:#98a2b3;}
</style></head><body>
  <h1>${escapeHtml(r.teacher_name)} · 教师成长报告</h1>
  <div class="meta">生成时间：${(r.generated_at || '').slice(0, 10)} ｜ 共 ${r.total} 条</div>
  <div class="chips">${cards}</div>
  <table><thead><tr><th>#</th><th>标题</th><th>类型</th><th>时间</th></tr></thead><tbody>${rows}</tbody></table>
</body></html>`
  const w = window.open('', '_blank', 'width=900,height=1000')
  if (!w) {
    ElMessage.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
    return
  }
  w.document.write(html)
  w.document.close()
  w.focus()
  w.print()
}

function escapeHtml(s: string) {
  return (s || '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string
  )
}

/** 最弱能力项：用于 AI 建议与「查看依据」 */
const weakestCapability = computed(() => {
  const items = data.value?.radar.items ?? []
  if (!items.length) return null
  return items.slice().sort((a, b) => a.score - b.score)[0]
})

/**
 * AI 成长建议（本地规则生成，不调用大模型）：
 * 三条建议分别对应「雷达短板」「履职缺口」「最近可达成徽章」，
 * 每条都指向一个能立刻执行的动作，避免只给空话。
 */
const growthAdvice = computed(() => {
  const d = data.value
  if (!d) return [] as { title: string; desc: string; action?: string; link?: string }[]
  const out: { title: string; desc: string; action?: string; link?: string }[] = []

  const weak = weakestCapability.value
  if (weak) {
    out.push({
      title: `补强「${weak.name}」`,
      desc: `当前 ${weak.score} 分，是九项能力里最低的一项。本月安排 1 次相关实践并留下记录，雷达与成长值都会同步更新。`,
      action: '去实践',
      link:
        weak.key === 'care'
          ? '/teacher/care-center'
          : weak.key === 'guardian'
            ? '/teacher/guardian'
            : '/teacher/schedule',
    })
  }

  const lowestTrend = (d.duty.metrics ?? [])
    .filter((m) => m.trend !== null)
    .slice()
    .sort((a, b) => (a.trend ?? 0) - (b.trend ?? 0))[0]
  if (lowestTrend) {
    out.push({
      title: `本月「${lowestTrend.label}」环比偏低`,
      desc: `当前 ${lowestTrend.value}${lowestTrend.unit}，较上月${lowestTrend.trend && lowestTrend.trend < 0 ? '下降' : '变化'} ${Math.abs(lowestTrend.trend ?? 0)}%。建议本周补上至少 1 次并留痕。`,
      action: '去记录',
      link: '/teacher/care-center',
    })
  } else if (d.duty.coverage_rate < 60) {
    out.push({
      title: '学生覆盖仍有提升空间',
      desc: `本月已关怀 ${d.duty.cared_students_month}/${d.duty.student_total} 人（覆盖率 ${d.duty.coverage_rate}%），优先联系最近两周没有互动记录的学生。`,
      action: '去关怀',
      link: '/teacher/care-center',
    })
  }

  const nextBadge = (d.badges.locked ?? []).slice().sort((a, b) => b.progress - a.progress)[0]
  if (nextBadge) {
    out.push({
      title: `最接近的徽章：${nextBadge.name}`,
      desc: `已完成 ${nextBadge.progress}%，还差「${nextBadge.target_label}」。把对应的教学成果或关怀记录补上，就能点亮它。`,
      action: '上传成果',
      link: '/teacher/portfolio?create=1',
    })
  }

  return out.slice(0, 3)
})

/** 「查看依据」一句话说清建议来自哪些真实字段 */
const adviceEvidence = computed(() => {
  const d = data.value
  if (!d) return ''
  const weakest = weakestCapability.value
  const w = weakest ? `能力雷达最弱项「${weakest.name}」${weakest.score} 分（均分 ${d.radar.avg}）` : '暂无能力雷达数据'
  return `${w}；本月履职：关怀 ${d.duty.metrics.find((m) => m.key === 'care')?.value ?? 0} 次、家访 ${d.duty.metrics.find((m) => m.key === 'visit')?.value ?? 0} 次、覆盖率 ${d.duty.coverage_rate}%；近 6 周育人影响力均值 ${d.impact.avg} 次；未获得徽章中进度最高为 ${(d.badges.locked ?? []).slice().sort((a, b) => b.progress - a.progress)[0]?.name ?? '无'}。建议由本地规则生成，仅供参考。`
})

interface GrowthAnalysisLine {
  key: string
  title: string
  value: string
  note: string
  tone: 'up' | 'down' | 'flat'
}

/**
 * 成长分析：把已有的真实字段（能力雷达 / 履职环比 / 育人影响力 / 等级进度）
 * 合成一份可读的诊断，只做汇总与对比，不引入新的评分来源。
 */
const growthAnalysis = computed(() => {
  const d = data.value
  if (!d) return null

  const avg = d.radar.avg || 0
  const sorted = (d.radar.items ?? []).slice().sort((a, b) => b.score - a.score)
  const top = sorted[0]
  const weak = sorted[sorted.length - 1]
  const badgeRate = d.badges.total_count ? (d.badges.earned_count / d.badges.total_count) * 100 : 0

  // 育人影响力：最近 3 周对比此前 3 周
  const pts = d.impact.points ?? []
  const recent = pts.slice(-3)
  const before = pts.slice(-6, -3)
  const recentAvg = recent.length ? recent.reduce((s, p) => s + p.value, 0) / recent.length : 0
  const beforeAvg = before.length ? before.reduce((s, p) => s + p.value, 0) / before.length : 0
  const impactDelta = beforeAvg > 0 ? Math.round(((recentAvg - beforeAvg) / beforeAvg) * 100) : null

  // 综合健康度 = 能力均分 50% + 徽章完成度 25% + 学生覆盖率 25%
  const score = Math.round(avg * 0.5 + badgeRate * 0.25 + d.duty.coverage_rate * 0.25)

  const falling = (d.duty.metrics ?? [])
    .filter((m) => m.trend !== null && (m.trend ?? 0) < 0)
    .sort((a, b) => (a.trend ?? 0) - (b.trend ?? 0))[0]

  const lines: GrowthAnalysisLine[] = [
    {
      key: 'capability',
      title: '能力结构',
      value: top ? `${top.name} ${top.score.toFixed(1)} 分` : '暂无数据',
      note:
        top && weak
          ? `高于均分 ${(top.score - avg).toFixed(1)} 分；短板「${weak.name}」低于均分 ${(avg - weak.score).toFixed(1)} 分`
          : '完成一次实践或互评后开始形成画像',
      tone: top ? (top.score >= avg ? 'up' : 'flat') : 'flat',
    },
    {
      key: 'impact',
      title: '影响力',
      value: `${recentAvg.toFixed(1)} 次/周`,
      note:
        impactDelta === null
          ? `累计 ${d.impact.total} 次 · 近 ${recent.length} 周均值`
          : impactDelta >= 0
            ? `较前 3 周提升 ${impactDelta}%`
            : `较前 3 周回落 ${Math.abs(impactDelta)}%`,
      tone: impactDelta === null ? 'flat' : impactDelta >= 0 ? 'up' : 'down',
    },
    {
      key: 'duty',
      title: '履职覆盖',
      value: `${d.duty.coverage_rate.toFixed(0)}%`,
      note: falling
        ? `「${falling.label}」环比下降 ${Math.abs(falling.trend ?? 0)}%，本月需补一次并留痕`
        : `本月关怀 ${d.duty.cared_students_month}/${d.duty.student_total} 人，履职节奏稳定`,
      tone: falling ? 'down' : 'up',
    },
    {
      key: 'level',
      title: '等级进度',
      value: `Lv.${d.level.level} · ${d.level.progress}%`,
      note:
        d.level.next_points !== null
          ? `距 ${d.level.next_points} 分晋级还差 ${Math.max(0, d.level.next_points - d.level.points)} 分`
          : '已是最高等级，重点转向影响力沉淀',
      tone: 'flat',
    },
  ]

  const summary =
    top && weak
      ? `你在「${top.name}」上优势最明显，短板集中在「${weak.name}」${
          falling
            ? `；本月「${falling.label}」环比回落，是当前最值得补的一环`
            : '；补齐短板后整体画像会更均衡'
        }。`
      : '完成更多实践与互评后，这里会给出更准确的诊断。'

  return { score, summary, lines }
})


/** 雷达半径（viewBox 内的像素单位） */
const R = 110
/** viewBox 留白：要装得下 1.18*R 处那个「6 个中文字」的标签 */
const PAD = 74

async function load() {
  loading.value = true
  try {
    data.value = await getMyGrowth()
  } catch {
    // 失败时保留上一次数据，仅首次加载失败才提示
    if (!data.value) ElMessage.error('成长数据加载失败')
  } finally {
    loading.value = false
  }
}

function go(path: string) {
  router.push(path)
}

function scoreColor(score: number) {
  if (score >= 75) return '#079455'
  if (score >= 50) return '#2563eb'
  if (score >= 25) return '#f79009'
  return '#d92d20'
}

function trendClass(trend: number | null) {
  if (trend === null) return 'flat'
  if (trend > 0) return 'up'
  if (trend < 0) return 'down'
  return 'flat'
}

/** 徽章墙：默认只展示已获得 + 前 6 枚未获得，避免一屏堆满 */
/* ---------- 移动端（定稿版·大环 + 徽章墙） ---------- */
/** 环周长与实到弧长（r = 34） */
const growCirc = 2 * Math.PI * 34
const growDash = computed(() => ((data.value?.level.progress ?? 0) / 100) * growCirc)

/** 徽章墙：已获得优先，未获得补到 8 格 */
const mobileBadges = computed<GrowthBadge[]>(() => {
  if (!data.value) return []
  const { earned, locked } = data.value.badges
  return [...earned, ...locked].slice(0, 8)
})
/** 最快加分项：未获得徽章里进度最高的三个 */
const nextBadges = computed<GrowthBadge[]>(() => {
  if (!data.value) return []
  return data.value.badges.locked
    .slice()
    .sort((a, b) => b.progress - a.progress)
    .slice(0, 3)
})
/** 近 6 周影响力柱高：按最大值归一，最小 12px，最高 68px */
const impactBars = computed(() => {
  const pts = (data.value?.impact.points || []).slice(-6)
  const max = Math.max(1, ...pts.map(p => p.value))
  return pts.map(p => ({ week: p.week, h: Math.round((p.value / max) * 56) + 12 }))
})
/** 点徽章：没有详情页，直接给一句说明 */
function showBadge(b: GrowthBadge) {
  ElMessage({
    message: b.earned
      ? `${b.name} · ${b.desc}`
      : `${b.name} · 还差「${b.target_label}」，已完成 ${b.progress}%`,
    duration: 2600,
  })
}

const displayBadges = computed<GrowthBadge[]>(() => {
  if (!data.value) return []
  const { earned, locked } = data.value.badges
  return showAllBadges.value ? [...earned, ...locked] : [...earned, ...locked.slice(0, 6)]
})

// ── 雷达几何 ──────────────────────────────────────────────
function axisPoint(i: number, scale: number) {
  if (!data.value) return { x: 0, y: 0 }
  const n = data.value.radar.items.length || 1
  // 从 12 点方向顺时针分布
  const angle = (Math.PI * 2 * i) / n - Math.PI / 2
  return { x: Math.cos(angle) * R * scale, y: Math.sin(angle) * R * scale }
}

function ringPoints(scale: number) {
  if (!data.value) return ''
  return data.value.radar.items
    .map((_, i) => {
      const p = axisPoint(i, scale)
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
    })
    .join(' ')
}

const dataPoints = computed(() => {
  if (!data.value) return []
  return data.value.radar.items.map((item, i) => {
    const scale = Math.max(0.02, Math.min(1, item.score / 100))
    return axisPoint(i, scale)
  })
})

const dataPolygon = computed(() =>
  dataPoints.value.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
)

function labelAnchor(i: number) {
  if (!data.value) return 'middle'
  const n = data.value.radar.items.length || 1
  const angle = (Math.PI * 2 * i) / n - Math.PI / 2
  const x = Math.cos(angle)
  if (x > 0.25) return 'start'
  if (x < -0.25) return 'end'
  return 'middle'
}

// ── 影响力曲线几何 ────────────────────────────────────────
const IMPACT_W = 640
const IMPACT_H = 160
const IMPACT_PAD = 8

const impactMax = computed(() => {
  const pts = data.value?.impact.points ?? []
  return Math.max(1, ...pts.map((p) => p.value))
})

function impactXY(i: number, value: number) {
  const n = Math.max(1, (data.value?.impact.points.length ?? 1) - 1)
  const x = (IMPACT_W / n) * i
  const y = IMPACT_H - IMPACT_PAD - ((IMPACT_H - IMPACT_PAD * 2) * value) / impactMax.value
  return { x, y }
}

const impactLine = computed(() => {
  const pts = data.value?.impact.points ?? []
  if (!pts.length) return ''
  return pts.map((p, i) => {
    const { x, y } = impactXY(i, p.value)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const impactArea = computed(() => {
  const line = impactLine.value
  if (!line) return ''
  return `${IMPACT_PAD},${IMPACT_H - IMPACT_PAD} ${line} ${IMPACT_W - IMPACT_PAD},${IMPACT_H - IMPACT_PAD}`
})

const impactAxisLine = computed(() => `${IMPACT_PAD},${IMPACT_H - IMPACT_PAD} ${IMPACT_W - IMPACT_PAD},${IMPACT_H - IMPACT_PAD}`)

const impactDots = computed(() => {
  const pts = data.value?.impact.points ?? []
  return pts.map((p, i) => impactXY(i, p.value))
})

function shortDate(d: string) {
  if (!d) return ''
  // '2026-08-10' → '8/10'
  const parts = d.split('-')
  return parts.length >= 3 ? `${Number(parts[1])}/${Number(parts[2])}` : d
}

onMounted(async () => {
  await Promise.all([load(), loadArchive()])
  // 从「学生成长档案」页的「我的育人档案」入口进来时，直接定位到档案区块
  if (route.query.tab === 'portfolio') {
    await nextTick()
    archiveRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
})
</script>

<style scoped>
/* 近 6 周影响力：拉高柱区高度并加宽柱体，避免图表展示过短 */
.tm-m .tm-bars {
  height: 96px;
  gap: 8px;
  margin-top: 6px;
  padding-bottom: 2px;
}
.tm-m .tm-bars .tm-bcol {
  gap: 5px;
}
.tm-m .tm-bars .tm-bcol i {
  max-width: 16px;
  border-radius: 4px 4px 2px 2px;
}
.tm-m .tm-bars .tm-bcol.tm-hi i {
  max-width: 18px;
}
.tm-m .tm-bars .tm-bcol em {
  font-size: 10px;
}
/* ---------- 移动端（定稿版·大环 + 徽章墙）私有件 ---------- */
.tm-m { min-height: calc(100vh - 60px); }
.tm-m .tm-gr-head { margin-top: 12px; }
.tm-bigring .tm-fgc { stroke: url(#tmGrowGrad); }
.tm-card { margin: 10px 14px 0; padding: 10px 11px 8px; background: var(--tm-surf); border: 1px solid var(--tm-line); border-radius: var(--tm-r); }
.tm-card-hd { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; }
.tm-card-hd .tm-ct { font-size: 11px; font-weight: 730; color: var(--tm-ink); }
.tm-card-hd .tm-cm { margin-left: auto; font-size: 9px; color: var(--tm-ink3); }

/* ---------- 成长分析（移动端） ---------- */
.tm-anal {
  margin: 0 14px 10px;
  padding: 13px 13px 11px;
  background: var(--tm-surf);
  border: 1px solid var(--tm-line);
  border-radius: var(--tm-r);
}
.tm-anal-hd { display: flex; align-items: center; gap: 6px; }
.tm-anal-hd .tm-anal-t { font-size: 14px; font-weight: 750; color: var(--tm-ink); }
.tm-anal-hd .tm-tag { margin-left: auto; }
.tm-anal-sum {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--tm-ink2);
}
.tm-anal-list { margin-top: 10px; display: flex; flex-direction: column; }
.tm-anal-row {
  display: grid;
  grid-template-columns: 66px 1fr;
  grid-template-areas: 'k v' 'n n';
  gap: 2px 10px;
  padding: 8px 0;
  border-top: 1px solid var(--tm-line2);
}
.tm-anal-k { grid-area: k; font-size: 11.5px; font-weight: 700; color: var(--tm-ink3); }
.tm-anal-v {
  grid-area: v;
  text-align: right;
  font-size: 13.5px;
  font-weight: 750;
  color: var(--tm-ink);
  font-variant-numeric: tabular-nums;
}
.tm-anal-v.is-up { color: #0f8e6b; }
.tm-anal-v.is-down { color: #c2410c; }
.tm-anal-n {
  grid-area: n;
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--tm-ink3);
}
.tm-plus-empty {
  margin: 0 14px;
  padding: 12px;
  text-align: center;
  font-size: 10.5px;
  color: var(--tm-ink3);
  border: 1px dashed var(--tm-line2);
  border-radius: var(--tm-r);
  background: var(--tm-surf);
}
.tm-bdg { cursor: pointer; }

/* ---------- 移动端字号：统一放大，避免 8~10px 在真机上难以阅读 ---------- */
.tm-m .tm-sec-t { font-size: 13px; letter-spacing: 0; text-transform: none; }
.tm-m .tm-sec-m { font-size: 11.5px; }
.tm-m .tm-kpi b { font-size: 20px; }
.tm-m .tm-kpi span { font-size: 11px; }
.tm-m .tm-gr-lv { font-size: 14px; }
.tm-m .tm-gr-s { font-size: 11.5px; }
.tm-m .tm-gr-nx { font-size: 11px; }
.tm-m .tm-bdg .tm-bi { width: 30px; height: 30px; border-radius: 10px; }
.tm-m .tm-bdg b { font-size: 11px; }
.tm-m .tm-bdg span { font-size: 9.5px; }
.tm-m .tm-plus-i .tm-pi-t { font-size: 13px; }
.tm-m .tm-plus-i .tm-pi-s { font-size: 10.5px; }
.tm-m .tm-plus-i .tm-pi-p { font-size: 12px; }
.tm-m .tm-card-hd .tm-ct { font-size: 13px; }
.tm-m .tm-card-hd .tm-cm { font-size: 11px; }
.tm-m .tm-r-t { font-size: 13.5px; }
.tm-m .tm-r-s { font-size: 11.5px; }
.tm-m .tm-tail { font-size: 11px; }

/* ---------- AI 成长建议 / 教学成果上传 ---------- */
.tm-ai-card {
  margin: 0 14px 10px;
  padding: 12px 13px;
  background: var(--tm-surf);
  border: 1px solid var(--tm-line);
  border-radius: var(--tm-r);
}
.tm-ai-hd { display: flex; align-items: center; gap: 6px; }
.tm-ai-hd .tm-ai-t { font-size: 14px; font-weight: 750; color: var(--tm-ink); }
.tm-ai-hd .tm-tag { margin-left: auto; }
.tm-ai-list { margin-top: 9px; display: flex; flex-direction: column; gap: 10px; }
.tm-ai-item { display: flex; gap: 9px; align-items: flex-start; }
.tm-ai-idx {
  width: 20px; height: 20px; flex: 0 0 20px; border-radius: 6px;
  background: var(--tm-brand-soft); color: var(--tm-brand-deep);
  display: grid; place-items: center; font-size: 11px; font-weight: 800;
}
.tm-ai-bd { flex: 1; min-width: 0; }
.tm-ai-name { font-size: 13.5px; font-weight: 700; color: var(--tm-ink); }
.tm-ai-desc { margin: 3px 0 0; font-size: 12px; line-height: 1.55; color: var(--tm-ink3); }
.tm-ai-go {
  margin-top: 6px; display: inline-flex; align-items: center; gap: 2px;
  padding: 4px 9px; border-radius: 8px; border: 1px solid var(--tm-line);
  background: var(--tm-surf2); font-family: inherit; font-size: 11.5px;
  font-weight: 650; color: var(--tm-brand-deep); cursor: pointer;
}
.tm-ai-evidence {
  margin-top: 8px; padding: 4px 0; border: 0; background: transparent;
  font-family: inherit; font-size: 11.5px; color: var(--tm-ink3);
  display: inline-flex; align-items: center; gap: 3px; cursor: pointer;
}
.tm-ai-evidence-bd {
  margin-top: 4px; padding: 8px 10px; border-radius: 8px;
  background: var(--tm-surf2); font-size: 11.5px; line-height: 1.6; color: var(--tm-ink2);
}
.tm-upload {
  margin: 0 14px 10px; padding: 11px 13px;
  display: flex; align-items: center; gap: 10px;
  background: var(--tm-surf); border: 1px solid var(--tm-line); border-radius: var(--tm-r);
}
.tm-upload-bd { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.tm-upload-bd b { font-size: 13.5px; color: var(--tm-ink); }
.tm-upload-bd span { font-size: 11.5px; line-height: 1.5; color: var(--tm-ink3); }
.tm-upload-btn {
  flex: 0 0 auto; padding: 7px 13px; border-radius: 9px; border: 0;
  background: #1f2430; color: #fff; font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}

/* 移动端：我的育人档案卡片 */
.tm-archive {
  margin: 0 14px 10px; padding: 11px 13px;
  display: flex; flex-direction: column; gap: 6px;
  background: var(--tm-surf); border: 1px solid var(--tm-line); border-radius: var(--tm-r);
}
.tm-archive-hd { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.tm-archive-hd b { font-size: 13.5px; color: var(--tm-ink); }
.tm-archive-hd em { font-style: normal; font-size: 11.5px; color: var(--tm-ink3); }
.tm-archive-sub { font-size: 11.5px; line-height: 1.5; color: var(--tm-ink3); }
.tm-archive-act { display: flex; gap: 8px; margin-top: 2px; }
.tm-archive-ghost {
  flex: 0 0 auto; padding: 7px 13px; border-radius: 9px;
  border: 1px solid var(--tm-line); background: transparent;
  color: var(--tm-ink2); font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
}

.growth-page {
  --card-pad: 18px;
}

.tui-content {
  padding: 0 16px 32px;
  max-width: 1080px;
  margin: 0 auto;
}

/* ===== Hero ===== */
.growth-hero {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #eff4ff 0%, #f8faff 60%, #ffffff 100%);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-lg);
  padding: 20px var(--card-pad);
  margin: 16px 0 14px;
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
.hero-left {
  display: flex;
  gap: 14px;
  align-items: center;
  min-width: 0;
}
.hero-name {
  font-size: 17px;
  font-weight: 650;
  color: var(--tui-text);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.hero-level {
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-brand-strong);
  background: #fff;
  border: 1px solid #c7d7fe;
  border-radius: 999px;
  padding: 2px 10px;
}
.hero-sub {
  font-size: 13px;
  color: var(--tui-text-tertiary);
  margin-top: 3px;
}
.hero-sign {
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  margin-top: 4px;
}
.hero-right {
  min-width: 240px;
  flex: 0 1 320px;
}
.hero-points {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.hero-points .num {
  font-size: 26px;
  font-weight: 700;
  color: var(--tui-brand-strong);
  font-variant-numeric: tabular-nums;
}
.hero-points .unit {
  font-size: 12px;
  color: var(--tui-text-tertiary);
}
.hero-progress {
  margin-top: 6px;
}
.hero-progress-text {
  display: block;
  font-size: 12px;
  color: var(--tui-text-tertiary);
  margin-top: 4px;
}
.hero-badges {
  font-size: 12px;
  color: var(--tui-text-tertiary);
  margin-top: 6px;
}
.dot {
  margin: 0 6px;
  color: var(--tui-text-quiet);
}

/* ===== 卡片 ===== */
.tui-card {
  background: var(--tui-surface);
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-lg);
  padding: var(--card-pad);
  margin-bottom: 14px;
  box-shadow: var(--tui-shadow-1);
}
.card-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
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

/* ===== 成长分析（桌面端） ===== */
.anal-top {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
}
.anal-score {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.2;
}
.anal-score b {
  font-size: 28px;
  font-weight: 700;
  color: var(--tui-brand-strong);
  font-variant-numeric: tabular-nums;
}
.anal-score span {
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
.anal-sum {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--tui-text-secondary);
}
.anal-rows {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 0 24px;
  margin-top: 8px;
}
.anal-row {
  display: grid;
  grid-template-columns: 76px 1fr;
  grid-template-areas: 'k v' 'n n';
  gap: 2px 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--tui-border);
}
.anal-k {
  grid-area: k;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-tertiary);
}
.anal-v {
  grid-area: v;
  text-align: right;
  font-size: 13.5px;
  font-weight: 650;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.anal-v.is-up { color: var(--tui-success); }
.anal-v.is-down { color: var(--tui-warn); }
.anal-n {
  grid-area: n;
  font-size: 12px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
}

/* ===== 雷达 ===== */
.radar-wrap {
  display: flex;
  gap: 24px;
  align-items: center;
  flex-wrap: wrap;
}
.radar-svg {
  /* PAD 加了之后 viewBox 变宽，同步把画布放大，否则九宫格会被压小、标签更挤 */
  width: 340px;
  height: 340px;
  flex: 0 0 auto;
}
.radar-ring {
  fill: none;
  stroke: var(--tui-border-strong);
  stroke-width: 1;
}
.radar-axis {
  stroke: var(--tui-border-strong);
  stroke-width: 1;
}
.radar-area {
  fill: rgba(37, 99, 235, 0.18);
  stroke: #2563eb;
  stroke-width: 2;
  stroke-linejoin: round;
}
.radar-dot {
  fill: #2563eb;
}
.radar-label {
  font-size: 10px;
  fill: var(--tui-text-tertiary);
}
.radar-side {
  flex: 1 1 200px;
  min-width: 180px;
}
.radar-stat {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}
.radar-stat-num {
  font-size: 30px;
  font-weight: 700;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.radar-stat-label {
  font-size: 12px;
  color: var(--tui-text-tertiary);
}
.radar-note {
  font-size: 13px;
  color: var(--tui-text-secondary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.radar-note b {
  color: var(--tui-text);
}
.tag {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 999px;
  flex: 0 0 auto;
}
.tag-success {
  background: var(--tui-success-soft);
  color: var(--tui-success);
}
.tag-warn {
  background: var(--tui-warn-soft);
  color: var(--tui-warn);
}
.radar-peer {
  font-size: 12px;
  color: var(--tui-text-tertiary);
  margin-top: 10px;
  line-height: 1.6;
}
.quiet {
  color: var(--tui-text-quiet);
}

/* 能力明细 */
.cap-list {
  margin-top: 20px;
  border-top: 1px solid var(--tui-border);
  padding-top: 8px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 2px 24px;
}
.cap-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 9px 0;
  border-bottom: 1px solid var(--tui-border);
}
.cap-icon {
  font-size: 16px;
  line-height: 1.4;
  flex: 0 0 auto;
}
.cap-body {
  flex: 1;
  min-width: 0;
}
.cap-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--tui-text);
  display: flex;
  align-items: center;
  gap: 6px;
}
.cap-peer {
  font-size: 10px;
  font-weight: 500;
  color: var(--tui-brand);
  background: var(--tui-brand-soft);
  border-radius: 4px;
  padding: 0 4px;
}
.cap-desc {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  margin: 2px 0 6px;
  line-height: 1.5;
}
.cap-score {
  font-size: 13px;
  font-weight: 650;
  color: var(--tui-text-secondary);
  font-variant-numeric: tabular-nums;
  flex: 0 0 auto;
  padding-top: 1px;
}

/* ===== 履职 ===== */
.duty-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}
.duty-cell {
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 12px;
}
.duty-top {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--tui-text-tertiary);
}
.duty-icon {
  font-size: 14px;
}
.duty-num {
  font-size: 22px;
  font-weight: 700;
  color: var(--tui-text);
  margin-top: 6px;
  font-variant-numeric: tabular-nums;
}
.duty-unit {
  font-size: 11px;
  font-weight: 400;
  color: var(--tui-text-quiet);
  margin-left: 3px;
}
.duty-trend {
  font-size: 11.5px;
  margin-top: 3px;
}
.duty-trend.up {
  color: var(--tui-success);
}
.duty-trend.down {
  color: var(--tui-danger);
}
.duty-trend.flat {
  color: var(--tui-text-quiet);
}

.duty-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--tui-border);
  font-size: 12.5px;
  color: var(--tui-text-secondary);
}
.duty-sub-item b {
  color: var(--tui-text);
  margin: 0 2px;
  font-variant-numeric: tabular-nums;
}
.duty-sub-item.warn b {
  color: var(--tui-warn);
}
.duty-alert {
  margin-top: 12px;
  background: var(--tui-warn-soft);
  color: var(--tui-warn);
  border-radius: var(--tui-radius-sm);
  padding: 8px 12px;
  font-size: 12.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ===== 影响力曲线 ===== */
.impact-wrap {
  width: 100%;
}
.impact-svg {
  width: 100%;
  height: 120px;
  display: block;
}
.impact-axis {
  fill: none;
  stroke: var(--tui-border-strong);
  stroke-width: 1;
}
.impact-area {
  fill: rgba(37, 99, 235, 0.1);
}
.impact-line {
  fill: none;
  stroke: #2563eb;
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.impact-dot {
  fill: #2563eb;
}
.impact-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--tui-text-quiet);
  margin-top: 4px;
}
.impact-foot {
  font-size: 12.5px;
  color: var(--tui-text-tertiary);
  margin-top: 10px;
}
.impact-foot b {
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}

/* ===== 教学规模 ===== */
.scale-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 10px;
}
.scale-cell {
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 12px 10px;
  text-align: center;
}
.scale-cell.highlight {
  background: var(--tui-brand-soft);
}
.scale-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--tui-text);
  font-variant-numeric: tabular-nums;
}
.scale-cell.highlight .scale-num {
  color: var(--tui-brand-strong);
}
.scale-label {
  display: block;
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
  margin-top: 2px;
}
.overlap-tip {
  margin-top: 12px;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--tui-text-secondary);
  background: var(--tui-brand-soft);
  border-radius: var(--tui-radius-sm);
  padding: 10px 12px;
}

/* ===== 徽章 ===== */
.badge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 12px;
}
.badge-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
  position: relative;
}
.badge-cell.locked {
  opacity: 0.45;
  filter: grayscale(1);
}
.badge-icon {
  font-size: 24px;
  line-height: 1;
}
.badge-name {
  font-size: 11.5px;
  color: var(--tui-text-secondary);
  text-align: center;
  line-height: 1.3;
}
.badge-progress {
  font-size: 10px;
  color: var(--tui-text-quiet);
}
.badge-more {
  margin-top: 12px;
  font-size: 12px;
  color: var(--tui-text-quiet);
}

/* ===== 时间线 ===== */
.timeline {
  position: relative;
  padding-left: 6px;
}
.tl-item {
  display: flex;
  gap: 12px;
  padding-bottom: 16px;
  position: relative;
}
.tl-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 30px;
  bottom: 0;
  width: 1px;
  background: var(--tui-border-strong);
}
.tl-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--tui-surface-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex: 0 0 auto;
  z-index: 1;
}
.tl-body {
  flex: 1;
  min-width: 0;
  padding-top: 3px;
}
.tl-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--tui-text);
}
.tl-desc {
  font-size: 12px;
  color: var(--tui-text-tertiary);
  margin-top: 2px;
  line-height: 1.6;
}
.tl-meta {
  font-size: 11px;
  color: var(--tui-text-quiet);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.tl-type {
  background: var(--tui-surface-muted);
  border-radius: 4px;
  padding: 0 5px;
}

.empty-tip {
  font-size: 12.5px;
  color: var(--tui-text-quiet);
  line-height: 1.8;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 12px;
}

/* ===== 移动端 ===== */
@media (max-width: 767px) {
  .tui-content {
    padding: 12px 12px 90px;
  }
  .growth-hero {
    padding: 16px;
  }
  .hero-right {
    min-width: 0;
    flex: 1 1 100%;
    border-top: 1px solid var(--tui-border-strong);
    padding-top: 12px;
  }
  .radar-svg {
    width: 300px;
    height: 300px;
    margin: 0 auto;
  }
  .cap-list {
    grid-template-columns: 1fr;
  }
  .tui-card {
    padding: 14px;
  }
}

/* ===== 我的育人档案（桌面端） ===== */
.arch-list {
  display: flex;
  flex-direction: column;
}
.arch-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 2px;
  border-bottom: 1px solid var(--tui-border);
  font-size: 13px;
}
.arch-item:last-child {
  border-bottom: none;
}
.arch-dot {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 50%;
}
.arch-title {
  flex: 1;
  min-width: 0;
  color: var(--tui-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.arch-type {
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--tui-text-tertiary);
}
.arch-date {
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.arch-vis {
  flex-shrink: 0;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--tui-text-tertiary);
  background: var(--tui-surface-sunken);
}
.arch-vis.is-public {
  color: var(--tui-success);
  background: var(--tui-success-soft);
}
.arch-act {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.arch-note {
  margin-top: 10px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
}
.arch-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}
.arch-tab {
  padding: 4px 11px;
  border: 1px solid var(--tui-border);
  border-radius: 999px;
  background: transparent;
  color: var(--tui-text-secondary);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.arch-tab em {
  margin-left: 4px;
  font-style: normal;
  color: var(--tui-text-quiet);
  font-variant-numeric: tabular-nums;
}
.arch-tab.active {
  border-color: transparent;
  background: var(--tui-brand-soft);
  color: var(--tui-brand-strong);
  font-weight: 600;
}
.arch-tab.active em {
  color: var(--tui-brand-strong);
  opacity: 0.7;
}

/* 同行公开展示区 */
.arch-public {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--tui-radius-sm);
  background: var(--tui-surface-muted);
}
.arch-public-hd {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--tui-text-secondary);
}
.arch-public-hd em {
  font-style: normal;
  font-weight: 400;
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.arch-public-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  font-size: 12.5px;
}

/* ===== 成长报告弹窗 ===== */
.rpt {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rpt-cover {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--tui-border);
  border-radius: var(--tui-radius-md, 14px);
  background: var(--tui-surface-muted);
}
.rpt-mascot {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  object-fit: contain;
}
.rpt-cover-bd {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.rpt-cover-bd h3 {
  margin: 0;
  font-size: 14.5px;
  font-weight: 700;
  color: var(--tui-text);
}
.rpt-cover-bd span {
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.rpt-print {
  flex: 0 0 auto;
}
.rpt-types {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.rpt-type {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--tui-surface-muted);
  border-radius: var(--tui-radius-sm);
  padding: 8px 10px;
}
.rpt-type-hd {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
}
.rpt-num {
  font-size: 18px;
  font-weight: 750;
  color: var(--tui-brand-strong);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.rpt-lb {
  font-size: 11px;
  color: var(--tui-text-quiet);
}
.rpt-bar {
  height: 4px;
  border-radius: 99px;
  background: rgba(17, 24, 39, 0.08);
  overflow: hidden;
}
.rpt-bar i {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 99px;
  transition: width 0.3s ease;
}
.rpt-sec {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--tui-text-quiet);
}
.rpt-sec span:first-child {
  font-weight: 700;
  color: var(--tui-text-secondary);
}
.rpt-list {
  display: flex;
  flex-direction: column;
}
.rpt-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 2px;
  border-bottom: 1px solid var(--tui-border);
  font-size: 12.5px;
}
.rpt-item:last-child {
  border-bottom: none;
}
.rpt-idx {
  width: 16px;
  text-align: center;
  color: var(--tui-text-quiet);
  font-size: 11px;
  flex-shrink: 0;
}
.rpt-dot {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  align-self: center;
  border-radius: 50%;
}
.rpt-title {
  color: var(--tui-text-secondary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rpt-meta {
  font-size: 11px;
  color: var(--tui-text-quiet);
  flex-shrink: 0;
}
.rpt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 18px 12px;
  text-align: center;
  border: 1px dashed var(--tui-border);
  border-radius: var(--tui-radius-md, 14px);
  background: var(--tui-surface-muted);
}
.rpt-empty b {
  font-size: 13.5px;
  color: var(--tui-text);
}
.rpt-empty span {
  max-width: 260px;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
}
.rpt-note {
  font-size: 11px;
  line-height: 1.6;
  color: var(--tui-text-quiet);
  text-align: center;
}
</style>
