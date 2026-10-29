/* =========================================================================
   学生端移动驾驶舱重构原型 · app.js
   ---------------------------------------------------------------------
   结构：
     1. 工具函数
     2. 图标 / 组件片段
     3. 主页渲染（4 张卡 + 功能网格）
     4. 子页：课程表 / AI 发现 / 待办 / 成长详情 / 成绩分析
     5. 图层栈（layer）与底部弹窗（sheet）
     6. 下拉刷新
     7. 全局交互绑定
   ========================================================================= */

/* ============================ 1. 工具 ============================ */
/* 选择器（避免使用 $ —— 某些预览环境会注入同名的控制台工具，导致作用域被遮蔽） */
const qs = (sel, root = document) => root.querySelector(sel);
const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const pad2 = (n) => String(n).padStart(2, '0');

/* 当前时间（原型固定为周三 10:32，便于稳定演示「进行中」状态） */
const NOW = { day: 3, period: 2, clock: '10:32' };

/* 课表分类色条：只作用于 .tt-course::before 的 2px 竖条，永不整块填充。
   旧数据里的 color 名（brand/violet/cyan…）在此收敛为 5 个低饱和色条色 */
const COURSE_BAR = {
  brand: 'var(--bar-1)', success: 'var(--bar-1)',
  violet: 'var(--bar-2)', cyan: 'var(--bar-2)',
  warn: 'var(--bar-3)', danger: 'var(--bar-3)',
};
const barOf = (k) => COURSE_BAR[k] || 'var(--bar-5)';

const todayCourses = () =>
  DB.courses.filter((c) => c.day === NOW.day).sort((a, b) => a.start - b.start);

function greeting() {
  const h = 10;
  return h < 6 ? '夜深了' : h < 11 ? '早上好' : h < 14 ? '中午好' : h < 18 ? '下午好' : '晚上好';
}

/* 找到「下一节课」：优先进行中，其次尚未开始的下一节 */
function findNext(courses) {
  const cur = courses.find((c) => NOW.period >= c.start && NOW.period < c.start + c.len);
  if (cur) return { course: cur, live: true };
  const next = courses.find((c) => c.start > NOW.period);
  if (next) return { course: next, live: false };
  return null;
}

/* ============================ 2. 图标 / 片段 ============================ */
function icon(name, size = 18, extra = '') {
  return `<svg class="ic ${extra}" width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-${name}"/></svg>`;
}

function segmented(items, activeKey, idAttr = 'data-seg') {
  return `<div class="segmented" role="tablist">${items.map((it) => `
    <button class="seg ${it.key === activeKey ? 'active' : ''}" role="tab"
      aria-selected="${it.key === activeKey}" ${idAttr}="${it.key}">
      ${esc(it.label)}${it.count != null ? `<span class="cnt">${it.count}</span>` : ''}
    </button>`).join('')}</div>`;
}

function emptyState(text, iconName = 'check-check') {
  return `<div class="empty">
    <div class="empty-ic">${icon(iconName, 21)}</div>
    <p class="empty-txt">${esc(text)}</p>
  </div>`;
}

