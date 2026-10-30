// ============================================================
// 绵小城 智慧校园 AI 服务平台 · 苹果风宣传片 PPTX
// ============================================================
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

// ---- 尺寸 ----
pres.layout = "LAYOUT_16x9";
const SLIDE_W = 10;
const SLIDE_H = 5.625;
const CX = SLIDE_W / 2;
const CY = SLIDE_H / 2;

// ---- 配色 (Apple style) ----
const C = {
  bg: "000000",
  white: "FFFFFF",
  gray: "8E8E93",
  gray2: "1C1C1E",
  gray3: "2C2C2E",
  accent: "0A84FF",
  accent2: "5E5CE6",
  red: "FF453A",
  orange: "FF9F0A",
  green: "30D158",
};

// ---- 字体 ----
const F = {
  title: "Georgia",     // 英文衬线
  cjkTitle: "SimSun",   // 中文衬线
  body: "Calibri",
  cjk: "Microsoft YaHei",
};

// ============================================================
// 通用：黑色背景
// ============================================================
function bg(slide) {
  slide.background = { color: C.bg };
}

// 标题样式
function titleOpts(extra) {
  return Object.assign({
    fontFace: F.cjkTitle, color: C.white, bold: true,
    align: "center", valign: "middle", margin: 0,
  }, extra);
}
function bodyOpts(extra) {
  return Object.assign({
    fontFace: F.cjk, color: C.white, align: "left", valign: "top", margin: 0,
  }, extra);
}
function grayOpts(extra) {
  return Object.assign({
    fontFace: F.cjk, color: C.gray, align: "center", valign: "middle", margin: 0,
  }, extra);
}

// ============================================================
// Slide 1: 问候 "你好。"
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("你好。", titleOpts({ x: 0, y: 0, w: SLIDE_W, h: SLIDE_H, fontSize: 72, charSpacing: 6 }));
  s.addText("Hello.", grayOpts({ x: 0, y: CY + 1.1, w: SLIDE_W, h: 0.5, fontSize: 18, charSpacing: 4 }));
}

// ============================================================
// Slide 2: 提问
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("如果，", titleOpts({ x: 0, y: 1.2, w: SLIDE_W, h: 1, fontSize: 44, charSpacing: 3 }));
  s.addText("校园也能懂你？", titleOpts({ x: 0, y: 2.3, w: SLIDE_W, h: 1.4, fontSize: 60, charSpacing: 4, color: C.accent }));
  s.addText("What if your campus could understand you?", grayOpts({ x: 0, y: 4.0, w: SLIDE_W, h: 0.5, fontSize: 16, charSpacing: 2 }));
}

// ============================================================
// Slide 3: 产品亮相
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  // logo 圆点
  s.addShape(pres.shapes.OVAL, { x: CX - 0.45, y: 0.7, w: 0.9, h: 0.9, fill: { color: C.accent }, line: { color: C.accent } });
  s.addText("绵", titleOpts({ x: CX - 0.45, y: 0.7, w: 0.9, h: 0.9, fontSize: 36, color: C.white }));
  s.addText("绵小城", titleOpts({ x: 0, y: 1.8, w: SLIDE_W, h: 1.3, fontSize: 66, charSpacing: 8 }));
  s.addText("智慧校园 AI 服务平台", grayOpts({ x: 0, y: 3.2, w: SLIDE_W, h: 0.6, fontSize: 24, charSpacing: 3 }));
  s.addText("WisPath CampusMate", grayOpts({ x: 0, y: 3.9, w: SLIDE_W, h: 0.4, fontSize: 14, charSpacing: 2 }));
  // 分隔细线
  s.addShape(pres.shapes.RECTANGLE, { x: CX - 0.4, y: 4.6, w: 0.8, h: 0.02, fill: { color: C.gray }, line: { color: C.gray } });
  s.addText("绵阳城市学院", grayOpts({ x: 0, y: 4.75, w: SLIDE_W, h: 0.4, fontSize: 12, charSpacing: 3 }));
}

