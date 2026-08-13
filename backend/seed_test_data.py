"""注入 2023-2026 年度全量测试数据（幂等：已注入则跳过）。

覆盖：班级(每个专业×2023/2024/2025/2026四个年级)、学生、教师与导师绑定、
课表/成绩/考试(跨2023-2024-1 ~ 2025-2026-2六个学期)、成长记录、项目、
请假、办事工单、心理危机预警、证书、知识库、校园人物/风景、反馈、通知、
私信、群组、智能体对话、画像快照、教师公告、失物招领、系统设置。

运行：python app/seed_test_data.py
"""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datetime import date, datetime, timedelta, time

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.crypto import encrypt_value
from app.models.user import User, UserRole
from app.models.academic import College, Major, ClassGroup, Course, Grade, Exam
from app.models.growth import GrowthRecord, RecordType, StudentProject
from app.models.leave import LeaveRequest, LeaveType, LeaveStatus
from app.models.service import ServiceTicket, TicketType, TicketStatus
from app.models.crisis import AIDialogSummary, CrisisLevel, InterventionType
from app.models.certificate import Certificate, AwardLevel, CertStatus
from app.models.knowledge import KnowledgeItem
from app.models.campus import CampusFigure, CampusScenery
from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from app.models.notification import Notification, NotificationType
from app.models.message import Message
from app.models.group import Group, GroupMember, GroupMessage
from app.models.conversation import Conversation, ConversationMessage, ConversationType, ProjectTemplate
from app.models.profile import StudentProfileSnapshot
from app.models.announcement import TeacherAnnouncement, UrgencyLevel
from app.models.setting import SystemSetting
from app.models.lost_found import LostFoundItem, ItemType, ItemStatus

logger = logging = sys.modules.get("logging") or __import__("logging")
logging.basicConfig(level=logging.INFO, format="%(message)s")

db = SessionLocal()

GLOBAL_SEMESTERS = [
    "2023-2024-1", "2023-2024-2",
    "2024-2025-1", "2024-2025-2",
    "2025-2026-1", "2025-2026-2",
]
CURRENT_SEMESTER = "2025-2026-2"
GRADE_START = {2023: 0, 2024: 2, 2025: 4, 2026: 6}  # 入学年份 -> 全局学期下标
GRADES = [2023, 2024, 2025, 2026]

# 大学名
CAMPUS_OF = {
    "人工智能学院": "安州",
    "智能制造与工程学院": "安州",
    "创意设计学院": "安州",
    "商学院": "游仙",
    "健康与教育学院": "游仙",
    "马克思主义学院": "游仙",
    "终身教育学院": "游仙",
}

# 每个学院每年的课程模板（6个学期）
COURSE_TEMPLATES: dict[str, list[list[tuple[str, float]]]] = {
    "人工智能学院": [
        [("高等数学(上)", 4), ("大学英语(1)", 3), ("思想道德与法治", 2), ("C语言程序设计", 3), ("大学物理(上)", 3)],
        [("高等数学(下)", 4), ("大学英语(2)", 3), ("线性代数", 3), ("面向对象程序设计", 3), ("中国近现代史纲要", 2)],
        [("概率论与数理统计", 3), ("数据结构", 4), ("离散数学", 3), ("数字逻辑", 3), ("大学物理(下)", 3)],
        [("操作系统", 4), ("数据库原理", 3), ("计算机网络", 3), ("计算机组成原理", 4), ("毛泽东思想和中国特色社会主义理论体系概论", 3)],
        [("软件工程", 3), ("算法设计与分析", 3), ("Web前端开发", 3), ("机器学习基础", 3), ("形势与政策", 1)],
        [("人工智能导论", 3), ("软件测试", 3), ("云计算与大数据", 3), ("毕业设计(开题)", 1)],
    ],
    "智能制造与工程学院": [
        [("高等数学(上)", 4), ("大学英语(1)", 3), ("工程制图", 3), ("思想道德与法治", 2), ("工程力学基础", 3)],
        [("高等数学(下)", 4), ("大学英语(2)", 3), ("线性代数", 3), ("材料力学", 3), ("中国近现代史纲要", 2)],
        [("概率论与数理统计", 3), ("机械原理", 3), ("电工电子技术", 3), ("理论力学", 3), ("毛泽东思想概论", 3)],
        [("机械设计", 4), ("自动控制原理", 3), ("电气控制与PLC", 3), ("结构力学", 3)],
        [("机电一体化系统设计", 3), ("液压与气压传动", 3), ("工程项目管理", 3), ("专业英语", 2), ("形势与政策", 1)],
        [("智能制造技术", 3), ("毕业设计(开题)", 1), ("生产实习", 2), ("现代制造技术", 3)],
    ],
    "创意设计学院": [
        [("设计素描", 3), ("色彩构成", 3), ("三大构成", 3), ("大学英语(1)", 3), ("思想道德与法治", 2)],
        [("设计史", 2), ("设计色彩", 3), ("计算机辅助设计", 3), ("大学英语(2)", 3), ("中国近现代史纲要", 2)],
        [("产品设计原理", 3), ("视觉传达设计", 3), ("人机工程学", 3), ("设计心理学", 2), ("毛泽东思想概论", 3)],
        [("三维建模", 3), ("交互设计", 3), ("景观设计初步", 3), ("数字影像设计", 3)],
        [("产品开发设计", 4), ("品牌设计", 3), ("动态设计", 3), ("设计管理", 2), ("形势与政策", 1)],
        [("毕业设计(开题)", 1), ("综合设计实践", 3), ("艺术考察", 2), ("毕业论文(设计)", 4)],
    ],
    "商学院": [
        [("高等数学(上)", 4), ("大学英语(1)", 3), ("管理学原理", 3), ("经济学基础", 3), ("思想道德与法治", 2)],
        [("高等数学(下)", 4), ("大学英语(2)", 3), ("会计学原理", 3), ("统计学原理", 3), ("中国近现代史纲要", 2)],
        [("财务管理", 4), ("微观经济学", 3), ("金融学概论", 3), ("市场营销学", 3), ("毛泽东思想概论", 3)],
        [("宏观经济学", 3), ("成本会计", 3), ("电子商务概论", 3), ("投资学", 3)],
        [("财务报表分析", 3), ("管理会计", 3), ("国际金融", 3), ("企业战略管理", 3), ("形势与政策", 1)],
        [("毕业论文(设计)", 4), ("财务综合实训", 2), ("毕业实习", 2), ("税法与税务筹划", 3)],
    ],
    "健康与教育学院": [
        [("大学英语(1)", 3), ("教育学基础", 3), ("运动解剖学", 3), ("思想道德与法治", 2), ("普通话与教师口语", 2)],
        [("大学英语(2)", 3), ("心理学基础", 3), ("运动生理学", 3), ("中国近现代史纲要", 2), ("健康教育学", 3)],
        [("学校体育学", 3), ("学前教育学", 3), ("儿童发展心理学", 3), ("运动训练学", 3), ("毛泽东思想概论", 3)],
        [("体育教学论", 3), ("幼儿游戏与指导", 3), ("健康评估", 3), ("英语听说(2)", 2)],
        [("运动保健学", 3), ("幼儿园课程与教学", 3), ("老年健康管理", 3), ("教学设计与评价", 3), ("形势与政策", 1)],
        [("毕业实习", 4), ("毕业论文(设计)", 4), ("教育见习", 2), ("创新创业教育", 1)],
    ],
    "马克思主义学院": [
        [("马克思主义基本原理", 3), ("思想道德与法治", 2), ("形势与政策", 1)],
        [("中国近现代史纲要", 2), ("毛泽东思想和中国特色社会主义理论体系概论", 3), ("习近平新时代中国特色社会主义思想概论", 2)],
        [("马克思主义发展史", 3), ("中国哲学史", 3)],
        [("思想政治教育方法论", 3), ("政治经济学", 3)],
        [("党的建设原理", 3), ("马克思主义经典著作选读", 3)],
        [("毕业实习", 4), ("毕业论文(设计)", 4)],
    ],
    "终身教育学院": [
        [("大学英语(1)", 3), ("现代远程教育概论", 2), ("思想道德与法治", 2)],
        [("大学英语(2)", 3), ("成人教育心理学", 3), ("中国近现代史纲要", 2)],
        [("终身学习与职业发展", 3), ("教育测量与评价", 3)],
        [("社区教育概论", 3), ("培训项目开发", 3)],
        [("学习型社会建设", 3), ("教育研究方法", 3)],
        [("毕业实习", 4), ("毕业论文(设计)", 4)],
    ],
}

