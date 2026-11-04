# 智慧校园 AI 创新实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 实现学生360画像引擎、语义危机分析、智能评分、主动触达、自适应对话、长期记忆六大模块

**Architecture:** 分层架构：Data Layer (models) → Intelligence Layer (services) → API Layer (routes)。所有新增模块与现有系统松耦合，通过依赖注入集成。

**Tech Stack:** Python/FastAPI + SQLAlchemy + OpenAI SDK

---

## 文件清单

### 新增文件
| 文件 | 职责 |
|------|------|
| `app/models/profile.py` | 画像快照 + 对话摘要数据模型 |
| `app/schemas/profile.py` | 画像 API Schema |
| `app/services/student_profile_engine.py` | 画像聚合与洞察生成 |
| `app/services/proactive_engine.py` | 主动触达触发器引擎 |
| `app/services/conversation_memory.py` | 对话摘要与长期记忆 |
| `app/api/profile.py` | 画像 API 路由 |

### 修改文件
| 文件 | 改动 |
|------|------|
| `app/services/scoring.py` | 新增常模对比、轨迹分析、风险指标 |
| `app/services/crisis_service.py` | 新增二级语义分析 pipeline |
| `app/services/agent_service.py` | 新增自适应策略注入 |
| `app/main.py` | 注册 profile router |

---

### Task 1: 数据模型

**Files:**
- Create: `app/models/profile.py`

- [ ] **Step 1: 创建画像数据模型**

```python
from datetime import datetime, date, timezone
from sqlalchemy import String, Text, Integer, Float, Date, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class StudentProfileSnapshot(Base):
    __tablename__ = "student_profile_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    academic_score: Mapped[float] = mapped_column(Float, default=0.0)
    psychological_risk: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    growth_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_risk: Mapped[float] = mapped_column(Float, default=0.0)
    behavioral_patterns: Mapped[dict | None] = mapped_column(JSON, default=dict)
    key_insights: Mapped[list | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(index=True)
    student_id: Mapped[int] = mapped_column(index=True)
    summary: Mapped[str] = mapped_column(Text)
    key_insights: Mapped[dict | None] = mapped_column(JSON, default=dict)
    topics: Mapped[list | None] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    message_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: 创建 Schema 文件**

```python
from datetime import date, datetime
from pydantic import BaseModel


class BehavioralPatterns(BaseModel):
    leave_frequency: str = "normal"
    crisis_trend: str = "stable"
    grade_trajectory: str = "stable"
    engagement_level: str = "normal"
    inactive_days: int = 0


class KeyInsight(BaseModel):
    dimension: str
    type: str
    content: str


class ProfileSnapshotOut(BaseModel):
    id: int
    student_id: int
    snapshot_date: date
    academic_score: float
    psychological_risk: float
    engagement_score: float
    growth_score: float
    overall_risk: float
    behavioral_patterns: dict | None = None
    key_insights: list | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ProfileTrendPoint(BaseModel):
    date: str
    academic_score: float
    psychological_risk: float
    engagement_score: float
    growth_score: float
    overall_risk: float


class CohortComparison(BaseModel):
    dimension: str
    student_score: float
    cohort_avg: float
    percentile: float


class ProfileTrendsOut(BaseModel):
    trends: list[ProfileTrendPoint]


class CohortComparisonOut(BaseModel):
    comparisons: list[CohortComparison]
```

- [ ] **Step 3: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.models.profile import StudentProfileSnapshot, ConversationSummary; from app.schemas.profile import ProfileSnapshotOut; print('Models OK')"
```

---

### Task 2: 增强评分系统

**Files:**
- Modify: `app/services/scoring.py` (append new functions)

- [ ] **Step 1: 添加常模对比、轨迹分析、风险指标函数**

在文件末尾追加（不要删除原有代码）：