// ============================================================
// Slide 4: 目录
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("目录", titleOpts({ x: 0.5, y: 0.35, w: 9, h: 0.7, fontSize: 32, align: "left", charSpacing: 3 }));
  const items = [
    ["01", "绵小城 AI 对话助手", "流式对话 · 语音 · 长期记忆"],
    ["02", "学生成长档案", "技能标签 · 勋章 · 综合评分"],
    ["03", "学习计划 · 连续打卡", "智能拆解 · 连击激励"],
    ["04", "教师端 · 学生管理与危机预警", "360 画像 · 三级预警"],
    ["05", "办事服务 · 请假审批", "在线申请 · 一键审批"],
    ["06", "校园资讯 · 资源中心", "聚合资讯 · AI 资源"],
  ];
  const startY = 1.25, rowH = 0.68;
  items.forEach((it, i) => {
    const y = startY + i * rowH;
    s.addText(it[0], titleOpts({ x: 0.5, y, w: 0.7, h: rowH, fontSize: 22, align: "left", color: C.accent, valign: "middle" }));
    s.addText(it[1], titleOpts({ x: 1.3, y, w: 4.2, h: rowH, fontSize: 20, align: "left", valign: "middle" }));
    s.addText(it[2], grayOpts({ x: 5.6, y, w: 4.0, h: rowH, fontSize: 14, align: "left", valign: "middle" }));
  });
}

// ============================================================
// 通用：功能标题页 (section title)
// ============================================================
function sectionSlide(num, title, en) {
  const s = pres.addSlide(); bg(s);
  s.addText(num, titleOpts({ x: 0, y: 1.0, w: SLIDE_W, h: 1.0, fontSize: 72, charSpacing: 6, color: C.accent }));
  s.addText(title, titleOpts({ x: 0, y: 2.2, w: SLIDE_W, h: 1.2, fontSize: 48, charSpacing: 4 }));
  if (en) s.addText(en, grayOpts({ x: 0, y: 3.6, w: SLIDE_W, h: 0.5, fontSize: 18, charSpacing: 3 }));
  return s;
}

// ============================================================
// Slide 5: F1 标题
// ============================================================
sectionSlide("01", "绵小城 AI 对话助手", "Your AI Campus Companion");

// ============================================================
// Slide 6: F1 详情 - 对话气泡
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("绵小城 AI 对话助手", titleOpts({ x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, align: "left", charSpacing: 2 }));
  s.addText("SSE 流式对话 · 语音输入 · 文件理解 · 长期记忆", grayOpts({ x: 0.5, y: 0.95, w: 9, h: 0.4, fontSize: 14, align: "left" }));

  // 对话气泡区
  const bx = 0.6, bw = 5.4;
  // 用户消息（右对齐，灰底）
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx + bw - 3.6, y: 1.6, w: 3.6, h: 0.6, fill: { color: C.gray3 }, line: { color: C.gray3 }, rectRadius: 0.12 });
  s.addText("帮我拆解一下高数学习计划", bodyOpts({ x: bx + bw - 3.5, y: 1.68, w: 3.4, h: 0.45, fontSize: 14, color: C.white, align: "left" }));
  // AI 回复（左对齐，蓝底）
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: 2.4, w: 4.6, h: 0.6, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.12 });
  s.addText("好的，已为你生成 4 阶段学习计划…", bodyOpts({ x: bx + 0.1, y: 2.48, w: 4.4, h: 0.45, fontSize: 14, color: C.white, align: "left" }));
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: 3.15, w: 4.8, h: 0.6, fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.12, transparency: 25 });
  s.addText("第一阶段：极限与连续（2 周）", bodyOpts({ x: bx + 0.1, y: 3.23, w: 4.6, h: 0.45, fontSize: 13, color: C.white, align: "left" }));
  // 输入框
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: 4.15, w: bw, h: 0.55, fill: { color: C.gray2 }, line: { color: C.gray3 }, rectRadius: 0.12 });
  s.addText("输入消息…  🎤  📎", bodyOpts({ x: bx + 0.2, y: 4.22, w: bw - 0.4, h: 0.4, fontSize: 13, color: C.gray, align: "left" }));

  // 右侧 4 大能力
  const caps = [
    ["流式对话", "SSE 实时输出，无需等待"],
    ["语音输入", "边说边问，解放双手"],
    ["文件理解", "上传文档，智能解读"],
    ["长期记忆", "记住你的每一次对话"],
  ];
  caps.forEach((c, i) => {
    const y = 1.6 + i * 0.85;
    s.addShape(pres.shapes.OVAL, { x: 6.5, y: y + 0.1, w: 0.35, h: 0.35, fill: { color: C.accent }, line: { color: C.accent } });
    s.addText((i + 1).toString(), titleOpts({ x: 6.5, y: y + 0.1, w: 0.35, h: 0.35, fontSize: 14, color: C.white }));
    s.addText(c[0], titleOpts({ x: 7.0, y, w: 2.6, h: 0.4, fontSize: 16, align: "left", valign: "middle" }));
    s.addText(c[1], grayOpts({ x: 7.0, y: y + 0.4, w: 2.6, h: 0.35, fontSize: 11, align: "left" }));
  });
}