SURNAMES = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "褚", "卫", "蒋", "沈", "韩", "杨",
            "朱", "秦", "尤", "许", "何", "吕", "施", "张", "孔", "曹", "严", "华", "金", "魏", "陶", "姜",
            "戚", "谢", "邹", "喻", "柏", "水", "窦", "章", "云", "苏", "潘", "葛", "奚", "范", "彭", "郎",
            "鲁", "韦", "昌", "马", "苗", "凤", "花", "方", "俞", "任", "袁", "柳", "唐", "罗", "薛", "雷"]
GIVEN = ["伟", "芳", "娜", "敏", "静", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英",
         "霞", "平", "刚", "桂英", "鹏", "华", "红", "玉兰", "飞", "强", "斌", "玲", "宇", "浩", "婷", "欣怡",
         "子涵", "梓轩", "浩然", "诗涵", "思远", "梦琪", "俊杰", "雨欣", "天翼", "嘉懿", "若曦", "明轩"]

TEACHER_TITLES = ["讲师", "副教授", "教授", "助教"]


def sid_by_username(username: str) -> int:
    u = db.query(User).filter(User.username == username).first()
    return u.id if u else 0


def get_or_create(cls, **kwargs):
    obj = db.query(cls).filter_by(**kwargs).first()
    if not obj:
        obj = cls(**kwargs)
        db.add(obj)
        db.flush()
    return obj


def score_to_gpa(score: float) -> float:
    if score >= 90:
        return 4.0
    if score >= 85:
        return 3.7
    if score >= 82:
        return 3.3
    if score >= 78:
        return 3.0
    if score >= 75:
        return 2.7
    if score >= 72:
        return 2.3
    if score >= 68:
        return 2.0
    if score >= 64:
        return 1.5
    if score >= 60:
        return 1.0
    return 0.0


def already_seeded() -> bool:
    marker = db.query(SystemSetting).filter(SystemSetting.key == "test_data_seeded_v2").first()
    return marker is not None


def set_marker():
    db.add(SystemSetting(key="test_data_seeded_v2", value="1", description="2023-2026 全量测试数据已注入"))
    db.commit()


