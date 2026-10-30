"""学习计划阶段 AI 服务：AI 拆解阶段（任务流关卡）+ 阶段成果评估打分。

LLM 不可用/超时/解析失败时回退到规则生成，保证功能可用。
"""
import json
import logging
import re
from datetime import date

from app.models.plan import StudyPlan, PlanStage, PlanTask, TaskStatus, StageStatus, TaskPriority
from app.services.llm_service import _get_llm_config, _get_client
from app.services.prompts import build_plan_stages_prompt, build_stage_evaluation_prompt

logger = logging.getLogger(__name__)

_parse_json = None  # 延迟导入 llm_service 的解析函数，避免循环

# 关闭思考：本项目推理模型开思考时会耗尽 max_tokens（content 为空），
# 导致拆解/评估只能走规则兜底，任务永远停留在“基础/实践/推进”这类套话
_JSON_EXTRA_BODY = {"thinking": {"type": "disabled"}}


def _parse_json_loose(text: str) -> dict | None:
    global _parse_json
    if _parse_json is None:
        from app.services.llm_service import _parse_json_loose as _pj
        _parse_json = _pj
    return _parse_json(text)


# ==================== AI 拆解阶段 ====================

_GENERIC_STAGE_WORDS = {
    "", "基础", "实践", "推进", "提升", "学习", "练习", "巩固", "入门", "准备",
    "基础夯实", "进阶提升", "冲刺实战", "基础学习", "实践练习",
    "夯实基础", "基础巩固", "全面复习", "稳步推进", "持续推进", "扎实推进",
    "专项训练", "强化训练", "冲刺阶段", "冲刺备考", "综合提升",
}


def _is_generic_stage(title: str) -> bool:
    """判断阶段标题是否是“基础/实践/推进”这类没有细化信息的空泛词。"""
    t = re.sub(r"阶段\s*[一二三四五六1-6]|第\s*[一二三四五六1-6]\s*(阶段|关)", "", title or "")
    t = re.sub(r"[：:、\s（）()\-]", "", t)
    return t in _GENERIC_STAGE_WORDS


async def ai_generate_stages(db, plan: StudyPlan, student_id: int) -> tuple[str, list[dict]]:
    """AI 拆解计划为阶段任务流。

    返回 (summary, stage_data_list)，stage_data 形如：
    {"title": ..., "goal": ..., "tasks": [{"title": ..., "description": ...}]}
    LLM 失败时回退规则拆解。
    """
    try:
        cfg = _get_llm_config()
        if not cfg["api_key"]:
            raise RuntimeError("no api key")
        client = _get_client()
        today = date.today()
        days_left = (plan.end_date - today).days if plan.end_date else None
        prompt = build_plan_stages_prompt(
            title=plan.title,
            objective=plan.objective,
            start_date=plan.start_date,
            end_date=plan.end_date,
            days_left=days_left,
        )
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2600,
            response_format={"type": "json_object"},
            extra_body=_JSON_EXTRA_BODY,
        )
        text = (resp.choices[0].message.content or "").strip()
        data = _parse_json_loose(text)
        if not data or not isinstance(data.get("stages"), list):
            raise RuntimeError("bad json")
        stages = []
        for s in data["stages"][:6]:
            title = str(s.get("title") or "").strip()
            if not title:
                continue
            tasks = []
            for t in (s.get("tasks") or [])[:4]:
                tt = str(t.get("title") or "").strip()
                if tt:
                    tasks.append({
                        "title": tt,
                        "description": str(t.get("description") or "").strip() or None,
                    })
            stages.append({
                "title": title[:100],
                "goal": str(s.get("goal") or "").strip()[:500] or None,
                "tasks": tasks,
            })
        if stages and sum(1 for s in stages if _is_generic_stage(s["title"])) > len(stages) / 2:
            raise RuntimeError("generic stages")
        if stages:
            return str(data.get("summary") or "已为你拆解为阶段任务流"), stages
        raise RuntimeError("empty stages")
    except Exception as e:
        logger.warning("AI 拆解阶段失败，回退规则拆解: %s", e)
        return _rule_generate_stages(plan)


