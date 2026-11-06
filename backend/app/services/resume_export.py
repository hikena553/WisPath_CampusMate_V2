"""简历导出服务：档案快照 → 岗位匹配 → 多套模板 → DOCX / PDF。

三条设计取舍，先写在这里，改代码前先读：

1. **匹配度是可解释的规则引擎**，不是大模型打分。
   四个维度（技能命中 / 项目支撑 / 学业表现 / 证书荣誉）加权，用户看到 78 分
   能立刻知道差在哪一项。大模型只负责润色「自我评价」，且失败静默回落——
   导出绝不能因为模型超时而失败。
2. **正文全部来自真实档案**（项目、证书、成绩、实践），模板只决定「怎么排」。
   所以同一份档案换模板，内容不变、版式变，不会出现两个模板说法不一致。
3. **字体是硬要求**：DOCX 显式写 ``w:eastAsia``（只设 ``font.name`` 的话 Word 会把
   中文回退成等线/雅黑），正文宋体、标题黑体；PDF 嵌入系统宋体/黑体，
   并用 ``wrapmode="CHAR"`` 断行——中文没有空格，默认按空格断行会整行溢出。
"""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.academic import ClassGroup, Grade, Major
from app.models.certificate import Certificate
from app.models.growth import GrowthRecord, StudentProject
from app.models.user import User

# ============================================================
# 一、岗位知识库
# 关键词同时用于「匹配打分」和「简历技能段落排序」；certs 只用于提示还缺什么证。
# ============================================================

INDUSTRIES: dict[str, dict] = {
    "internet": {
        "label": "互联网 / 软件",
        "jobs": [
            {"key": "backend", "label": "后端开发工程师",
             "keywords": ["Java", "Python", "Go", "MySQL", "Redis", "微服务", "Spring", "FastAPI",
                          "Django", "数据库", "接口", "并发", "消息队列", "Linux", "Docker"],
             "certs": ["软考中级", "计算机等级考试"]},
            {"key": "frontend", "label": "前端开发工程师",
             "keywords": ["Vue", "React", "TypeScript", "JavaScript", "HTML", "CSS", "小程序",
                          "Node", "Webpack", "组件", "响应式", "Element", "ECharts"],
             "certs": ["计算机等级考试", "前端相关认证"]},
            {"key": "mobile", "label": "客户端开发工程师",
             "keywords": ["Android", "iOS", "Flutter", "Kotlin", "Swift", "小程序", "React Native", "性能优化"],
             "certs": ["计算机等级考试"]},
            {"key": "qa", "label": "测试 / 运维工程师",
             "keywords": ["Linux", "Docker", "自动化", "脚本", "测试", "CI", "监控", "Shell", "K8s"],
             "certs": ["软考中级", "云计算认证"]},
            {"key": "pm", "label": "产品经理",
             "keywords": ["需求", "原型", "Figma", "Axure", "用户研究", "数据分析", "项目管理",
                          "文档", "沟通", "竞品", "指标"],
             "certs": ["产品相关认证"]},
        ],
    },
    "ai": {
        "label": "人工智能 / 算法",
        "jobs": [
            {"key": "algo", "label": "算法工程师",
             "keywords": ["Python", "PyTorch", "TensorFlow", "机器学习", "深度学习", "NLP", "CV",
                          "推荐", "数学", "竞赛", "论文", "模型", "数据"],
             "certs": ["数学建模竞赛", "Kaggle/天池竞赛"]},
            {"key": "data", "label": "数据分析师",
             "keywords": ["SQL", "Python", "Excel", "统计", "可视化", "Tableau", "数据清洗",
                          "A/B", "指标", "报告"],
             "certs": ["数据分析相关认证", "CDA"]},
            {"key": "ai_pm", "label": "AI 产品 / 解决方案",
             "keywords": ["需求", "Prompt", "LLM", "原型", "数据", "方案", "行业", "沟通"],
             "certs": ["AI 相关认证"]},
        ],
    },
    "finance": {
        "label": "金融 / 银行",
        "jobs": [
            {"key": "bank", "label": "银行管培生",
             "keywords": ["金融", "会计", "经济", "风控", "Excel", "证书", "沟通", "实习",
                          "英语", "客户", "营销"],
             "certs": ["银行从业", "证券从业", "基金从业"]},
            {"key": "quant", "label": "量化 / 投研",
             "keywords": ["Python", "数学", "统计", "金融", "建模", "回测", "数据", "策略", "研报"],
             "certs": ["CFA", "FRM", "证券从业"]},
            {"key": "audit", "label": "审计 / 财务",
             "keywords": ["会计", "审计", "CPA", "Excel", "报表", "税务", "财务", "凭证"],
             "certs": ["初级会计", "CPA"]},
        ],
    },
    "edu": {
        "label": "教育 / 培训",
        "jobs": [
            {"key": "teacher", "label": "中小学教师",
             "keywords": ["教师资格", "教学", "实习", "班级管理", "表达", "课件", "教研",
                          "学科", "公开课", "班主任"],
             "certs": ["教师资格证", "普通话等级"]},
            {"key": "curriculum", "label": "课程研发 / 教研",
             "keywords": ["课程", "教研", "内容", "教学设计", "教案", "评估", "教研活动"],
             "certs": ["教师资格证"]},
        ],
    },
    "hardware": {
        "label": "硬件 / 智能制造",
        "jobs": [
            {"key": "embedded", "label": "嵌入式开发工程师",
             "keywords": ["C", "C++", "单片机", "STM32", "电路", "嵌入式", "Linux", "驱动",
                          "串口", "传感器"],
             "certs": ["电子设计竞赛", "计算机等级考试"]},
            {"key": "mech", "label": "机械 / 结构工程师",
             "keywords": ["CAD", "SolidWorks", "结构", "工艺", "仿真", "材料", "图纸", "建模"],
             "certs": ["CAD 认证", "机械设计竞赛"]},
        ],
    },
    "design": {
        "label": "设计 / 传媒",
        "jobs": [
            {"key": "ui", "label": "UI / UX 设计师",
             "keywords": ["Figma", "Sketch", "PS", "交互", "作品集", "视觉", "排版", "原型",
                          "设计规范", "用户"],
             "certs": ["设计类竞赛"]},
            {"key": "media", "label": "新媒体运营",
             "keywords": ["文案", "剪辑", "短视频", "公众号", "数据", "活动", "排版", "选题",
                          "社群", "增长"],
             "certs": ["新媒体相关认证"]},
        ],
    },
    "gov": {
        "label": "公共服务 / 事业单位",
        "jobs": [
            {"key": "civil", "label": "公务员 / 选调生",
             "keywords": ["申论", "行测", "公文", "政策", "党员", "学生干部", "志愿", "基层", "调研"],
             "certs": ["学生干部经历", "志愿服务证明"]},
            {"key": "soe", "label": "国企技术岗",
             "keywords": ["专业", "证书", "项目", "英语", "政治面貌", "党员", "实习", "规范"],
             "certs": ["计算机等级考试", "英语四六级"]},
        ],
    },
    "medical": {
        "label": "医疗 / 健康",
        "jobs": [
            {"key": "medtech", "label": "医疗技术 / 器械",
             "keywords": ["医学", "临床", "仪器", "数据", "检验", "影像", "规范", "实验"],
             "certs": ["医学相关资格"]},
        ],
    },
    "other": {
        "label": "暂不确定 / 综合岗",
        "jobs": [
            {"key": "general", "label": "综合管理培训生",
             "keywords": ["沟通", "团队", "项目", "实习", "组织", "协调", "学习能力", "写作",
                          "Excel", "PPT"],
             "certs": ["英语四六级", "计算机等级考试"]},
        ],
    },
}

