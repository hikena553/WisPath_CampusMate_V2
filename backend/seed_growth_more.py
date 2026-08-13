"""为成长记录与项目展示补充更多测试数据（幂等：有标记则跳过）。

在 seed_test_data.py 基础上追加更多、更完整的成长记录与项目，
方便验证"查看详情"弹窗的字段展示效果。

运行：python app/seed_growth_more.py   （项目根目录下 python backend/seed_growth_more.py）
"""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datetime import date, timedelta

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.growth import GrowthRecord, RecordType, StudentProject
from app.models.setting import SystemSetting

db = SessionLocal()
rng = random.Random(20260814)

GROWTH_MORE_MARKER = "test_data_growth_more_v1"

HONOR_PLAN = [
    ("国家励志奖学金", "校级", "综合测评专业前10%，品学兼优", "学习成绩优秀，家庭经济困难但仍自强不息"),
    ("三好学生", "校级", "德智体美劳全面发展，连续两年获评", "担任班级学习委员，成绩保持年级前列"),
    ("优秀学生干部", "校级", "服务同学、组织能力强", "策划班级活动十余场，获师生一致好评"),
    ("国家奖学金", "国家级", "成绩年级第一，综合素质突出", "GPA 3.9，主持省级大创项目，发表论文1篇"),
    ("省级优秀毕业生", "省级", "省级就业创业典型", "在校期间多次参与乡村振兴志愿服务"),
    ("最美志愿者", "院级", "累计志愿服务200+小时", "长期参与社区支教与敬老院志愿服务"),
    ("优秀共青团员", "校级", "思想进步，模范带头", "积极参与团组织活动，获校级表彰"),
    ("单项奖学金", "校级", "学科竞赛表现突出", "ACM区域赛铜奖、蓝桥杯省二等奖"),
]

COMPETITION_PLAN = [
    ("ACM-ICPC国际大学生程序设计竞赛", "ACM/ICPC组委会", "国际级", "区域赛铜奖", "算法基础扎实，团队配合默契"),
    ("全国大学生数学建模竞赛", "中国工业与应用数学学会", "国家级", "国家二等奖", "负责建模与论文撰写"),
    ("蓝桥杯全国软件和信息技术专业人才大赛", "工业和信息化部人才交流中心", "省级", "省一等奖", "C/C++组"),
    ("中国互联网+大学生创新创业大赛", "教育部", "国家级", "省赛金奖", "项目负责人，负责商业计划书"),
    ("全国大学生电子设计竞赛", "教育部高教司", "国家级", "省二等奖", "负责硬件设计与调试"),
    ("挑战杯全国大学生课外学术科技作品竞赛", "共青团中央", "省级", "省三等奖", "负责数据采集与统计分析"),
    ("全国大学生英语竞赛", "全国大学生英语竞赛组委会", "省级", "省二等奖", "C类非英语专业组"),
    ("全国大学生物联网设计竞赛", "全国高等学校计算机教育研究会", "国家级", "全国三等奖", "负责云端平台搭建"),
    ("中国大学生计算机设计大赛", "中国大学生计算机设计大赛组委会", "省级", "省一等奖", "作品：智慧校园助手"),
    ("全国大学生信息安全竞赛", "教育部高等学校网络空间安全专业教指委", "国家级", "全国二等奖", "负责渗透测试与漏洞分析"),
]

PRACTICE_PLAN = [
    ("社会志愿活动", "暑期三下乡社会实践", "优秀志愿者", "赴四川凉山开展支教与农产品电商帮扶"),
    ("三下乡", "乡村振兴调研实践", "优秀实践团队", "围绕乡村产业振兴开展问卷调查与访谈"),
    ("支教", "西部计划研究生支教团", "优秀支教志愿者", "赴贵州支教一学年，教授数学与英语"),
    ("西部计划", "西部计划基层服务", None, "在基层乡镇开展信息化建设志愿服务"),
    ("筑梦扬帆计划", "筑梦扬帆技能培训", "结业证书", "参加编程与新媒体运营培训并顺利结业"),
    ("其他社会实践", "企业暑期实习", "优秀实习生", "在互联网公司担任前端开发实习生，参与智慧校园项目"),
    ("社会志愿活动", "校园疫情防控志愿岗", None, "连续两个月负责食堂测温与秩序维护"),
    ("其他社会实践", "返家乡政务实习", "优秀实习生", "在县政府办公室参与公文处理与活动组织"),
]