_PLAN_SUFFIXES = ("学习计划", "复习计划", "提升计划", "训练计划", "计划", "方案", "目标")


def _plan_topic(plan: StudyPlan) -> str:
    """从计划标题里取出主题词，供兜底拆解时写进关卡与任务，避免空泛的“基础/实践/推进”。"""
    raw = (plan.title or "").strip()
    for suffix in _PLAN_SUFFIXES:
        if raw.endswith(suffix) and len(raw) > len(suffix):
            raw = raw[: -len(suffix)].strip()
            break
    return raw or "这个目标"


def _task(title: str, description: str) -> dict:
    return {"title": title, "description": description}


# 常见方向的“真实模块”拆解包：LLM 不可用时也能给出方向性的每日/每周固定动作，
# 而不是“基础/实践/推进”这类看不出要做什么的套话。
_DOMAIN_PACKS: list[dict] = [
    {
        "name": "考公",
        "keywords": ("考公", "公务员", "公考", "国考", "省考", "选调", "行测", "申论", "事业单位"),
        "stages": [
            {
                "title": "摸底定岗，把时政变成每天的习惯",
                "goal": "用真题测出行测各模块正确率，锁定目标岗位与分差，并建立每天 30 分钟时政积累",
                "tasks": [
                    _task("每天 30 分钟时政新闻，摘录 3 条并写 1 句点评",
                          "来源可用新闻联播、半月谈、人民日报评论，记在同一个笔记本或表格里"),
                    _task("限时做 1 套近三年省考真题（行测+申论），记录各模块正确率与用时",
                          "形成分数基线表，标出正确率最低的 3 个模块"),
                    _task("查目标岗位近 3 年进面分数线，写清当前分差与目标分",
                          "把目标拆成行测、申论两科的目标分数，贴在计划首页"),
                ],
            },
            {
                "title": "行测薄弱模块逐个补强",
                "goal": "数量、资料、判断等薄弱模块各刷 200 题，正确率提到 65% 以上",
                "tasks": [
                    _task("每天 60 分钟精学 1 个薄弱模块 + 20 道专项题",
                          "数量关系与资料分析优先，学完公式当天做题验证"),
                    _task("每周 1 次错题归因，按知识点整理高频考点清单",
                          "错题写清错因与正确思路，同类题隔天重做"),
                    _task("每天 15 分钟时政摘录不断档，周末汇总成 1 页时政周报",
                          "周报按领域分类，方便后面写申论时直接取用"),
                ],
            },
            {
                "title": "申论从读材料到写出完整文章",
                "goal": "申论五大题型各练 3 道，大作文形成自己的开头—分论点—结尾框架",
                "tasks": [
                    _task("每周 2 道申论小题，对照参考答案自评并改到二稿",
                          "归纳概括、综合分析、提出对策轮流练，标注失分点"),
                    _task("每周 1 篇大作文，限时 60 分钟，改 2 稿沉淀个人模板",
                          "固定开头、三个分论点、结尾的写法，积累 10 个常用句式"),
                    _task("把时政周报整理成 20 张申论素材卡",
                          "每张写清事例、适用主题与一句对策，写作时直接调用"),
                ],
            },
            {
                "title": "真题模考，锁定考场节奏",
                "goal": "完成 4 套全真模考，行测稳定 70 分以上，申论稳定中上水平",
                "tasks": [
                    _task("每两周 1 次全真模考，按考试时间连做行测+申论",
                          "严格计时涂卡，记录各模块用时与总分"),
                    _task("模考后 24 小时内完成失分归因，每类弱项补 50 题",
                          "只改最影响分数的三类问题，改完重做同类题验证"),
                    _task("每天 20 分钟背诵高频时政与常识考点",
                          "考前一个月汇总 50 条高频考点，每周自测 1 次"),
                ],
            },
        ],
    },
    {
        "name": "考研",
        "keywords": ("考研", "研究生", "读研", "保研", "初试", "复试", "专业课"),
        "stages": [
            {
                "title": "定校定专业，摸清四门课的底子",
                "goal": "确定目标院校专业与分数线，用真题摸清政治、英语、专业课当前水平",
                "tasks": [
                    _task("查目标院校近 3 年复试线与报录比，写清总分和单科目标",
                          "把目标分数拆到政治、英语、专业课三门课上"),
                    _task("每天背 50 个考研核心词，连续积累不中断",
                          "用词表或 App 滚动复习，周日复盘本周 350 个词"),
                    _task("限时做 1 套目标专业课真题，标出 3 个最薄弱章节",
                          "按章节统计失分，作为后面二轮复习的重点"),
                ],
            },
            {
                "title": "公共课打底：英语长难句 + 政治框架",
                "goal": "英语真题阅读正确率到 60%，政治核心框架过完一轮",
                "tasks": [
                    _task("每天 30 分钟长难句拆解 + 2 篇真题阅读精读",
                          "逐句翻译，标出定位句与错因，生词当天进生词本"),
                    _task("每天 30 分钟政治框架学习，配套 10 道选择题",
                          "先搭章节框架再刷题，错题回到教材对应位置"),
                    _task("每周日复盘本周单词与全部错题",
                          "把仍不熟的词和题单独列一张清单，下周优先处理"),
                ],
            },
            {
                "title": "专业课一轮过完，建立知识框架",
                "goal": "专业课教材过完一轮，每章产出 1 页笔记与 1 张思维导图",
                "tasks": [
                    _task("每天 90 分钟专业课精读，当天做 10 道配套题",
                          "按章节推进，读不完的章节顺延但不停更"),
                    _task("每章结束画 1 张思维导图，标出考点与易混点",
                          "导图只写关键词与逻辑关系，不抄原文"),
                    _task("每周做 1 套章节真题，记录得分与盲区",
                          "盲区回到教材补齐，再重做同类题"),
                ],
            },
            {
                "title": "真题驱动二轮复习与模考收口",
                "goal": "完成 4 套真题模考，总分接近目标线，背诵内容滚动复习 3 轮",
                "tasks": [
                    _task("每周 1 套完整真题限时模拟，按考试时间作答",
                          "模拟后统计各科分数，形成成绩曲线"),
                    _task("错题按知识点归类，48 小时内完成回补",
                          "每类错题重做 10 道，验证是否真的补上"),
                    _task("每天 40 分钟背诵专业课与政治大题",
                          "用艾宾浩斯节奏滚动复习，考前一周只过高频考点"),
                ],
            },
        ],
    },
    {
        "name": "英语考试",
        "keywords": ("四六级", "四级", "六级", "cet", "英语", "雅思", "托福", "gre", "专四", "专八"),
        "stages": [
            {
                "title": "摸底，并建立每天的词汇与听力动作",
                "goal": "用 1 套真题摸清各题型正确率，建立每天 50 个单词、精听 1 段的习惯",
                "tasks": [
                    _task("每天 30 分钟背 50 个核心词，滚动复习",
                          "新词 25 个 + 复习 25 个，周日只复盘本周生词"),
                    _task("每天 20 分钟精听 1 段真题听力，逐句听写并跟读",
                          "听不清的句子反复 3 遍，仍不懂再看原文标记"),
                    _task("限时做 1 套真题，记录听力/阅读/写作/翻译四项得分",
                          "按题型统计正确率，锁定最弱的两项"),
                ],
            },
            {
                "title": "阅读与听力专项突破",
                "goal": "阅读正确率到 70%，听力 Section A/B 稳定 8 题以上",
                "tasks": [
                    _task("每天 2 篇真题阅读精做，标出定位句与错因",
                          "限时 16 分钟两篇，做完逐题写清错因"),
                    _task("每天 1 段听力精听 + 1 段泛听，隔天复听",
                          "精听做听写，泛听只抓主旨与关键词"),
                    _task("每周整理 1 次高频词与同义替换清单",
                          "把阅读里反复出现的替换表达单独成表"),
                ],
            },
            {
                "title": "写作翻译模板化",
                "goal": "写出 3 套作文模板，翻译 10 篇真题并稳定得分",
                "tasks": [
                    _task("每周 2 篇作文，套用模板后改写 1 稿",
                          "每篇限时 30 分钟，写完后替换重复词汇与句式"),
                    _task("每周 5 句翻译真题，对照答案积累固定搭配",
                          "把错译的搭配整理进模板句库"),
                    _task("每天 20 分钟默写模板句与高频表达",
                          "默写后与原文比对，错处当天重写 3 遍"),
                ],
            },
            {
                "title": "整套真题限时模拟",
                "goal": "完成 4 套真题模考，总分稳定超过目标线 20 分",
                "tasks": [
                    _task("每周 1 套完整真题，按考试时间与顺序作答",
                          "作文与翻译也要写完，不能只做客观题"),
                    _task("模考后当天完成错题归因，隔天重做同类题",
                          "按听力、阅读、写作、翻译四类分别统计"),
                    _task("考前一周围定作文模板与高频词",
                          "只复习自己的模板与错题本，不再开新内容"),
                ],
            },
        ],
    },
    {
        "name": "编程技能",
        "keywords": ("编程", "前端", "后端", "java", "python", "spring", "vue", "算法", "开发", "项目实战",
                     "数据分析", "人工智能", "机器学习", "技能提升"),
        "stages": [
            {
                "title": "定技术栈与可验收的项目目标",
                "goal": "选定 1 个技术栈与 1 个能写进简历的项目，跑通开发环境",
                "tasks": [
                    _task("写清项目验收功能（3-5 条），拆成可交付的小模块",
                          "每条功能写成能演示的结果，如“能登录并查看列表”"),
                    _task("搭好环境并跑通最小 demo，记录踩坑与解决方式",
                          "把环境问题一次性解决，避免后面反复卡住"),
                    _task("每天 60 分钟官方文档/教程学习，边学边写示例代码",
                          "当天学的每个知识点都要有一段可运行的示例"),
                ],
            },
            {
                "title": "打通项目所需的核心知识点",
                "goal": "掌握 8-10 个核心知识点，能独立写出示例并解释原理",
                "tasks": [
                    _task("每天 1 个核心知识点 + 3 道练习，当天跑通",
                          "知识点按项目依赖排序，学不会的先跳过再回补"),
                    _task("每周整理 1 篇学习笔记，写清适用场景与坑点",
                          "笔记只写自己的理解与踩坑，不抄教程"),
                    _task("对照项目需求补齐缺失知识，维护待学清单",
                          "每完成一项就划掉，清单不超过 10 项"),
                ],
            },
            {
                "title": "完成项目核心模块并跑通主流程",
                "goal": "完成 2-3 个核心模块，主流程可从入口走到结果",
                "tasks": [
                    _task("每天推进 1 个功能点，提交代码并写清改动说明",
                          "提交信息写清做了什么、为什么这样做"),
                    _task("每完成 1 个模块补 1 组测试或自测用例",
                          "至少覆盖正常流程与 1 个异常分支"),
                    _task("每周复盘代码，处理遗留问题与技术债",
                          "把临时写法记成 TODO，下周优先清理"),
                ],
            },
            {
                "title": "完善、部署与复盘",
                "goal": "项目可运行可展示，形成 README、演示截图与复盘",
                "tasks": [
                    _task("完成部署或本地一键启动，确保他人可复现",
                          "写清依赖版本与启动步骤，换台机器验证一次"),
                    _task("写 README 与项目亮点说明，整理 1 份演示稿",
                          "亮点写清解决的问题、技术选型与效果数据"),
                    _task("复盘 3 个最难的问题与解决方案，沉淀成面试素材",
                          "每个问题按“现象—定位—解决—收获”写清"),
                ],
            },
        ],
    },
    {
        "name": "求职就业",
        "keywords": ("就业", "求职", "实习", "面试", "简历", "offer", "秋招", "春招", "校招"),
        "stages": [
            {
                "title": "锁定目标岗位与差距",
                "goal": "确定 3 个目标岗位，梳理 JD 要求与自身差距",
                "tasks": [
                    _task("每天看 2 条目标岗位 JD，摘录高频要求",
                          "连续看一周，统计出现最多的 5 项能力"),
                    _task("整理现有经历，列出 3 项硬差距与补齐方式",
                          "每项差距写清补什么、用什么项目或练习补"),
                    _task("定 3 家目标公司与投递时间表",
                          "按冲刺/匹配/保底三档各选 1 家"),
                ],
            },
            {
                "title": "打磨简历与项目亮点",
                "goal": "产出一版可投递简历，2 个项目能讲清亮点与数据",
                "tasks": [
                    _task("完成 1 版简历，按 STAR 写清项目结果与数据",
                          "每条经历只写结果与贡献，不写岗位职责"),
                    _task("每天打磨 1 个项目亮点，能 2 分钟讲完",
                          "录音检查表达是否清楚，删掉含糊的形容词"),
                    _task("找同学或老师做 1 次简历评审并修改",
                          "把反馈逐条改完，改完再自查一遍错别字"),
                ],
            },
            {
                "title": "刷高频面试题与模拟面试",
                "goal": "覆盖岗位高频面试题，完成 3 次模拟面试",
                "tasks": [
                    _task("每天 20 道岗位高频题，写清答题要点",
                          "技术题写思路，行为题写具体事例"),
                    _task("每周 1 次模拟面试，录音复盘表达问题",
                          "重点改掉口头禅、答非所问与超时"),
                    _task("准备 5 个行为面试故事（冲突/失败/协作等）",
                          "每个故事控制在 2 分钟内，突出自己的动作"),
                ],
            },
            {
                "title": "投递、复盘与补短板",
                "goal": "完成 10 次投递，按面试反馈补齐短板，争取拿到 offer",
                "tasks": [
                    _task("每周投递 3-5 家，记录投递与反馈状态",
                          "用表格跟踪，避免错过笔试与面试时间"),
                    _task("每次面试后 24 小时内复盘，写下 3 条改进",
                          "答不上的题当天补，形成自己的题库"),
                    _task("针对高频挂点做专项准备，每周验证一次",
                          "用模拟题或项目复述验证是否真的补上"),
                ],
            },
        ],
    },
]