```python
def get_cohort_percentile(db: Session, student_id: int, college: str | None = None) -> dict:
    from app.models.user import User, UserRole
    from app.models.profile import StudentProfileSnapshot

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        return {}

    college = college or student.college
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if college:
        query = query.filter(User.college == college)
    cohort_ids = [u.id for u in query.all()]
    if not cohort_ids or student_id not in cohort_ids:
        return {}

    latest_snapshot = db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).first()
    if not latest_snapshot:
        return {"overall": 50, "academic": 50, "practice": 50}

    scores = ["academic_score", "psychological_risk", "engagement_score", "growth_score", "overall_risk"]
    result = {}
    for s in scores:
        all_scores = [
            r[0] for r in db.query(getattr(StudentProfileSnapshot, s))
            .filter(
                StudentProfileSnapshot.student_id.in_(cohort_ids),
                StudentProfileSnapshot.snapshot_date == latest_snapshot.snapshot_date
            ).all()
        ]
        if not all_scores:
            continue
        student_val = getattr(latest_snapshot, s)
        below = sum(1 for v in all_scores if v <= student_val)
        result[s.replace("_score", "").replace("_risk", "_risk")] = round(below / len(all_scores) * 100, 1)
    return result


def get_trajectory(db: Session, student_id: int, weeks: int = 12) -> dict:
    from datetime import timedelta
    from app.models.profile import StudentProfileSnapshot

    cutoff = date.today() - timedelta(weeks=weeks)
    snapshots = db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id,
        StudentProfileSnapshot.snapshot_date >= cutoff
    ).order_by(StudentProfileSnapshot.snapshot_date.asc()).all()

    if len(snapshots) < 2:
        return {"academic": 0, "psychological_risk": 0, "engagement": 0, "growth": 0, "overall_risk": 0}

    first = snapshots[0]
    last = snapshots[-1]
    return {
        "academic": round(last.academic_score - first.academic_score, 1),
        "psychological_risk": round(last.psychological_risk - first.psychological_risk, 1),
        "engagement": round(last.engagement_score - first.engagement_score, 1),
        "growth": round(last.growth_score - first.growth_score, 1),
        "overall_risk": round(last.overall_risk - first.overall_risk, 1),
    }


def get_risk_indicators(db: Session, student_id: int) -> list[dict]:
    from app.models.user import User
    from app.models.growth import GrowthRecord
    from app.models.crisis import AIDialogSummary
    from app.models.leave import LeaveRequest
    from app.models.conversation import Conversation

    indicators = []
    now = datetime.now(timezone.utc)
    today = date.today()

    grades = db.query(Grade).filter(Grade.student_id == student_id).order_by(Grade.semester.desc()).all()
    if grades:
        semesters = {}
        for g in grades:
            semesters.setdefault(g.semester, []).append(g.gpa)
        sem_avgs = [(s, sum(gpas)/len(gpas)) for s, gpas in semesters.items()]
        if len(sem_avgs) >= 2:
            latest_avg = sem_avgs[0][1]
            prev_avg = sem_avgs[1][1]
            if latest_avg < prev_avg - 0.3:
                indicators.append({
                    "dimension": "academic", "severity": "high",
                    "detail": f"GPA 从 {prev_avg:.2f} 降至 {latest_avg:.2f}",
                })

    leaves_90d = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student_id,
        LeaveRequest.created_at >= now - timedelta(days=90),
    ).count()
    if leaves_90d >= 5:
        indicators.append({
            "dimension": "behavior", "severity": "medium",
            "detail": f"近 90 天请假 {leaves_90d} 次，频率偏高",
        })

    latest_crisis = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).first()
    if latest_crisis and latest_crisis.level.value in ("severe", "moderate") and not latest_crisis.resolved:
        indicators.append({
            "dimension": "psychology", "severity": "high",
            "detail": f"未解决的 {latest_crisis.level.value} 级危机预警",
        })

    last_conv = db.query(Conversation).filter(
        Conversation.user_id == student_id
    ).order_by(Conversation.updated_at.desc()).first()
    if last_conv:
        inactive = (now - last_conv.updated_at).days
        if inactive > 14:
            indicators.append({
                "dimension": "engagement", "severity": "medium",
                "detail": f"已 {inactive} 天无对话交互",
            })

    growth_90d = db.query(GrowthRecord).filter(
        GrowthRecord.student_id == student_id,
        GrowthRecord.date >= today - timedelta(days=90),
    ).count()
    if growth_90d == 0:
        indicators.append({
            "dimension": "growth", "severity": "low",
            "detail": "近 90 天无新增成长记录",
        })

    return indicators
```

