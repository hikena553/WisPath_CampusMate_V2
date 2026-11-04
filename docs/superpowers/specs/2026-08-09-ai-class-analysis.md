# AI 班级分析功能计划

## 概述

在教师首页的右侧区域（性别比例和心理危机分布饼图下方空白处）添加 AI 班级分析功能，利用现有智能体对班级数据进行辅导员指导分析。

## 功能设计

### 1. 触发方式

- 用户点击"AI 分析"按钮触发
- 按钮位于右侧区域底部
- 分析完成后显示结果

### 2. 分析内容

AI 将根据当前班级数据生成以下分析：

1. **班级整体概况** - 学生总数、性别比例、政治面貌分布
2. **心理健康分析** - 预警等级分布、高危学生数量、建议干预措施
3. **学生成绩分析** - 成绩分布、平均分、需要关注的学生
4. **辅导员建议** - 基于数据的具体工作建议和下一步行动

### 3. 实现方案

#### 3.1 使用现有 `useAiAnalysis` composable

```typescript
import { useAiAnalysis } from '@/composables/useAiAnalysis'

const { loading, renderedResult, analyze } = useAiAnalysis('teacher-class-analysis')

async function runClassAnalysis() {
  const prompt = buildAnalysisPrompt()
  await analyze(prompt, { skipCache: true })
}

function buildAnalysisPrompt() {
  return `作为辅导员老师，请分析以下班级数据并给出指导建议：

班级数据：
- 学生总数：${classStats.value.total_students}
- 性别比例：${JSON.stringify(classStats.value.gender_stats)}
- 政治面貌：${JSON.stringify(classStats.value.political_stats)}
- 心理危机分布：${JSON.stringify(classStats.value.crisis_stats)}
- 成绩分布：${JSON.stringify(classStats.value.grade_stats)}
- 生源地分布：${JSON.stringify(classStats.value.hometown_stats)}

请从以下方面进行分析：
1. 班级整体概况
2. 心理健康状况分析
3. 学业成绩分析
4. 辅导员工作建议

请用简洁专业的语言，控制在500字以内。`
}
```

#### 3.2 模板结构

```html
<div class="ai-analysis-section">
  <div class="section-title">
    <el-icon><Magic /></el-icon>
    <span>AI 班级分析</span>
  </div>
  
  <div v-if="!analysisResult && !analysisLoading" class="analysis-placeholder">
    <p>点击下方按钮，AI 将为您分析班级数据</p>
    <el-button type="primary" @click="runClassAnalysis" :loading="analysisLoading">
      开始分析
    </el-button>
  </div>
  
  <div v-else-if="analysisLoading" class="analysis-loading">
    <el-icon class="loading-icon"><Loading /></el-icon>
    <p>AI 正在分析班级数据...</p>
  </div>
  
  <div v-else class="analysis-content">
    <div class="analysis-text">{{ analysisResult }}</div>
    <el-button text type="primary" size="small" @click="runClassAnalysis">
      重新分析
    </el-button>
  </div>
</div>
```

### 4. 样式设计

```css
.ai-analysis-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.analysis-placeholder {
  text-align: center;
  padding: 20px;
  color: #888;
}

.analysis-loading {
  text-align: center;
  padding: 20px;
}

.loading-icon {
  font-size: 24px;
  color: #5b8def;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.analysis-content {
  font-size: 13px;
  line-height: 1.6;
  color: #555;
}

.analysis-text {
  white-space: pre-wrap;
  margin-bottom: 12px;
}
```

## 实施步骤

1. 在 HomePage.vue 中导入 `useAiAnalysis` composable
2. 添加分析触发函数和响应式变量
3. 在模板右侧区域添加 AI 分析 UI
4. 添加样式
5. 测试功能

## 预期效果

右侧区域布局将变为：
```
┌─────────────────────┐
│   性别比例饼图       │
├─────────────────────┤
│   心理危机饼图       │
├─────────────────────┤
│   AI 班级分析       │
│   [开始分析] 按钮    │
│                     │
│   分析结果文本...    │
└─────────────────────┘
```