// ============================================================
// Slide 7: F2 标题
// ============================================================
sectionSlide("02", "学生成长档案", "Growth Portfolio");

// ============================================================
// Slide 8: F2 详情 - 技能标签 + 勋章 + 雷达
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("学生成长档案", titleOpts({ x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, align: "left", charSpacing: 2 }));
  s.addText("技能兴趣标签 · 勋章体系 · 综合评分雷达图", grayOpts({ x: 0.5, y: 0.95, w: 9, h: 0.4, fontSize: 14, align: "left" }));

  // 左：技能标签云
  s.addText("技能与兴趣", bodyOpts({ x: 0.5, y: 1.5, w: 4, h: 0.4, fontSize: 15, color: C.gray }));
  const tags = [
    { t: "Python", x: 0.5, y: 1.95, w: 1.1, c: C.accent },
    { t: "数据分析", x: 1.7, y: 1.95, w: 1.2, c: C.accent2 },
    { t: "机器学习", x: 3.0, y: 1.95, w: 1.2, c: C.accent },
    { t: "团队协作", x: 0.5, y: 2.5, w: 1.2, c: C.green },
    { t: "项目管理", x: 1.8, y: 2.5, w: 1.2, c: C.accent2 },
    { t: "UI 设计", x: 3.1, y: 2.5, w: 1.0, c: C.accent },
    { t: "英语 CET-6", x: 0.5, y: 3.05, w: 1.3, c: C.orange },
    { t: "竞赛获奖", x: 1.9, y: 3.05, w: 1.2, c: C.green },
  ];
  tags.forEach(tg => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: tg.x, y: tg.y, w: tg.w, h: 0.42, fill: { color: tg.c }, line: { color: tg.c }, rectRadius: 0.2, transparency: 35 });
    s.addText(tg.t, bodyOpts({ x: tg.x, y: tg.y, w: tg.w, h: 0.42, fontSize: 12, color: C.white, align: "center", valign: "middle" }));
  });

  // 中：勋章展示
  s.addText("成长勋章", bodyOpts({ x: 0.5, y: 3.65, w: 4, h: 0.35, fontSize: 15, color: C.gray }));
  const medals = [
    { c: "CD7F32", n: "铜" }, { c: "C0C0C0", n: "银" }, { c: "FFD700", n: "金" }, { c: "5AC8FA", n: "钻" },
  ];
  medals.forEach((m, i) => {
    const x = 0.6 + i * 0.95;
    s.addShape(pres.shapes.OVAL, { x, y: 4.1, w: 0.6, h: 0.6, fill: { color: m.c }, line: { color: m.c } });
    s.addShape(pres.shapes.OVAL, { x: x + 0.12, y: 4.22, w: 0.36, h: 0.36, fill: { color: C.bg }, line: { color: C.bg } });
    s.addText(m.n, titleOpts({ x, y: 4.1, w: 0.6, h: 0.6, fontSize: 16, color: C.white }));
  });

  // 右：雷达图（手绘多边形）
  const rcx = 7.6, rcy = 3.15, R = 1.15;
  const axes = 6;
  // 网格 - CUSTOM_GEOMETRY 使用 {x,y} 点数组
  for (let r = 1; r <= 3; r++) {
    const pts = [];
    for (let i = 0; i < axes; i++) {
      const a = (Math.PI * 2 * i) / axes - Math.PI / 2;
      pts.push({ x: rcx + (R * r / 3) * Math.cos(a), y: rcy + (R * r / 3) * Math.sin(a) });
    }
    s.addShape(pres.shapes.CUSTOM_GEOMETRY, { x: rcx - R, y: rcy - R, w: R * 2, h: R * 2, points: pts, fill: { color: C.bg, transparency: 100 }, line: { color: C.gray3, width: 0.75 } });
  }
  // 轴线
  for (let i = 0; i < axes; i++) {
    const a = (Math.PI * 2 * i) / axes - Math.PI / 2;
    s.addShape(pres.shapes.LINE, { x: rcx, y: rcy, w: R * Math.cos(a), h: R * Math.sin(a), line: { color: C.gray3, width: 0.75 } });
  }
  // 数据多边形
  const dataVals = [0.85, 0.7, 0.9, 0.6, 0.78, 0.72];
  const dpts = dataVals.map((v, i) => {
    const a = (Math.PI * 2 * i) / axes - Math.PI / 2;
    return { x: rcx + R * v * Math.cos(a), y: rcy + R * v * Math.sin(a) };
  });
  s.addShape(pres.shapes.CUSTOM_GEOMETRY, { x: rcx - R, y: rcy - R, w: R * 2, h: R * 2, points: dpts, fill: { color: C.accent, transparency: 60 }, line: { color: C.accent, width: 1.5 } });
  // 数据点
  dataVals.forEach((v, i) => {
    const a = (Math.PI * 2 * i) / axes - Math.PI / 2;
    s.addShape(pres.shapes.OVAL, { x: rcx + R * v * Math.cos(a) - 0.04, y: rcy + R * v * Math.sin(a) - 0.04, w: 0.08, h: 0.08, fill: { color: C.white }, line: { color: C.accent } });
  });
  // 轴标签
  const labels = ["学业", "技能", "实践", "竞赛", "品德", "身心"];
  labels.forEach((lb, i) => {
    const a = (Math.PI * 2 * i) / axes - Math.PI / 2;
    const lx = rcx + (R + 0.3) * Math.cos(a);
    const ly = rcy + (R + 0.3) * Math.sin(a);
    s.addText(lb, bodyOpts({ x: lx - 0.4, y: ly - 0.15, w: 0.8, h: 0.3, fontSize: 11, color: C.gray, align: "center", valign: "middle" }));
  });
  s.addText("综合评分", bodyOpts({ x: 6.4, y: 0.7, w: 2.4, h: 0.3, fontSize: 14, color: C.gray, align: "center" }));
  s.addText("86.5", titleOpts({ x: 6.4, y: 0.98, w: 2.4, h: 0.52, fontSize: 36, color: C.accent, align: "center" }));
}