- [ ] **Step 2: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.services.scoring import get_cohort_percentile, get_trajectory, get_risk_indicators; print('Scoring enhanced OK')"
```

---

### Task 3: 学生 360 画像引擎

**Files:**
- Create: `app/services/student_profile_engine.py`

- [ ] **Step 1: 创建画像引擎核心服务**

```python
import json
import logging
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.academic import Grade
from app.models.growth import GrowthRecord
from app.models.crisis import AIDialogSummary
from app.models.leave import LeaveRequest
from app.models.conversation import Conversation
from app.models.profile import StudentProfileSnapshot, ConversationSummary
from app.services.scoring import (
    calc_radar_score, get_risk_indicators, get_trajectory
)
from app.services.llm_service import _get_client, _get_llm_config

logger = logging.getLogger(__name__)


def _detect_behavioral_patterns(db, student_id: int, now=None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    today = date.today()
    ninety_days_ago = today - timedelta(days=90)

    leave_count = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student_id,
        LeaveRequest.created_at >= now - timedelta(days=90),
    ).count()
    leave_frequency = "high" if leave_count >= 5 else "medium" if leave_count >= 2 else "low"

    crises = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).limit(5).all()
    if len(crises) >= 2:
        risk_values = {"normal": 0, "mild": 1, "moderate": 2, "severe": 3}
        levels = [risk_values.get(c.level.value, 0) for c in crises[:3]]
        crisis_trend = "worsening" if levels == sorted(levels, reverse=True) else "improving" if levels == sorted(levels) else "stable"
    else:
        crisis_trend = "stable"

    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    semesters = defaultdict(list)
    for g in grades:
        semesters[g.semester].append(g.gpa)
    sem_avgs = [(s, sum(gpas)/len(gpas)) for s, gpas in semesters.items()]
    sem_avgs.sort(key=lambda x: x[0])
    if len(sem_avgs) >= 2:
        diff = sem_avgs[-1][1] - sem_avgs[-2][1]
        grade_trajectory = "declining" if diff < -0.2 else "improving" if diff > 0.2 else "stable"
    else:
        grade_trajectory = "stable"

    convs_90d = db.query(Conversation).filter(
        Conversation.user_id == student_id,
        Conversation.created_at >= now - timedelta(days=90),
    ).count()
    engagement_level = "high" if convs_90d > 20 else "medium" if convs_90d > 5 else "low"

    last_conv = db.query(Conversation).filter(
        Conversation.user_id == student_id
    ).order_by(Conversation.updated_at.desc()).first()
    inactive_days = (now - last_conv.updated_at).days if last_conv else 999

    return {
        "leave_frequency": leave_frequency,
        "crisis_trend": crisis_trend,
        "grade_trajectory": grade_trajectory,
        "engagement_level": engagement_level,
        "inactive_days": inactive_days,
    }


def _compute_dimension_scores(db, student_id: int, user=None) -> dict:
    if not user:
        user = db.query(User).filter(User.id == student_id).first()
    if not user:
        return {"academic": 0, "psychological_risk": 0, "engagement": 0, "growth": 0, "overall_risk": 0}

    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == student_id).all()
    skills_data = user.skills_json or {"skills": [], "interests": []}
    raw_skills = skills_data.get("skills", [])
    skills = [s["name"] if isinstance(s, dict) else s for s in raw_skills]
    interests = skills_data.get("interests", [])

    type_counts = defaultdict(int)
    for r in records:
        type_counts[r.type.value if hasattr(r.type, 'value') else r.type] += 1

    n_records = len(records)
    n_skills = len(skills)
    n_interests = len(interests)

    academic = min(100, type_counts.get("honor", 0) * 15 + type_counts.get("paper", 0) * 30 + n_records * 3)
    growth = min(100, n_records * 10 + n_skills * 8 + type_counts.get("practice", 0) * 10)
    engagement = min(100, n_interests * 15 + type_counts.get("practice", 0) * 15)

    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    if grades:
        gpas = [g.gpa for g in grades if g.gpa]
        if gpas:
            academic = min(100, academic + (sum(gpas) / len(gpas)) * 15)

    recent_crises = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).limit(3).all()
    risk_values = {"normal": 0, "mild": 25, "moderate": 60, "severe": 90}
    psych_risk = 0
    for c in recent_crises:
        psych_risk = max(psych_risk, risk_values.get(c.level.value if hasattr(c.level, 'value') else "normal", 0))
    if recent_crises and not recent_crises[0].resolved:
        psych_risk = min(100, psych_risk + 15)

    overall_risk = min(100, (100 - academic) * 0.3 + psych_risk * 0.4 + (100 - engagement) * 0.2 + (100 - growth) * 0.1)

    return {
        "academic": round(academic, 1),
        "psychological_risk": round(psych_risk, 1),
        "engagement": round(engagement, 1),
        "growth": round(growth, 1),
        "overall_risk": round(overall_risk, 1),
    }