PAPER_PLAN = [
    ("基于知识图谱的智慧校园问答系统研究", "核心期刊", "《计算机工程与应用》", "2025年6月见刊"),
    ("深度学习在学业预警中的应用", "普刊", "《信息技术与信息化》", "第一作者"),
    ("大学生心理健康影响因素的多维分析", "普刊", "《科教导刊》", "参与省级课题阶段成果"),
    ("基于YOLOv8的校园异常行为检测", "会议论文", "2025 IEEE会议", "EI检索"),
    ("面向移动端的智慧校园应用交互优化", "普刊", "《软件工程》", "第二作者"),
    ("思政教育与专业课程融合路径探索", "核心期刊", "《高教学刊》", "合作研究"),
]

ACHIEVEMENT_PLAN = [
    ("发明专利", "一种基于深度学习的学业预警方法及系统", "学业预警方法发明专利", "实审阶段"),
    ("软件著作权", "校园智能问答助手软件V1.0", "智能问答软件", "已获授权"),
    ("软件著作权", "智慧选课与教务信息管理平台V2.0", "教务管理平台", "已获授权"),
    ("实用新型专利", "一种便携式智能考勤装置", "考勤装置专利", "已授权"),
    ("软件著作权", "大学生心理健康测评与干预系统V1.0", "心理测评软件", "已获授权"),
    ("外观设计专利", "智能校园卡套", "校园卡套外观", "已授权"),
    ("作品著作权", "《青春校园》系列摄影作品集", "摄影作品集", "已登记"),
]

PROJECT_PLAN = [
    ("基于大数据的智慧校园行为分析平台", 60, 150, 0.8, "负责数据采集、行为画像建模与可视化看板"),
    ("校园二手交易与闲置交换小程序", 45, 120, 0.7, "负责前后端开发、支付模块对接与线上运营"),
    ("基于AI的学业预警与帮扶系统", 30, 100, 0.9, "负责算法设计、教师端管理与学生画像"),
    ("新生入学导航与校园服务App", 40, 90, 0.6, "负责地图引擎接入、UI设计与新手引导"),
    ("大学生心理健康自助测评工具", 50, 130, 0.75, "负责量表设计、测评引擎与数据分析"),
    ("智慧教室预约与考勤一体化系统", 35, 80, 0.7, "负责系统架构、考勤算法与数据看板"),
    ("校园失物招领信息共享平台", 25, 70, 0.5, "负责平台搭建、消息推送与运营推广"),
    ("基于大模型的学生成长档案智能生成", 60, 160, 0.85, "负责提示词设计、数据接入与报告生成"),
    ("乡村振兴助农产品电商平台", 30, 110, 0.6, "负责平台开发与农户对接培训"),
    ("智能体驱动的校园综合服务平台", 45, 140, 0.8, "负责智能体编排、工具调用与部署运维"),
]


def is_test_student(u: User) -> bool:
    return u.username and u.username[:4].isdigit() and u.role == UserRole.STUDENT


def pick_title_existing(u: User, title: str) -> bool:
    return db.query(GrowthRecord).filter(
        GrowthRecord.student_id == u.id, GrowthRecord.title == title
    ).count() > 0


