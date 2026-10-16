"""各子任务提示词（纯函数，无 IO）。

对应《提示词工程规范.md》§2（模块体系）、§3（标签词表）、§5（输出契约）、§6（统一话术库）。
业务模块只调用本模块的函数，数据一律由调用方注入，本模块不访问数据库/网络。
"""

from __future__ import annotations

from .conventions import (
    ANTI_FABRICATION,
    INJECTION_GUARD,
    PII_GUARD,
    TAG_CONSTRAINTS,
    TAG_CONTEXT,
    TAG_EVIDENCE,
    TAG_EXAMPLES,
    TAG_GOAL,
    TAG_IDENTITY,
    TAG_OUTPUT_FORMAT,
    bullets,
    compose,
    section,
)


# ==================== 多模态：图片识别 ====================

_IMAGE_JSON_SPEC = """以严格 JSON 返回（不要额外文字、不要代码块标记）：
{
  "is_document": false,
  "category": "",
  "name": "",
  "color": "",
  "brand": "",
  "features": "",
  "document_type": "",
  "document_title": "",
  "description": ""
}

字段说明：
- is_document: 是否为证书/奖状/成绩单/证明类文档
- category: 物品大类，如 水杯/钱包/耳机/钥匙/雨伞/校园卡/书包/充电器/证书/其他
- name: 一句话物品名称，含颜色等关键特征，如"黑色保温杯"
- features: 显著外观特征、磨损、挂件、内含物等
- document_type: 仅当 is_document 为 true 时填写（荣誉证书/竞赛获奖/成绩单/其他证明）
- document_title: 仅当 is_document 为 true 时尽量提取标题原文
- description: 50 字以内综合描述"""