# ═══════════════════════════════════════════════════════════
def main():
    if already_seeded():
        logging.info("已检测到测试数据标记 test_data_seeded_v2，跳过注入。")
        db.close()
        return

    rng = random.Random(20260813)
    now = datetime.now()

    # ── 1. 班级：每个专业 × 4 个年级 ──────────────────────
    majors = db.query(Major).all()
    class_groups: dict[tuple[int, int], ClassGroup] = {}
    for m in majors:
        for g in GRADES:
            cg_name = f"{g}级{m.name}1班"
            cg = db.query(ClassGroup).filter(ClassGroup.major_id == m.id, ClassGroup.name == cg_name).first()
            if not cg:
                cg = ClassGroup(major_id=m.id, grade=g, name=cg_name)
                db.add(cg)
                db.flush()
            class_groups[(m.id, g)] = cg
    # 兼容 app/seed.py 中的额外班级（如"2024级软件工程2班"）
    extra_class_ids: list[int] = []
    for cg in db.query(ClassGroup).all():
        key = (cg.major_id, cg.grade)
        if key in class_groups and cg.id != class_groups[key].id:
            extra_class_ids.append(cg.id)
    db.commit()
    logging.info(f"班级：{len(class_groups)} 个（34专业×4年级）")

    # ── 2. 教师（每学院若干） ─────────────────────────────
    college_teachers: dict[str, list[User]] = {}
    teacher_plan = {
        "人工智能学院": ["周建国", "吴慧敏", "郑学锋"],
        "智能制造与工程学院": ["孙志刚", "黄丽华", "徐文博"],
        "创意设计学院": ["许颖", "何佳", "沈子墨"],
        "商学院": ["韩梅", "曹春晖", "沈悦"],
        "健康与教育学院": ["蒋云", "魏洁", "潘璐"],
        "马克思主义学院": ["郭德明", "宋丹"],
        "终身教育学院": ["汪洋", "董倩"],
    }
    tseq = 2000
    for college, names in teacher_plan.items():
        college_teachers[college] = []
        for nm in names:
            tseq += 1
            uname = f"t{tseq}"
            t = db.query(User).filter(User.username == uname).first()
            if not t:
                t = User(username=uname, password_hash=hash_password("123456"), name=nm,
                         role=UserRole.TEACHER, college=college,
                         title=rng.choice(TEACHER_TITLES), department="绵阳城市学院",
                         gender=rng.choice(["男", "女"]),
                         phone=f"138{rng.randint(10000000, 99999999)}")
                db.add(t)
                db.flush()
            college_teachers[college].append(t)
    db.commit()
    teacher_count = db.query(User).filter(User.role == UserRole.TEACHER).count()
    logging.info(f"教师总数：{teacher_count}")

    # ── 3. 学生（每班2~4人）并绑定导师 ─────────────────────
    demo_students: dict[int, User] = {}  # 班级id -> 首位学生(演示账号)
    all_students: list[User] = []
    seq_by_grade = {g: 1 for g in GRADES}
    existing_students_by_class: dict[int, list[User]] = {}
    # 已有学生占用学号段
    existing = db.query(User).filter(User.role == UserRole.STUDENT).all()
    for u in existing:
        if u.username and u.username[:4].isdigit():
            g = int(u.username[:4])
            n = int(u.username[4:])
            if g in seq_by_grade:
                seq_by_grade[g] = max(seq_by_grade[g], n + 1)
        if u.class_group_id:
            existing_students_by_class.setdefault(u.class_group_id, []).append(u)

    for m in majors:
        for g in GRADES:
            cg = class_groups[(m.id, g)]
            pool = existing_students_by_class.get(cg.id, [])
            n_students = max(len(pool), rng.randint(2, 4))
            for i in range(n_students):
                if i < len(pool):
                    u = pool[i]
                    db.add(u)
                    all_students.append(u)
                    if cg.id not in demo_students:
                        demo_students[cg.id] = u
                    continue
                uname = f"{g}{seq_by_grade[g]:03d}"
                seq_by_grade[g] += 1
                name = rng.choice(SURNAMES) + rng.choice(GIVEN)
                teacher = rng.choice(college_teachers[m.college.name])
                u = User(username=uname, password_hash=hash_password("123456"), name=name,
                         role=UserRole.STUDENT, college=m.college.name,
                         class_name=cg.name, class_group_id=cg.id, tutor_id=teacher.id,
                         gender=rng.choice(["男", "女"]),
                         political_status=rng.choice(["共青团员", "中共党员", "群众"]),
                         hometown=rng.choice(["四川绵阳", "四川成都", "四川南充", "四川达州", "重庆", "贵州贵阳"]),
                         phone=f"139{rng.randint(10000000, 99999999)}",
                         age=18 + (2026 - g),
                         skills_json={"skills": [{"name": "python"}, {"name": "office"}, {"name": "沟通"}], "interests": ["阅读", "运动"]})
                db.add(u)
                db.flush()
                all_students.append(u)
                if cg.id not in demo_students:
                    demo_students[cg.id] = u
    # 处理 seed.py 中的额外班级（如 2024级软件工程2班），复用其学生并补充生成
    for cgid in extra_class_ids:
        cg = db.get(ClassGroup, cgid)
        if not cg:
            continue
        pool = existing_students_by_class.get(cg.id, [])
        n_students = max(len(pool), rng.randint(2, 3))
        for i in range(n_students):
            if i < len(pool):
                u = pool[i]
                db.add(u)
                all_students.append(u)
                if cg.id not in demo_students:
                    demo_students[cg.id] = u
                continue
            g = cg.grade
            uname = f"{g}{seq_by_grade[g]:03d}"
            seq_by_grade[g] += 1
            name = rng.choice(SURNAMES) + rng.choice(GIVEN)
            teacher = rng.choice(college_teachers[cg.major.college.name])
            u = User(username=uname, password_hash=hash_password("123456"), name=name,
                     role=UserRole.STUDENT, college=cg.major.college.name,
                     class_name=cg.name, class_group_id=cg.id, tutor_id=teacher.id,
                     gender=rng.choice(["男", "女"]),
                     political_status=rng.choice(["共青团员", "中共党员", "群众"]),
                     hometown=rng.choice(["四川绵阳", "四川成都", "四川南充", "四川达州", "重庆", "贵州贵阳"]),
                     phone=f"139{rng.randint(10000000, 99999999)}",
                     age=18 + (2026 - g),
                     skills_json={"skills": [{"name": "python"}, {"name": "office"}, {"name": "沟通"}], "interests": ["阅读", "运动"]})
            db.add(u)
            db.flush()
            all_students.append(u)
            if cg.id not in demo_students:
                demo_students[cg.id] = u
    db.commit()
    student_count = db.query(User).filter(User.role == UserRole.STUDENT).count()
    logging.info(f"学生总数：{student_count}")

    # ── 4. 课表：每个班级 × 其有效学期 ──────────────────────
    location_pool = {
        "安州": ["安州教学楼101", "安州教学楼302", "安州实验楼401", "安州实验楼502", "安州机房303"],
        "游仙": ["游仙经管楼301", "游仙教学楼201", "游仙外语楼101", "游仙体育楼101", "游仙机房202"],
    }
    created_courses = 0
    all_cg_ids = {cg.id for cg in class_groups.values()}
    all_cg_ids.update(extra_class_ids)
    for cid_ in all_cg_ids:
        cg = db.get(ClassGroup, cid_)
        if not cg:
            continue
        college = cg.major.college.name
        campus = CAMPUS_OF.get(college, "安州")
        templates = COURSE_TEMPLATES.get(college)
        if not templates:
            continue
        g = cg.grade
        start = GRADE_START[g]
        active_life_indices = [i for i in range(start, len(GLOBAL_SEMESTERS))]
        for li in active_life_indices:
            semester = GLOBAL_SEMESTERS[li]
            year_term = li - start  # 0..5
            tpl = templates[year_term] if year_term < len(templates) else templates[-1]
            if db.query(Course).filter(Course.class_group_id == cg.id, Course.semester == semester).count():
                continue
            for cidx, (cname, credit) in enumerate(tpl):
                teacher = rng.choice(college_teachers[college]).name
                day = cidx % 5 + 1
                sp = (cidx * 2) % 8 + 1
                db.add(Course(class_group_id=cg.id, name=cname, teacher=teacher,
                              location=rng.choice(location_pool[campus]),
                              day_of_week=day, start_period=sp, end_period=sp + 1,
                              week_start=1, week_end=20, semester=semester, credit=credit))
                created_courses += 1
    db.commit()
    logging.info(f"课程新增：{created_courses}")

    # ── 5. 成绩：学生 × 有效学期 × 该班课程 ─────────────────
    ability_by_student = {}
    created_grades = 0
    for u in all_students:
        g = int(u.username[:4])
        start = GRADE_START[g]
        cg = db.get(ClassGroup, u.class_group_id)
        ability_by_student[u.id] = rng.uniform(0.35, 1.0)
        for li in range(start, len(GLOBAL_SEMESTERS)):
            semester = GLOBAL_SEMESTERS[li]
            courses = db.query(Course).filter(Course.class_group_id == cg.id, Course.semester == semester).all()
            if not courses:
                continue
            for c in courses:
                if db.query(Grade).filter(Grade.student_id == u.id, Grade.course_name == c.name,
                                         Grade.semester == semester).count():
                    continue
                ability = ability_by_student[u.id]
                score = round(min(99, max(35, ability * 95 + rng.uniform(-10, 8))), 1)
                db.add(Grade(student_id=u.id, course_name=c.name, score=score, credit=c.credit,
                             gpa=score_to_gpa(score), semester=semester))
                created_grades += 1
    db.commit()
    logging.info(f"成绩新增：{created_grades}")

    # ── 6. 考试安排（当前学期） ────────────────────────────
    created_exams = 0
    for u in all_students:
        if int(u.username[:4]) > 2025:
            continue
        cg = db.get(ClassGroup, u.class_group_id)
        courses = db.query(Course).filter(Course.class_group_id == cg.id, Course.semester == CURRENT_SEMESTER).all()
        if not courses:
            continue
        for c in rng.sample(courses, k=min(2, len(courses))):
            exam_date = now.date() + timedelta(days=rng.randint(-15, 25))
            start_t = time(9, 0)
            end_t = time(11, 0)
            db.add(Exam(student_id=u.id, course_name=c.name, exam_date=exam_date,
                        start_time=start_t, end_time=end_t, location=c.location))
            created_exams += 1
    db.commit()
    logging.info(f"考试新增：{created_exams}")

    # ── 7. 成长记录（日期跨2023-2026）──────────────────────
    record_types = [RecordType.HONOR, RecordType.COMPETITION, RecordType.PRACTICE, RecordType.PAPER, RecordType.ACHIEVEMENT]
    created_growth = 0
    for u in all_students:
        n = rng.randint(1, 4)
        for _ in range(n):
            rt = rng.choice(record_types)
            d = now.date() - timedelta(days=rng.randint(30, 1000))
            kw = {}
            if rt == RecordType.HONOR:
                kw = {"honor_level": rng.choice(["院级", "校级", "省级", "国家级"])}
            elif rt == RecordType.COMPETITION:
                kw = {"organizer": rng.choice(["中国计算机学会", "全国大学生数学建模组委会", "教育部高教司", "蓝桥杯组委会"]),
                      "competition_level": rng.choice(["校级", "省级", "国家级"])}
            elif rt == RecordType.PRACTICE:
                kw = {"practice_type": rng.choice(["企业实习", "志愿服务", "三下乡", "迎新志愿者", "暑期社会实践"]),
                      "practice_certificate": rng.choice([None, "优秀实习生", "优秀志愿者"])}
            elif rt == RecordType.PAPER:
                kw = {"paper_type": rng.choice(["普刊", "核心期刊", "会议论文"]),
                      "paper_name": rng.choice(["基于大数据的校园行为分析", "深度学习在智慧校园中的应用", "大学生心理健康影响因素研究"]),
                      "first_author": u.name}
            else:
                kw = {"achievement_type": rng.choice(["软件著作权", "实用新型专利", "发明专利", "外观设计专利"]),
                      "achievement_name": rng.choice(["校园智能问答系统", "智能考勤装置", "智慧选课平台"])}
            title = rng.choice(["国家励志奖学金", "ACM程序设计竞赛", "三好学生", "优秀学生干部", "挑战杯", "数学建模",
                                "暑期社会实践", "志愿者服务", "创新杯", "蓝桥杯"]) + str(d.year)
            if db.query(GrowthRecord).filter(GrowthRecord.student_id == u.id, GrowthRecord.title == title).count():
                continue
            db.add(GrowthRecord(student_id=u.id, type=rt, title=title, description=f"{u.name} 的成长记录",
                            date=d, **kw))
            created_growth += 1
    db.commit()
    logging.info(f"成长记录新增：{created_growth}")

    # ── 8. 学生项目 ────────────────────────────────────────
    created_projects = 0
    for u in all_students:
        if rng.random() < 0.5:
            continue
        cg = db.get(ClassGroup, u.class_group_id)
        start_d = now.date() - timedelta(days=rng.randint(30, 300))
        end_d = start_d + timedelta(days=rng.randint(30, 120))
        name = rng.choice(["智慧校园助手开发", "校园二手交易平台", "基于AI的学业预警系统", "新生导航小程序", "心理健康测评工具"])
        if db.query(StudentProject).filter(StudentProject.student_id == u.id, StudentProject.project_name == name).count():
            continue
        db.add(StudentProject(student_id=u.id, project_name=name, start_date=start_d, end_date=end_d,
                          is_team=rng.random() < 0.6,
                          team_members=f"{u.name}、{'、'.join(rng.sample([s.name for s in all_students[:20] if s.id != u.id], k=min(3, 2)))}" if rng.random() < 0.6 else None,
                          attachment_url="/uploads/projects/demo.pdf" if rng.random() < 0.3 else None))
        created_projects += 1
    db.commit()
    logging.info(f"项目新增：{created_projects}")

    # ── 9. 请假记录 ────────────────────────────────────────
    created_leaves = 0
    for u in all_students:
        n = rng.randint(0, 3)
        for _ in range(n):
            ltype = rng.choice([LeaveType.COMPETITION, LeaveType.SICK, LeaveType.PERSONAL, LeaveType.OTHER])
            start_d = now.date() + timedelta(days=rng.randint(-60, 30))
            end_d = start_d + timedelta(days=rng.randint(1, 4))
            status = rng.choice([LeaveStatus.APPROVED, LeaveStatus.APPROVED, LeaveStatus.PENDING, LeaveStatus.REJECTED])
            lr = LeaveRequest(student_id=u.id, start_date=start_d, end_date=end_d,
                              reason=rng.choice(["参加ACM竞赛", "感冒发烧去医院", "回家办事", "参加婚礼", "外出实习面试"]),
                              leave_type=ltype, status=status,
                              tutor_id=u.tutor_id,
                              reject_reason="理由不充分，请补充材料" if status == LeaveStatus.REJECTED else None)
            db.add(lr)
            created_leaves += 1
    db.commit()
    logging.info(f"请假新增：{created_leaves}")

    # ── 10. 办事工单 ───────────────────────────────────────
    ticket_plan = [
        (TicketType.CERTIFICATE, "在校证明", "实习求职需要在校证明"),
        (TicketType.CERTIFICATE, "成绩单打印", "考研报名需要"),
        (TicketType.PROJECT, "科研项目立项", "基于大数据的校园行为分析立项申请"),
        (TicketType.LEAVE, "补假申请", "上周请假忘记提交申请"),
        (TicketType.PROJECT, "创新创业项目申报", "校园二手平台创业项目申报"),
    ]
    created_tickets = 0
    for u in all_students[:60]:
        if rng.random() < 0.6:
            continue
        ttype, title, content = rng.choice(ticket_plan)
        if db.query(ServiceTicket).filter(ServiceTicket.applicant_id == u.id, ServiceTicket.title == title).count():
            continue
        db.add(ServiceTicket(applicant_id=u.id, applicant_name=u.name, applicant_no=u.username,
                         applicant_college=u.college, type=ttype, title=title, content=content,
                         status=rng.choice([TicketStatus.PENDING, TicketStatus.APPROVED, TicketStatus.PENDING]),
                         form_data={"reason": content}))
        created_tickets += 1
    db.commit()
    logging.info(f"办事工单新增：{created_tickets}")

    # ── 11. 心理危机预警（时间跨近一年，供趋势图）──────────
    crisis_samples = [
        ("student 表示近期学习压力较大，睡眠质量下降，情绪有些焦虑。", CrisisLevel.MILD, "焦虑,失眠"),
        ("学生多次提到对未来迷茫，情绪低落，建议辅导员关注。", CrisisLevel.MODERATE, "迷茫,低落"),
        ("对话中出现'活着没意思'等高危表述，已触发紧急提醒。", CrisisLevel.SEVERE, "没意思,活着"),
        ("学生近期状态正常，学习生活节奏平稳。", CrisisLevel.NORMAL, ""),
        ("学生对考试感到极度恐慌，频繁失眠，建议心理转介。", CrisisLevel.MODERATE, "恐慌,失眠"),
        ("学生表达了对家庭关系的担忧，情绪波动较大。", CrisisLevel.MILD, "家庭,担忧"),
    ]
    created_crisis = 0
    crisis_students = rng.sample(all_students, k=min(40, len(all_students)))
    for u in crisis_students:
        for _ in range(rng.randint(1, 3)):
            summary, level, kw = rng.choice(crisis_samples)
            created_at = now - timedelta(days=rng.randint(0, 350))
            resolved = level != CrisisLevel.SEVERE and rng.random() < 0.7
            c = AIDialogSummary(student_id=u.id, summary=summary, level=level, keywords_matched=kw,
                                resolved=resolved, created_at=created_at,
                                intervention_type=rng.choice(list(InterventionType)) if resolved else None,
                                intervention_note="已与学生谈话沟通，情绪稳定" if resolved else None)
            db.add(c)
            created_crisis += 1
    db.commit()
    logging.info(f"危机预警新增：{created_crisis}")

    # ── 12. 证书 ───────────────────────────────────────────
    cert_plan = [
        ("全国大学生计算机设计大赛", AwardLevel.NATIONAL, "国家二等奖"),
        ("蓝桥杯程序设计大赛", AwardLevel.PROVINCE, "省一等奖"),
        ("英语四级证书", AwardLevel.SCHOOL, "CET-4"),
        ("普通话水平测试", AwardLevel.SCHOOL, "二甲"),
        ("大学生数学建模竞赛", AwardLevel.PROVINCE, "省二等奖"),
    ]
    created_certs = 0
    for u in all_students:
        if rng.random() < 0.7:
            continue
        comp, lvl, desc = rng.choice(cert_plan)
        db.add(Certificate(student_id=u.id, title=desc, competition_name=comp, award_level=lvl,
                       date=now.date() - timedelta(days=rng.randint(30, 600)), description=f"{u.name} 获得{desc}",
                       status=rng.choice([CertStatus.APPROVED, CertStatus.PENDING])))
        created_certs += 1
    db.commit()
    logging.info(f"证书新增：{created_certs}")

    # ── 13. 知识库补充 ─────────────────────────────────────
    kb_items = [
        ("办事流程", "如何申请贫困生认定", "联系辅导员提交《家庭经济困难学生认定申请表》及相关证明材料。"),
        ("办事流程", "怎么补办校园卡", "携带身份证到校园卡服务中心（行政楼101）办理，工本费10元。"),
        ("校园导航", "快递点在哪里", "安州校区：东门快递服务中心；游仙校区：后勤楼一楼。"),
        ("规章制度", "晚自习时间", "周一至周四 19:00-21:00，周五周六无晚自习。"),
        ("校园生活", "校历查询", "可在教务处官网查看最新校历，或问我'这学期第几周'。"),
    ]
    added = 0
    for cat, q, a in kb_items:
        if not db.query(KnowledgeItem).filter(KnowledgeItem.question == q).first():
            db.add(KnowledgeItem(category=cat, question=q, answer=a, tags=cat))
            added += 1
    db.commit()
    logging.info(f"知识库新增：{added}")

    # ── 14. 校园人物 & 风景 ────────────────────────────────
    figures = [
        ("刘嘉懿", "国家奖学金获得者", "人工智能学院2023级，GPA 3.9，主持省级大创项目", "student", None),
        ("陈思远", "优秀学生标兵", "商学院2023级学生会主席，组织多项大型活动", "student", None),
        ("郑皓", "ACM亚洲区域赛银奖", "智能制造与工程学院2023级，算法竞赛达人", "student", None),
        ("何老师", "校级教学名师", "深耕程序设计教学15年，指导多项国家级竞赛", "teacher", None),
        ("优秀校友·刘芳", "知名互联网企业架构师", "2015届计算机科学与技术专业毕业，现就职于头部互联网公司", "alumni", None),
    ]
    fadd = 0
    for name, title, desc, cat, proofs in figures:
        if not db.query(CampusFigure).filter(CampusFigure.name == name).first():
            db.add(CampusFigure(name=name, title=title, avatar=f"/images/avatar{rng.randint(1,5)}.jpg",
                                description=desc, category=cat, proofs=proofs))
            fadd += 1
    sceneries = [
        ("安州校区图书馆", "/images/lib_anzhou.jpg", "藏书丰富，环境优雅", "校园中心", "anzhou"),
        ("游仙校区体育馆", "/images/gym_youxian.jpg", "综合性体育场馆", "校园东侧", "youxian"),
        ("安州校区实验楼", "/images/lab_anzhou.jpg", "现代化实验教学中心", "校园南侧", "anzhou"),
        ("游仙校区林荫道", "/images/tree_youxian.jpg", "四季常青的校园主干道", "主干道", "youxian"),
    ]
    sadd = 0
    for title, img, desc, loc, area in sceneries:
        if not db.query(CampusScenery).filter(CampusScenery.title == title).first():
            db.add(CampusScenery(title=title, image_url=img, description=desc, location=loc, area=area))
            sadd += 1
    db.commit()
    logging.info(f"人物新增:{fadd} 风景新增:{sadd}")

    # ── 15. 反馈 ───────────────────────────────────────────
    feedback_plan = [
        (FeedbackType.BUG, "课表页面加载慢", "切换学期时页面卡顿约3秒"),
        (FeedbackType.FEATURE, "希望增加日程提醒", "想对考试和重要活动做提醒"),
        (FeedbackType.COMPLAINT, "食堂菜价偏贵", "建议增加平价窗口"),
        (FeedbackType.OTHER, "寝室网络不稳定", "晚上高峰时段经常掉线"),
        (FeedbackType.FEATURE, "成绩分析增加雷达图", "想直观看到自己的优劣势"),
    ]
    fback_add = 0
    for u in all_students[:30]:
        if rng.random() < 0.5:
            continue
        ftype, title, content = rng.choice(feedback_plan)
        if db.query(Feedback).filter(Feedback.user_id == u.id, Feedback.title == title).count():
            continue
        fb = Feedback(user_id=u.id, type=ftype, title=title, content=content,
                       contact=u.phone or "", status=rng.choice([FeedbackStatus.PENDING, FeedbackStatus.PROCESSING, FeedbackStatus.RESOLVED]))
        if fb.status == FeedbackStatus.RESOLVED:
            fb.reply = "感谢反馈，已安排相关部门处理。"
        db.add(fb)
        fback_add += 1
    db.commit()
    logging.info(f"反馈新增：{fback_add}")

    # ── 16. 通知 ───────────────────────────────────────────
    notify_plan = [
        (NotificationType.SYSTEM, "系统维护通知", "本周六0:00-6:00系统维护"),
        (NotificationType.APPROVAL, "请假审批结果", "您的请假申请已通过"),
        (NotificationType.LEAVE, "请假提醒", "您有1条请假待审批"),
        (NotificationType.CRISIS, "危机预警提醒", "检测到新的心理危机预警，请及时关注"),
        (NotificationType.ANNOUNCEMENT, "新公告", "教务处发布了新通知"),
    ]
    nadd = 0
    for u in all_students[:40] + [t for tl in college_teachers.values() for t in tl][:20]:
        if rng.random() < 0.6:
            continue
        ntype, title, content = rng.choice(notify_plan)
        db.add(Notification(user_id=u.id, title=title, content=content, type=ntype,
                     is_read=rng.random() < 0.4, link=None))
        nadd += 1
    db.commit()
    logging.info(f"通知新增：{nadd}")

    # ── 17. 私信（师生/学生间） ────────────────────────────
    madd = 0
    for u in all_students:
        if u.tutor_id:
            teacher = db.get(User, u.tutor_id)
            if teacher:
                msg = Message(sender_id=teacher.id, receiver_id=u.id,
                              content=rng.choice(["最近学习情况怎么样？", "有困难及时和我说", "注意劳逸结合，加油！", "别忘了提交周记"]),
                              read=rng.random() < 0.5)
                db.add(msg)
                madd += 1
        if rng.random() < 0.4:
            peer = rng.choice([s for s in all_students if s.id != u.id])
            db.add(Message(sender_id=u.id, receiver_id=peer.id, content=rng.choice(["在吗？借一下作业", "周末一起去图书馆？", "收到，谢谢！"]),
                           read=rng.random() < 0.5))
            madd += 1
    db.commit()
    logging.info(f"私信新增：{madd}")

    # ── 18. 群组（班级群 + 兴趣群）─────────────────────────
    gadd = 0
    gmadd = 0
    gmsgadd = 0
    created_groups: list[Group] = []
    for cg_id, demo in list(demo_students.items()):
        cg = db.get(ClassGroup, cg_id)
        members = [s for s in all_students if s.class_group_id == cg_id]
        if not members:
            continue
        grp_name = f"{cg.name}班群"
        grp = db.query(Group).filter(Group.name == grp_name).first()
        if not grp:
            grp = Group(name=grp_name, creator_id=demo.id, announcement="欢迎加入班级群，遵守群规！", is_dismissed=False)
            db.add(grp)
            db.flush()
            gadd += 1
            # 群主
            db.add(GroupMember(group_id=grp.id, user_id=demo.id, role="owner"))
            gmadd += 1
            for m in members:
                if m.id != demo.id:
                    db.add(GroupMember(group_id=grp.id, user_id=m.id, role="member"))
                    gmadd += 1
            for _ in range(rng.randint(1, 4)):
                sender = rng.choice(members)
                db.add(GroupMessage(group_id=grp.id, sender_id=sender.id,
                                    content=rng.choice(["大家记得交作业", "晚自习教室在301", "谁有上节课的笔记？", "收到！", "周末聚餐有没有人"])))
                gmsgadd += 1
        created_groups.append(grp)
    interest_groups = [
        ("ACM集训队", "算法竞赛爱好者交流群"),
        ("校园摄影社", "记录校园美好瞬间"),
        ("考研互助群", "一起上岸！"),
    ]
    for gname, gdesc in interest_groups:
        if not db.query(Group).filter(Group.name == gname).first():
            owner = rng.choice(all_students)
            grp = Group(name=gname, creator_id=owner.id, announcement=gdesc, is_dismissed=False)
            db.add(grp)
            db.flush()
            gadd += 1
            db.add(GroupMember(group_id=grp.id, user_id=owner.id, role="owner"))
            gmadd += 1
            for m in rng.sample(all_students, k=min(8, len(all_students))):
                if m.id != owner.id:
                    db.add(GroupMember(group_id=grp.id, user_id=m.id, role="member"))
                    gmadd += 1
            for _ in range(rng.randint(1, 3)):
                db.add(GroupMessage(group_id=grp.id, sender_id=rng.choice(all_students).id,
                                    content=rng.choice(["大家好！", "今天训练吗？", "欢迎新人"])))
                gmsgadd += 1
    db.commit()
    logging.info(f"群新增:{gadd} 群成员:{gmadd} 群消息:{gmsgadd}")

    # ── 19. 智能体对话（普通 + 项目）───────────────────────
    cadd = 0
    cmadd = 0
    for u in all_students:
        n_conv = rng.randint(1, 3)
        for ci in range(n_conv):
            is_project = ci == 0 and rng.random() < 0.6
            if is_project:
                ptype = rng.choice(["competition", "thesis", "practice", "certificate"])
                title_map = {"competition": "ACM竞赛", "thesis": "毕业论文", "practice": "社会实践", "certificate": "英语四级"}
                conv = Conversation(user_id=u.id, title=title_map[ptype], type=ConversationType.PROJECT,
                                    project_template=ptype, project_stage=rng.choice(["赛前准备", "方案设计", "实施优化", "答辩展示"]) if ptype == "competition" else rng.choice(["选题开题", "文献综述", "实验调研"]),
                                    is_active=True, updated_at=now - timedelta(hours=rng.randint(1, 96)))
            else:
                conv = Conversation(user_id=u.id, title=rng.choice(["学习计划", "课程咨询", "生活助手"]),
                                    type=ConversationType.NORMAL, is_active=True,
                                    updated_at=now - timedelta(hours=rng.randint(1, 96)))
            db.add(conv)
            db.flush()
            cadd += 1
            q = rng.choice(["我想了解一下这学期的安排", "帮我制定一个复习计划", "图书馆几点开门？", "怎么申请贫困认定？"])
            db.add(ConversationMessage(conversation_id=conv.id, role="user", content=q, timestamp=now - timedelta(hours=2)))
            db.add(ConversationMessage(conversation_id=conv.id, role="assistant", content="好的，我来帮你查询并安排。", timestamp=now - timedelta(hours=2)))
            cmadd += 2
    db.commit()
    logging.info(f"对话新增:{cadd} 对话消息:{cmadd}")

    # ── 20. 画像快照（供趋势图/档案）───────────────────────
    snap_students = rng.sample(all_students, k=min(60, len(all_students)))
    snap_add = 0
    for u in snap_students:
        base = ability_by_student.get(u.id, 0.7)
        for w in range(6):
            d = now.date() - timedelta(weeks=5 - w)
            if db.query(StudentProfileSnapshot).filter(StudentProfileSnapshot.student_id == u.id,
                                                       StudentProfileSnapshot.snapshot_date == d).count():
                continue
            academic = round(min(98, max(40, base * 90 + rng.uniform(-8, 8))), 1)
            risk = round(min(90, max(10, 55 - base * 30 + rng.uniform(-15, 25))), 1)
            db.add(StudentProfileSnapshot(student_id=u.id, snapshot_date=d,
                                   academic_score=academic,
                                   psychological_risk=risk,
                                   engagement_score=round(min(95, max(30, base * 80 + rng.uniform(-10, 15))), 1),
                                   growth_score=round(min(95, max(20, base * 75 + rng.uniform(-10, 20))), 1),
                                   overall_risk=round(min(85, max(5, risk * 0.8 + rng.uniform(-10, 10))), 1),
                                   behavioral_patterns={"study_hours": rng.randint(3, 9), "sports_week": rng.randint(0, 4)},
                                   key_insights=["学习状态稳定", "参与活动积极"]))
            snap_add += 1
    db.commit()
    logging.info(f"画像快照新增：{snap_add}")

    # ── 21. 教师公告 ───────────────────────────────────────
    announce_plan = [
        (UrgencyLevel.NORMAL, "关于第15周教学安排的通知", "请同学们关注本周教学安排，正常上课。"),
        (UrgencyLevel.IMPORTANT, "期中考试时间安排", "期中考试将于第10周进行，请提前复习。"),
        (UrgencyLevel.URGENT, "关于疫情防控的通知", "请全体同学遵守校园疫情防控规定。"),
        (UrgencyLevel.NORMAL, "学术讲座预告", "本周五下午2点举办《人工智能前沿》讲座。"),
        (UrgencyLevel.IMPORTANT, "毕业设计选题开放", "2026届毕业设计选题系统已开放，请及时选题。"),
    ]
    aadd = 0
    for tlist in college_teachers.values():
        for t in tlist[:2]:
            urg, title, content = rng.choice(announce_plan)
            if db.query(TeacherAnnouncement).filter(TeacherAnnouncement.teacher_id == t.id, TeacherAnnouncement.title == title).count():
                continue
            db.add(TeacherAnnouncement(teacher_id=t.id, title=title, content=content, urgency=urg,
                                       created_at=now - timedelta(hours=rng.randint(1, 72))))
            aadd += 1
    db.commit()
    logging.info(f"教师公告新增：{aadd}")

    # ── 22. 失物招领 ───────────────────────────────────────
    lf_plan = [
        (ItemType.LOST, "黑色钱包", "内含身份证和银行卡，丢失于图书馆二楼"),
        (ItemType.FOUND, "校园卡", "在食堂门口捡到，失主请联系认领"),
        (ItemType.LOST, "蓝色耳机", "遗失于体育馆篮球场"),
        (ItemType.FOUND, "红色雨伞", "在教学楼301拾得"),
    ]
    ladd = 0
    for u in all_students[:20]:
        if rng.random() < 0.5:
            continue
        itype, title, desc = rng.choice(lf_plan)
        if db.query(LostFoundItem).filter(LostFoundItem.title == title).count():
            continue
        db.add(LostFoundItem(user_id=u.id, type=itype, title=title, description=desc,
                             location=rng.choice(["图书馆", "食堂", "体育馆", "教学楼", "宿舍"]),
                             contact=u.phone or "", status=rng.choice([ItemStatus.OPEN, ItemStatus.CLAIMED])))
        ladd += 1
    db.commit()
    logging.info(f"失物招领新增：{ladd}")

    # ── 23. 系统设置 ───────────────────────────────────────
    setting_plan = [
        ("site_name", "绵阳城市学院智慧校园", "系统名称"),
        ("site_announcement", "欢迎使用绵阳城市学院智慧校园服务平台", "系统公告"),
        ("llm_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1", "LLM API 地址"),
        ("llm_model", "qwen-turbo", "主模型"),
        ("llm_agent_model", "qwen-turbo", "智能体模型"),
        ("max_chat_history", "50", "最大对话轮数"),
        ("temperature", "0.7", "生成随机性"),
    ]
    sadd2 = 0
    for key, val, desc in setting_plan:
        if db.query(SystemSetting).filter(SystemSetting.key == key).first():
            continue
        db.add(SystemSetting(key=key, value=val, description=desc))
        sadd2 += 1
    # 敏感字段：加密占位（不影响 .env 实际配置）
    if not db.query(SystemSetting).filter(SystemSetting.key == "llm_api_key").first():
        db.add(SystemSetting(key="llm_api_key", value=encrypt_value(""), description="通义千问 API Key（加密存储）"))
        sadd2 += 1
    db.commit()
    logging.info(f"系统设置新增：{sadd2}")

    set_marker()
    logging.info("════════ 测试数据注入完成 ════════")
    logging.info(f"年级：2023~2026 | 学期：{GLOBAL_SEMESTERS}")
    logging.info("演示账号（密码均为 123456）：")
    logging.info("  管理员 admin | 教师 t1001~t1007/t2001+ | 学生 2023001+ / 2024001+ / 2025001+ / 2026001+")
    db.close()


if __name__ == "__main__":
    main()