/* ============================ 3. 主页渲染 ============================ */
const Home = {
  /* ---------- 主页：今天一句话 + 4 个数字 ---------- */
  /* 抽成独立方法，勾选待办后只刷这一块，不必整页重渲 */
  renderToday() {
    const list = todayCourses();
    const todos = DB.today.filter((t) => !t.done);
    const next = findNext(list);

    /* 一句话：今天真正要关心的事。
       分行按语义切（课 / 待办），不靠容器宽度自动折行，
       否则 320px 下会出现「截止」孤行 */
    const urgentCount = todos.filter((t) => t.urgent).length;
    const line = qs('#todayLine');
    if (line) {
      if (!list.length && !todos.length) {
        line.innerHTML = '今天没有课，也没有待办';
      } else if (!list.length) {
        line.innerHTML = `今天没课，<br>${todos.length} 项待办等你`;
      } else if (urgentCount) {
        line.innerHTML = `今天有 <em>${list.length} 节课</em>，<br>${urgentCount} 项作业今晚截止`;
      } else if (todos.length) {
        line.innerHTML = `今天有 <em>${list.length} 节课</em>，<br>${todos.length} 项待办等你`;
      } else {
        line.innerHTML = `今天有 <em>${list.length} 节课</em>`;
      }
    }

    /* 下一节 */
    const sub = qs('#todaySub');
    if (sub) {
      if (next) {
        const time = PERIOD_TIMES[next.course.start];
        sub.innerHTML = `${next.live ? '正在进行' : '下一节'} ${time} ${esc(next.course.name)} · ${esc(next.course.location)}`;
      } else {
        sub.textContent = '今天的课已经全部上完';
      }
    }

  },

  /* ---------- 四个数字（原 KPI 四项的等价物） ---------- */
  renderMetrics() {
    const g = DB.growth;
    const todos = DB.today.filter((t) => !t.done);
    const setM = (id, val, unit) => {
      const el = qs(id);
      if (el) el.innerHTML = `${val}<small>${unit}</small>`;
    };
    setM('#mScore', g.totalScore, '分');
    setM('#mRank', g.semesterRank.split(' / ')[0], '/' + g.semesterRank.split(' / ')[1]);
    setM('#mTodo', todos.length, '项');
    setM('#mRecord', g.recordCount, '条');
  },

  renderShell() {
    this.renderToday();
    this.renderMetrics();
    this.renderSchedule();
    this.renderTasks();
    this.renderGrowth();
    this.renderFnGrid();
  },

  /* ---------- 今天：下一节摘要 + 竖向时间条 ---------- */
  renderSchedule() {
    const list = todayCourses();
    const next = findNext(list);
    const meta = qs('#schedMeta');
    if (meta) meta.textContent = `${list.length} 节课`;

    if (!list.length) {
      qs('#schedCard').innerHTML = `<div class="empty-line">
        <p class="t1">今天没有课程</p>
        <p class="t2">可以去图书馆，或补一补落下的章节</p>
      </div>`;
      return;
    }

    let summary = '';
    if (next) {
      const c = next.course;
      const end = PERIOD_ENDS[c.start + c.len - 1];
      summary = `<button class="next-row" data-open="schedule">
        <span class="next-row-body">
          <span class="next-row-kicker">${next.live ? '正在进行' : '下一节'} · 第 ${c.start}–${c.start + c.len - 1} 节</span>
          <span class="next-row-name">${esc(c.name)}</span>
        </span>
        <span class="next-row-right">
          <span class="next-row-time">${PERIOD_TIMES[c.start]}–${end}</span>
          <span class="next-row-place">${esc(c.location)}</span>
        </span>
      </button>`;
    }

    const items = list.map((c, i) => {
      const isCur = NOW.period >= c.start && NOW.period < c.start + c.len;
      const isPast = NOW.period >= c.start + c.len;
      const cls = isCur ? 'is-current' : isPast ? 'is-past' : '';
      return `<li class="rail-item ${cls}">
        <div class="rail-time">
          <b>${PERIOD_TIMES[c.start]}</b>
          <span>${PERIOD_ENDS[c.start + c.len - 1]}</span>
        </div>
        <div class="rail-line"><span class="rail-dot" aria-hidden="true"></span></div>
        <div class="rail-body">
          <div class="rail-name">${esc(c.name)}${isCur ? '<span class="tag-now">进行中</span>' : ''}</div>
          <div class="rail-meta">${esc(c.teacher)} · ${esc(c.location)}</div>
        </div>
      </li>`;
    }).join('');

    qs('#schedCard').innerHTML = summary + `<div class="rail-wrap"><ul class="rail">${items}</ul></div>`;
  },

  /* ---------- 要交的：最多 3 条 ---------- */
  renderTasks() {
    const todos = DB.today.filter((t) => !t.done);
    const doneCount = DB.today.length - todos.length;
    const total = DB.today.length;
    const meta = qs('#taskMeta');
    if (meta) meta.textContent = `${todos.length} 项`;

    const rows = DB.today.slice(0, 3).map((t) => taskRowHTML(t)).join('');
    const pct = total ? Math.round((doneCount / total) * 100) : 0;

    qs('#taskCard').innerHTML = `<ul>${rows}</ul>
      ${todos.length === 0 ? `<div class="empty-line"><p class="t1">今天的待办都清空了</p></div>` : ''}
      <div class="todo-foot">
        <div class="todo-progress"><i style="width:${pct}%"></i></div>
        <span class="todo-foot-txt num">${doneCount}/${total} 已完成</span>
      </div>`;
  },

  /* ---------- 成长：灰条 + AI 引用 ---------- */
  renderGrowth() {
    const g = DB.growth;
    const meta = qs('#growthMeta');
    if (meta) meta.textContent = `${g.recordCount} 条记录`;

    /* 找出最低的一项，只有它着警示色 */
    const lowest = g.dims.reduce((a, b) => (a.score <= b.score ? a : b));
    const prev = g.monthlyTrend[g.monthlyTrend.length - 2].value;
    const delta = (g.totalScore - prev).toFixed(1);

    const dims = g.dims.map((d) => `
      <div class="dim-row ${d.key === lowest.key && d.score < 75 ? 'is-low' : ''}">
        <span class="dim-name">${esc(d.name)}</span>
        <span class="dim-track" role="progressbar" aria-label="${esc(d.name)}"
              aria-valuenow="${d.score}" aria-valuemin="0" aria-valuemax="100">
          <i data-w="${d.score}" style="width:0"></i>
        </span>
        <span class="dim-val">${d.score}</span>
      </div>`).join('');

    qs('#growthCard').innerHTML = `
      <div class="dims">${dims}</div>
      <button class="ai-quote" data-open="ai">
        <span class="ai-quote-mark" aria-hidden="true"></span>
        <span class="ai-quote-body">
          <span class="ai-quote-kicker">
            ${icon('sparkles', 12)}AI 洞察 · 本月 +${delta}
          </span>
          <span class="ai-quote-txt">${esc(DB.aiInsight)}</span>
        </span>
        ${icon('chevron-right', 15, 'chev')}
      </button>`;

    requestAnimationFrame(() => {
      qsa('#growthCard .dim-track > i').forEach((el, i) => {
        setTimeout(() => { el.style.width = el.dataset.w + '%'; }, 100 + i * 55);
      });
    });
  },

  /* ---------- 更多：两列单色入口 ---------- */
  renderFnGrid() {
    qs('#fnGrid').innerHTML = DB.shortcuts.map((s) => `
      <button class="fn-cell" data-nav="${s.route}">
        ${icon(s.icon, 16)}
        <span>${esc(s.name)}</span>
      </button>`).join('');
  },

  /* 勾选后：待办列表 + 今天一句话 + 指标三处联动 */
  refreshTasks() { this.renderTasks(); this.renderToday(); this.renderMetrics(); },
};