JOB_TYPE_OPTIONS = ["校招实习", "校招全职", "社会招聘", "兼职 / 日常实习"]


# ============================================================
# 二、模板
# ============================================================

TEMPLATES: list[dict] = [
    {
        "key": "classic", "name": "经典单栏", "tag": "国企 · 考公 · 保研",
        "desc": "黑白细线，信息规整，机器筛选与人工翻阅都稳",
        "accent": "1F2328", "accent_soft": "F2F4F3",
        "order": ["edu", "skill", "project", "cert", "practice", "self"],
        "compact": False,
    },
    {
        "key": "accent", "name": "青绿强调", "tag": "互联网 · 技术岗",
        "desc": "左侧色块抬头 + 强调色小节，技能提到项目前面",
        "accent": "0F7A58", "accent_soft": "EDF7F2",
        "order": ["skill", "project", "edu", "cert", "practice", "self"],
        "compact": False,
    },
    {
        "key": "compact", "name": "紧凑双栏", "tag": "校招海投",
        "desc": "字号收紧、技能多列、证书并排，一页塞进最多信息",
        "accent": "1D4ED8", "accent_soft": "EEF2FD",
        "order": ["edu", "skill", "project", "cert", "practice", "self"],
        "compact": True,
    },
]

TEMPLATE_MAP = {t["key"]: t for t in TEMPLATES}

# 证书级别 → 分量（满分 100 的证书维度里每张加的分）
CERT_LEVEL_WEIGHT = {
    "international": 26, "national": 22, "province": 17,
    "city": 11, "school": 6,
}
CERT_LEVEL_LABEL = {
    "international": "国际级", "national": "国家级", "province": "省级",
    "city": "市级", "school": "校级",
}

DIM_WEIGHTS = {"skill": 0.35, "project": 0.30, "academic": 0.20, "cert": 0.15}
DIM_LABELS = {"skill": "专业技能", "project": "项目作品", "academic": "学业表现", "cert": "证书荣誉"}


# ============================================================
# 三、档案快照
# ============================================================

def _split_tokens(raw: str | None) -> list[str]:
    return [t.strip() for t in re.split(r"[,，、;；/|]", raw or "") if t.strip()]


def _level_of(score: float) -> str:
    if score >= 80:
        return "高"
    if score >= 65:
        return "中上"
    if score >= 50:
        return "中等"
    return "偏低"


def collect_profile(db: Session, user: User) -> dict:
    """把散落在各表的档案收成一份扁平快照（一次查完，后续纯内存计算）。"""
    projects: list[StudentProject] = (
        db.query(StudentProject)
        .filter(StudentProject.student_id == user.id)
        .order_by(StudentProject.start_date.desc())
        .all()
    )
    certs: list[Certificate] = (
        db.query(Certificate)
        .filter(Certificate.student_id == user.id)
        .order_by(Certificate.date.desc())
        .all()
    )
    grades: list[Grade] = db.query(Grade).filter(Grade.student_id == user.id).all()
    records = (
        db.query(GrowthRecord)
        .filter(GrowthRecord.student_id == user.id)
        .order_by(GrowthRecord.date.desc())
        .limit(12)
        .all()
    )

    major_name = None
    grade_year = None
    if user.class_group_id:
        grp = db.query(ClassGroup).filter(ClassGroup.id == user.class_group_id).first()
        if grp:
            grade_year = grp.grade
            major = db.query(Major).filter(Major.id == grp.major_id).first()
            major_name = major.name if major else None

    # 成绩
    grade_count = len(grades)
    avg_score = round(sum(g.score for g in grades) / grade_count, 1) if grade_count else 0.0
    credits = round(sum(g.credit for g in grades), 1) if grade_count else 0.0
    gpa = round(sum(g.gpa * g.credit for g in grades) / max(credits, 0.01), 2) if grade_count else 0.0
    pass_rate = round(sum(1 for g in grades if g.score >= 60) / grade_count * 100, 1) if grade_count else 0.0
    top_courses = [
        {"name": g.course_name, "score": g.score, "credit": g.credit}
        for g in sorted(grades, key=lambda x: x.score, reverse=True)[:8]
    ]

    # 技能：学生手填技能 + 技术栈分词 + 高分课程名（课程名也能证明技能面）
    skills: list[str] = []
    raw_skills = (user.skills_json or {}).get("skills") if isinstance(user.skills_json, dict) else None
    if isinstance(raw_skills, list):
        # skills_json 里的元素可能是 {'name': 'python', 'level': 3} 而不是纯字符串，
        # 直接 str(dict) 会得到 "{'name': 'python'}" 这种脏文本，必须先取 name
        for item in raw_skills:
            if isinstance(item, dict):
                label = str(item.get("name") or item.get("label") or "").strip()
            else:
                label = str(item).strip()
            if label:
                skills.append(label)
    for p in projects:
        skills.extend(_split_tokens(p.tech_stack))
    for c in top_courses[:4]:
        # 课程名过长（如「毛泽东思想和中国特色社会主义理论体系概论」）不适合当技能标签：
        # 挤进三列技能栏会压到右列，且教育背景的「主修课程」已完整列出，这里只取短名
        if len(str(c["name"]).strip()) <= 12:
            skills.append(c["name"])
    seen: set[str] = set()
    uniq_skills = [s for s in skills if not (s.lower() in seen or seen.add(s.lower()))]

    return {
        "user": user,
        "name": user.name or user.username or "",
        "student_no": user.username or "",
        "gender": user.gender or "",
        "phone": user.phone or "",
        "political": user.political_status or "",
        "hometown": user.hometown or "",
        "college": user.college or "",
        "major": major_name or "",
        "class_name": user.class_name or "",
        "grade_year": grade_year,
        "signature": user.signature or "",
        "projects": projects,
        "certs": certs,
        "records": records,
        "skills": uniq_skills[:24],
        "grade_count": grade_count,
        "avg_score": avg_score,
        "gpa": gpa,
        "credits": credits,
        "pass_rate": pass_rate,
        "top_courses": top_courses,
    }


