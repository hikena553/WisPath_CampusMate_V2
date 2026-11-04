# -*- coding: utf-8 -*-
"""Lead-side draft copy (used until deck/content.py lands from content-writer)."""

BRAND = {"en": "WisPath CampusMate", "cn": "智慧校园 AI 服务平台",
         "school": "绵阳城市学院", "mascot": "绵小城"}

FACTS = {"pages": "45 个页面", "api_modules": "20 个 API 模块",
         "models": "26 张数据表", "roles": "学生 / 教师 / 管理员",
         "tech": ["Vue 3", "TypeScript", "FastAPI", "MySQL 8", "WebSocket", "SSE", "JWT", "通义千问"]}

HELLO = {"hello": "你好", "sub": "绵小城 · 你的校园 AI 伙伴",
         "tagline": "让校园服务，从一句你好开始。"}

QUESTIONS = [
    {"main": "课表改了，怎么第一时间知道？", "sub": "信息散落在通知群和官网"},
    {"main": "请假要跑几趟办公室才算完？", "sub": "纸质流程，来回折腾"},
    {"main": "成绩背后，我到底进步了吗？", "sub": "只有分数，没有画像"},
]

PILLARS = [
    {"icon": "chat", "title": "AI 对话", "desc": "流式回答、语音输入、文件上传，工具调用直达业务。", "tag": "SSE 流式"},
    {"icon": "chart", "title": "成长档案", "desc": "荣誉、竞赛、实践、成果沉淀为可追踪的成长轨迹。", "tag": "五维画像"},
    {"icon": "calendar", "title": "学业与办事", "desc": "课表、成绩、GPA、请假与校园服务，一屏处理。", "tag": "一站式"},
    {"icon": "shield", "title": "关怀与预警", "desc": "对话语义识别情绪风险，危机分级推送到老师。", "tag": "三级预警"},
]

STUDENT = {
    "eyebrow": "学生端 · 移动优先",
    "headline": "大学四年，\n一个小城就够了。",
    "sub": "查课表、问流程、办请假、看成长——手机里的一次对话全部搞定。",
    "phone_title": "绵小城", "phone_sub": "在线 · 随时可问",
    "chat": [
        {"role": "user", "text": "我这学期的课表在哪看？"},
        {"role": "ai", "text": "已找到本周 6 门课程，第一节是《数据结构》，周三 8:00 · A301。"},
        {"role": "user", "text": "那请假怎么申请？"},
        {"role": "ai", "text": "打开办事服务即可提交，我会同步通知你的辅导员。"},
    ],
    "features": [
        {"icon": "chat", "title": "AI 助手", "desc": "校园知识库 + 工具调用，问什么答什么"},
        {"icon": "chart", "title": "成长档案", "desc": "综合评分、技能标签、成果一键归档"},
        {"icon": "grade", "title": "学业查询", "desc": "课表、成绩、GPA 与成绩分析"},
        {"icon": "heart", "title": "心理关怀", "desc": "情绪记录与暖心陪伴，随时可说"},
    ],
    "chips": ["课表", "成绩", "请假", "办事服务", "成长档案", "心理关怀"],
}

TEACHER = {
    "eyebrow": "教师端 · 移动办公",
    "headline": "班级的事，\n在手机上办完。",
    "sub": "班级概览、请假审批、学生画像与危机工单，随身的班级驾驶舱。",
    "kpis": [
        {"label": "我的学生", "value": "42", "tone": "blue"},
        {"label": "待审批", "value": "3", "tone": "orange"},
        {"label": "危机预警", "value": "1", "tone": "red"},
        {"label": "本周任务", "value": "5", "tone": "green"},
    ],
    "approval": {"name": "李同学", "type": "病假 · 2 天", "time": "今天 09:20", "status": "待审批"},
    "features": [
        {"icon": "users", "title": "班级概览", "desc": "班级成绩、评分与出勤一屏掌握"},
        {"icon": "leave", "title": "一键审批", "desc": "请假申请实时推送，手机上秒批"},
        {"icon": "target", "title": "学生画像", "desc": "成长档案与综合评分，随点随看"},
        {"icon": "shield", "title": "危机工单", "desc": "分级预警 + 处理闭环，留痕可追溯"},
    ],
    "chips": ["审批", "班级看板", "危机工单", "学生画像", "实时消息", "家长沟通"],
}

ADMIN = {
    "eyebrow": "管理端 · 全局掌控",
    "headline": "看得见的校园运行。",
    "sub": "组织、账号、知识库、舆情与系统状态，一个后台统一治理。",
    "kpis": [
        {"label": "在校学生", "value": "12,480", "delta": "+2.4%"},
        {"label": "教师账号", "value": "986", "delta": "+1.1%"},
        {"label": "今日对话", "value": "8,642", "delta": "+12.6%"},
    ],
    "features": [
        {"icon": "users", "title": "权限与组织", "desc": "角色、班级与账号全生命周期管理"},
        {"icon": "knowledge", "title": "知识库运营", "desc": "问答语料、官网通知与参考库沉淀"},
        {"icon": "monitor", "title": "系统监控", "desc": "服务健康、模型调用与异常告警"},
        {"icon": "chart", "title": "数据看板", "desc": "使用趋势、活跃分布与运营指标"},
    ],
    "chips": ["组织架构", "账号权限", "知识库", "通知公告", "反馈处理", "系统监控"],
}

TECH = {
    "headline": "看不见的底座，\n撑起每一次对话。",
    "sub": "前后端分离的全栈架构，为实时对话与校园数据提供稳定支撑。",
    "layers": [
        {"name": "体验层", "items": ["Vue 3", "TypeScript", "Element Plus", "ECharts"]},
        {"name": "服务层", "items": ["FastAPI", "SSE 流式", "WebSocket", "工具调用"]},
        {"name": "智能层", "items": ["通义千问", "知识库检索", "画像引擎", "危机识别"]},
        {"name": "数据层", "items": ["MySQL 8", "SQLAlchemy", "Alembic", "JWT 鉴权"]},
    ],
    "security": ["JWT 三角色隔离", "敏感配置加密存储", "操作留痕与审计"],
    "tech": ["Vue 3", "TypeScript", "FastAPI", "MySQL 8", "WebSocket", "SSE", "JWT", "通义千问"],
}

FEATURES_MATRIX = {
    "student": ["AI 对话助手", "成长档案", "课表查询", "成绩与 GPA", "成绩分析", "办事与请假", "心理关怀", "情绪记录"],
    "teacher": ["班级概览", "请假审批", "学生画像", "危机工单", "关怀记录", "问卷调研", "通知公告", "师生消息"],
    "admin": ["组织与班级", "账号与权限", "知识库", "通知公告", "课程安排", "危机监控", "反馈处理", "系统监控"],
}

SUMMARY = {
    "headline": "让校园服务，\n像对话一样自然。",
    "sub": "查得到、问得准、办得顺、陪得久。",
    "values": ["查得快", "问得准", "办得顺", "陪得久"],
    "cta": "现在，对它说一声「你好」。",
    "footer": "绵阳城市学院 · 智慧校园 AI 服务平台",
}

NOTES = {}