/* 单条待办行（主页与待办页共用） */
function taskRowHTML(t, opts = {}) {
  const overdue = opts.overdue || (/^10-2[0-6]/.test(t.due) && !t.done);
  const isAlert = !t.done && (overdue || t.urgent);
  const dueTxt = t.done ? '已完成' : overdue ? '已逾期' : t.due;
  return `<li class="todo-row ${t.done ? 'is-done' : ''}" data-task="${t.id}">
    <button class="check" role="checkbox" aria-checked="${t.done}" aria-label="标记「${esc(t.title)}」为${t.done ? '未完成' : '已完成'}" data-check="${t.id}">
      ${icon('check', 12)}
    </button>
    <div class="todo-body">
      <div class="todo-title">${esc(t.title)}</div>
      <div class="todo-meta">
        ${t.course ? `<span class="cname">${esc(t.course)}</span><span class="sep" aria-hidden="true">·</span>` : ''}
        <span class="due ${isAlert ? 'is-alert' : ''}">${esc(dueTxt)}</span>
      </div>
    </div>
  </li>`;
}

/* 数字滚动 */
function animateNumber(el, from, to, dur = 600, decimals = 0) {
  if (!el) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { el.textContent = to.toFixed(decimals); return; }
  const t0 = performance.now();
  const tick = (now) => {
    const p = Math.min(1, (now - t0) / dur);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = (from + (to - from) * e).toFixed(decimals);
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* ============================ 4. 子页 ============================ */

const Pages = {
  /* ---------- A. 课程表 ---------- */
  schedule() {
    const days = [1, 2, 3, 4, 5, 6, 7];
    const maxPeriod = 12;
    const DAY_SHORT = ['', '一', '二', '三', '四', '五', '六', '日'];

    const head = `<div class="tt-head">
      <div></div>
      ${days.map((d) => `<div class="tt-head-cell ${d === NOW.day ? 'is-today' : ''}">
        <b>${DAY_SHORT[d]}</b>${d === NOW.day ? '今天' : '&nbsp;'}
      </div>`).join('')}
    </div>`;

    const body = [];
    for (let p = 1; p <= maxPeriod; p++) {
      body.push(`<div class="tt-period"><b>${p}</b>${PERIOD_TIMES[p]}</div>`);
      days.forEach((d) => {
        const c = DB.courses.find((x) => x.day === d && x.start === p);
        const covered = DB.courses.some((x) => x.day === d && p > x.start && p < x.start + x.len);
        if (c) {
          body.push(`<div class="tt-course ${d === NOW.day ? 'is-today-course' : ''}"
              style="grid-row: span ${c.len}; --bar: ${barOf(c.color)}"
              title="${esc(c.name)} · ${esc(c.teacher)} · ${esc(c.location)}">
            <b>${esc(c.name)}</b>
            <span>${esc(c.location)}</span>
          </div>`);
        } else if (!covered) {
          body.push(`<div class="tt-cell is-empty"></div>`);
        }
      });
    }

    /* 图例按「课程类型」去重，色条色取该类型第一门课 */
    const typeMap = new Map();
    DB.courses.forEach((c) => { if (!typeMap.has(c.type)) typeMap.set(c.type, c.color); });
    const legend = [...typeMap.entries()].map(([type, col]) =>
      `<span><i style="background:${barOf(col)}"></i>${esc(type)}</span>`).join('');

    return `<section class="layer-scroll" data-scroll>
      <div class="tt-wrap" style="padding-top:8px">
        ${head}
        <div class="tt-body">${body.join('')}</div>
      </div>
      <div class="tt-legend">${legend}</div>
      <div style="height:8px"></div>
    </section>`;
  },

  /* ---------- B. AI 主动发现 ---------- */
  ai() {
    const groups = [
      { key: 'high', label: '需要今天处理' },
      { key: 'medium', label: '值得留意' },
      { key: 'low', label: '可以安排' },
    ];
    const blocks = groups.map((g) => {
      const list = DB.aiActions.filter((a) => a.level === g.key);
      if (!list.length) return '';
      return `<div class="block">
        <div class="block-head"><h2 class="block-title">${g.label}</h2>
        <span class="block-meta num">${list.length} 条</span></div>
        <div class="card">${list.map(actionHTML).join('')}</div>
      </div>`;
    }).join('');

    return `<section class="layer-scroll" data-scroll>
      <div style="padding:12px var(--pad-x) 0">
        <div class="card insight-block">
          <p class="insight-lead">这周你的压力主要来自两门专业核心课的作业叠加。</p>
          <p class="insight-body" id="aiText">${esc(DB.aiInsight)}</p>
          <div class="insight-foot">
            <span class="insight-foot-txt" id="aiTime">${esc(DB.aiUpdatedAt)}</span>
            <button class="insight-refresh" id="btnAiRefresh">
              ${icon('refresh-cw', 14)}<span>重新生成</span>
            </button>
          </div>
        </div>
      </div>
      <div style="padding:0 var(--pad-x)">${blocks}</div>
      <div style="height:12px"></div>
    </section>`;
  },

  /* ---------- C. 待办全部 ---------- */
  tasks(seg = 'today') {
    const src = seg === 'week' ? DB.week : seg === 'overdue' ? DB.overdue : DB.today;
    const doneCount = src.filter((t) => t.done).length;
    const total = src.length;
    const pct = total ? Math.round((doneCount / total) * 100) : 0;
    const R = 16, C = 2 * Math.PI * R;

    const rows = src.length
      ? `<ul>${src.map((t) => taskRowHTML(t, { overdue: seg === 'overdue' })).join('')}</ul>`
      : emptyState(seg === 'overdue' ? '没有逾期任务，保持住' : '这个分组暂时是空的', 'coffee');

    return `<section class="layer-scroll" data-scroll>
      <div style="padding:12px var(--pad-x) 0">
        <div class="card">
          <div class="stat-strip">
            <div class="stat-cell">
              <div class="stat-num num">${doneCount}<small>/ ${total}</small></div>
              <div class="stat-label">已完成</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num num">${total - doneCount}<small>项</small></div>
              <div class="stat-label">待处理</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num num">${pct}<small>%</small></div>
              <div class="stat-label">完成度</div>
            </div>
          </div>
        </div>
        <div style="margin-top:12px" id="taskSeg">${segmented([
          { key: 'today', label: '今天', count: DB.today.filter(t=>!t.done).length },
          { key: 'week', label: '本周', count: DB.week.filter(t=>!t.done).length },
          { key: 'overdue', label: '逾期', count: DB.overdue.length },
        ], seg)}</div>
        <div class="card" style="margin-top:10px">${rows}</div>
        ${total === 0 ? '' : `<p style="margin-top:14px;text-align:center;font-size:11.5px;color:var(--text-quiet);line-height:16px">勾选环形按钮即可标记完成</p>`}
      </div>
      <div style="height:12px"></div>
    </section>`;
  },

  /* ---------- D. 成长详情 ---------- */
  growth() {
    const g = DB.growth;
    const lowest = g.dims.reduce((a, b) => (a.score <= b.score ? a : b));
    const trendMax = Math.max(...g.monthlyTrend.map((m) => m.value));
    const trendMin = Math.min(...g.monthlyTrend.map((m) => m.value)) - 4;

    const chart = `<div class="trend-chart" role="img"
        aria-label="月度成长趋势：${g.monthlyTrend.map(m => m.month + ' ' + m.value).join('，')}">
      ${g.monthlyTrend.map((m, i) => {
        const h = 62 * (m.value - trendMin) / (trendMax - trendMin) + 12;
        return `<div class="trend-col ${i === g.monthlyTrend.length - 1 ? 'is-last' : ''}">
          <span class="trend-val">${m.value}</span>
          <span class="trend-bar" style="height:${h.toFixed(0)}px"></span>
          <span class="trend-x">${m.month}</span>
        </div>`;
      }).join('')}
    </div>`;

    const dims = g.dims.map((d) => `
      <div class="dim-detail ${d.score < 75 ? 'is-low' : ''}">
        <div class="dim-detail-head">
          <span class="dim-detail-name">${esc(d.name)}</span>
          <span class="dim-detail-score">${d.score}</span>
        </div>
        <div class="dim-detail-track" role="progressbar" aria-label="${esc(d.name)}"
             aria-valuenow="${d.score}" aria-valuemin="0" aria-valuemax="100">
          <i data-w="${d.score}" style="width:0"></i>
        </div>
        <p class="dim-detail-src">${esc(d.source)}</p>
        <p class="dim-detail-tip">${esc(d.tip)}</p>
      </div>`).join('');

    return `<section class="layer-scroll" data-scroll>
      <div style="padding:12px var(--pad-x) 0">
        <div class="card">
          <div class="stat-strip">
            <div class="stat-cell"><div class="stat-num num">${g.totalScore}</div><div class="stat-label">成长指数</div></div>
            <div class="stat-cell"><div class="stat-num num">${g.comprehensiveScore}</div><div class="stat-label">综合评分</div></div>
            <div class="stat-cell"><div class="stat-num num">${g.recordCount}</div><div class="stat-label">成长记录</div></div>
            <div class="stat-cell"><div class="stat-num num">${g.skillCount}</div><div class="stat-label">技能标签</div></div>
          </div>
        </div>
        <div class="card" style="margin-top:12px">
          <div class="radar-wrap">
            <canvas id="radar" width="200" height="176" aria-hidden="true"></canvas>
            <div class="radar-legend">
              ${g.dims.map((d) => {
                const low = d.score === lowest.score;
                return `<div class="radar-legend-row${low ? ' is-low' : ''}">
                  <span class="rl-name">${esc(d.name)}</span><b>${d.score}</b>
                </div>`;
              }).join('')}
            </div>
          </div>
        </div>
        <div style="margin-top:16px" class="sec-head"><span class="sec-title">成长趋势</span><span class="sec-meta">近 6 个月</span></div>
        <div class="card">${chart}</div>
        <div style="margin-top:16px" class="sec-head"><span class="sec-title">维度解读</span></div>
        <div class="card">${dims}</div>
      </div>
      <div style="height:12px"></div>
    </section>`;
  },

  /* ---------- E. 成绩分析 ---------- */
  grades(termKey) {
    const G = DB.grades;
    const terms = G.terms;
    const active = terms.find((t) => t.key === termKey) || terms[terms.length - 1];

    const rows = active.courses.map((c) => {
      return `<div class="course-row">
        <div class="course-name"><b>${esc(c.name)}</b><span>${esc(c.type)} · ${c.credit} 学分</span></div>
        <div class="course-score ${c.score < 60 ? 'is-low' : ''}">${c.score}</div>
      </div>`;
    }).join('');

    return `<section class="layer-scroll" data-scroll>
      <div style="padding:12px var(--pad-x) 0">
        <div class="card grade-hero">
          <div class="gpa-block">
            <div class="gpa-label">平均学分绩点</div>
            <div class="gpa-val num">${active.gpa.toFixed(2)}</div>
            <div class="gpa-sub">专业排名 <b>${active.rank} / ${G.total}</b> · 累计 <b>${G.credits}</b> 学分</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:11.5px;color:var(--text-3);line-height:15px">较上学期</div>
            <div style="font-size:17px;font-weight:700;color:var(--ok);line-height:22px;letter-spacing:-0.3px">
              +0.14
            </div>
          </div>
        </div>
        <div style="margin-top:12px">
          ${segmented(terms.map((t) => ({ key: t.key, label: t.label })), active.key, 'data-term')}
        </div>
        <div class="card" style="margin-top:10px">${rows}</div>
      </div>
      <div style="height:12px"></div>
    </section>`;
  },
};

function actionHTML(a) {
  const levelText = { high: '高优先级', medium: '关注', low: '建议' }[a.level];
  return `<div class="action-row ${a.level === 'high' ? 'is-high' : ''}">
    <span class="action-flag" aria-hidden="true"></span>
    <div class="action-body">
      <div class="action-title">${esc(a.title)}</div>
      <div class="action-desc">${esc(a.desc)}</div>
    </div>
    <button class="action-cta" data-action="${a.id}">${esc(a.action)}</button>
  </div>`;
}

/* ============================ 5. 图层栈 ============================ */
const Layers = {
  stack: [],
  host: null,

  init() { this.host = qs('#layers'); },

  titles: {
    schedule: ['课程表', '第 9 教学周 · 11 门课'],
    ai:       ['AI 主动发现', '根据课表与记录实时生成'],
    tasks:    ['待办', '勾选即完成'],
    growth:   ['成长详情', '五维成长 · 近 6 个月'],
    grades:   ['成绩分析', '软件工程 · 2202 班'],
  },

  open(key, params = {}) {
    const render = Pages[key];
    if (!render) { toast('该入口在真实产品中跳转路由：' + key); return; }

    const row = document.createElement('div');
    row.className = 'layer anim-in';
    const [title, sub] = this.titles[key] || [key, ''];
    const body = render(params.seg || params.term);

    row.innerHTML = `
      <header class="appbar is-white">
        <button class="appbar-back" data-layer-back aria-label="返回">
          ${icon('arrow-left', 22)}
        </button>
        <div class="appbar-title">${esc(title)}${sub ? `<small>${esc(sub)}</small>` : ''}</div>
        <div class="appbar-actions">
          <button class="icon-btn" data-layer-close aria-label="关闭">
            ${icon('x', 20)}
          </button>
        </div>
      </header>
      ${body}`;

    row.dataset.key = key;
    this.host.appendChild(row);
    this.stack.push(row);

    /* 交互：分段控件（待办 / 学期）重新渲染当前层 */
    row.addEventListener('click', (e) => {
      const segTask = e.target.closest('[data-seg]');
      if (segTask) {
        const scrollTop = qs('.layer-scroll', row)?.scrollTop || 0;
        const next = render(segTask.dataset.seg);
        qs('.layer-scroll', row).outerHTML = next;
        qs('.layer-scroll', row).scrollTop = scrollTop;
        return;
      }
      const segTerm = e.target.closest('[data-term]');
      if (segTerm) {
        const next = render(segTerm.dataset.term);
        qs('.layer-scroll', row).outerHTML = next;
        return;
      }
      if (e.target.closest('[data-layer-back]')) { this.close(); return; }
      if (e.target.closest('[data-layer-close]')) { this.close(true); return; }
      if (e.target.closest('#btnAiRefresh')) { this.refreshAi(row); return; }
      if (e.target.closest('[data-action]')) {
        toast('已跳转到对应处理页');
        return;
      }
      const chk = e.target.closest('[data-check]');
      if (chk) {
        toggleTask(chk.dataset.check);
        Home.refreshTasks();
        /* 原地更新该行视觉，不重排列表 */
        const li = chk.closest('.todo-row');
        const id = chk.dataset.check;
        const t = [...DB.today, ...DB.week, ...DB.overdue].find((x) => x.id === id);
        if (t && li) {
          li.classList.toggle('is-done', t.done);
          chk.setAttribute('aria-checked', t.done);
        }
        return;
      }
    });

    /* 挂载后动画 */
    requestAnimationFrame(() => {
      qsa('.dim-detail-track > i', row).forEach((el, i) =>
        setTimeout(() => { el.style.width = el.dataset.w + '%'; }, 100 + i * 55));
      if (key === 'growth') drawRadar(qs('#radar', row));
    });
  },

  refreshAi(row) {
    const btn = qs('#btnAiRefresh', row);
    const txt = qs('#aiText', row);
    btn.classList.add('is-loading');
    txt.style.opacity = '0.45';
    setTimeout(() => {
      btn.classList.remove('is-loading');
      txt.style.opacity = '1';
      qs('#aiTime', row).textContent = '刚刚更新';
      toast('洞察已刷新');
    }, 900);
  },

  close(instant = false) {
    const row = this.stack.pop();
    if (!row) return;
    if (instant) { row.remove(); return; }
    row.classList.remove('anim-in');
    row.classList.add('anim-out');
    /* 离场只加 pointer-events:none，不改布局属性 */
    setTimeout(() => row.remove(), 230);
  },

  closeTop() {
    if (this.stack.length) this.close();
  },
};

/* 雷达图 */
function drawRadar(canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2 + 4, R = Math.min(W, H) / 2 - 26;
  const dims = DB.growth.dims;
  const n = dims.length;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const angle = (i) => (Math.PI * 2 * i) / n - Math.PI / 2;

  const draw = (progress) => {
    ctx.clearRect(0, 0, W, H);
    /* 网格环 */
    for (let r = 1; r <= 4; r++) {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const a = angle(i);
        const rr = (R * r) / 4;
        const x = cx + Math.cos(a) * rr, y = cy + Math.sin(a) * rr;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = r === 4 ? '#e2e5e9' : '#eef0f3';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    /* 轴线 */
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R);
      ctx.strokeStyle = '#eef0f3';
      ctx.stroke();
    }
    /* 数据面 */
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      const v = (dims[i].score / 100) * progress;
      const x = cx + Math.cos(a) * R * v, y = cy + Math.sin(a) * R * v;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(20, 23, 26, 0.055)';
    ctx.fill();
    ctx.strokeStyle = '#14171a';
    ctx.lineWidth = 1.8;
    ctx.stroke();
    /* 顶点 */
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      const v = (dims[i].score / 100) * progress;
      ctx.beginPath();
      ctx.arc(cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v, 2.6, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.strokeStyle = '#14171a';
      ctx.lineWidth = 1.8;
      ctx.stroke();
    }
    /* 轴标签 */
    ctx.font = '500 10px "PingFang SC", system-ui, sans-serif';
    ctx.fillStyle = '#6b7280';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      const x = cx + Math.cos(a) * (R + 22);
      const y = cy + Math.sin(a) * (R + 14);
      ctx.fillText(dims[i].name.slice(0, 2), x, y);
    }
  };

  if (reduce) { draw(1); return; }
  const t0 = performance.now();
  const run = (now) => {
    const p = Math.min(1, (now - t0) / 620);
    draw(1 - Math.pow(1 - p, 3));
    if (p < 1) requestAnimationFrame(run);
  };
  requestAnimationFrame(run);
}

