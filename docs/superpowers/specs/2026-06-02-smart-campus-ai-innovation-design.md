# 智慧校园 AI 服务平台 — 创新架构设计

> 日期：2026-06-02
> 状态：已批准

## 设计目标

将项目从「CRUD + LLM 套壳」升级为「AI-Native 智能服务平台」，核心差异点：

| 之前 | 之后 |
|------|------|
| 关键词匹配危机检测 | 语义级情绪分析 + 趋势跟踪 |
| 拍脑袋评分公式 | 常模对标 + 轨迹分析 |
| 等学生来问 | AI 主动触达 |
| 统一回复 | 千人千面对话策略 |
| 对话无记忆 | 长期记忆 + 摘要压缩 |

## 架构总览

```
┌──────────────────────────────────────────────────────┐
│                     API Layer                         │
│  /api/profile/*  (学生360)   /api/proactive/* (触达)  │
├──────────────────────────────────────────────────────┤
│                 Orchestration Layer                    │
│   Agent Service (Adaptive)    Proactive Engine        │
├────────────────────┬──────────────────────────────────┤
│   Memory Layer     │       Intelligence Layer          │
│   Conversation     │   Student Profile Engine          │
│   Summarization    │   Semantic Crisis Analyzer        │
│   Insight Store    │   Intelligent Scoring             │
└────────────────────┴──────────────────────────────────┘
│                 Data Layer                              │
│  Existing models + profile_snapshots + conv_summaries  │
└────────────────────────────────────────────────────────┘
```

## 模块详细设计

### 1. 学生 360 画像引擎

**数据模型** `app/models/profile.py`:

```python
class StudentProfileSnapshot(Base):
    __tablename__ = "student_profile_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    snapshot_date: Mapped[date] = mapped_column(Date)
    academic_score: Mapped[float] = mapped_column(Float, default=0)
    psychological_risk: Mapped[float] = mapped_column(Float, default=0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0)
    growth_score: Mapped[float] = mapped_column(Float, default=0)
    overall_risk: Mapped[float] = mapped_column(Float, default=0)
    behavioral_patterns: Mapped[dict] = mapped_column(JSON, default=dict)
    key_insights: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=...)
```

**Service** `app/services/student_profile_engine.py`:

核心函数 `refresh_all_profiles(db)` 每日批处理流程：

1. **查学生列表** → 遍历需要更新的学生
2. **聚合数据**：拉取该生 grades / growth_records / ai_dialog_summaries / leave_requests / conversations / messages
3. **计算维度分**：调用 enhanced scoring.py 的 `calc_all_scores(db, student)`
4. **检测行为模式**：
   - 请假频率：`count(leaves in 90d) / 90 > threshold → "high"`
   - 危机趋势：`最近3次危机等级变化 → "improving"/"stable"/"worsening"`
   - 成绩轨迹：`最近2学期GPA变化 → "improving"/"stable"/"declining"`
   - 参与度：`对话频率变化 + 消息量变化 → "active"/"normal"/"disengaged"`
   - 沉默期：`最近对话距今天数 → 超过14天标记`
5. **批量 NL 洞察生成**：`_batch_generate_insights(db, students_data)` 一次 LLM 调用分析 5 个学生，减少 API 消耗
6. **存储快照**

**API** `app/api/profile.py`:

```
GET  /api/profile/student/{student_id}         → 最新画像完整信息
GET  /api/profile/student/{student_id}/trends  → 历史趋势数据（趋势图用）
GET  /api/profile/cohort/{student_id}          → 同龄常模百分位
POST /api/profile/refresh                      → 手动触发刷新（管理员）
```

### 2. 语义级危机分析

**文件**：修改 `app/services/crisis_service.py`

双级 pipeline 架构：

```
用户消息
  │
  ├─ 一级：关键词匹配（保留现有 detect_crisis_keywords）
  │    └─ 命中 → 快速标记
  │
  └─ 二级：LLM 语义分析（新增）
       └─ 对以下情况触发：
           - 关键词未命中但有可疑模式（如大量负面词汇但无预设关键词）
           - 关键词命中但需确认严重程度
       └─ 新增函数 analyze_semantic_risk(text: str, context: list[dict]) -> dict
```

新函数 `analyze_semantic_risk` 输出：
```json
{
  "risk_level": "severe",
  "emotion_tags": ["焦虑", "无助", "绝望"],
  "recommended_action": "immediate_intervention",
  "explanation": "学生表达了对未来的绝望感..."
}
```

趋势跟踪：新函数 `get_crisis_trend(student_id) → "improving"/"stable"/"worsening"`，基于最近 5 条危机记录分析。

### 3. 智能评分

**文件**：增强 `app/services/scoring.py`

新增三个能力：