def _job_index() -> list[dict]:
    out = []
    for ind_key, ind in INDUSTRIES.items():
        for job in ind["jobs"]:
            out.append({**job, "industry": ind_key, "industry_label": ind["label"]})
    return out


def _custom_job_def(custom_job: str | None, industry: str | None) -> dict:
    """用户手动输入的岗位：库里没有现成定义，就按输入文本合成一个。

    关键词 = 输入里的分词 + 岗位名本身 + 通用软素质词，保证匹配度不会因为
    词库没覆盖而给出离谱的低分；certs 留空（没有可对照的证书清单）。
    """
    label = (custom_job or "").strip()[:20] or "自定义岗位"
    tokens = _split_tokens(label)
    keywords = list(dict.fromkeys(tokens + [label] + ["沟通", "团队协作", "学习能力", "Office", "英语"]))
    ind = INDUSTRIES.get(industry or "", {})
    return {
        "key": "custom",
        "label": label,
        "industry": industry or "",
        "industry_label": ind.get("label", "自定义方向"),
        "keywords": keywords,
        "certs": [],
    }


def find_job(industry: str | None, job_key: str | None, custom_job: str | None = None) -> dict:
    """定位岗位定义：自定义岗位优先合成，其余按 job_key 全局找，找不到退回综合岗。"""
    if job_key == "custom":
        return _custom_job_def(custom_job, industry)
    jobs = _job_index()
    if job_key:
        for j in jobs:
            if j["key"] == job_key and (not industry or j["industry"] == industry):
                return j
        for j in jobs:
            if j["key"] == job_key:
                return j
    if industry and industry in INDUSTRIES:
        return next(j for j in jobs if j["industry"] == industry)
    return next(j for j in jobs if j["key"] == "general")


# ============================================================
# 四、匹配度
# ============================================================

def _corpus(profile: dict) -> str:
    parts: list[str] = list(profile["skills"])
    for p in profile["projects"]:
        parts += [p.project_name or "", p.my_role or "", p.tech_stack or "", p.description or ""]
    for c in profile["certs"]:
        parts += [c.title or "", c.competition_name or "", c.description or ""]
    for g in profile["top_courses"]:
        parts.append(g["name"])
    for r in profile["records"]:
        parts += [r.title or "", r.description or ""]
    parts.append(profile["major"])
    return " ".join(parts).lower()


def _score_skill(profile: dict, job: dict, corpus: str) -> tuple[float, list[str], list[str]]:
    kws = job["keywords"]
    hits = [k for k in kws if k.lower() in corpus]
    gaps = [k for k in kws if k.lower() not in corpus]
    ratio = len(hits) / len(kws) if kws else 0
    # 命中率直接映射，但给一个下限：技能全空时不是 0 分，避免总分被拉成个位数
    score = 12 + ratio * 88 if hits else 10
    return round(min(100, score), 1), hits, gaps


def _score_project(profile: dict, job: dict) -> tuple[float, str]:
    projects = profile["projects"]
    if not projects:
        return 20.0, "还没有项目经历，这是简历最大的空洞"

    kws = [k.lower() for k in job["keywords"]]
    best = 0.0
    best_name = ""
    best_hits = 0
    for p in projects:
        blob = " ".join([p.project_name or "", p.my_role or "", p.tech_stack or "", p.description or ""]).lower()
        hits = sum(1 for k in kws if k in blob)
        imgs = _project_images(p)
        score = 42.0
        score += min(20, (len(projects) - 1) * 8)          # 数量：多一个项目 +8，封顶 20
        score += 12 if len(p.description or "") >= 80 else 6 if p.description else 0
        score += 8 if len(imgs) >= 2 else 4 if imgs else 0   # 有图的项目可信度高
        score += 6 if p.project_link else 0
        score += 6 if p.my_role else 0
        score += min(14, hits * 3.5)                        # 与岗位的相关度
        score = min(100, score)
        if score > best:
            best, best_name, best_hits = score, p.project_name, hits

    if best_hits:
        note = f"「{best_name}」与岗位技术栈有 {best_hits} 处交集"
    else:
        note = f"「{best_name}」描述里缺少岗位关键词，面试官看不出相关性"
    return round(best, 1), note


def _score_academic(profile: dict) -> tuple[float, str]:
    if not profile["grade_count"]:
        return 55.0, "没有成绩数据，按中位计分"
    avg = profile["avg_score"]
    if avg >= 90:
        base = 96
    elif avg >= 85:
        base = 88
    elif avg >= 80:
        base = 78
    elif avg >= 75:
        base = 66
    elif avg >= 70:
        base = 55
    elif avg >= 60:
        base = 42
    else:
        base = 30
    if profile["pass_rate"] >= 99:
        base += 3
    note = f"均分 {avg}、绩点 {profile['gpa']}、{profile['grade_count']} 门课程"
    return round(min(100, base), 1), note


def _score_cert(profile: dict) -> tuple[float, str]:
    certs = profile["certs"]
    if not certs:
        return 25.0, "还没有证书荣誉"
    total = 30.0
    for c in certs:
        total += CERT_LEVEL_WEIGHT.get(_enum_value(c.award_level), 8)
    if any(_enum_value(c.status) == "approved" for c in certs):
        total += 6
    return round(min(100, total), 1), f"{len(certs)} 项证书荣誉"


def _enum_value(v) -> str:
    """枚举字段统一取字符串值：ORM 存的可能是 AwardLevel.NATIONAL，也可能是 'national'。"""
    if v is None:
        return ""
    return getattr(v, "value", str(v)).strip()