/* ============================ 6. 底部弹窗 ============================ */
const Sheet = {
  el: null,
  mask: null,

  init() {
    this.mask = qs('#sheetMask');
    this.host = qs('#sheetHost');
    this.mask.addEventListener('click', () => this.close());
  },

  open({ title, items = [], foot = '', onPick }) {
    const wrap = document.createElement('div');
    wrap.className = 'sheet';
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-modal', 'true');
    wrap.setAttribute('aria-label', title);
    wrap.innerHTML = `
      <div class="sheet-grab" aria-hidden="true"></div>
      <div class="sheet-head">
        <span class="sheet-title">${esc(title)}</span>
        <button class="icon-btn" data-sheet-close aria-label="关闭">${icon('x', 20)}</button>
      </div>
      <div class="sheet-body">
        ${items.map((it, i) => `
          <button class="sheet-item ${it.danger ? 'is-danger' : ''}" data-idx="${i}">
            ${icon(it.icon, 18)}<span>${esc(it.label)}</span>
            ${it.note ? `<span class="sheet-item-note">${esc(it.note)}</span>` : ''}
          </button>`).join('')}
      </div>
      ${foot ? `<div class="sheet-foot">${foot}</div>` : ''}`;

    this.host.appendChild(wrap);
    this.el = wrap;
    this.mask.hidden = false;
    requestAnimationFrame(() => {
      wrap.classList.add('show');
      this.mask.classList.add('show');
    });

    wrap.addEventListener('click', (e) => {
      if (e.target.closest('[data-sheet-close]')) { this.close(); return; }
      const it = e.target.closest('[data-idx]');
      if (it) {
        const idx = +it.dataset.idx;
        this.close();
        onPick?.(idx, items[idx]);
      }
    });

    /* 焦点移入弹窗（容器，不落在按钮上，避免出现无谓的聚焦环） */
    wrap.tabIndex = -1;
    setTimeout(() => wrap.focus({ preventScroll: true }), 60);
  },

  close() {
    if (!this.el) return;
    const el = this.el;
    el.classList.remove('show');
    this.mask.classList.remove('show');
    setTimeout(() => {
      el.remove();
      this.mask.hidden = true;
    }, 280);
    this.el = null;
  },
};