def _batch_generate_insights(db, students_batch: list[tuple[int, dict, dict]], max_retries=1):
    if not students_batch:
        return {}
    try:
        lines = []
        for sid, scores, patterns in students_batch:
            lines.append(
                f"学生ID={sid}：学业={scores['academic']}，心理风险={scores['psychological_risk']}，"
                f"参与度={scores['engagement']}，请假频率={patterns['leave_frequency']}，"
                f"危机趋势={patterns['crisis_trend']}，成绩轨迹={patterns['grade_trajectory']}"
            )
        prompt = f"""你是一名校园学生数据分析师。基于以下学生数据，为每位学生生成1-2条关键洞察（中文）。

每条洞察包含：
- dimension: academic/psychology/behavior/engagement/growth
- type: warning/praise/observation/escalation
- content: 具体描述（20-40字）

学生数据：
{chr(10).join(lines)}

以JSON数组格式返回，每个元素包含 student_id 和 insights 数组：
[{{"student_id": 1, "insights": [{{"dimension": "academic", "type": "warning", "content": "..."}}]}}]
只返回JSON，不要其他文字。"""
        config = _get_llm_config()
        resp = _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "[]"
        cleaned = content.strip().strip("```json").strip("```").strip()
        results = json.loads(cleaned)
        if isinstance(results, dict) and "insights" in results:
            results = [results]
        return {r["student_id"]: r.get("insights", []) for r in results}
    except Exception:
        logger.exception("批量洞察生成失败")
        return {}


def refresh_single_profile(db: Session, student_id: int) -> StudentProfileSnapshot | None:
    user = db.query(User).filter(User.id == student_id).first()
    if not user:
        return None
    scores = _compute_dimension_scores(db, student_id, user)
    patterns = _detect_behavioral_patterns(db, student_id)
    insights = _batch_generate_insights(db, [(student_id, scores, patterns)])
    snapshot = StudentProfileSnapshot(
        student_id=student_id,
        snapshot_date=date.today(),
        academic_score=scores["academic"],
        psychological_risk=scores["psychological_risk"],
        engagement_score=scores["engagement"],
        growth_score=scores["growth"],
        overall_risk=scores["overall_risk"],
        behavioral_patterns=patterns,
        key_insights=insights.get(student_id, []),
    )
    db.add(snapshot)
    db.commit()
    return snapshot


def refresh_all_profiles():
    db = SessionLocal()
    try:
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        batch_size = 5
        for i in range(0, len(students), batch_size):
            batch = students[i:i + batch_size]
            batch_data = []
            for s in batch:
                scores = _compute_dimension_scores(db, s.id, s)
                patterns = _detect_behavioral_patterns(db, s.id)
                batch_data.append((s.id, scores, patterns))
            insights_map = _batch_generate_insights(db, batch_data)
            for s in batch:
                scores = _compute_dimension_scores(db, s.id, s)
                patterns = _detect_behavioral_patterns(db, s.id)
                snapshot = StudentProfileSnapshot(
                    student_id=s.id,
                    snapshot_date=date.today(),
                    academic_score=scores["academic"],
                    psychological_risk=scores["psychological_risk"],
                    engagement_score=scores["engagement"],
                    growth_score=scores["growth"],
                    overall_risk=scores["overall_risk"],
                    behavioral_patterns=patterns,
                    key_insights=insights_map.get(s.id, []),
                )
                db.add(snapshot)
            db.commit()
            logger.info("已刷新学生画像 %d-%d / %d", i + 1, min(i + batch_size, len(students)), len(students))
    finally:
        db.close()


def get_latest_profile(db: Session, student_id: int) -> StudentProfileSnapshot | None:
    return db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).first()


def get_profile_history(db: Session, student_id: int, limit: int = 30):
    return db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student_id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).limit(limit).all()