def _project_images(p: StudentProject) -> list[str]:
    try:
        data = json.loads(p.images) if p.images else []
        return [x for x in data if x] if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def evaluate(profile: dict, industry: str | None, job_key: str | None, custom_job: str | None = None) -> dict:
    """四维加权打分 + 可执行建议。返回结构直接给前端渲染，不再二次加工。"""
    job = find_job(industry, job_key, custom_job)
    corpus = _corpus(profile)

    skill_score, hits, gaps = _score_skill(profile, job, corpus)
    project_score, project_note = _score_project(profile, job)
    academic_score, academic_note = _score_academic(profile)
    cert_score, cert_note = _score_cert(profile)

    dims = [
        {"key": "skill", "label": DIM_LABELS["skill"], "score": skill_score,
         "weight": DIM_WEIGHTS["skill"],
         "note": f"命中 {len(hits)}/{len(job['keywords'])} 个岗位关键词"},
        {"key": "project", "label": DIM_LABELS["project"], "score": project_score,
         "weight": DIM_WEIGHTS["project"], "note": project_note},
        {"key": "academic", "label": DIM_LABELS["academic"], "score": academic_score,
         "weight": DIM_WEIGHTS["academic"], "note": academic_note},
        {"key": "cert", "label": DIM_LABELS["cert"], "score": cert_score,
         "weight": DIM_WEIGHTS["cert"], "note": cert_note},
    ]
    total = round(sum(d["score"] * d["weight"] for d in dims), 1)

    # 建议投递：同行业全部岗位 + 综合岗兜底，按分数排序
    pool = [j for j in _job_index() if j["industry"] == job["industry"]]
    if job["industry"] != "other":
        pool.append(next(j for j in _job_index() if j["key"] == "general"))
    suggest = []
    for j in pool:
        s, h, _ = _score_skill(profile, j, corpus)
        p_score, _ = _score_project(profile, j)
        est = round(s * DIM_WEIGHTS["skill"] + p_score * DIM_WEIGHTS["project"]
                    + academic_score * DIM_WEIGHTS["academic"] + cert_score * DIM_WEIGHTS["cert"], 1)
        suggest.append({
            "job_key": j["key"], "label": j["label"], "score": est,
            "why": ("命中 " + "、".join(h[:4])) if h else "关键词覆盖较少，建议先补项目",
        })
    suggest.sort(key=lambda x: x["score"], reverse=True)

    # 缺口按「岗位关键词 - 已命中」取前 5，去重保序
    gap_list = gaps[:5]
    tips: list[str] = []
    if gap_list:
        tips.append(f"补齐这几个关键词能直接抬分：{'、'.join(gap_list)}（写进项目描述或技能栏）")
    low = min(dims, key=lambda d: d["score"])
    if low["score"] < 60:
        tips.append(f"最拖分的是「{low['label']}」：{low['note']}")
    if not profile["projects"]:
        tips.append("至少补 1 个项目，并上传 2 张以上截图——有图的项目在初筛里可信度高得多")
    elif max((len(_project_images(p)) for p in profile["projects"]), default=0) < 2:
        tips.append("项目还缺过程截图，建议补 2~3 张（主页/关键界面/数据结果）")
    if not profile["certs"]:
        tips.append("证书栏是空的：竞赛、软考、四六级都能算，先把已有的录进来")

    return {
        "job": {"key": job["key"], "label": job["label"],
                "industry": job["industry"], "industry_label": job["industry_label"]},
        "score": total,
        "level": _level_of(total),
        "dims": dims,
        "hits": hits,
        "gaps": gap_list,
        "suggest": suggest[:3],
        "tips": tips,
    }


# ============================================================
# 五、简历内容组装（与模板无关）
# ============================================================

@dataclass
class Entry:
    """一条简历条目。head 加粗、meta 灰小字、lines 前面补圆点、chips 是技能标签。"""
    head: str = ""
    meta: str = ""
    lines: list[str] = field(default_factory=list)
    chips: list[str] = field(default_factory=list)
    tail: str = ""


@dataclass
class Section:
    key: str
    title: str
    entries: list[Entry]


def _ym(d: date | None) -> str:
    return f"{d.year}.{d.month:02d}" if d else ""


def _clean_sentences(text: str | None, limit: int = 3) -> list[str]:
    """把项目描述拆成 2~3 条陈述句：中文按句号/分号切，英文保留句点后的空格判定。"""
    if not text:
        return []
    raw = re.split(r"[。；;\n]+", text.strip())
    out = [s.strip(" ，,、") for s in raw if s.strip(" ，,、")]
    if len(out) <= 1:
        # 没有标点的一句话，按逗号切开，避免一整段压成一行
        out = [s.strip() for s in re.split(r"[，,]", text.strip()) if s.strip()]
    return out[:limit]


def _objective_text(profile: dict, target: dict, match: dict) -> str:
    """自我评价：由档案事实拼出来的句子，不吹牛、不出现档案里没有的东西。"""
    bits: list[str] = []
    edu = "".join(x for x in [profile["college"], profile["major"]] if x)
    if edu:
        yr = f"{profile['grade_year']}级" if profile["grade_year"] else ""
        bits.append(f"{edu}{yr}在读" if yr else f"{edu}在读")
    if profile["skills"]:
        bits.append(f"熟悉 {'、'.join(profile['skills'][:5])}")
    if profile["projects"]:
        best = max(profile["projects"], key=lambda p: len(p.description or ""))
        role = f"作为{best.my_role}" if best.my_role else "参与"
        bits.append(f"{role}完成「{best.project_name}」等 {len(profile['projects'])} 个项目")
    if profile["certs"]:
        top = profile["certs"][0]
        lv = CERT_LEVEL_LABEL.get(_enum_value(top.award_level), "")
        bits.append(f"获{lv}{top.title}" if lv else f"获{top.title}")
    if profile["grade_count"] and profile["avg_score"] >= 80:
        bits.append(f"学业均分 {profile['avg_score']}")

    head = "，".join(bits) + "。" if bits else ""
    goal = f"求职意向为{target['industry_label']}方向的「{target['label']}」"
    tail = f"{goal}，与该岗位的档案匹配度为 {match['score']} 分（{match['level']}）。"
    if match["gaps"]:
        tail += f"目前正在补齐 {'、'.join(match['gaps'][:3])} 等能力。"
    else:
        tail += "技能面与岗位要求基本对齐，可快速上手。"
    return head + tail