def build_image_recognize_prompt(hint: str = "") -> str:
    """图片识别提示词：服务失物招领与成长档案两个场景。"""
    identity = section(TAG_IDENTITY, "你是校园视觉识别助手，服务于校园失物招领与成长档案两个场景。")
    goal = section(TAG_GOAL, "识别用户上传的图片，输出结构化字段，供后续失物登记或成长档案提取使用。")
    constraints = section(TAG_CONSTRAINTS, bullets(
        "只依据图片中真实可见的内容作答，不要编造",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    output_format = section(TAG_OUTPUT_FORMAT, _IMAGE_JSON_SPEC)
    context = section(TAG_CONTEXT, f"用户附带的说明（可作为判断线索）：{hint[:300]}") if hint else ""
    return compose(identity, goal, constraints, output_format, context)


# ==================== 心理健康：危机摘要 / 语义风险 ====================

def build_crisis_summary_prompt(*, user_message: str, ai_reply: str, keywords: list[str]) -> str:
    """危机关键词命中后生成脱敏摘要与等级评定。"""
    identity = section(TAG_IDENTITY, "你是校园心理健康辅助分析助手。")
    goal = section(TAG_GOAL, "针对命中危机关键词的学生消息，生成脱敏摘要并评估危机等级。")
    context = section(TAG_CONTEXT, (
        f"命中关键词：{', '.join(keywords)}\n"
        f"学生消息：{user_message}\n"
        f"AI回复：{ai_reply}"
    ))
    constraints = section(TAG_CONSTRAINTS, bullets(
        "摘要必须脱敏：不包含具体姓名、班级、学号等可识别信息",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    output_format = section(TAG_OUTPUT_FORMAT, """以 JSON 格式返回：
{"summary": "脱敏后的摘要描述", "level": "severe" 或 "moderate" 或 "mild"}

等级定义：
- severe: 明确的自杀/自残倾向
- moderate: 明显的焦虑、抑郁、压力过大
- mild: 轻度情绪困扰

只返回 JSON，不要其他内容。""")
    return compose(identity, goal, context, constraints, output_format)


def build_semantic_risk_prompt(user_message: str) -> str:
    """语义级心理危机信号识别。"""
    identity = section(TAG_IDENTITY, "你是校园心理健康分析助手。")
    goal = section(TAG_GOAL, "分析学生消息中是否存在心理危机信号。")
    context = section(TAG_CONTEXT, f"消息内容：{user_message}")
    output_format = section(TAG_OUTPUT_FORMAT, """以 JSON 返回，字段如下：
- risk_level: "none" / "mild" / "moderate" / "severe"
- emotion_tags: 情绪标签数组（如 ["焦虑","无助"]）
- recommended_action: "none" / "monitor" / "intervene" / "immediate_intervention"
- explanation: 简要说明判断依据

示例：{"risk_level": "none", "emotion_tags": [], "recommended_action": "none", "explanation": ""}

只返回 JSON，不要其他内容。""")
    constraints = section(TAG_CONSTRAINTS, bullets(ANTI_FABRICATION, INJECTION_GUARD))
    return compose(identity, goal, context, constraints, output_format)


# ==================== 对话记忆：摘要与洞察 ====================

def build_conversation_summary_prompt(message_text: str) -> str:
    """把一次会话压缩为摘要 + 结构化洞察（供后续注入长期记忆）。"""
    identity = section(TAG_IDENTITY, "你是对话分析助手。")
    goal = section(TAG_GOAL, "分析 AI 助手与学生的对话，生成摘要与结构化洞察。")
    context = section(TAG_CONTEXT, f"对话内容：\n{message_text}")
    output_format = section(TAG_OUTPUT_FORMAT, """以 JSON 格式返回：
{"summary": "对话摘要（50字以内）", "key_insights": {"skills": [], "concerns": [], "interests": [], "requests": []}, "topics": ["主题1", "主题2"], "sentiment": "positive/neutral/negative"}

只返回 JSON，不要其他内容。""")
    constraints = section(TAG_CONSTRAINTS, bullets(PII_GUARD, ANTI_FABRICATION, INJECTION_GUARD))
    return compose(identity, goal, context, constraints, output_format)


# ==================== 学生画像：批量洞察 ====================

def build_student_insights_prompt(data_lines: str) -> str:
    """基于画像分数为学生批量生成 1-2 条关键洞察。"""
    identity = section(TAG_IDENTITY, "你是校园学生数据分析师。")
    goal = section(TAG_GOAL, """基于给出的学生数据，为每位学生生成 1-2 条关键洞察（中文）。每条洞察包含：
- dimension: academic/psychology/behavior/engagement/growth
- type: warning/praise/observation/escalation
- content: 具体描述（20-40字）""")
    context = section(TAG_CONTEXT, f"学生数据：\n{data_lines}")
    output_format = section(TAG_OUTPUT_FORMAT, """以 JSON 数组格式返回，每个元素包含 student_id 和 insights 数组：
[{"student_id": 1, "insights": [{"dimension": "academic", "type": "warning", "content": "..."}]}]

只返回 JSON，不要其他文字。""")
    constraints = section(TAG_CONSTRAINTS, bullets(ANTI_FABRICATION, INJECTION_GUARD))
    return compose(identity, goal, context, constraints, output_format)


# ==================== 学情诊断：可溯源辅导建议 ====================

def build_insight_advice_prompt(
    *, student_name: str, facts: str, risk_level: str, risk_reasons: list[str]
) -> str:
    """只依据已核实事实生成辅导建议（严禁编造）。"""
    identity = section(TAG_IDENTITY, "你是高校辅导员的工作助手。")
    goal = section(TAG_GOAL, f"基于已核实事实，为辅导员生成针对学生「{student_name}」的辅导建议。")
    evidence = section(TAG_EVIDENCE, (
        f"事实清单：\n{facts}\n\n"
        f"系统判定风险等级：{risk_level}；依据：{'；'.join(risk_reasons) or '无'}"
    ))
    constraints = section(TAG_CONSTRAINTS, bullets(
        "只能使用上述事实，不得编造任何未给出的信息",
        INJECTION_GUARD,
    ))
    output_format = section(TAG_OUTPUT_FORMAT, bullets(
        "用 3 条以内的要点给出可执行动作（先做什么、再做什么）",
        "控制在 150 字以内，纯文本，不要 Markdown 标记",
    ))
    return compose(identity, goal, evidence, constraints, output_format)


# ==================== 主动发现：一句话洞察 ====================

def build_proactive_insight_prompt(*, student_name: str, lines: str, max_chars: int) -> str:
    """把系统发现的真实动作，转成一句体贴的主动提醒。"""
    identity = section(TAG_IDENTITY, f"你是校园 AI 助手，正在给学生「{student_name}」做主动提醒。")
    goal = section(
        TAG_GOAL,
        f"用一句自然、体贴的中文口语（不超过 {max_chars} 字）总结提醒重点，并给出一个可执行的小建议。",
    )
    context = section(TAG_CONTEXT, f"系统基于真实数据发现了以下情况：\n{lines}")
    output_format = section(TAG_OUTPUT_FORMAT, "只返回这一句话，不要列表、不要引号、不要解释。")
    constraints = section(TAG_CONSTRAINTS, bullets(ANTI_FABRICATION, INJECTION_GUARD))
    return compose(identity, goal, context, constraints, output_format)


# ==================== 学习计划：阶段拆解 / 阶段评估 ====================

def build_plan_stages_prompt(
    *, title: str, objective: str, start_date, end_date, days_left
) -> str:
    """把学习计划拆解为闯关式阶段任务流。"""
    period = f"{start_date} 至 {end_date or '至今'}"
    if days_left is not None:
        period += f"（剩余 {days_left} 天）"
    identity = section(TAG_IDENTITY, "你是学习计划设计助手。")
    goal = section(TAG_GOAL, "把学生的学习计划拆解为 3-6 个循序渐进的阶段（里程碑/关卡），用于闯关式任务流。")
    context = section(TAG_CONTEXT, f"计划标题：{title}\n计划目标：{objective or '未填写'}\n周期：{period}")
    constraints = section(TAG_CONSTRAINTS, bullets(
        "阶段按完成目标的先后逻辑排列，每阶段给出简短标题（如'基础夯实'）与阶段目标 goal（说明本阶段要达成什么，40字内）",
        "每个阶段给出 1-4 个具体任务（title + 简短 description），任务要可执行、可量化",
        "总任务量要符合剩余时间，避免过重",
    ))
    output_format = section(TAG_OUTPUT_FORMAT, """只输出 JSON：
{"summary": "拆解思路(40字内)", "stages": [{"title": "...", "goal": "...", "tasks": [{"title": "...", "description": "..."}]}]}

不要输出其他文字。""")
    return compose(identity, goal, context, constraints, output_format)


def build_stage_evaluation_prompt(
    *, objective: str, stage_title: str, stage_goal: str, task_lines: str, submitted_result: str
) -> str:
    """对学生提交的阶段成果打分并给出改进建议。"""
    identity = section(TAG_IDENTITY, "你是学习计划成果评估助手。")
    goal = section(TAG_GOAL, "对学生提交的阶段成果进行严格评估，并给出改进建议。")
    context = section(TAG_CONTEXT, (
        f"计划目标：{objective}\n"
        f"阶段：{stage_title}\n"
        f"阶段目标：{stage_goal or '未填写'}\n"
        f"阶段任务：\n{task_lines}\n"
        f"学生提交的成果：{submitted_result or ''}"
    ))
    constraints = section(TAG_CONSTRAINTS, bullets(
        "score 要结合任务完成情况与成果质量合理打分（0-100 的整数）",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    output_format = section(TAG_OUTPUT_FORMAT, """只输出 JSON：
{"score": 0-100的整数, "evaluation": "综合评估(120字内)", "weaknesses": "不足与改进点(100字内)", "suggestions": "对后续阶段任务的调整建议(100字内)"}

不要输出其他文字。""")
    return compose(identity, goal, context, constraints, output_format)


def build_plan_reschedule_prompt(*, today_iso: str, plan_lines: str, task_lines: str) -> str:
    """针对未完成任务给出顺延与重排建议。"""
    identity = section(TAG_IDENTITY, "你是学习计划调度助手。")
    goal = section(TAG_GOAL, "为学生给出学习任务的顺延与重排建议。")
    context = section(TAG_CONTEXT, (
        f"今天是 {today_iso}。\n学生现有的学习计划：\n{plan_lines}\n未完成/未开始任务：\n{task_lines}"
    ))
    constraints = section(TAG_CONSTRAINTS, bullets(
        "只对未完成任务给出建议，任务 ID 必须来自上面列表",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    output_format = section(TAG_OUTPUT_FORMAT, """只输出 JSON：
{"summary": "总体建议(60字内)", "items": [{"task_id": 数字, "suggest": "针对该任务的一句建议(40字内)"}]}

不要输出其他内容。""")
    return compose(identity, goal, context, constraints, output_format)


# ==================== 审批 / 教师工作台 / 资源推荐 ====================

def build_leave_analysis_prompt(
    *, student_name: str, leave_type: str, start_date, end_date, reason: str
) -> str:
    """请假申请的审批建议。"""
    identity = section(TAG_IDENTITY, "你是校园审批助手。")
    goal = section(TAG_GOAL, "分析请假申请，给出审批建议与理由。")
    context = section(TAG_CONTEXT, (
        f"学生：{student_name}\n类型：{leave_type}\n时间：{start_date} 至 {end_date}\n原因：{reason}"
    ))
    constraints = section(TAG_CONSTRAINTS, bullets(
        'suggestion 必须是 "approve" 或 "reject"',
        "reason 必须用中文给出具体的分析理由（至少20字）",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    output_format = section(
        TAG_OUTPUT_FORMAT,
        '只返回 JSON，不要其他内容：\n{"suggestion": "approve", "reason": "具体分析理由..."}',
    )
    return compose(identity, goal, context, constraints, output_format)


_TEACHER_OUTREACH_DIMENSIONS = """分析维度：
1. 长时间未联系的学生（优先级高）
2. 有危机预警的学生（优先级高）
3. 近期请假较多的学生（需关注）
4. 有成长成果但未沟通的学生（鼓励）"""


def build_teacher_outreach_prompt(*, students_text: str, focus_student_id: int | None = None) -> str:
    """教师工作台：推荐值得主动联系的学生（单人或 Top3）。"""
    identity = section(TAG_IDENTITY, "你是校园管理助手。")
    context = section(TAG_CONTEXT, f"学生信息：\n{students_text}")
    if focus_student_id is not None:
        goal = section(
            TAG_GOAL,
            f"分析下面这位学生，判断是否值得主动联系，并给出具体理由。\n{_TEACHER_OUTREACH_DIMENSIONS}",
        )
        constraints = section(TAG_CONSTRAINTS, bullets(
            "给出该学生的具体理由（至少20字）",
            "标注优先级：high/medium/low",
            ANTI_FABRICATION,
        ))
        output_format = section(
            TAG_OUTPUT_FORMAT,
            "只返回 JSON 数组（仅含该学生一条），不要其他内容：\n"
            f'[{{"student_id": {focus_student_id}, "student_name": "姓名", '
            '"reason": "具体理由...", "priority": "high"}]',
        )
    else:
        goal = section(TAG_GOAL, f"从学生名单中分析并推荐 3 位最应该主动联系的学生。\n{_TEACHER_OUTREACH_DIMENSIONS}")
        constraints = section(TAG_CONSTRAINTS, bullets(
            "从列表中选出3位学生",
            "每位学生给出具体理由（至少20字）",
            "标注优先级：high/medium/low",
            ANTI_FABRICATION,
        ))
        output_format = section(
            TAG_OUTPUT_FORMAT,
            "只返回 JSON 数组，不要其他内容：\n"
            '[{"student_id": 1, "student_name": "姓名", "reason": "具体理由...", "priority": "high"}]',
        )
    return compose(identity, goal, context, constraints, output_format)


def build_resource_recommend_prompt(*, keywords: list[str], pool, limit: int) -> tuple[str, str]:
    """资源中心个性化推荐：返回 (system, user) 两条消息。"""
    identity = section(TAG_IDENTITY, "你是校园平台的内容推荐助手。")
    goal = section(
        TAG_GOAL,
        "根据学生的兴趣画像，从候选资源中挑选最值得推荐的条目，并给出简短推荐理由（不超过25字，贴合学生方向）。",
    )
    context = section(
        TAG_CONTEXT,
        f"学生画像关键词：{', '.join(keywords[:10]) if keywords else '暂无（默认推荐热门内容）'}",
    )
    system_msg = compose(identity, goal, context)
    user_msg = f'候选资源：{pool}\n请返回 JSON：{{"items":[{{"index":0,"reason":"..."}}]}}，共 {limit} 条。'
    return system_msg, user_msg


# ==================== 推荐问题 / 管家 / 语音 / 技能抽取 ====================

def build_recommend_questions_prompt(
    *, role_label: str, context_text: str, history_text: str, count: int, features: str
) -> str:
    """结合画像与历史对话生成推荐问题。"""
    identity = section(TAG_IDENTITY, "你是对话推荐助手。")
    goal = section(TAG_GOAL, f"根据用户信息与历史对话，生成 {count} 个用户可能接下来想问的推荐问题。")
    context = section(TAG_CONTEXT, (
        f"用户角色：{role_label}\n\n"
        f"用户当前画像与待办（真实数据，优先结合这些）：\n{context_text}"
    ))
    constraints = section(TAG_CONSTRAINTS, bullets(
        "问题控制在20字以内，自然口语化",
        "结合用户的历史兴趣、画像与待办事项，避免空泛",
        f"推荐内容必须贴合该用户角色，涵盖其常用功能（{features}），不要推荐其他角色的功能"
        "（例如不要给学生推荐班级管理，不要给教师推荐成绩单查询）",
        ANTI_FABRICATION,
    ))
    examples = section(TAG_EXAMPLES, f"历史对话记录：\n{history_text}")
    output_format = section(
        TAG_OUTPUT_FORMAT,
        f"直接返回 {count} 个问题的 JSON 数组，不要其他文字，例如：\n"
        '["帮我查一下下周的课程安排", "我想看看这学期的成绩单", '
        '"最近有什么校园活动通知", "我这周的任务完成得怎么样"]',
    )
    return compose(identity, goal, context, constraints, examples, output_format)


def build_butler_summary_prompt(transcript: str) -> str:
    """管家「小绵」：对话总结。"""
    identity = section(TAG_IDENTITY, "你是校园智能管家「小绵」。")
    goal = section(TAG_GOAL, "阅读给出的对话记录，输出简洁的中文总结。")
    context = section(TAG_CONTEXT, f"对话记录：\n{transcript}")
    constraints = section(TAG_CONSTRAINTS, bullets(ANTI_FABRICATION, INJECTION_GUARD))
    output_format = section(TAG_OUTPUT_FORMAT, bullets(
        "先用一句话概括对话主题",
        "再用不超过 5 条要点列出关键信息与待办事项",
        "纯文本，不使用 Markdown 标记（#、代码块等）",
    ))
    return compose(identity, goal, context, constraints, output_format)


def build_butler_chat_prompt(*, message: str, transcript: str = "") -> str:
    """管家「小绵」：日常问答。"""
    identity = section(TAG_IDENTITY, "你是校园智能管家「小绵」，服务绵阳城市学院的师生。")
    goal = section(TAG_GOAL, f"回答用户提问。\n\n用户提问：{message}")
    context = section(TAG_CONTEXT, f"最近对话：\n{transcript}") if transcript else ""
    constraints = section(TAG_CONSTRAINTS, bullets(
        "回答要亲切、简洁，纯文本输出，不使用 Markdown 标记，控制在 150 字以内",
        "涉及个人隐私数据或不确定的信息时，如实说明并建议对方咨询老师或辅导员",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    return compose(identity, goal, context, constraints)


def build_skill_extraction_prompt(user_message: str) -> str:
    """从学生发言中抽取技能与兴趣。"""
    identity = section(TAG_IDENTITY, "你是学生信息抽取助手。")
    goal = section(TAG_GOAL, "从学生的发言中提取技能和兴趣信息，只提取明确提及的技能或兴趣。")
    context = section(TAG_CONTEXT, f"学生发言：{user_message}")
    constraints = section(TAG_CONSTRAINTS, bullets(
        "没有提取到任何内容时返回空数组",
        ANTI_FABRICATION,
        INJECTION_GUARD,
    ))
    output_format = section(TAG_OUTPUT_FORMAT, """以 JSON 格式返回：
{"skills": [{"name": "技能名称", "context": "上下文"}], "interests": ["兴趣1", "兴趣2"]}

如果没有提取到，返回 {"skills": [], "interests": []}""")
    return compose(identity, goal, context, constraints, output_format)


def build_voice_greeting_prompt(*, emotion_label: str = "", emotion_hint: str = "") -> str:
    """语音通话接通时的开场问候（按视觉情绪状态定制）。"""
    goal = section(
        TAG_GOAL,
        "【本次为语音通话接通时刻】请由你先开口，用一句自然、亲切、口语化的问候开启聊天，不超过 30 字。",
    )
    context = section(
        TAG_CONTEXT,
        f"视觉情绪模块刚检测到：学生此刻表情偏【{emotion_label}】。{emotion_hint}",
    ) if emotion_label else ""
    constraints = section(TAG_CONSTRAINTS, bullets(
        "不要提及「接通」「系统」「检测」等字眼",
        "若已知学生的表情状态，请自然地关照一下他的状态，可顺着你观察到的情绪开口，但不要生硬地说「我检测到你的表情」",
    ))
    return compose(goal, context, constraints)


def build_tts_style_suffix(voice_prompt: str) -> str:
    """把语音播报风格提示词包装为规范标签块，叠加到系统提示词之后。"""
    return section(
        TAG_OUTPUT_FORMAT,
        f"【语音播报风格要求】{voice_prompt}\n"
        "请遵循以上风格要求回复，并在表达时尽量口语化、简短，便于语音合成朗读。",
    )


def build_voice_emotion_context_prompt(*, emotion_label: str) -> str:
    """语音对话中，把当轮检测到的情绪状态作为上下文约束注入。"""
    return section(TAG_CONTEXT, (
        f"视觉情绪模块检测到：学生当前情绪状态为【{emotion_label}】。"
        "请感知并顺应学生的情绪状态，语气温暖、共情地回应；"
        "若学生情绪低落或紧张，请给予安抚与支持，避免生硬说教。回答保持简洁。"
    ))