// ============================================================
// Slide 9: F3 标题
// ============================================================
sectionSlide("03", "学习计划 · 连续打卡", "Study Plan & Check-in Streak");

// ============================================================
// Slide 10: F3 详情 - 时间轴 + 连击
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("学习计划 · 连续打卡", titleOpts({ x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, align: "left", charSpacing: 2 }));
  s.addText("AI 智能拆解目标 · 连续打卡激励 · 断签提醒", grayOpts({ x: 0.5, y: 0.95, w: 9, h: 0.4, fontSize: 14, align: "left" }));

  // 阶段时间轴
  const stages = [
    { t: "阶段一", d: "极限与连续", days: "第 1-2 周" },
    { t: "阶段二", d: "导数与微分", days: "第 3-4 周" },
    { t: "阶段三", d: "积分学", days: "第 5-7 周" },
    { t: "阶段四", d: "综合应用", days: "第 8-10 周" },
  ];
  const axisY = 2.0;
  const stageStartX = 1.1, stageStep = 2.6;
  s.addShape(pres.shapes.LINE, { x: stageStartX, y: axisY, w: stageStep * 3, h: 0, line: { color: C.gray3, width: 2 } });
  stages.forEach((st, i) => {
    const x = stageStartX + i * stageStep;
    s.addShape(pres.shapes.OVAL, { x: x - 0.13, y: axisY - 0.13, w: 0.26, h: 0.26, fill: { color: i === 0 ? C.accent : C.gray3 }, line: { color: i === 0 ? C.accent : C.gray3 } });
    s.addText(st.t, titleOpts({ x: x - 1.0, y: axisY - 0.6, w: 2.0, h: 0.35, fontSize: 13, color: C.accent, align: "center" }));
    s.addText(st.d, bodyOpts({ x: x - 1.1, y: axisY + 0.25, w: 2.2, h: 0.35, fontSize: 14, align: "center" }));
    s.addText(st.days, grayOpts({ x: x - 1.1, y: axisY + 0.6, w: 2.2, h: 0.3, fontSize: 11, align: "center" }));
  });

  // 连续打卡热力图（小方块）
  s.addText("连续打卡热力图", bodyOpts({ x: 0.5, y: 3.3, w: 4, h: 0.35, fontSize: 15, color: C.gray }));
  const cols = 14, rows = 5;
  const cw = 0.17, ch = 0.17, gap = 0.04, startX = 0.6, startY = 3.75;
  const streakData = [1,1,1,1,1,1,1, 1,1,0,1,1,1,1, 1,1,1,0,1,1,1,1, 1,1,1,1,1,0,1,1, 1,1,1,1,1,1,1,1, 1,1,1,0,1,1,1,1, 1,1,1,1,1,1,1,1, 1,1,0,1,1,1,1,1, 1,1,1,1,0,1,1,1, 1,1,1,1,1,1,1,0];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      const v = idx < streakData.length ? streakData[idx] : 0;
      const color = v ? (Math.random() > 0.5 ? C.accent : C.accent2) : C.gray3;
      s.addShape(pres.shapes.RECTANGLE, { x: startX + c * (cw + gap), y: startY + r * (ch + gap), w: cw, h: ch, fill: { color }, line: { color } });
    }
  }
  // 连击数
  s.addText("连续打卡", bodyOpts({ x: 6.0, y: 3.3, w: 1.6, h: 0.35, fontSize: 15, color: C.gray, align: "center" }));
  s.addText("28", titleOpts({ x: 6.0, y: 3.65, w: 1.6, h: 0.85, fontSize: 64, color: C.accent, align: "center" }));
  s.addText("天", grayOpts({ x: 6.0, y: 4.65, w: 1.6, h: 0.35, fontSize: 16, align: "center" }));
  // 勋章
  s.addShape(pres.shapes.OVAL, { x: 8.0, y: 3.8, w: 0.7, h: 0.7, fill: { color: "FFD700" }, line: { color: "FFD700" } });
  s.addText("🏅", titleOpts({ x: 8.0, y: 3.8, w: 0.7, h: 0.7, fontSize: 28, align: "center" }));
  s.addText("月度恒心", bodyOpts({ x: 7.6, y: 4.6, w: 1.5, h: 0.35, fontSize: 12, color: C.gray, align: "center" }));
}