def build_sections(profile: dict, target: dict, match: dict, template: dict) -> list[Section]:
    user = profile["user"]
    sections: dict[str, Section] = {}

    # 教育背景
    edu_entries: list[Entry] = []
    school_bits = [profile["college"], profile["major"]]
    head = " · ".join([b for b in school_bits if b]) or "在读"
    meta_bits = []
    cls = profile["class_name"] or ""
    if profile["grade_year"] and str(profile["grade_year"]) not in cls:
        # 班级名本身通常已含「2023级」，再补一遍会变成「2023级 | 2023级xx班」
        meta_bits.append(f"{profile['grade_year']}级")
    if cls:
        meta_bits.append(cls)
    if profile["grade_count"]:
        meta_bits.append(f"均分 {profile['avg_score']} / 绩点 {profile['gpa']}")
    if profile["credits"]:
        meta_bits.append(f"已修 {profile['credits']} 学分")
    lines = []
    if profile["top_courses"]:
        lines.append("主修课程：" + "、".join(
            f"{c['name']} {int(c['score'])}" for c in profile["top_courses"][:4]))
    edu_entries.append(Entry(head=head, meta="｜".join(meta_bits), lines=lines))
    sections["edu"] = Section("edu", "教育背景", edu_entries)

    # 专业技能：命中岗位关键词的排前面，让 HR 三秒内看到对口的
    kws = [k.lower() for k in target["keywords"]]
    ordered = sorted(profile["skills"], key=lambda s: 0 if any(k in s.lower() or s.lower() in k for k in kws) else 1)
    skill_entries = [Entry(chips=ordered[:16])] if ordered else [Entry(tail="还没有录入技能，建议先在资料里补充")]
    sections["skill"] = Section("skill", "专业技能", skill_entries)

    # 项目经历
    proj_entries: list[Entry] = []
    for p in profile["projects"][:4]:
        period = f"{_ym(p.start_date)} – {_ym(p.end_date) if p.end_date else '至今'}"
        meta = "｜".join(x for x in [period, p.my_role or "", "团队项目" if p.is_team else "个人项目"] if x)
        lines = _clean_sentences(p.description, limit=3)
        if p.tech_stack:
            lines.append("技术栈：" + "、".join(_split_tokens(p.tech_stack)))
        if p.project_link:
            lines.append(f"项目链接：{p.project_link}")
        proj_entries.append(Entry(head=p.project_name or "", meta=meta, lines=lines))
    sections["project"] = Section("project", "项目经历", proj_entries)

    # 荣誉证书
    cert_entries = [
        Entry(head=c.title or "",
              meta="｜".join(x for x in [c.competition_name or "",
                                        CERT_LEVEL_LABEL.get(_enum_value(c.award_level), ""),
                                        str(c.date or "")[:7]] if x))
        for c in profile["certs"][:8]
    ]
    sections["cert"] = Section("cert", "荣誉证书", cert_entries)

    # 校园经历与实践（成长记录里挑非项目的）
    type_label = {"honor": "荣誉", "competition": "竞赛", "practice": "实践",
                  "paper": "论文", "achievement": "成果"}
    practice_entries = [
        Entry(head=r.title or "",
              meta="｜".join(x for x in [type_label.get(_enum_value(r.type), "经历"), str(r.date or "")[:7]] if x),
              lines=_clean_sentences(r.description, limit=1))
        for r in profile["records"][:5]
    ]
    sections["practice"] = Section("practice", "校园经历与实践", practice_entries)

    # 自我评价
    sections["self"] = Section("self", "自我评价",
                              [Entry(lines=[_objective_text(profile, target, match)])])

    # 空段落不占位（否则导出后每节都有一条空标题）
    ordered = [sections[k] for k in template["order"] if k in sections]
    result = []
    for s in ordered:
        if s.entries and any(e.head or e.lines or e.chips or e.tail for e in s.entries):
            result.append(s)
    return result


def build_header(profile: dict, target: dict, meta: dict | None = None) -> dict:
    contact = [
        profile["phone"],
        profile["student_no"] and f"学号 {profile['student_no']}",
        user_political(profile),
    ]
    return {
        "name": profile["name"],
        "contact": [c for c in contact if c],
        "target_line": " · ".join(x for x in [
            f"求职意向：{target['label']}",
            target["industry_label"],
            (meta or {}).get("job_type", ""),
            (meta or {}).get("city", ""),
        ] if x),
        "match": (meta or {}).get("match_score"),
    }


def user_political(profile: dict) -> str:
    bits = [profile["gender"], profile["political"]]
    return "｜".join(b for b in bits if b)


# ============================================================
# 六、DOCX 渲染
# ============================================================

def _set_font(run, *, ea: str, ascii_font: str = "Times New Roman", size: float | None = None,
              bold: bool | None = None, color: str | None = None) -> None:
    """同时写 ascii/hAnsi/eastAsia：只设 font.name 时 Word 中文会回退到等线。"""
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    run.font.name = ascii_font
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color.replace("#", "").upper())
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        from docx.oxml import OxmlElement
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), ea)
    rFonts.set(qn("w:cs"), ascii_font)


def _shade(paragraph, fill: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill.replace("#", "").upper())
    pPr.append(shd)


def _bottom_border(paragraph, color: str, sz: int = 6) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(sz))
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), color.replace("#", "").upper())
    pBdr.append(bottom)
    pPr.append(pBdr)


def _left_border(paragraph, color: str, sz: int = 18) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(sz))
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), color.replace("#", "").upper())
    pBdr.append(left)
    pPr.append(pBdr)


