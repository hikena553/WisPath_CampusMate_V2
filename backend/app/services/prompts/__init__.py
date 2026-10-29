"""提示词工程包：遵循《提示词工程规范.md》集中管理全部 LLM 提示词。

- ``conventions``：标签词表、渲染器、统一话术常量（纯定义层）
- ``system``：系统提示词与回答模式指令
- ``tasks``：各子任务提示词（危机/记忆/画像/诊断/计划/审批/推荐/管家/语音等）
"""

from __future__ import annotations

from .conventions import (
    ANTI_FABRICATION,
    IDENTITY_GUARD,
    INJECTION_GUARD,
    META_RULE,
    NO_MARKDOWN,
    PII_GUARD,
    TAG_VOCABULARY,
    bullets,
    compose,
    section,
)
from .system import (
    ESSENCE_MODE_NOTE,
    ROLE_GREETING,
    build_answer_mode_note,
    build_student_system_prompt,
    build_teacher_system_prompt,
)
from .tasks import (
    build_butler_chat_prompt,
    build_butler_summary_prompt,
    build_conversation_summary_prompt,
    build_crisis_summary_prompt,
    build_daily_report_prompt,
    build_image_recognize_prompt,
    build_insight_advice_prompt,
    build_leave_analysis_prompt,
    build_plan_reschedule_prompt,
    build_plan_stages_prompt,
    build_proactive_insight_prompt,
    build_recommend_questions_prompt,
    build_resource_recommend_prompt,
    build_semantic_risk_prompt,
    build_skill_extraction_prompt,
    build_stage_evaluation_prompt,
    build_student_insights_prompt,
    build_teacher_outreach_prompt,
    build_tts_style_suffix,
    build_voice_emotion_context_prompt,
    build_voice_greeting_prompt,
)

__all__ = [
    # conventions
    "ANTI_FABRICATION", "IDENTITY_GUARD", "INJECTION_GUARD", "META_RULE", "NO_MARKDOWN", "PII_GUARD",
    "TAG_VOCABULARY", "bullets", "compose", "section",
    # system
    "ESSENCE_MODE_NOTE", "ROLE_GREETING",
    "build_answer_mode_note", "build_student_system_prompt", "build_teacher_system_prompt",
    # tasks
    "build_butler_chat_prompt", "build_butler_summary_prompt",
    "build_conversation_summary_prompt", "build_crisis_summary_prompt",
    "build_daily_report_prompt",
    "build_image_recognize_prompt", "build_insight_advice_prompt",
    "build_leave_analysis_prompt", "build_plan_reschedule_prompt",
    "build_plan_stages_prompt", "build_proactive_insight_prompt",
    "build_recommend_questions_prompt", "build_resource_recommend_prompt",
    "build_semantic_risk_prompt", "build_skill_extraction_prompt",
    "build_stage_evaluation_prompt", "build_student_insights_prompt",
    "build_teacher_outreach_prompt", "build_tts_style_suffix", "build_voice_greeting_prompt",
    "build_voice_emotion_context_prompt",
]