// ============================================================
// Slide 11: F4 标题
// ============================================================
sectionSlide("04", "教师端 · 学生管理与危机预警", "Teacher Workbench & Crisis Alert");

// ============================================================
// Slide 12: F4 详情 - 三级预警 + 学生列表
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("教师端 · 学生管理与危机预警", titleOpts({ x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, align: "left", charSpacing: 2 }));
  s.addText("学生 360 画像 · 语义级心理危机分析 · 三级分级推送", grayOpts({ x: 0.5, y: 0.95, w: 9, h: 0.4, fontSize: 14, align: "left" }));

  // 三级预警色卡
  const levels = [
    { lv: "严重", c: C.red, desc: "立即介入", n: "2" },
    { lv: "中度", c: C.orange, desc: "重点关注", n: "5" },
    { lv: "轻微", c: C.green, desc: "持续跟踪", n: "8" },
  ];
  levels.forEach((lv, i) => {
    const x = 0.6 + i * 1.55;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 1.4, h: 1.3, fill: { color: lv.c, transparency: 20 }, line: { color: lv.c }, rectRadius: 0.1 });
    s.addText(lv.n, titleOpts({ x, y: 1.6, w: 1.4, h: 0.6, fontSize: 36, color: C.white, align: "center" }));
    s.addText(lv.lv, titleOpts({ x, y: 2.15, w: 1.4, h: 0.35, fontSize: 16, color: C.white, align: "center" }));
    s.addText(lv.desc, grayOpts({ x, y: 2.5, w: 1.4, h: 0.3, fontSize: 11, color: C.white, align: "center" }));
  });

  // 学生预警列表
  const students = [
    { name: "张同学", lv: "严重", c: C.red, msg: "近期对话频繁出现消极词汇" },
    { name: "李同学", lv: "中度", c: C.orange, msg: "成绩下滑 + 请假频率升高" },
    { name: "王同学", lv: "轻微", c: C.green, msg: "连续 14 天未发起对话" },
  ];
  students.forEach((st, i) => {
    const y = 3.05 + i * 0.72;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.6, y, w: 4.0, h: 0.6, fill: { color: C.gray2 }, line: { color: C.gray3 }, rectRadius: 0.08 });
    // 左侧色条
    s.addShape(pres.shapes.RECTANGLE, { x: 5.6, y, w: 0.08, h: 0.6, fill: { color: st.c }, line: { color: st.c } });
    s.addText(st.name, bodyOpts({ x: 5.8, y: y + 0.05, w: 1.2, h: 0.25, fontSize: 14, color: C.white }));
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.0, y: y + 0.08, w: 0.7, h: 0.25, fill: { color: st.c, transparency: 30 }, line: { color: st.c }, rectRadius: 0.12 });
    s.addText(st.lv, bodyOpts({ x: 7.0, y: y + 0.08, w: 0.7, h: 0.25, fontSize: 10, color: C.white, align: "center", valign: "middle" }));
    s.addText(st.msg, grayOpts({ x: 5.8, y: y + 0.32, w: 3.7, h: 0.25, fontSize: 11, color: C.gray }));
  });

  // 底部说明
  s.addText("AI 主动触达 · 基于对话语义实时分析", grayOpts({ x: 0.6, y: 5.0, w: 9, h: 0.35, fontSize: 13, align: "left" }));
}