def render_docx(header: dict, sections: list[Section], template: dict, photo: bytes | None = None) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    compact = template["compact"]
    accent = template["accent"]
    body_ea, title_ea = "宋体", "黑体"
    base = 9.0 if compact else 10.0

    doc = Document()

    # 正文样式：中文宋体、西文 Times New Roman，行距与段后统一在这里定
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(base)
    n_rPr = normal.element.get_or_add_rPr()
    n_fonts = n_rPr.find(qn("w:rFonts"))
    if n_fonts is None:
        from docx.oxml import OxmlElement
        n_fonts = OxmlElement("w:rFonts")
        n_rPr.append(n_fonts)
    n_fonts.set(qn("w:ascii"), "Times New Roman")
    n_fonts.set(qn("w:hAnsi"), "Times New Roman")
    n_fonts.set(qn("w:eastAsia"), body_ea)
    normal.paragraph_format.line_spacing = 1.08 if compact else 1.18
    normal.paragraph_format.space_after = Pt(0)

    # 页面：A4，上下 1.7/1.5cm，左右 2.0/1.7cm（紧凑模板再收 0.3）
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    side = 1.7 if compact else 2.0
    sec.left_margin = sec.right_margin = Cm(side)
    sec.top_margin = Cm(1.6)
    sec.bottom_margin = Cm(1.5)
    text_width = Cm(21.0 - side * 2)

    # ── 抬头 ──
    # 有证件照时抬头顶进左格、照片放右格（一寸照比例），没有就维持纯段落排版
    def _emit_header(container, is_cell: bool = False) -> None:
        p = container.paragraphs[0] if is_cell else container.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(header["name"])
        _set_font(r, ea=title_ea, ascii_font="Arial", size=19 if not compact else 17, bold=True, color=accent)

        if header["contact"]:
            p = container.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run("　|　".join(header["contact"]))
            _set_font(r, ea=body_ea, size=base - 1, color="4A5560")

        p = container.add_paragraph()
        p.paragraph_format.space_after = Pt(6 if compact else 8)
        r = p.add_run(header["target_line"])
        _set_font(r, ea=title_ea, ascii_font="Arial", size=base - 0.5, bold=True, color="2B333B")
        if template["key"] == "accent":
            _left_border(p, accent, sz=14)
            p.paragraph_format.left_indent = Cm(0.2)
        elif template["key"] == "classic":
            _bottom_border(p, "C9D0D6", sz=8)

    if photo:
        text_w = Cm(21.0 - side * 2 - 2.6)
        head_table = doc.add_table(rows=1, cols=2)
        head_table.autofit = False
        cell_l, cell_r = head_table.rows[0].cells
        cell_l.width = text_w
        cell_r.width = Cm(2.6)
        _emit_header(cell_l, is_cell=True)
        rp = cell_r.paragraphs[0]
        rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        # 只给高度：上传前已按一寸照比例裁好，写死宽度会把它拉变形
        rp.add_run().add_picture(io.BytesIO(photo), height=Cm(3.2))
    else:
        _emit_header(doc)

    # ── 小节 ──
    for section in sections:
        hp = doc.add_paragraph()
        hp.paragraph_format.space_before = Pt(7 if compact else 9)
        hp.paragraph_format.space_after = Pt(3)
        hr = hp.add_run(section.title)
        _set_font(hr, ea=title_ea, ascii_font="Arial", size=base + 1, bold=True, color=accent)
        if template["key"] == "accent":
            _shade(hp, template["accent_soft"])
            hp.paragraph_format.left_indent = Cm(0.15)
        else:
            _bottom_border(hp, accent, sz=6)

        for entry in section.entries:
            if entry.head:
                tp = doc.add_paragraph()
                tp.paragraph_format.space_before = Pt(2)
                tp.paragraph_format.space_after = Pt(1)
                tr = tp.add_run(entry.head)
                _set_font(tr, ea=title_ea, ascii_font="Arial", size=base, bold=True, color="1F2328")
                if entry.meta:
                    # 右对齐制表位：岗位/时间落在行尾，视觉上像正经简历
                    tp.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
                    mr = tp.add_run("\t" + entry.meta)
                    _set_font(mr, ea=body_ea, size=base - 1, color="6B7480")
            elif entry.meta:
                mp = doc.add_paragraph()
                mp.paragraph_format.space_after = Pt(1)
                mr = mp.add_run(entry.meta)
                _set_font(mr, ea=body_ea, size=base - 1, color="6B7480")

            for line in entry.lines:
                bp = doc.add_paragraph()
                bp.paragraph_format.space_after = Pt(1)
                bp.paragraph_format.left_indent = Cm(0.44)
                bp.paragraph_format.first_line_indent = Cm(-0.44)
                bp.add_run("· ")
                br = bp.add_run(line)
                _set_font(br, ea=body_ea, size=base, color="2B333B")

            if entry.chips:
                if compact:
                    # 紧凑模板：技能排成 3 列无框表格，竖着看不浪费行
                    cols = 3
                    rows = (len(entry.chips) + cols - 1) // cols
                    table = doc.add_table(rows=rows, cols=cols)
                    table.autofit = True
                    for idx, chip in enumerate(entry.chips):
                        cell = table.cell(idx // cols, idx % cols)
                        cp = cell.paragraphs[0]
                        cp.paragraph_format.space_after = Pt(0)
                        cr = cp.add_run(chip)
                        _set_font(cr, ea=body_ea, size=base, color="2B333B")
                else:
                    cp = doc.add_paragraph()
                    cp.paragraph_format.space_after = Pt(1)
                    cp.paragraph_format.left_indent = Cm(0.44)
                    cp.paragraph_format.first_line_indent = Cm(-0.44)
                    cp.add_run("· ")
                    cr = cp.add_run("　·　".join(entry.chips))
                    _set_font(cr, ea=body_ea, size=base, color="2B333B")

            if entry.tail:
                tp = doc.add_paragraph()
                tr = tp.add_run(entry.tail)
                _set_font(tr, ea=body_ea, size=base, color="6B7480")

    # 页脚：说明这份简历怎么来的（对求职者自己有用，投递前可删）
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run(f"{header['name']} · 求职简历 · 由校园成长档案生成")
    _set_font(fr, ea=body_ea, size=7.5, color="A7AEB6")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ============================================================
# 七、PDF 渲染
# ============================================================

_FONT_CANDIDATES_SONG = [
    ("C:/Windows/Fonts/simsun.ttc", "SimSun"),
    ("C:/Windows/Fonts/simsun.ttf", "SimSun"),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", "AR PL UMing"),
    ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", "Noto Serif CJK"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WenQuanYi"),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", "Songti"),
]
_FONT_CANDIDATES_HEI = [
    ("C:/Windows/Fonts/simhei.ttf", "SimHei"),
    ("C:/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK"),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WenQuanYi"),
    ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
]

# 中文排版禁则：这些符号不许出现在行首 / 行尾
NO_LINE_START = set("，。、；：？！）〉》」』】〕…·%,.;:!?)]}’”")
NO_LINE_END = set("（〈《「『【〔([{‘“")


def _pick_font(candidates: list[tuple[str, str]]) -> str | None:
    for path, _ in candidates:
        if Path(path).is_file():
            return path
    return None


def _is_cjk(ch: str) -> bool:
    return "\u2e80" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef"


def wrap_text(pdf, text: str, width: float) -> list[str]:
    """按字符宽度断行，并做两件 fpdf2 默认不做的事：

    1. **禁则处理**——中文里「，。」不能落在行首（默认 wrapmode="CHAR" 会直接搬过去，
       读起来像断句错）；
    2. **西文不断词**——遇到 FastAPI / Vue3 这种词，宁可把整词挪到下一行，
       也不要断成 "FastA / PI"。

    逐字符量宽度在 500 字规模下完全够快（简历一页最多几千字符）。
    """
    lines: list[str] = []
    cur = ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if pdf.get_string_width(cur + ch) <= width:
            cur += ch
            continue

        # 需要换行：先决定在哪断
        cut = len(cur)
        if ch in NO_LINE_START and cur:
            cut = len(cur) - 1
        elif not _is_cjk(ch) and ch.isalnum():
            # 正在拼一个西文词：往回找到词首（前一个字符不是字母数字）
            i = len(cur)
            while i > 0 and cur[i - 1].isalnum() and not _is_cjk(cur[i - 1]):
                i -= 1
            if 0 < i < len(cur):
                cut = i
        # 行尾禁则：把（「 之类的符号一起带下去
        while cut > 0 and cur[cut - 1] in NO_LINE_END:
            cut -= 1
        cut = max(cut, 1)

        lines.append(cur[:cut].rstrip())
        cur = cur[cut:] + ch
    if cur:
        lines.append(cur)
    return lines


