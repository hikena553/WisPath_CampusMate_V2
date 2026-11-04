# 班级综合评估图表扩展计划

## 概述

在教师首页的班级综合评估区域添加三个新图表：
1. 政治面貌分布饼图
2. 预警趋势折线图
3. 生源地分布柱状图

## 修改范围

### 1. 后端 API 修改

**文件：`backend/app/api/teacher.py`**

在 `ClassStatsOut` 模型中添加新字段：
```python
class ClassStatsOut(BaseModel):
    total_students: int = 0
    gender_stats: dict = {}
    crisis_stats: dict = {}
    grade_stats: dict = {}
    # 新增字段
    political_stats: dict = {}      # 政治面貌分布
    hometown_stats: dict = {}       # 生源地分布
    crisis_trend: list = []         # 预警趋势数据
```

在 `class_stats` 函数中添加统计逻辑：
- 查询 `User.political_status` 字段并分组统计
- 查询 `User.hometown` 字段并分组统计（取前10个省份）
- 查询 `AIDialogSummary.created_at` 按月统计预警数量

### 2. 前端 API 修改

**文件：`frontend/src/api/teacher.ts`**

更新 `ClassStats` 接口：
```typescript
export interface ClassStats {
  total_students: number
  gender_stats: Record<string, number>
  crisis_stats: Record<string, number>
  grade_stats: Record<string, number>
  // 新增字段
  political_stats: Record<string, number>
  hometown_stats: Record<string, number>
  crisis_trend: { month: string; count: number }[]
}
```

### 3. 前端页面修改

**文件：`frontend/src/views/teacher/HomePage.vue`**

#### 3.1 模板修改

在第二层数据分析区的左侧区域（analytics-left）添加三个新图表：

```html
<!-- 原有：雷达图 + 成绩分布 -->
<!-- 新增：政治面貌 + 预警趋势 + 生源地 -->

<div class="analytics-left">
  <!-- 第一行：雷达图 + 成绩分布（已有） -->
  <div class="chart-row">
    <div class="chart-half">雷达图</div>
    <div class="chart-half">成绩分布</div>
  </div>
  
  <!-- 第二行：政治面貌 + 预警趋势（新增） -->
  <div class="chart-row">
    <div class="chart-half">政治面貌分布饼图</div>
    <div class="chart-half">预警趋势折线图</div>
  </div>
  
  <!-- 第三行：生源地分布（新增，全宽） -->
  <div class="chart-full">生源地分布柱状图</div>
</div>
```

#### 3.2 ECharts 组件导入

添加新的 ECharts 图表类型：
```typescript
import { LineChart } from 'echarts/charts'
use([...existing, LineChart])
```

#### 3.3 新增图表配置

**政治面貌饼图配置：**
```typescript
const politicalPieOptions = computed(() => {
  // 使用 ECharts 饼图，显示党员/团员/群众等分布
})
```

**预警趋势折线图配置：**
```typescript
const crisisTrendOptions = computed(() => {
  // 使用 ECharts 折线图，X轴为月份，Y轴为预警数量
})
```

**生源地柱状图配置：**
```typescript
const hometownBarOptions = computed(() => {
  // 使用 ECharts 柱状图，显示各省学生数量
})
```

### 4. 样式修改

调整 `.analytics-left` 的布局，支持多行图表展示：

```css
.analytics-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-half {
  height: 220px;
}

.chart-full {
  height: 200px;
}
```

## 实施步骤

1. 后端：修改 `ClassStatsOut` 模型和 `class_stats` 函数
2. 前端：更新 `ClassStats` 接口
3. 前端：添加 ECharts LineChart 导入
4. 前端：添加三个新图表的 computed 配置
5. 前端：修改模板结构，添加新图表区域
6. 前端：调整样式布局
7. 测试：运行 TypeScript 检查

## 预期效果

班级综合评估区域将包含：
- **第一行**：雷达图（左）+ 成绩分布柱状图（右）
- **第二行**：政治面貌饼图（左）+ 预警趋势折线图（右）
- **第三行**：生源地分布柱状图（全宽）