```python
def get_cohort_percentile(db, student_id: int, college: str | None = None) -> dict:
    """常模对比：该生在同学院/同年级中的百分位"""
    # 返回: {"academic": 72, "practice": 85, "overall": 78}
    # 逻辑: 查询同学院学生的最新 score，计算百分位

def get_trajectory(db, student_id: int, weeks: int = 12) -> dict:
    """轨迹分析：各维度变化趋势"""
    # 返回: {"academic": -15, "practice": +5, "psych_risk": +22}
    # 逻辑: 对比当前 snapshot 与 weeks 前的 snapshot

def get_risk_indicators(db, student_id: int) -> list[dict]:
    """风险指标：返回所有触发风险信号的具体项"""
    # 返回: [{"dimension": "academic", "severity": "high", "detail": "GPA连续下降"},
    #        {"dimension": "engagement", "severity": "medium", "detail": "14天无交互"}]
    # 逻辑: 综合评估各维度数据
```

现有 `calc_radar_score` 保持不变，只做新增。

### 4. 主动触达引擎

**文件**：`app/services/proactive_engine.py`（新建）

```python
class ProactiveAction(BaseModel):
    trigger: str
    student_id: int
    priority: int  # 1-100
    action_type: str  # "notification" / "system_message" / "escalation"
    title: str
    content: str
    target_role: str  # "student" / "teacher" / "admin"

TRIGGERS = {
    "crisis_escalation": CrisisEscalationTrigger(),
    "prolonged_inactivity": InactivityTrigger(),
    "grade_drop": GradeDropTrigger(),
    "pattern_alert": PatternAlertTrigger(),
}
```

评估流程 `evaluate_all(db)`：
1. 遍历所有学生（或增量变更的学生）
2. 运行每个触发器
3. 合并结果 × 优先级去重
4. 批量执行（发通知、发系统消息、升级告警）

触发器接口：
```python
class BaseTrigger(ABC):
    @abstractmethod
    def evaluate(self, db, student: User, profile: StudentProfileSnapshot | None) -> ProactiveAction | None: ...
```

### 5. 自适应对话策略

**文件**：修改 `app/services/agent_service.py`

新增函数：
```python
STUDENT_STRATEGIES = {
    "at_risk": {
        "style": "gentle_care",
        "tone": "温和鼓励",
        "max_questions": 1,     # 少追问，降低压力
        "greeting_extra": "最近过得怎么样？有什么想聊聊的吗？",
    },
    "high_performer": {
        "style": "challenge_growth",
        "tone": "积极引导",
        "max_questions": 3,
        "greeting_extra": "最近有没有参加什么有意思的比赛或项目？",
    },
    "disengaged": {
        "style": "re_engage",
        "tone": "轻松友好",
        "max_questions": 1,
        "greeting_extra": "好久不见！最近有什么新鲜事吗？",
    },
    "normal": {
        "style": "standard",
        "tone": "标准",
        "max_questions": 2,
        "greeting_extra": "",
    },
}

def select_strategy(profile: StudentProfileSnapshot | None) -> str:
    """根据画像选择对话策略"""
    if not profile:
        return "normal"
    if profile.psychological_risk > 60 or profile.overall_risk > 50:
        return "at_risk"
    if profile.academic_score > 75 and profile.engagement_score > 60:
        return "high_performer"
    if profile.engagement_score < 30:
        return "disengaged"
    return "normal"
```

修改 `chat()` 函数：加载画像 → 选择策略 → 注入策略到 system prompt。

### 6. 长期记忆

**文件**：`app/services/conversation_memory.py`（新建）

**数据模型**（复用 `app/models/`，在现有 conversation 模型中扩展，或新建表）：

```python
class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(index=True)
    student_id: Mapped[int] = mapped_column(index=True)
    summary: Mapped[str] = mapped_column(Text)
    key_insights: Mapped[dict] = mapped_column(JSON, default=dict)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    message_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=...)
```

核心函数：
```python
async def summarize_conversation(db, conv_id: int):
    """对话结束时，生成摘要并存储"""
    ...

def get_relevant_memories(db, student_id: int, current_message: str) -> str:
    """检索与该生相关的历史记忆，用于注入对话上下文"""
    ...
```

生成时机：对话关闭时 / 每 20 条消息自动摘要 / 手动触发

## 文件变更清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `app/models/profile.py` | 画像快照模型 |
| `app/services/student_profile_engine.py` | 画像引擎 |
| `app/services/proactive_engine.py` | 主动触达 |
| `app/services/conversation_memory.py` | 长期记忆 |
| `app/api/profile.py` | 画像 API |
| `app/schemas/profile.py` | 画像 Schema |

### 修改文件
| 文件 | 改动 |
|------|------|
| `app/services/crisis_service.py` | 增加语义分析二级 pipeline |
| `app/services/scoring.py` | 增加常模对比 + 轨迹 + 风险指标 |
| `app/services/agent_service.py` | 自适应策略注入 |
| `app/main.py` | 注册 profile router |

## 测试策略

- 核心逻辑（维度计算、模式识别、趋势分析）可单元测试，mock 数据层
- 画像引擎集成测试：验证聚合结果正确性
- 危机分析：用预设消息验证分级准确性
- 主动触达：验证触发生成逻辑

## 部署注意事项

- profile 刷新是 CPU/API 密集型任务，建议定时任务避开高峰期
- NL 洞察生成使用批量 prompt（5人/次），控制 API 成本
- 画像快照每天一份，支持按时间戳查询，便于趋势分析
