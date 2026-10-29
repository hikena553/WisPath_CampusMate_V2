"""技能与兴趣标签推导。

标签不再由学生手填，而是由绵小城依据成长档案（成长记录、项目作品、课程成绩）
以及对话中沉淀的信息自动归纳，并且每一条标签都保留可回溯的来源证据，
前端点击标签即可查看「这条标签是从哪条档案推出来的」。
"""
import re

from sqlalchemy.orm import Session

from app.models.academic import Grade
from app.models.growth import GrowthRecord, StudentProject
from app.models.user import User
from app.services.scoring import TYPE_LABELS
from app.utils.enum_helpers import safe_enum_val

# 技能关键词规则：命中任意关键词即视为具备该技能
SKILL_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("编程开发", (
        "编程", "开发", "代码", "前端", "后端", "算法", "软件", "程序", "网站", "小程序",
        "系统实现", "数据库", "数据结构", "计算机网络", "操作系统", "github", "git", "linux",
        "java", "python", "vue", "react", "javascript", "typescript", "c++", "c#", "html",
        "css", "flask", "django", "spring", "fastapi", "api",
    )),
    ("人工智能", (
        "人工智能", "机器学习", "深度学习", "神经网络", "大模型", "智能体", "提示词", "prompt",
        "nlp", "自然语言处理", "计算机视觉", "ocr", "图像识别", "模型训练", "智能算法", "aigc",
    )),
    ("数据分析", (
        "数据分析", "数据挖掘", "数据可视化", "统计", "大数据", "爬虫", "报表", "bi",
        "excel", "指标", "看板", "sql",
    )),
    ("UI/UX设计", (
        "ui", "ux", "交互设计", "视觉设计", "界面设计", "原型", "figma", "sketch",
        "photoshop", "设计规范", "配色", "排版", "设计",
    )),
    ("项目管理", (
        "项目管理", "项目负责", "统筹", "组织协调", "策划", "排期", "进度管理", "管理团队",
        "负责人", "团队协作",
    )),
    ("学术写作", (
        "论文", "期刊", "综述", "文献", "写作", "撰稿", "投稿", "报告撰写", "学术",
    )),
    ("演讲表达", ("演讲", "汇报", "答辩", "宣讲", "讲解", "主持", "辩论", "分享会")),
    ("摄影摄像", ("摄影", "拍摄", "摄像", "构图", "照片")),
    ("视频剪辑", ("视频剪辑", "剪辑", "后期制作", "vlog", "动画制作", "短视频", "视频")),
    ("外语能力", ("英语", "翻译", "外语", "日语", "雅思", "托福", "四六级")),
    ("竞赛实战", ("竞赛", "比赛", "大赛", "挑战赛", "赛事", "获奖")),
    ("社会实践", ("社会实践", "志愿服务", "支教", "实习", "公益", "调研", "实践")),
    ("科研能力", ("科研", "研究", "实验", "课题", "专利", "创新项目", "成果")),
]

# 兴趣关键词规则
INTEREST_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("阅读", ("阅读", "读书", "书单", "文学", "小说", "散文")),
    ("运动健身", ("运动", "跑步", "篮球", "足球", "羽毛球", "健身", "游泳", "骑行", "乒乓球", "排球", "徒步")),
    ("音乐", ("音乐", "唱歌", "乐器", "吉他", "钢琴", "乐队", "合唱")),
    ("摄影", ("摄影", "拍照", "拍摄")),
    ("绘画", ("绘画", "插画", "手绘", "美术", "素描")),
    ("影视", ("电影", "影视", "追剧", "纪录片")),
    ("旅行", ("旅行", "旅游", "citywalk", "自驾")),
    ("美食", ("美食", "烹饪", "做饭", "烘焙")),
    ("游戏", ("游戏", "电竞")),
    ("舞蹈", ("舞蹈", "街舞")),
    ("公益", ("公益", "志愿", "义工", "慈善")),
    ("创业", ("创业", "商业模式")),
]

# 记录类型天然对应的技能标签（竞赛记录 → 竞赛实战等）
RECORD_TYPE_TAG: dict[str, str] = {
    "competition": "竞赛实战",
    "practice": "社会实践",
    "paper": "学术写作",
    "achievement": "科研能力",
}

MAX_SKILL_TAGS = 8
MAX_INTEREST_TAGS = 6
MAX_EVIDENCE_PER_TAG = 4

_ASCII_ONLY = re.compile(r"^[a-z0-9+#./ -]+$")


def _hit(text: str, keywords: tuple[str, ...]) -> bool:
    """中文关键词直接包含匹配；英文/符号关键词加词边界，避免 "ai" 命中 "said" 之类的误判。"""
    low = text.lower()
    for kw in keywords:
        if _ASCII_ONLY.match(kw):
            if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", low):
                return True
        elif kw in low:
            return True
    return False


def _record_text(r: GrowthRecord) -> str:
    fields = (
        r.title, r.description, r.honor_level, r.organizer, r.competition_level,
        r.practice_type, r.paper_type, r.paper_name, r.achievement_type, r.achievement_name,
    )
    return " ".join(str(f) for f in fields if f)


