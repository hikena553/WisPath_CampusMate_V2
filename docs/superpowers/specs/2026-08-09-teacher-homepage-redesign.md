# 教师首页布局重新设计

## 概述

重新设计教师端首页的内容区域布局，采用三层递进式结构，遵循Dashboard设计最佳实践，提升信息层级清晰度和用户体验。

## 设计原则

1. **5秒法则** - 用户在5秒内能获取最关键信息
2. **Z型视觉路径** - 从左上到右上的自然阅读顺序
3. **渐进式信息披露** - 总览→趋势→详情
4. **60-30-10颜色规则** - 主色60%，辅色30%，强调色10%

---

## 新布局结构

```
┌─────────────────────────────────────────────────────────────┐
│                    欢迎横幅（精简版）                          │
│  问候语 + 待办提示 + 高危预警标签                              │
└─────────────────────────────────────────────────────────────┘

┌──────────┬──────────┬──────────┬──────────┐
│ 学生总数  │ 危机预警  │ 待批请假  │ 平均绩点  │
│  [图标]   │  [图标]   │  [图标]   │  [图标]   │
│   128     │    5     │    3     │   3.45   │
└──────────┴──────────┴──────────┴──────────┘

┌─────────────────────────┬─────────────────┐
│    班级综合评估雷达图      │   性别比例饼图    │
│                         │                 │
│         ◇◇◇◇            │     ◐◑◑◑      │
│        ◇◇◇◇◇           │                 │
│         ◇◇◇◇            │   男: 65%       │
│                         │   女: 35%       │
├─────────────────────────┼─────────────────┤
│    成绩分布柱状图          │  心理危机饼图     │
│    ▂▃▅▇▁               │                 │
│    优秀 良好 中等 及格 不及格 │   高危: 2       │
│                         │   中危: 3       │
└─────────────────────────┴─────────────────┘

┌─────────────────────────┬─────────────────┐
│      日程日历             │    班级公告       │
│   日 一 二 三 四 五 六    │                 │
│  ┌─┬─┬─┬─┬─┬─┬─┐      │  · 公告标题1     │
│  │ │ │ │●│ │ │ │      │    2026-08-09   │
│  ├─┼─┼─┼─┼─┼─┼─┤      │  · 公告标题2     │
│  │ │ │ │ │ │ │ │      │    2026-08-08   │
│  └─┴─┴─┴─┴─┴─┴─┘      │                 │
│                         │  ─────────────  │
│  📌 未来3日提醒           │    校园公告       │
│  · 08-10 班会            │  · 教务通知1     │
│  · 08-12 考试            │  · 教务通知2     │
└─────────────────────────┴─────────────────┘
```

---

## 详细设计说明

### 第一层：概览区（Overview Zone）

#### 1.1 精简版欢迎横幅
- **高度**: 从当前 ~120px 缩减至 ~80px
- **内容**: 只保留问候语 + 待办数量 + 高危预警标签
- **移除**: 右侧空白区域、渐变背景改为纯色背景

```html
<div class="welcome-banner">
  <div class="welcome-content">
    <h2>{{ greeting }}, {{ userName }}</h2>
    <span class="pending-badge" v-if="pendingCount > 0">
      {{ pendingCount }} 件待办
    </span>
  </div>
  <div class="welcome-tags">
    <el-tag v-if="severeCount > 0" type="danger" size="small">
      {{ severeCount }} 条高危预警
    </el-tag>
  </div>
</div>
```

#### 1.2 KPI统计卡片
- **数量**: 4个（与当前一致）
- **样式**: 增大卡片高度，使用更醒目的数字
- **新增**: 每个卡片下方显示趋势箭头（↑/↓）
- **颜色编码**: 
  - 学生总数: 蓝色 #5b8def
  - 危机预警: 红色 #f56c6c
  - 待批请假: 橙色 #e6a23c
  - 平均绩点: 绿色 #67c23a