/* 轻提示 */
function toast(msg) {
  const host = qs('#toastHost');
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = `position:absolute;left:50%;bottom:96px;transform:translateX(-50%) translateY(8px);
    background:rgba(15,17,21,.88);color:#fff;font-size:13px;line-height:18px;padding:9px 14px;
    border-radius:10px;white-space:nowrap;z-index:90;opacity:0;transition:opacity .2s,transform .2s;pointer-events:none;`;
  host.appendChild(t);
  requestAnimationFrame(() => {
    t.style.opacity = '1';
    t.style.transform = 'translateX(-50%) translateY(0)';
  });
  setTimeout(() => {
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 220);
  }, 1600);
}

/* ============================ 7. 下拉刷新 ============================ */
const PullToRefresh = {
  THRESHOLD: 64,

  init() {
    const screen = qs('#scr-home');
    const body = qs('#homeBody');
    const ptr = qs('#ptrHome');
    let startY = 0, dist = 0, tracking = false, busy = false;

    screen.addEventListener('touchstart', (e) => {
      if (busy || screen.scrollTop > 0 || Layers.stack.length) return;
      startY = e.touches[0].clientY;
      tracking = true;
      body.classList.add('no-anim');
    }, { passive: true });

    screen.addEventListener('touchmove', (e) => {
      if (!tracking) return;
      dist = Math.max(0, e.touches[0].clientY - startY);
      if (dist > 0) {
        const d = Math.pow(dist, 0.85) * 1.6;
        body.style.transform = `translateY(${Math.min(d, 90)}px)`;
        ptr.classList.add('show');
      }
    }, { passive: true });

    screen.addEventListener('touchend', () => {
      if (!tracking) return;
      tracking = false;
      body.classList.remove('no-anim');
      if (dist > this.THRESHOLD) {
        busy = true;
        body.style.transform = 'translateY(56px)';
        ptr.classList.add('loading');
        ptr.querySelector('span').textContent = '刷新中…';
        setTimeout(() => {
          body.style.transform = '';
          ptr.classList.remove('show', 'loading');
          ptr.querySelector('span').textContent = '下拉刷新';
          busy = false;
          Home.renderTasks();
          toast('已是最新');
        }, 820);
      } else {
        body.style.transform = '';
        ptr.classList.remove('show');
      }
      dist = 0;
    });
  },
};