class ResumePDF:
    """fpdf2 的薄封装：这里只放简历需要的画法（小节标题、条目、圆点行、技能列）。"""

    def __init__(self, template: dict):
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos

        self.XPos, self.YPos = XPos, YPos
        self.t = template
        self.compact = template["compact"]
        self.accent = template["accent"]
        self.base = 9.0 if self.compact else 10.0
        self.side = 17.0 if self.compact else 19.0

        self.pdf = FPDF(format="A4", unit="mm")
        self.pdf.set_margins(self.side, 15, self.side)
        self.pdf.set_auto_page_break(True, margin=15)
        self.pdf.set_title("求职简历")
        self.pdf.add_page()

        song = _pick_font(_FONT_CANDIDATES_SONG)
        hei = _pick_font(_FONT_CANDIDATES_HEI)
        if not song and not hei:
            raise RuntimeError("服务器缺少中文字体（宋体/黑体），请先导出 DOCX；或安装 fonts-wqy-zenhei")
        self.pdf.add_font("Body", "", song or hei)
        self.pdf.add_font("Head", "", hei or song)
        self.content_w = self.pdf.w - self.side * 2
        self.line_h = self.base * 0.55

    # ── 基础画法 ──
    def rgb(self, hexcolor: str) -> tuple[int, int, int]:
        h = hexcolor.replace("#", "")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def para(self, txt: str, *, font: str = "Body", size: float | None = None,
             color: str = "2B333B", indent: float = 0.0, bullet: bool = False,
             h: float | None = None) -> None:
        """一段自动断行的文本；bullet=True 时首行前面加圆点并整体右缩进。"""
        pdf = self.pdf
        size = size or self.base
        h = h or self.line_h
        pdf.set_font(font, "", size)
        pdf.set_text_color(*self.rgb(color))
        x0 = self.side + indent
        width = self.content_w - indent
        lines = wrap_text(pdf, txt, width)
        for i, line in enumerate(lines):
            if i > 0 and pdf.will_page_break(h):
                pdf.add_page()
                pdf.set_font(font, "", size)
                pdf.set_text_color(*self.rgb(color))
            if bullet and i == 0:
                pdf.set_x(self.side)
                pdf.cell(indent, h, "·", new_x=self.XPos.LEFT, new_y=self.YPos.TOP)
            pdf.set_x(x0)
            pdf.cell(width, h, line, new_x=self.XPos.LMARGIN, new_y=self.YPos.NEXT)

    def heading(self, title: str) -> None:
        pdf = self.pdf
        pdf.ln(2.2 if self.compact else 3.0)
        y0 = pdf.get_y()
        hh = (self.base + 1) * 0.55 + 1.6
        if pdf.will_page_break(hh + 4):
            pdf.add_page()
            y0 = pdf.get_y()
        pdf.set_font("Head", "", self.base + 1)
        pdf.set_text_color(*self.rgb(self.accent))
        if self.t["key"] == "accent":
            pdf.set_fill_color(*self.rgb(self.t["accent_soft"]))
            pdf.rect(self.side - 1.5, y0 - 1.2, self.content_w + 3, hh, "F")
            pdf.set_fill_color(*self.rgb(self.accent))
            pdf.rect(self.side - 1.5, y0 - 1.2, 1.2, hh, "F")
            pdf.set_x(self.side + 1.4)
            pdf.cell(self.content_w - 1.4, hh - 1.0, title, new_x=self.XPos.LMARGIN, new_y=self.YPos.NEXT)
            pdf.ln(0.6)
        else:
            pdf.cell(self.content_w, hh - 1.0, title, new_x=self.XPos.LMARGIN, new_y=self.YPos.NEXT)
            pdf.set_draw_color(*self.rgb(self.accent))
            pdf.set_line_width(0.3)
            pdf.line(self.side, pdf.get_y() + 0.2, self.side + self.content_w, pdf.get_y() + 0.2)
            pdf.ln(1.4)

    def entry_head(self, head: str, meta: str) -> None:
        pdf = self.pdf
        h = self.line_h
        pdf.set_font("Head", "", self.base)
        if not meta:
            self.para(head, font="Head", size=self.base, color="1F2328")
            return
        pdf.set_font("Body", "", self.base - 1)
        meta_w = min(self.content_w * 0.6, pdf.get_string_width(meta) + 1.5)
        head_w = self.content_w - meta_w
        # 标题过长时截断加省略号——挤到第二行反而更难读
        text = head
        while text and pdf.get_string_width(text) > head_w:
            text = text[:-1]
        if text != head:
            text = text[:-1] + "…" if len(text) > 1 else text
        if pdf.will_page_break(h):
            pdf.add_page()
        pdf.set_font("Head", "", self.base)
        pdf.set_text_color(*self.rgb("1F2328"))
        pdf.cell(head_w, h, text, new_x=self.XPos.RIGHT, new_y=self.YPos.TOP)
        pdf.set_font("Body", "", self.base - 1)
        pdf.set_text_color(*self.rgb("6B7480"))
        pdf.cell(meta_w, h, meta, align="R", new_x=self.XPos.LMARGIN, new_y=self.YPos.NEXT)

    def chips(self, items: list[str]) -> None:
        """技能标签：按行排，每行 cols 个，列宽均分（不用多列 cell，位置算不准）。

        fpdf2 的 cell 不截断文字：条目比列宽长时会横穿到右列造成重叠。
        所以先按实测字宽把条目排成行，放不进一格的长条目单独占整行。
        """
        pdf = self.pdf
        cols = 4 if self.compact else 3
        gap = 2.5
        lead = 3.2
        col_w = (self.content_w - lead - gap * (cols - 1)) / cols
        h = self.line_h + 0.6
        pdf.set_font("Body", "", self.base)
        pdf.set_text_color(*self.rgb("2B333B"))

        rows: list[list[str]] = []
        buf: list[str] = []
        for item in items:
            text = str(item)
            if pdf.get_string_width(text) > col_w - 1.5:
                if buf:
                    rows.append(buf)
                    buf = []
                rows.append([text])
                continue
            buf.append(text)
            if len(buf) == cols:
                rows.append(buf)
                buf = []
        if buf:
            rows.append(buf)

        first = True
        for row in rows:
            if pdf.will_page_break(h):
                pdf.add_page()
                pdf.set_font("Body", "", self.base)
                pdf.set_text_color(*self.rgb("2B333B"))
            y = pdf.get_y()
            if first:
                pdf.set_xy(self.side, y)
                pdf.cell(lead, h, "·", new_x=self.XPos.LEFT, new_y=self.YPos.TOP)
                first = False
            if len(row) == 1:
                pdf.set_xy(self.side + lead, y)
                pdf.cell(self.content_w - lead, h, row[0], new_x=self.XPos.LEFT, new_y=self.YPos.TOP)
            else:
                for col, item in enumerate(row):
                    pdf.set_xy(self.side + lead + col * (col_w + gap), y)
                    pdf.cell(col_w, h, item, new_x=self.XPos.LEFT, new_y=self.YPos.TOP)
            pdf.set_y(y + h)

    def footer_all(self) -> None:
        """页脚：先关自动分页再画，否则 set_y(-15) 本身会触发一次新页（多出空白页）。"""
        pdf = self.pdf
        pdf.set_auto_page_break(False)
        last = pdf.page
        for i in range(1, last + 1):
            pdf.page = i
            pdf.set_y(-13)
            pdf.set_font("Body", "", 7.5)
            pdf.set_text_color(*self.rgb("A7AEB6"))
            pdf.cell(0, 5, f"{self.name} · 求职简历 · 由校园成长档案生成", align="C")
        pdf.page = last

    def output(self) -> bytes:
        return bytes(self.pdf.output())