```html
<div class="kpi-cards">
  <div class="kpi-card" v-for="card in kpiCards" :key="card.label">
    <div class="kpi-icon" :style="{ background: card.bgColor }">
      <el-icon :size="24"><component :is="card.icon" /></el-icon>
    </div>
    <div class="kpi-info">
      <div class="kpi-value">{{ card.value }}</div>
      <div class="kpi-label">{{ card.label }}</div>
    </div>
    <div class="kpi-trend" :class="card.trendClass">
      {{ card.trend }}
    </div>
  </div>
</div>
```

**CSS样式:**
```css
.kpi-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.kpi-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: all 0.3s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
}

.kpi-label {
  font-size: 13px;
  color: #888;
  margin-top: 2px;
}

.kpi-trend {
  margin-left: auto;
  font-size: 14px;
  font-weight: 600;
}

.kpi-trend.up { color: #67c23a; }
.kpi-trend.down { color: #f56c6c; }
```

---

### 第二层：数据分析区（Analytics Zone）

#### 2.1 左侧大区域（2/3宽度）
- **上半部分**: 班级综合评估雷达图（高度: 280px）
- **下半部分**: 成绩分布柱状图（高度: 200px）
- 两个图表之间用细分割线分隔

```html
<div class="analytics-left">
  <div class="chart-section">
    <div class="section-title">
      <el-icon><DataAnalysis /></el-icon>
      班级综合评估
    </div>
    <div class="chart-container radar-chart">
      <VChart :option="radarOptions" autoresize />
    </div>
  </div>
  <div class="chart-divider"></div>
  <div class="chart-section">
    <div class="section-title">
      <el-icon><Histogram /></el-icon>
      成绩分布
    </div>
    <div class="chart-container bar-chart">
      <VChart :option="barOptions" autoresize />
    </div>
  </div>
</div>
```

#### 2.2 右侧小区域（1/3宽度）
- **上半部分**: 性别比例饼图（环形图，高度: 200px）
- **下半部分**: 心理危机分布饼图（环形图，高度: 200px）
- 两个饼图垂直排列，各占一半空间

```html
<div class="analytics-right">
  <div class="chart-section half">
    <div class="section-title">
      <el-icon><User /></el-icon>
      性别比例
    </div>
    <div class="chart-container pie-chart">
      <VChart :option="genderPieOptions" autoresize />
    </div>
  </div>
  <div class="chart-section half">
    <div class="section-title">
      <el-icon><Warning /></el-icon>
      心理危机分布
    </div>
    <div class="chart-container pie-chart">
      <VChart :option="crisisPieOptions" autoresize />
    </div>
  </div>
</div>
```

**CSS样式:**
```css
.analytics-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.analytics-left, .analytics-right {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.chart-section {
  margin-bottom: 16px;
}

.chart-section.half {
  margin-bottom: 0;
}

.chart-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 16px 0;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chart-container.radar-chart {
  height: 280px;
}

.chart-container.bar-chart {
  height: 200px;
}

.chart-container.pie-chart {
  height: 180px;
}
```

---

### 第三层：日程与公告区（Schedule & Announcements Zone）

#### 3.1 左侧日程日历
- **日历**: 保持现有样式，但压缩高度
- **提醒**: 移到日历下方，减少显示数量（最多3条）

```html
<div class="schedule-section">
  <div class="section-title">
    <el-icon><Calendar /></el-icon>
    日程安排
  </div>
  <div class="calendar-wrapper">
    <div class="cal-header">
      <el-button text @click="prevMonth">&lt;</el-button>
      <span>{{ calYear }}年{{ calMonth }}月</span>
      <el-button text @click="nextMonth">&gt;</el-button>
    </div>
    <table class="cal-table">
      <!-- 日历内容 -->
    </table>
  </div>
  <div class="upcoming-reminders">
    <div class="reminder-title">📌 近期提醒</div>
    <div v-for="r in upcomingReminders.slice(0, 3)" :key="r.id" class="reminder-item">
      <span class="reminder-date">{{ r.date.slice(5) }}</span>
      <span class="reminder-content">{{ r.content }}</span>
    </div>
  </div>
</div>
```