```

- [ ] **Step 2: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.services.student_profile_engine import refresh_all_profiles, get_latest_profile; print('Profile engine OK')"
```

---

### Task 4: 语义危机分析增强

**Files:**
- Modify: `app/services/crisis_service.py`

- [ ] **Step 1: 在 crisis_service.py 末尾追加语义分析函数**

```python
import json
from typing import Any


async def analyze_semantic_risk(user_message: str, context: list[dict] | None = None) -> dict | None:
    prompt = f"""你是一名校园心理健康分析助手。分析以下学生消息中是否存在心理危机信号。

消息内容：{user_message}

请评估：
1. risk_level: "none" / "mild" / "moderate" / "severe"
2. emotion_tags: 情绪标签数组（如 ["焦虑","无助"]）
3. recommended_action: "none" / "monitor" / "intervene" / "immediate_intervention"
4. explanation: 简要说明判断依据

只返回JSON，不要其他内容。
{{"risk_level": "none", "emotion_tags": [], "recommended_action": "none", "explanation": ""}}"""
    try:
        config = _get_llm_config()
        resp = _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        return None


def get_crisis_trend(db: Session, student_id: int) -> str:
    crises = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).limit(5).all()
    if len(crises) < 2:
        return "stable"
    risk_values = {"normal": 0, "mild": 1, "moderate": 2, "severe": 3}
    levels = [risk_values.get(c.level.value if hasattr(c.level, 'value') else "normal", 0) for c in crises]
    if levels == sorted(levels, reverse=True):
        return "worsening"
    if levels == sorted(levels):
        return "improving"
    return "stable"
```

- [ ] **Step 2: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.services.crisis_service import analyze_semantic_risk, get_crisis_trend; print('Crisis enhanced OK')"
```

---

### Task 5: 长期记忆模块

**Files:**
- Create: `app/services/conversation_memory.py`

- [ ] **Step 1: 创建对话摘要与记忆检索服务**

```python
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationMessage
from app.models.profile import ConversationSummary
from app.services.llm_service import _get_client, _get_llm_config

logger = logging.getLogger(__name__)


async def summarize_conversation(db: Session, conversation_id: int) -> ConversationSummary | None:
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return None
    messages = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conversation_id
    ).order_by(ConversationMessage.created_at.asc()).all()
    if not messages:
        return None

    message_text = "\n".join(
        f"{m.role}: {m.content[:200]}" for m in messages if m.content
    )
    prompt = f"""你是一名对话分析助手。分析以下AI助手与学生的对话，生成摘要和洞察。

对话内容：
{message_text}

以JSON格式返回：
{{
    "summary": "对话摘要（50字以内）",
    "key_insights": {{"skills": [], "concerns": [], "interests": [], "requests": []}},
    "topics": ["主题1", "主题2"],
    "sentiment": "positive/neutral/negative"
}}
只返回JSON，不要其他内容。"""
    try:
        config = _get_llm_config()
        resp = _get_client().chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        result = json.loads(content)
        summary = ConversationSummary(
            conversation_id=conversation_id,
            student_id=conv.user_id,
            summary=result.get("summary", ""),
            key_insights=result.get("key_insights", {}),
            topics=result.get("topics", []),
            sentiment=result.get("sentiment", "neutral"),
            message_count=len(messages),
        )
        db.add(summary)
        db.commit()
        return summary
    except Exception:
        logger.exception("对话摘要生成失败")
        return None


def get_relevant_memories(db: Session, student_id: int, current_message: str, limit: int = 3) -> str:
    summaries = db.query(ConversationSummary).filter(
        ConversationSummary.student_id == student_id
    ).order_by(ConversationSummary.created_at.desc()).limit(limit).all()
    if not summaries:
        return ""
    parts = []
    for s in summaries:
        insights = s.key_insights or {}
        concerns = insights.get("concerns", [])
        skills = insights.get("skills", [])
        interests = insights.get("interests", [])
        extras = []
        if concerns:
            extras.append(f"关注点：{', '.join(concerns[:3])}")
        if skills:
            extras.append(f"技能：{', '.join(skills[:3])}")
        if interests:
            extras.append(f"兴趣：{', '.join(interests[:3])}")
        extra = "；".join(extras)
        if extra:
            parts.append(f"[{s.created_at.strftime('%m-%d')}] {s.summary}（{extra}）")
        else:
            parts.append(f"[{s.created_at.strftime('%m-%d')}] {s.summary}")
    return "；".join(parts) if parts else ""