def main():
    if db.query(SystemSetting).filter(SystemSetting.key == GROWTH_MORE_MARKER).first():
        print("已检测到标记，跳过补充注入。")
        db.close()
        return

    now = date.today()
    students = [u for u in db.query(User).all() if is_test_student(u)]
    if not students:
        print("未找到测试学生，先运行 seed_test_data.py。")
        db.close()
        return

    g_add = 0
    p_add = 0

    # ── 成长记录：每位学生补 3~6 条，覆盖全部五类 ─────────
    for u in students:
        n = rng.randint(3, 6)
        types = rng.choices(list(RecordType), k=n)
        for i, rt in enumerate(types):
            d = now - timedelta(days=rng.randint(5, 900))
            kw = {}
            if rt == RecordType.HONOR:
                title, level, desc, extra = rng.choice(HONOR_PLAN)
                kw = {"honor_level": level, "description": f"{u.name}：{desc}。{extra}"}
            elif rt == RecordType.COMPETITION:
                comp, org, lvl, award, extra = rng.choice(COMPETITION_PLAN)
                title = comp
                kw = {"organizer": org, "competition_level": lvl,
                      "description": f"获得{award}。{extra}"}
            elif rt == RecordType.PRACTICE:
                ptype, name, cert, extra = rng.choice(PRACTICE_PLAN)
                title = name
                kw = {"practice_type": ptype,
                      "practice_certificate": cert or f"已按时完成并提交实践报告",
                      "description": f"{u.name}参与{name}：{extra}"}
            elif rt == RecordType.PAPER:
                pname, ptype, journal, extra = rng.choice(PAPER_PLAN)
                title = f"{u.name}参与的{pname}研究"
                kw = {"paper_type": ptype, "paper_name": pname,
                      "first_author": u.name,
                      "second_author": rng.choice(["刘伟", "陈静", "张明"]) if rng.random() < 0.6 else None,
                      "third_author": rng.choice(["王磊", "李娜", "赵强"]) if rng.random() < 0.3 else None,
                      "description": f"发表于{journal}。{extra}"}
            else:
                atype, aname, short, extra = rng.choice(ACHIEVEMENT_PLAN)
                title = short
                kw = {"achievement_type": atype, "achievement_name": aname,
                      "description": f"{extra}。申请人：{u.name}"}
            if pick_title_existing(u, title):
                continue
            db.add(GrowthRecord(student_id=u.id, type=rt, title=title,
                                date=d, attachment_url="/uploads/growth/demo.pdf" if rng.random() < 0.35 else None,
                                **kw))
            g_add += 1

    # ── 项目：每位学生补 1~3 个项目，含进行中与已完成 ──────
    names = [s.name for s in students]
    for u in students:
        n = rng.randint(1, 3)
        used = {p.project_name for p in db.query(StudentProject).filter(StudentProject.student_id == u.id).all()}
        for _ in range(n):
            pname, dmin, dmax, team_prob, desc = rng.choice(PROJECT_PLAN)
            if pname in used:
                continue
            used.add(pname)
            start_d = now - timedelta(days=rng.randint(dmin, dmax))
            is_team = rng.random() < team_prob
            ongoing = rng.random() < 0.3
            members = None
            if is_team:
                peers = [nm for nm in names if nm != u.name]
                members = u.name + "、" + "、".join(rng.sample(peers, k=min(3, len(peers))))
            db.add(StudentProject(
                student_id=u.id, project_name=pname,
                start_date=start_d,
                end_date=None if ongoing else start_d + timedelta(days=rng.randint(30, 90)),
                is_team=is_team,
                team_members=members,
                attachment_url="/uploads/projects/demo.pdf" if rng.random() < 0.4 else None,
            ))
            p_add += 1

    db.add(SystemSetting(key=GROWTH_MORE_MARKER, value="1", description="成长记录/项目补充测试数据已注入"))
    db.commit()
    print(f"成长记录新增：{g_add}")
    print(f"项目新增：{p_add}")
    print("补充注入完成。")
    db.close()


if __name__ == "__main__":
    main()