// ============================================================
// Slide 13: F5 标题
// ============================================================
sectionSlide("05", "办事服务 · 请假审批", "Services & Leave Approval");

// ============================================================
// Slide 14: F5 详情 - 审批流程
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("办事服务 · 请假审批", titleOpts({ x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, align: "left", charSpacing: 2 }));
  s.addText("在线申请 · 一键审批 · 全流程留痕", grayOpts({ x: 0.5, y: 0.95, w: 9, h: 0.4, fontSize: 14, align: "left" }));

  // 流程节点
  const nodes = [
    { t: "学生提交", d: "填写申请", icon: "📝" },
    { t: "教师审批", d: "在线处理", icon: "✓" },
    { t: "自动归档", d: "留痕可查", icon: "📁" },
  ];
  const nodeW = 2.1, nodeH = 1.4, startX = 0.7, gapX = 1.0;
  nodes.forEach((n, i) => {
    const x = startX + i * (nodeW + gapX);
    const y = 1.8;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: nodeW, h: nodeH, fill: { color: C.gray2 }, line: { color: i === 1 ? C.accent : C.gray3, width: i === 1 ? 2 : 1 }, rectRadius: 0.15 });
    s.addText(n.icon, titleOpts({ x, y: y + 0.15, w: nodeW, h: 0.6, fontSize: 32, align: "center" }));
    s.addText(n.t, titleOpts({ x, y: y + 0.75, w: nodeW, h: 0.35, fontSize: 16, align: "center" }));
    s.addText(n.d, grayOpts({ x, y: y + 1.08, w: nodeW, h: 0.28, fontSize: 12, align: "center" }));
    // 箭头
    if (i < nodes.length - 1) {
      const ax = x + nodeW;
      s.addText("→", titleOpts({ x: ax, y: y + 0.4, w: gapX, h: nodeH, fontSize: 28, color: C.accent, align: "center", valign: "middle" }));
    }
  });

  // 办事服务网格
  s.addText("办事服务矩阵", bodyOpts({ x: 0.6, y: 3.6, w: 9, h: 0.35, fontSize: 15, color: C.gray }));
  const services = ["请假申请", "证明申请", "项目申请", "失物招领"];
  services.forEach((sv, i) => {
    const x = 0.6 + i * 2.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.05, w: 2.0, h: 0.7, fill: { color: C.gray3 }, line: { color: C.gray3 }, rectRadius: 0.1 });
    s.addText(sv, bodyOpts({ x, y: 4.05, w: 2.0, h: 0.7, fontSize: 15, color: C.white, align: "center", valign: "middle" }));
  });
}