/* ============================ 8. 全局交互 ============================ */
function toggleTask(id) {
  const t = [...DB.today, ...DB.week, ...DB.overdue].find((x) => x.id === id);
  if (t) t.done = !t.done;
}

function bindGlobal() {
  /* 页面内所有「data-open」入口 */
  document.addEventListener('click', (e) => {
    const opener = e.target.closest('[data-open]');
    if (opener) { Layers.open(opener.dataset.open); return; }

    const nav = e.target.closest('[data-nav]');
    if (nav) {
      const r = nav.dataset.nav;
      if (r.startsWith('route:')) toast('跳转 ' + r.slice(6));
      else Layers.open(r);
      return;
    }

    /* 主页勾选 */
    const chk = e.target.closest('#taskCard [data-check]');
    if (chk) {
      toggleTask(chk.dataset.check);
      Home.refreshTasks();
      return;
    }

    if (e.target.closest('#btnOpenSchedule')) { Layers.open('schedule'); return; }
    if (e.target.closest('#btnOpenTasks'))    { Layers.open('tasks'); return; }
    if (e.target.closest('#btnOpenGrowth'))   { Layers.open('growth'); return; }
    if (e.target.closest('#btnBell'))         { toast('有 3 条未读通知'); return; }

    if (e.target.closest('#btnMore')) {
      Sheet.open({
        title: '驾驶舱设置',
        items: [
          { icon: 'sliders-horizontal', label: '调整区块顺序', note: '共 4 个区块' },
          { icon: 'eye', label: '显示/隐藏区块', note: '' },
          { icon: 'refresh-cw', label: '刷新全部数据', note: '' },
          { icon: 'circle-question-mark', label: '关于成长指数', note: '' },
        ],
        onPick: (i) => {
          if (i === 2) { Home.renderShell(); toast('已刷新'); }
          else toast('原型演示：' + ['调整区块顺序', '显示隐藏区块', '', '关于成长指数'][i]);
        },
      });
      return;
    }

    /* 底部导航（本原型只演示驾驶舱，其余页签提示） */
    const tab = e.target.closest('.tab');
    if (tab && tab.dataset.tab !== 'home') {
      toast(`本原型聚焦驾驶舱，${tab.querySelector('span:last-child').textContent} 页签未重做`);
    }
  });

  /* Esc 逐层关闭 */
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (Sheet.el) { Sheet.close(); return; }
    Layers.closeTop();
  });
}

/* ============================ 启动 ============================ */
document.addEventListener('DOMContentLoaded', () => {
  Layers.init();
  Sheet.init();
  Home.renderShell();
  bindGlobal();
  PullToRefresh.init();

  /* 首屏可访问性：把主标题焦点不给，保持自然 Tab 顺序 */
});