def _match_domain_pack(topic: str, objective: str) -> dict | None:
    """按计划标题/目标里的方向词匹配拆解包，命中关键词最多者优先；匹配不到返回 None 走通用拆解。"""
    text = f"{topic} {objective}".lower()
    best: tuple[int, dict | None] = (0, None)
    for pack in _DOMAIN_PACKS:
        hits = sum(1 for kw in pack["keywords"] if kw in text)
        if hits > best[0]:
            best = (hits, pack)
    return best[1]



def _rule_generate_stages(plan: StudyPlan) -> tuple[str, list[dict]]:
    """规则兜底：围绕计划主题与总目标，拆成“摸底 → 学习 → 练习 → 产出 → 检验”的里程碑。

    与旧版按周平均切段不同，这里每个关卡都对应大目标的一次验收，
    任务写明学什么、练什么、产出什么，LLM 不可用时也能得到可执行的细化。
    """
    total_days = 14
    if plan.end_date:
        total_days = max(7, (plan.end_date - plan.start_date).days)
    if total_days <= 10:
        n = 3
    elif total_days <= 24:
        n = 4
    else:
        n = 5
    per = max(2, -(-total_days // n))
    topic = _plan_topic(plan)
    objective = (plan.objective or "").strip()
    pack = _match_domain_pack(topic, objective)

    phases = pack["stages"] if pack else [
        {
            "title": "摸清现状，锁定差距",
            "goal": "弄清现在会什么、还差什么，把总目标落成可验收的小目标",
            "tasks": [
                {"title": f"梳理「{topic}」当前掌握情况，列出 3-5 个具体薄弱点",
                 "description": "按已会/半会/不会三档盘点，标出最影响达标的两项"},
                {"title": f"把总目标拆成 {n} 个阶段的验收标准",
                 "description": "每条标准写成可检查的结果，如“能独立完成”“正确率达到 80%”"},
            ],
        },
        {
            "title": "补齐核心知识与方法",
            "goal": f"把「{topic}」完成目标所必需的核心内容学通，形成自己的框架",
            "tasks": [
                {"title": f"学完「{topic}」第一轮核心内容，输出 1 页思维导图",
                 "description": "按薄弱点清单排序学习，边学边补全导图"},
                {"title": f"每天固定 60 分钟推进「{topic}」，连续 14 天不断档",
                 "description": "固定时段学习并在计划里打卡，记录当天卡住的地方"},
                {"title": "整理核心方法/典型例题，标注仍不清楚的 3 处",
                 "description": "每类方法写清适用场景与步骤，留下的疑问当天查清"},
            ],
        },
        {
            "title": "专项练习，盯住薄弱点",
            "goal": "用练习暴露问题，把错得最多的部分逐个补上",
            "tasks": [
                {"title": f"完成 2 轮「{topic}」专项练习并记录正确率",
                 "description": "两轮之间至少隔一天，第二轮只做第一轮的错误类型"},
                {"title": "针对最薄弱的 2 个点做错题复盘并重练",
                 "description": "写清错因、正确思路和下次避免办法，再重做同类题"},
            ],
        },
        {
            "title": "综合应用，做出成果",
            "goal": f"把零散内容串起来，用一次完整产出检验「{topic}」的掌握程度",
            "tasks": [
                {"title": f"用「{topic}」完成 1 个小型综合作品/项目/整套卷",
                 "description": "按真实任务要求一次做完，记录卡住的位置"},
                {"title": "对照阶段验收标准逐条自查，补齐未达标项",
                 "description": "每项标出证据（作品、正确率、笔记），没有证据的算未完成"},
            ],
        },
        {
            "title": "限时检验与收尾",
            "goal": "模拟真实场景限时完成，稳定发挥并整理可复用材料",
            "tasks": [
                {"title": f"完成 1 次「{topic}」限时模拟，记录得分与失分点",
                 "description": "按正式时长和规则执行，结束后只分析失分原因"},
                {"title": "整理最终笔记/错题本/作品说明，形成复盘清单",
                 "description": "留下下次可直接复用的步骤与易错点"},
            ],
        },
    ]

    picks = {3: [0, 1, 3], 4: [0, 1, 2, 3], 5: [0, 1, 2, 3, 4]}[n]
    if pack:
        # 拆解包固定 4 关：周期短时保留前 n-1 关 + 最后一关，保证有收口
        selected = list(phases) if n >= len(phases) else phases[: n - 1] + [phases[-1]]
    else:
        selected = [phases[i] for i in picks]
    stages = []
    for i, phase in enumerate(selected, start=1):
        start_day = (i - 1) * per + 1
        end_day = min(total_days, i * per)
        goal = f"第 {start_day}~{end_day} 天：{phase['goal']}"
        if i == 1 and objective:
            goal = f"围绕「{objective[:40]}」，第 {start_day}~{end_day} 天：{phase['goal']}"
        tasks = [dict(t) for t in phase["tasks"]]
        if not pack and i == len(selected) and n <= 4:
            tasks.append({
                "title": f"做 1 次「{topic}」限时模拟并复盘失分点",
                "description": "按正式要求限时完成，结束后只改最影响结果的三个问题",
            })
        stages.append({"title": phase["title"], "goal": goal, "tasks": tasks})
    if pack:
        return f"已按「{pack['name']}」方向拆出每天/每周可执行的固定动作（规则模式）", stages
    return "已围绕总目标拆出可验收的里程碑（规则模式）", stages


# ==================== 阶段成果 AI 评估 ====================

async def ai_evaluate_stage(db, stage: PlanStage) -> tuple[int, str, str, str]:
    """AI 评估阶段成果：返回 (score, evaluation, weaknesses, suggestions)。

    LLM 失败时回退规则评估。
    """
    tasks = db.query(PlanTask).filter(PlanTask.stage_id == stage.id).all()
    plan = db.query(StudyPlan).filter(StudyPlan.id == stage.plan_id).first()
    task_lines = "\n".join(
        f"- 「{t.title}」状态={'已完成' if t.status == TaskStatus.DONE else '未完成'}"
        for t in tasks
    ) or "- 无"
    try:
        cfg = _get_llm_config()
        if not cfg["api_key"]:
            raise RuntimeError("no api key")
        client = _get_client()
        prompt = build_stage_evaluation_prompt(
            objective=(plan.objective or plan.title) if plan else "",
            stage_title=stage.title,
            stage_goal=stage.goal,
            task_lines=task_lines,
            submitted_result=stage.submitted_result,
        )
        resp = await client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1200,
            response_format={"type": "json_object"},
            extra_body=_JSON_EXTRA_BODY,
        )
        text = (resp.choices[0].message.content or "").strip()
        data = _parse_json_loose(text)
        if not data:
            raise RuntimeError("bad json")
        try:
            score = max(0, min(100, int(float(data.get("score", 60)))))
        except (TypeError, ValueError):
            score = 60
        return (
            score,
            str(data.get("evaluation") or "").strip()[:500],
            str(data.get("weaknesses") or "").strip()[:500],
            str(data.get("suggestions") or "").strip()[:500],
        )
    except Exception as e:
        logger.warning("AI 评估阶段失败，回退规则评估: %s", e)
        return _rule_evaluate_stage(stage, tasks)


def _rule_evaluate_stage(stage: PlanStage, tasks: list) -> tuple[int, str, str, str]:
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
    rate = round(done / total * 100) if total else 0
    score = min(100, 40 + rate // 2) if total else 70
    evaluation = (
        f"已收到阶段成果。阶段任务完成 {done}/{total}（{rate}%）。"
        if total else "已收到阶段成果。"
    )
    weaknesses = "任务完成度不足，建议补齐未完成项并复盘。" if rate < 100 else "成果与目标的对应说明不够具体，建议补充量化产出。"
    suggestions = "下一阶段先复习本阶段薄弱点，再推进新内容，保持每天固定学习时长。"
    return score, evaluation, weaknesses, suggestions


# ==================== 入库 ====================

def persist_generated_stages(db, plan: StudyPlan, stages: list[dict], student_id: int) -> list[PlanStage]:
    """把 AI 拆解结果写入 plan_stages + 对应任务；返回新建阶段列表。"""
    created = []
    for i, s in enumerate(stages):
        order = i
        st = PlanStage(
            plan_id=plan.id,
            title=s["title"],
            goal=s.get("goal"),
            order_index=order,
            status=StageStatus.LOCKED,
            ai_generated=True,
        )
        db.add(st)
        db.flush()
        for j, t in enumerate(s.get("tasks") or []):
            db.add(PlanTask(
                plan_id=plan.id,
                stage_id=st.id,
                title=t["title"],
                description=t.get("description"),
                priority=TaskPriority.MEDIUM,
                order_index=j,
            ))
        created.append(st)
    # 解锁第一个阶段
    if created:
        created[0].status = StageStatus.ACTIVE
    db.commit()
    for st in created:
        db.refresh(st)
    return created