// ============================================================
// Slide 15: F6 标题
// ============================================================
sectionSlide("06", "校园资讯 · 资源中心", "Campus News & AI Resource Hub");

// ============================================================
// Slide 16: F6 详情 - 资讯流
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("校园资讯 · 资源中心", titleOpts({ x: 0.5, y: 0.3, w: 9, h: 0.7, fontSize: 30, align: "left", charSpacing: 2 }));
  s.addText("聚合全网 AI 资讯 · 智能体榜 · 开源项目 · 权威排行", grayOpts({ x: 0.5, y: 0.95, w: 9, h: 0.4, fontSize: 14, align: "left" }));

  // Tabs
  const tabs = ["AI 论文", "开源项目", "智能体榜", "时政要闻", "国产模型"];
  tabs.forEach((t, i) => {
    const x = 0.6 + i * 1.2;
    const active = i === 0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 1.1, h: 0.4, fill: { color: active ? C.accent : C.gray3 }, line: { color: active ? C.accent : C.gray3 }, rectRadius: 0.2 });
    s.addText(t, bodyOpts({ x, y: 1.5, w: 1.1, h: 0.4, fontSize: 12, color: active ? C.white : C.gray, align: "center", valign: "middle" }));
  });

  // 资讯卡片
  const news = [
    { t: "DeepSeek 发布新一代推理模型", src: "DeepSeek 官网", hot: true },
    { t: "LMArena 最新 Chatbot 排行榜更新", src: "LMArena", hot: false },
    { t: "开源项目周榜：Agent 框架领跑", src: "GitHub Trending", hot: true },
    { t: "教育部发布 AI 教育指导意见", src: "新华网", hot: false },
  ];
  news.forEach((n, i) => {
    const y = 2.1 + i * 0.78;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 5.4, h: 0.65, fill: { color: C.gray2 }, line: { color: C.gray3 }, rectRadius: 0.1 });
    s.addText(n.t, bodyOpts({ x: 0.8, y: y + 0.08, w: 4.0, h: 0.28, fontSize: 14, color: C.white }));
    s.addText(n.src, grayOpts({ x: 0.8, y: y + 0.36, w: 2.0, h: 0.25, fontSize: 11, color: C.gray }));
    if (n.hot) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.4, y: y + 0.18, w: 0.5, h: 0.28, fill: { color: C.red, transparency: 30 }, line: { color: C.red }, rectRadius: 0.14 });
      s.addText("热", bodyOpts({ x: 5.4, y: y + 0.18, w: 0.5, h: 0.28, fontSize: 11, color: C.white, align: "center", valign: "middle" }));
    }
  });

  // 右侧：资源入口
  s.addText("AI 资源空间", bodyOpts({ x: 6.4, y: 1.5, w: 3.2, h: 0.4, fontSize: 16, color: C.accent }));
  const res = ["学术论文库", "开源代码仓", "模型排行榜", "学习路径图"];
  res.forEach((r, i) => {
    const y = 2.0 + i * 0.72;
    s.addShape(pres.shapes.OVAL, { x: 6.4, y: y + 0.12, w: 0.3, h: 0.3, fill: { color: C.gray3 }, line: { color: C.gray3 } });
    s.addText("▸", bodyOpts({ x: 6.4, y: y + 0.12, w: 0.3, h: 0.3, fontSize: 14, color: C.accent, align: "center", valign: "middle" }));
    s.addText(r, bodyOpts({ x: 6.85, y, w: 2.5, h: 0.55, fontSize: 14, color: C.white, valign: "middle" }));
  });
}