```

- [ ] **Step 2: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.services.conversation_memory import get_relevant_memories; print('Memory OK')"
```

---

### Task 6: 自适应对话策略

**Files:**
- Modify: `app/services/agent_service.py`

- [ ] **Step 1: 在文件开头追加策略选择函数（from app.services.student_profile_engine import get_latest_profile 后）**

```python
STUDENT_STRATEGIES = {
    "at_risk": {
        "style": "gentle_care",
        "tone": "温和鼓励",
        "max_questions": 1,
        "greeting_extra": "最近过得怎么样？有什么想聊聊的吗？",
        "rules": ["避免追问学业压力", "多关心情绪状态", "回复控制在100字以内"],
    },
    "high_performer": {
        "style": "challenge_growth",
        "tone": "积极引导",
        "max_questions": 3,
        "greeting_extra": "最近有没有参加什么有意思的比赛或项目？",
        "rules": ["推荐更高阶的挑战", "主动介绍竞赛/论文机会"],
    },
    "disengaged": {
        "style": "re_engage",
        "tone": "轻松友好",
        "max_questions": 1,
        "greeting_extra": "好久不见！最近有什么新鲜事吗？",
        "rules": ["从轻松话题切入", "避免追问近况", "多分享校园趣事"],
    },
    "normal": {
        "style": "standard",
        "tone": "标准",
        "max_questions": 2,
        "greeting_extra": "",
        "rules": [],
    },
}


def select_conversation_strategy(profile) -> tuple[str, dict]:
    if profile is None:
        return "normal", STUDENT_STRATEGIES["normal"]
    if profile.psychological_risk > 60 or profile.overall_risk > 50:
        return "at_risk", STUDENT_STRATEGIES["at_risk"]
    if profile.academic_score > 75 and profile.engagement_score > 60:
        return "high_performer", STUDENT_STRATEGIES["high_performer"]
    if profile.engagement_score < 30:
        return "disengaged", STUDENT_STRATEGIES["disengaged"]
    return "normal", STUDENT_STRATEGIES["normal"]
```

- [ ] **Step 2: 修改 `chat()` 函数开头，注入策略**

在 `async def chat(...)` 函数中，在 `system_prompt = build_system_prompt(user)` 之前添加：

```python
    # 自适应对话策略
    from app.services.student_profile_engine import get_latest_profile
    profile = get_latest_profile(db, user.id)
    strategy_name, strategy = select_conversation_strategy(profile)
    strategy_notes = ""
    if strategy["rules"]:
        strategy_notes = "\n".join(f"- {r}" for r in strategy["rules"])
        strategy_notes = f"\n\n## 本次对话策略\n{strategy_notes}"
```

然后在 `system_content = system_prompt` 之后追加注入：

在 `if context:` 块之后添加：

```python
    if strategy_notes:
        system_content += strategy_notes
```

- [ ] **Step 3: 在 `async def chat()` 中新增记忆注入**

在 `messages = [{"role": "system", "content": system_content}]` 之前添加：

```python
    from app.services.conversation_memory import get_relevant_memories
    memory_context = get_relevant_memories(db, user.id, message)
    if memory_context:
        system_content += f"\n\n关于该生的历史记忆：{memory_context}"
```

- [ ] **Step 4: 在 `_save_assistant_response()` 末尾添加对话摘要触发**

在 `except Exception: pass` 之前添加：

```python
    # 触发对话摘要（每20条消息自动摘要）
    msg_count = db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id == conv_id
    ).count()
    if msg_count % 20 == 0:
        from app.services.conversation_memory import summarize_conversation
        import asyncio
        asyncio.ensure_future(summarize_conversation(db, conv_id))
```

- [ ] **Step 5: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.services.agent_service import select_conversation_strategy, STUDENT_STRATEGIES; print('Agent enhanced OK')"
```

---

### Task 7: 主动触达引擎

**Files:**
- Create: `app/services/proactive_engine.py`

- [ ] **Step 1: 创建主动触达服务**

```python
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, date
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.crisis import AIDialogSummary
from app.models.profile import StudentProfileSnapshot
from app.models.notification import Notification
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)