#### 3.2 右侧公告区
- **班级公告**: 显示教师发布的公告（最多5条）
- **校园公告**: 显示学校教务公告（最多5条）
- 两个区域用Tab切换或直接堆叠显示

```html
<div class="announcements-section">
  <el-tabs v-model="activeAnnouncementTab">
    <el-tab-pane label="班级公告" name="class">
      <div class="announcement-list">
        <div v-for="a in myAnnouncements.slice(0, 5)" :key="a.id" class="announcement-item">
          <el-tag :type="urgencyTagType(a.urgency)" size="small">
            {{ urgencyLabel(a.urgency) }}
          </el-tag>
          <div class="announcement-content">
            <div class="announcement-title">{{ a.title }}</div>
            <div class="announcement-date">{{ formatDate(a.created_at) }}</div>
          </div>
        </div>
        <el-button text type="primary" size="small" @click="goToAnnouncements">
          查看全部 <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </el-tab-pane>
    <el-tab-pane label="校园公告" name="campus">
      <div class="announcement-list">
        <a v-for="(item, index) in campusAnnouncements.slice(0, 5)" :key="index"
          :href="item.url || '#'" target="_blank" class="campus-item">
          <span class="campus-title">{{ item.title }}</span>
          <span class="campus-date">{{ item.date }}</span>
        </a>
      </div>
    </el-tab-pane>
  </el-tabs>
</div>
```

**CSS样式:**
```css
.schedule-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.schedule-section, .announcements-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.cal-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
}

.cal-table {
  width: 100%;
  border-collapse: collapse;
}

.cal-table th {
  font-size: 12px;
  color: #999;
  padding: 8px 0;
  text-align: center;
}

.cal-table td {
  text-align: center;
  padding: 6px 0;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
}

.cal-table td:hover {
  background: rgba(91,141,239,0.08);
}

.cal-today .cal-day {
  background: #5b8def;
  color: #fff;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  line-height: 28px;
}

.upcoming-reminders {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.reminder-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 8px;
}

.reminder-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-size: 13px;
}

.reminder-date {
  color: #5b8def;
  font-weight: 600;
  min-width: 45px;
}

.reminder-content {
  color: #666;
}

/* 公告列表样式 */
.announcement-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}

.announcement-item:last-child {
  border-bottom: none;
}

.announcement-title {
  font-size: 14px;
  color: #333;
}

.announcement-date {
  font-size: 12px;
  color: #999;
}

.campus-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
  text-decoration: none;
  color: #333;
  transition: background 0.2s;
}

.campus-item:hover {
  background: #f8f9ff;
}

.campus-title {
  font-size: 14px;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.campus-date {
  font-size: 12px;
  color: #999;
  margin-left: 12px;
}
```

---

## 响应式适配

```css
/* 平板端 */
@media (max-width: 1024px) {
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .analytics-row {
    grid-template-columns: 1fr;
  }
  
  .schedule-row {
    grid-template-columns: 1fr;
  }
}

/* 移动端 */
@media (max-width: 768px) {
  .kpi-cards {
    grid-template-columns: 1fr;
  }
  
  .welcome-banner {
    flex-direction: column;
    align-items: flex-start;
  }
}
```

---

## 动画优化

移除过度的入场动画，只保留必要的过渡效果：

1. **卡片hover**: `transform: translateY(-2px)` + 阴影加深
2. **图表加载**: 使用ECharts内置动画
3. **列表项**: 移除交错动画，改为简单的淡入

---

## 实施步骤

1. 创建新的 `HomePage.vue` 组件结构
2. 实现第一层：KPI卡片区域
3. 实现第二层：图表区域（雷达图 + 柱状图 + 饼图）
4. 实现第三层：日历 + 公告区域
5. 添加响应式样式
6. 优化动画效果
7. 测试和调优