def render_pdf(header: dict, sections: list[Section], template: dict, photo: bytes | None = None) -> bytes:
    r = ResumePDF(template)
    r.name = header["name"]
    pdf = r.pdf

    # 证件照：右上角一寸照（上传前已按比例裁好），文字块让出右侧宽度。
    # 注意绘制顺序——accent 色带必须先铺底、照片后盖上去，否则色带会把照片上沿切掉。
    photo_w, photo_h = (24.0, 33.0) if photo else (0.0, 0.0)
    photo_x = pdf.w - r.side - photo_w
    photo_y = 8.0

    # 抬头：accent 模板用满宽色块打底，其余靠字号和细分隔线
    if template["key"] == "accent":
        # 色带高度跟着照片走，让照片正好落在色带里（下沿齐平），像证件照贴条
        band_h = max(30.0, photo_y + photo_h + 1.0) if photo_h else 30.0
        pdf.set_fill_color(*r.rgb(template["accent_soft"]))
        pdf.rect(0, 0, pdf.w, band_h, "F")
        pdf.set_fill_color(*r.rgb(template["accent"]))
        pdf.rect(0, 0, pdf.w, 1.8, "F")
        pdf.set_y(9)

    if photo:
        try:
            pdf.image(io.BytesIO(photo), x=photo_x, y=photo_y, w=photo_w, h=photo_h)
        except Exception:
            photo_w, photo_h = 0.0, 0.0   # 图片损坏不能挡住整个导出

    name_w = r.content_w - (photo_w + 4 if photo_w else 0)
    pdf.set_font("Head", "", 20 if not r.compact else 18)
    pdf.set_text_color(*r.rgb(template["accent"]))
    pdf.cell(name_w, 9, header["name"], new_x=r.XPos.LMARGIN, new_y=r.YPos.NEXT)

    if header["contact"]:
        # 有照片时联系方式压在一行内（右上有图，长联系方式会顶进去）
        contact_line = "　|　".join(header["contact"])
        if photo_w:
            contact_line = wrap_text(pdf, contact_line, name_w)[0]
        r.para(contact_line, size=r.base - 1, color="4A5560", h=4.8)

    pdf.ln(0.6)
    if template["key"] == "classic":
        r.para(header["target_line"], font="Head", size=r.base, color="2B333B", h=5.0)
        pdf.set_draw_color(*r.rgb("C9D0D6"))
        pdf.set_line_width(0.3)
        pdf.line(r.side, pdf.get_y() + 0.6, r.side + (name_w if photo_w else r.content_w), pdf.get_y() + 0.6)
        pdf.ln(2.0)
    else:
        y0 = pdf.get_y()
        hh = r.line_h * max(1, len(wrap_text(pdf, header["target_line"], r.content_w - 3))) + 1.2
        pdf.set_fill_color(*r.rgb(template["accent"]))
        pdf.rect(r.side, y0 - 0.4, 1.2, hh, "F")
        r.para(header["target_line"], font="Head", size=r.base, color="2B333B", indent=3.0, h=5.0)

    # 照片比文字抬头高时，正文从照片下缘开始，避免第一小节标题顶进照片
    if photo_h:
        pdf.set_y(max(pdf.get_y(), 8.0 + photo_h + 3.0))

    for section in sections:
        r.heading(section.title)
        for entry in section.entries:
            if entry.head:
                r.entry_head(entry.head, entry.meta)
            elif entry.meta:
                r.para(entry.meta, size=r.base - 1, color="6B7480")
            for line in entry.lines:
                r.para(line, bullet=True, indent=3.2)
            if entry.chips:
                r.chips(entry.chips)
            if entry.tail:
                r.para(entry.tail, size=r.base, color="6B7480")

    r.footer_all()
    return r.output()


# ============================================================
# 八、对外入口
# ============================================================

def safe_filename(text: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\s]+", "-", text).strip("-")[:40] or "resume"


def generate(
    db: Session,
    user: User,
    *,
    job_key: str | None,
    industry: str | None,
    custom_job: str | None = None,
    job_type: str = "",
    city: str = "",
    template_key: str = "classic",
    fmt: str = "docx",
    objective: str | None = None,
    photo: bytes | None = None,
) -> dict:
    """一次性产出：匹配报告 + 文件字节 + 建议文件名。"""
    profile = collect_profile(db, user)
    match = evaluate(profile, industry, job_key, custom_job)
    target = find_job(industry, job_key or match["job"]["key"], custom_job)
    template = TEMPLATE_MAP.get(template_key) or TEMPLATES[0]

    sections = build_sections(profile, target, match, template)
    if objective:
        # 用户/大模型给的自我评价优先，替换最后那节
        for s in sections:
            if s.key == "self":
                s.entries = [Entry(lines=[objective])]
    header = build_header(profile, target, {"job_type": job_type, "city": city,
                                            "match_score": match["score"]})

    if fmt == "pdf":
        data = render_pdf(header, sections, template, photo=photo)
        ext, mime = "pdf", "application/pdf"
    else:
        data = render_docx(header, sections, template, photo=photo)
        ext = "docx"
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    filename = f"{safe_filename(profile['name'])}-{safe_filename(target['label'])}-简历.{ext}"
    return {
        "data": data, "filename": filename, "mime": mime,
        "match": match, "template": template_key, "format": ext,
        "sections": [{"key": s.key, "title": s.title, "count": len(s.entries)} for s in sections],
    }