def _project_text(p: StudentProject) -> str:
    fields = (p.project_name, p.tech_stack, p.my_role, p.description)
    return " ".join(str(f) for f in fields if f)


def _clip(text: str | None, limit: int = 46) -> str:
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[:limit] + "…"


def _record_evidence(r: GrowthRecord, type_label: str, extra: str | None) -> dict:
    detail = _clip(r.description) or " / ".join(x for x in (type_label, extra) if x)
    return {
        "source": "record",
        "label": type_label,
        "title": r.title or type_label,
        "date": r.date.isoformat() if r.date else "",
        "detail": detail,
    }


def _project_evidence(p: StudentProject) -> dict:
    detail = _clip(p.tech_stack, 40) or _clip(p.my_role, 40) or ("团队项目" if p.is_team else "个人项目")
    return {
        "source": "project",
        "label": "项目",
        "title": p.project_name,
        "date": p.start_date.isoformat() if p.start_date else "",
        "detail": detail,
    }


def _grade_evidence(g: Grade) -> dict:
    detail = f"{g.score} 分" if getattr(g, "score", None) is not None else ""
    return {
        "source": "course",
        "label": "课程",
        "title": g.course_name or "课程",
        "date": g.semester or "",
        "detail": detail,
    }


def _add(tags: dict, name: str, kind: str, evidence: dict) -> None:
    key = (kind, name)
    item = tags.setdefault(key, {"name": name, "kind": kind, "evidence": []})
    ident = (evidence["source"], evidence["title"], evidence["date"])
    if any((e["source"], e["title"], e["date"]) == ident for e in item["evidence"]):
        return
    item["evidence"].append(evidence)


def _finalize(tags: dict, kind: str, limit: int) -> list[dict]:
    items = [t for t in tags.values() if t["kind"] == kind]
    for t in items:
        t["evidence"].sort(key=lambda e: e["date"], reverse=True)
        t["evidence"] = t["evidence"][:MAX_EVIDENCE_PER_TAG]
    # 证据越多说明越「有据可查」，排在前面
    items.sort(key=lambda t: (-len(t["evidence"]), t["name"]))
    return items[:limit]


def _merge_stored(user: User, tags: dict, kind: str) -> None:
    """把对话里已沉淀的技能/兴趣并入标签，并以对话上下文作为来源证据。"""
    stored = user.skills_json or {}
    if kind == "skill":
        for s in stored.get("skills") or []:
            name = s.get("name") if isinstance(s, dict) else str(s)
            context = s.get("context") if isinstance(s, dict) else ""
            if not name:
                continue
            _add(tags, name.strip(), "skill", {
                "source": "chat",
                "label": "对话",
                "title": "与绵小城的对话",
                "date": "",
                "detail": _clip(context) or "绵小城在对话中识别到你提到过这一技能",
            })
    else:
        for name in stored.get("interests") or []:
            if not name:
                continue
            _add(tags, str(name).strip(), "interest", {
                "source": "chat",
                "label": "对话",
                "title": "与绵小城的对话",
                "date": "",
                "detail": "绵小城在对话中识别到你提到过这一兴趣",
            })


def derive_growth_tags(
    db: Session,
    user: User,
    records: list[GrowthRecord] | None = None,
    grades: list[Grade] | None = None,
) -> dict[str, list[dict]]:
    """基于成长档案推导技能与兴趣标签（含来源证据）。"""
    if records is None:
        records = db.query(GrowthRecord).filter(GrowthRecord.student_id == user.id).all()
    if grades is None:
        grades = db.query(Grade).filter(Grade.student_id == user.id).all()
    projects = db.query(StudentProject).filter(StudentProject.student_id == user.id).all()

    tags: dict = {}

    for r in records:
        text = _record_text(r)
        type_key = safe_enum_val(r.type)
        type_label = TYPE_LABELS.get(type_key, type_key)
        extra = r.competition_level or r.honor_level or r.practice_type or r.paper_type or r.achievement_type
        ev = _record_evidence(r, type_label, extra)
        for name, keywords in SKILL_RULES:
            if _hit(text, keywords):
                _add(tags, name, "skill", ev)
        for name, keywords in INTEREST_RULES:
            if _hit(text, keywords):
                _add(tags, name, "interest", ev)
        type_tag = RECORD_TYPE_TAG.get(type_key)
        if type_tag:
            _add(tags, type_tag, "skill", ev)

    for p in projects:
        text = _project_text(p)
        ev = _project_evidence(p)
        for name, keywords in SKILL_RULES:
            if _hit(text, keywords):
                _add(tags, name, "skill", ev)
        for name, keywords in INTEREST_RULES:
            if _hit(text, keywords):
                _add(tags, name, "interest", ev)

    for g in grades:
        text = g.course_name or ""
        ev = _grade_evidence(g)
        for name, keywords in SKILL_RULES:
            if _hit(text, keywords):
                _add(tags, name, "skill", ev)

    _merge_stored(user, tags, "skill")
    _merge_stored(user, tags, "interest")

    return {
        "skills": _finalize(tags, "skill", MAX_SKILL_TAGS),
        "interests": _finalize(tags, "interest", MAX_INTEREST_TAGS),
    }