// ============================================================
// Slide 17: 总结
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addText("一个平台", titleOpts({ x: 0, y: 0.8, w: SLIDE_W, h: 1.0, fontSize: 48, charSpacing: 4 }));
  s.addText("连接全部校园生活", titleOpts({ x: 0, y: 1.9, w: SLIDE_W, h: 1.0, fontSize: 48, charSpacing: 4, color: C.accent }));

  const feats = ["AI 对话", "成长档案", "学习计划", "教师管理", "办事服务", "资讯资源"];
  feats.forEach((f, i) => {
    const x = 0.7 + (i % 3) * 3.0;
    const y = 3.2 + Math.floor(i / 3) * 0.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.6, h: 0.6, fill: { color: C.gray2 }, line: { color: C.gray3 }, rectRadius: 0.1 });
    s.addText(f, bodyOpts({ x, y, w: 2.6, h: 0.6, fontSize: 16, color: C.white, align: "center", valign: "middle" }));
  });
}

// ============================================================
// Slide 18: 结尾
// ============================================================
{
  const s = pres.addSlide(); bg(s);
  s.addShape(pres.shapes.OVAL, { x: CX - 0.4, y: 1.1, w: 0.8, h: 0.8, fill: { color: C.accent }, line: { color: C.accent } });
  s.addText("绵", titleOpts({ x: CX - 0.4, y: 1.1, w: 0.8, h: 0.8, fontSize: 32, color: C.white }));
  s.addText("绵小城", titleOpts({ x: 0, y: 2.1, w: SLIDE_W, h: 1.0, fontSize: 56, charSpacing: 8 }));
  s.addText("让校园更懂你", titleOpts({ x: 0, y: 3.2, w: SLIDE_W, h: 0.8, fontSize: 32, color: C.accent, charSpacing: 4 }));
  s.addText("WisPath CampusMate", grayOpts({ x: 0, y: 4.1, w: SLIDE_W, h: 0.4, fontSize: 14, charSpacing: 3 }));
  s.addText("Thanks", grayOpts({ x: 0, y: 4.6, w: SLIDE_W, h: 0.4, fontSize: 16, charSpacing: 6 }));
}

// ============================================================
// 输出
// ============================================================
const outPath = "d:/StudyNote/Mian02/绵小城_智慧校园宣传片.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("PPTX generated:", outPath);
}).catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