class ProactiveAction(BaseModel):
    trigger: str
    student_id: int
    priority: int
    action_type: str
    title: str
    content: str
    target_role: str


class BaseTrigger(ABC):
    @abstractmethod
    def evaluate(self, db: Session, student: User, profile: StudentProfileSnapshot | None) -> ProactiveAction | None: ...


class CrisisEscalationTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == student.id
        ).order_by(AIDialogSummary.created_at.desc()).first()
        if not latest_crisis or latest_crisis.resolved:
            return None
        risk = profile.psychological_risk
        if risk > 75:
            return ProactiveAction(
                trigger="crisis_escalation", student_id=student.id, priority=90,
                action_type="escalation",
                title=f"⚠️ 高危预警：{student.name}",
                content=f"心理风险评分 {risk}，危机等级 {latest_crisis.level.value}，建议立即联系辅导员",
                target_role="teacher",
            )
        if risk > 50:
            return ProactiveAction(
                trigger="crisis_escalation", student_id=student.id, priority=70,
                action_type="notification",
                title=f"注意：{student.name} 的心理状态变化",
                content=f"心理风险评分 {risk}，请关注学生状态",
                target_role="teacher",
            )
        return None


class InactivityTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        patterns = profile.behavioral_patterns or {}
        inactive_days = patterns.get("inactive_days", 0)
        if inactive_days > 14:
            return ProactiveAction(
                trigger="prolonged_inactivity", student_id=student.id, priority=50,
                action_type="system_message",
                title="好久不见 👋",
                content=f"同学你好，你已经 {inactive_days} 天没有来找我聊天了。最近过得怎么样？有什么需要帮忙的吗？",
                target_role="student",
            )
        return None


class GradeDropTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        patterns = profile.behavioral_patterns or {}
        if patterns.get("grade_trajectory") == "declining" and profile.academic_score < 50:
            return ProactiveAction(
                trigger="grade_drop", student_id=student.id, priority=60,
                action_type="notification",
                title=f"学业关注：{student.name}",
                content=f"学业评分 {profile.academic_score}，成绩呈下降趋势，建议提供学业支持",
                target_role="teacher",
            )
        return None


class MilestoneTrigger(BaseTrigger):
    def evaluate(self, db, student, profile):
        if not profile:
            return None
        if profile.growth_score > 0 and profile.growth_score % 25 == 0:
            return ProactiveAction(
                trigger="milestone_reached", student_id=student.id, priority=40,
                action_type="system_message",
                title="成长里程碑 🎉",
                content=f"恭喜！你的成长评分已经达到 {profile.growth_score} 分！继续保持，未来可期！",
                target_role="student",
            )
        return None


TRIGGERS: list[BaseTrigger] = [
    CrisisEscalationTrigger(),
    InactivityTrigger(),
    GradeDropTrigger(),
    MilestoneTrigger(),
]


def evaluate_student(db: Session, student: User) -> list[ProactiveAction]:
    profile = db.query(StudentProfileSnapshot).filter(
        StudentProfileSnapshot.student_id == student.id
    ).order_by(StudentProfileSnapshot.snapshot_date.desc()).first()

    actions = []
    for trigger in TRIGGERS:
        try:
            action = trigger.evaluate(db, student, profile)
            if action:
                actions.append(action)
        except Exception:
            logger.exception("触发器 %s 评估失败", trigger.__class__.__name__)

    actions.sort(key=lambda a: a.priority, reverse=True)
    max_per_student = 3
    return actions[:max_per_student]


def execute_action(db: Session, action: ProactiveAction):
    if action.action_type == "notification":
        if action.target_role == "teacher":
            tutors = db.query(User).filter(
                User.role == UserRole.TEACHER,
                User.id.in_(
                    db.query(User.tutor_id).filter(User.id == action.student_id).all()
                )
            ).all()
            for tutor in tutors:
                notif = Notification(
                    user_id=tutor.id,
                    title=action.title,
                    content=action.content,
                    type="system",
                )
                db.add(notif)
            db.commit()
    elif action.action_type == "system_message":
        notif = Notification(
            user_id=action.student_id,
            title=action.title,
            content=action.content,
            type="system",
        )
        db.add(notif)
        db.commit()


