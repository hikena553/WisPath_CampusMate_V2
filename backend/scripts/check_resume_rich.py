"""用假档案渲染一版「信息量满」的简历，专测长句断行、多项目、两页溢出。

走的是和线上完全一样的 render_docx / render_pdf，只是 profile 用构造的 dict，
不碰数据库——这样既能测排版，又不污染任何真实数据。
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import resume_export as rx  # noqa: E402

OUT = Path("D:/StudyNote/Mian02/.workbuddy/tmp/resume")


def fake_profile() -> dict:
    user = SimpleNamespace(id=9999, name="林嘉禾", username="20230704001", gender="女",
                           phone="13800001234", political_status="中共党员",
                           hometown="四川成都", college="计算机科学与技术学院",
                           signature="", skills_json={"skills": [{"name": "TypeScript"}, {"name": "Vue3"}]})
    projects = [
        SimpleNamespace(
            project_name="「学伴」AI 学习助手（Vue3 + FastAPI 全栈）",
            start_date=__import__("datetime").date(2026, 3, 1), end_date=None,
            is_team=True, team_members="4 人", my_role="前端负责人 / 核心开发",
            tech_stack="Vue3, TypeScript, Vite, Element Plus, FastAPI, MySQL, Redis",
            project_link="https://github.com/linjiahe/study-buddy",
            images='["https://cdn.example.com/a.png","https://cdn.example.com/b.png","https://cdn.example.com/c.png"]',
            description=("面向本校本硕学生的 AI 学习助手，负责前端架构与核心交互。"
                         "主导把课程表、打卡、成长档案三套页面重构成统一的移动端设计语言，抽象出 12 个可复用组件，"
                         "同类页面开发时间从 3 天压缩到 6 小时；"
                         "接入流式对话与 SSE 进度推送，首字延迟从 2.4s 降到 380ms；"
                         "上线 4 个月累计 3200+ 注册用户，日活 640，页面崩溃率从 0.8% 降到 0.05%。"),
        ),
        SimpleNamespace(
            project_name="校园二手交易小程序",
            start_date=__import__("datetime").date(2025, 10, 1), end_date=__import__("datetime").date(2026, 1, 20),
            is_team=True, team_members="3 人", my_role="后端开发",
            tech_stack="Python, FastAPI, MySQL, 微信小程序",
            project_link=None,
            images='["https://cdn.example.com/d.png"]',
            description=("独立负责订单与支付模块，用状态机管理下单、支付回调、超时关单三类事件，"
                         "把超卖问题从每周 3~5 单降到 0；"
                         "引入 Redis 缓存热门商品列表，接口 P99 从 480ms 优化到 120ms。"),
        ),
        SimpleNamespace(
            project_name="基于 YOLOv8 的实验室器材识别与盘点系统",
            start_date=__import__("datetime").date(2025, 5, 1), end_date=__import__("datetime").date(2025, 9, 1),
            is_team=False, team_members=None, my_role="独立完成",
            tech_stack="Python, PyTorch, YOLOv8, OpenCV, Flask",
            project_link=None,
            images="[]",
            description=("自建 1800 张实验室器材数据集，完成标注、训练与部署全流程；"
                         "在验证集上 mAP@0.5 达到 0.91，单张推理 38ms，替代了原来人工逐件清点的方式。"),
        ),
    ]
    certs = [
        SimpleNamespace(title="中国大学生计算机设计大赛 国家级二等奖",
                        competition_name="教育部高等学校计算机类专业教学指导委员会",
                        award_level=rx._enum_value and "national", date="2026-07-12",
                        description="", status="approved"),
        SimpleNamespace(title="蓝桥杯 Web 应用开发 省赛一等奖", competition_name="工业和信息化部人才交流中心",
                        award_level="province", date="2026-04-18", description="", status="approved"),
        SimpleNamespace(title="校级一等奖学金", competition_name="计算机科学与技术学院",
                        award_level="school", date="2026-09-20", description="", status="approved"),
        SimpleNamespace(title="CET-6 546 分", competition_name="全国大学英语四六级考试委员会",
                        award_level=None, date="2025-12-14", description="", status="approved"),
    ]
    records = [
        SimpleNamespace(type="practice", title="校学生会技术部部长",
                        date=__import__("datetime").date(2026, 3, 1),
                        description="带 8 人技术小组维护学生会官网与活动报名系统，一学期支撑 6 场活动、4700 人次报名。"),
        SimpleNamespace(type="competition", title="ACM-ICPC 亚洲区域赛 成都站 铜牌",
                        date=__import__("datetime").date(2026, 10, 3), description="队伍三人，负责图论与动态规划题目。"),
        SimpleNamespace(type="paper", title="《面向高校场景的轻量化对话式学习助手设计》",
                        date=__import__("datetime").date(2026, 8, 15), description="第二作者，已投稿校级学报。"),
    ]
    return {
        "user": user, "name": user.name, "student_no": user.username, "gender": user.gender,
        "phone": user.phone, "political": user.political_status, "hometown": user.hometown,
        "college": user.college, "major": "软件工程", "class_name": "2023级软件工程2班",
        "grade_year": 2023, "signature": "",
        "projects": projects, "certs": certs, "records": records,
        "skills": ["Vue3", "TypeScript", "React", "Python", "FastAPI", "MySQL", "Redis",
                   "Docker", "Git", "ECharts", "小程序", "Node.js"],
        "grade_count": 32, "avg_score": 88.6, "gpa": 3.72, "credits": 96.5, "pass_rate": 100.0,
        "top_courses": [
            {"name": "数据结构", "score": 95, "credit": 4}, {"name": "操作系统", "score": 92, "credit": 4},
            {"name": "数据库原理", "score": 91, "credit": 3}, {"name": "计算机网络", "score": 89, "credit": 3.5},
            {"name": "机器学习", "score": 93, "credit": 3},
        ],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    profile = fake_profile()
    for ind, job in [("internet", "frontend"), ("ai", "algo")]:
        m = rx.evaluate(profile, ind, job)
        print(f"[{m['job']['label']}] {m['score']} ({m['level']})  命中 {len(m['hits'])} / 缺 {len(m['gaps'])}")
        for d in m["dims"]:
            print(f"    {d['label']} {d['score']:>5}  {d['note']}")
        print("    建议:", " / ".join(f"{s['label']}({s['score']})" for s in m["suggest"]))

    for tpl in rx.TEMPLATES:
        for fmt in ("docx", "pdf"):
            r = rx.generate(None, None, job_key="frontend", industry="internet",
                            job_type="校招全职", city="成都", template_key=tpl["key"], fmt=fmt) \
                if False else _render(profile, tpl, fmt)
            (OUT / f"rich-{tpl['key']}.{fmt}").write_bytes(r["data"])
            print(f"{tpl['key']:8s} {fmt:5s} {len(r['data']):>7d}B  "
                  + " / ".join(f"{s['title']}({s['count']})" for s in r["sections"]))


def _render(profile, tpl, fmt):
    """复刻 generate() 的后半段：不查库，直接用构造好的 profile。"""
    match = rx.evaluate(profile, "internet", "frontend")
    target = rx.find_job("internet", "frontend")
    sections = rx.build_sections(profile, target, match, tpl)
    header = rx.build_header(profile, target, {"job_type": "校招全职", "city": "成都",
                                               "match_score": match["score"]})
    data = rx.render_pdf(header, sections, tpl) if fmt == "pdf" else rx.render_docx(header, sections, tpl)
    return {"data": data, "sections": [{"title": s.title, "count": len(s.entries)} for s in sections]}


if __name__ == "__main__":
    main()