def evaluate_all():
    db = SessionLocal()
    try:
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        for student in students:
            actions = evaluate_student(db, student)
            for action in actions:
                execute_action(db, action)
                logger.info("[主动触达] %s → %s(%s): %s", action.trigger, student.name, student.username, action.title)
    finally:
        db.close()
```

- [ ] **Step 2: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.services.proactive_engine import evaluate_all, evaluate_student; print('Proactive engine OK')"
```

---

### Task 8: API 端点

**Files:**
- Create: `app/api/profile.py`

- [ ] **Step 1: 创建画像 API**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.profile import StudentProfileSnapshot
from app.schemas.profile import (
    ProfileSnapshotOut, ProfileTrendsOut, ProfileTrendPoint,
    CohortComparisonOut, CohortComparison,
)
from app.services.student_profile_engine import (
    refresh_single_profile, get_latest_profile, get_profile_history,
)
from app.services.scoring import get_cohort_percentile, get_trajectory, get_risk_indicators

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/student/{student_id}", response_model=ProfileSnapshotOut | None)
def get_student_profile(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.ADMIN and user.role == UserRole.TEACHER:
        student = db.query(User).filter(User.id == student_id, User.tutor_id == user.id).first()
        if not student:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="无权查看该学生画像")
    return get_latest_profile(db, student_id)


@router.get("/student/{student_id}/trends", response_model=ProfileTrendsOut)
def get_student_trends(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == UserRole.STUDENT and user.id != student_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权查看")
    history = get_profile_history(db, student_id, limit=30)
    trends = [
        ProfileTrendPoint(
            date=str(h.snapshot_date),
            academic_score=h.academic_score,
            psychological_risk=h.psychological_risk,
            engagement_score=h.engagement_score,
            growth_score=h.growth_score,
            overall_risk=h.overall_risk,
        ) for h in history
    ]
    trends.reverse()
    return ProfileTrendsOut(trends=trends)


@router.get("/cohort/{student_id}", response_model=CohortComparisonOut)
def get_student_cohort(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    cohort = get_cohort_percentile(db, student_id)
    comparisons = [
        CohortComparison(dimension=k, student_score=0, cohort_avg=0, percentile=v)
        for k, v in cohort.items()
    ]
    return CohortComparisonOut(comparisons=comparisons)


@router.get("/student/{student_id}/risk-indicators")
def get_student_risk_indicators(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return get_risk_indicators(db, student_id)


@router.get("/student/{student_id}/trajectory")
def get_student_trajectory(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return get_trajectory(db, student_id)


@router.post("/refresh")
def refresh_profiles(
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    import threading
    threading.Thread(target=lambda: refresh_single_profile(db=None, student_id=0), daemon=True).start()
    return {"message": "画像刷新已启动"}
```

- [ ] **Step 2: 注册路由到 main.py**

在 `from app.api.setting import router as setting_router` 之后添加：

```python
from app.api.profile import router as profile_router
```

在 `app.include_router(setting_router)` 之后添加：

```python
app.include_router(profile_router)
```

- [ ] **Step 3: 验证语法**

```bash
cd mianyang-campus/backend && python -c "from app.api.profile import router; print('Profile API OK')"
```

---

### Task 9: 整体验证

- [ ] **Step 1: 运行全部语法检查**

```bash
cd mianyang-campus/backend && python -c "
import py_compile, glob
files = (glob.glob('app/**/*.py', recursive=True) + 
         glob.glob('tests/**/*.py', recursive=True))
errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f'{f}: {e}')
if errors:
    for e in errors: print(e)
else:
    print(f'All {len(files)} files syntax OK')
"
```

- [ ] **Step 2: 运行测试**

```bash
cd mianyang-campus/backend && python -m pytest tests/ -v --tb=short 2>&1
```

---

### Task 10: 提交

- [ ] **Step 1: Commit**

```bash
cd mianyang-campus/backend && git add -A && git commit -m "feat: 实现 AI 创新六大模块

- 学生360画像引擎：跨模块数据聚合 + 行为模式识别 + NL洞察
- 语义级危机分析：LLM语义分析二期 pipeline + 趋势跟踪
- 智能评分系统：常模对比 + 轨迹分析 + 风险指标
- 主动触达引擎：触发器注册表 + 优先级评分 + 自动执行
- 自适应对话策略：画像感知的差异化对话策略
- 长期记忆模块：对话摘要 + 关键洞察提取 + 记忆检索
"
```
