import sys
import logging
from pathlib import Path

# 支持 python app/seed.py 直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.campus import CampusFigure, CampusScenery
from app.models.academic import College, Major, ClassGroup, Course, Grade
from app.models.growth import GrowthRecord, RecordType
from app.models.service import ServiceTicket, TicketType, TicketStatus
from app.models.leave import LeaveRequest, LeaveType, LeaveStatus
from app.models.crisis import AIDialogSummary, CrisisLevel
from app.models.knowledge import KnowledgeItem

logger = logging.getLogger(__name__)

db = SessionLocal()
seeded = False


# ─── 辅助函数 ─────────────────────────────────────────────
def sid(username: str) -> int:
    u = db.query(User).filter(User.username == username).first()
    return u.id if u else 0


def get_or_create(cls, **kwargs):
    obj = db.query(cls).filter_by(**kwargs).first()
    if not obj:
        obj = cls(**kwargs)
        db.add(obj)
        db.flush()
    return obj


# ═══════════════════════════════════════════════════════════
# 1. 组织架构（学院 → 专业 → 班级）
# ═══════════════════════════════════════════════════════════

colleges_data = [
    ("人工智能学院", "AI", "安州校区，培养计算机、软件、电子信息、通信、物联网、人工智能人才"),
    ("智能制造与工程学院", "ME", "安州校区，培养机械、自动化、土木、交通、测绘、电气工程人才"),
    ("创意设计学院", "CD", "安州校区，培养产品设计、新媒体艺术、风景园林、城乡规划、数字媒体技术人才"),
    ("商学院", "BUS", "游仙校区，培养财务管理、电子商务、工商管理、金融工程、物流工程人才"),
    ("健康与教育学院", "HE", "游仙校区，培养体育教育、学前教育、健康服务与管理、英语人才"),
    ("马克思主义学院", "MARX", "负责全校思想政治理论课教学"),
    ("终身教育学院", "LIFE", "负责继续教育与终身学习"),
]
colleges = {}
for name, code, desc in colleges_data:
    c = db.query(College).filter(College.name == name).first()
    if not c:
        c = College(name=name, code=code, description=desc)
        db.add(c)
        db.flush()
    else:
        c.code = code
        c.description = desc
    colleges[name] = c
db.flush()

majors_data = [
    # 人工智能学院
    ("人工智能学院", "计算机科学与技术", "AI01", "计算机系统与应用开发"),
    ("人工智能学院", "软件工程", "AI02", "软件开发与工程管理"),
    ("人工智能学院", "电子信息工程", "AI03", "电子信息系统设计与开发"),
    ("人工智能学院", "通信工程", "AI04", "通信系统与网络工程"),
    ("人工智能学院", "物联网工程", "AI05", "物联网系统设计与应用"),
    ("人工智能学院", "人工智能", "AI06", "AI算法与应用（新增本科）"),
    # 智能制造与工程学院
    ("智能制造与工程学院", "机械设计制造及其自动化", "ME01", "机械设计与制造"),
    ("智能制造与工程学院", "电气工程及其自动化", "ME02", "电气工程与自动化控制"),
    ("智能制造与工程学院", "自动化", "ME03", "自动化系统与控制"),
    ("智能制造与工程学院", "机器人工程", "ME04", "机器人系统设计与应用（新增本科）"),
    ("智能制造与工程学院", "智能制造工程", "ME05", "智能制造技术与系统"),
    ("智能制造与工程学院", "土木工程", "ME06", "建筑工程设计与施工"),
    ("智能制造与工程学院", "工程造价", "ME07", "工程造价管理"),
    ("智能制造与工程学院", "测绘工程", "ME08", "测绘与地理信息"),
    ("智能制造与工程学院", "交通工程", "ME09", "交通规划与工程"),
    ("智能制造与工程学院", "地理信息科学", "ME10", "地理信息系统与空间分析"),
    ("智能制造与工程学院", "能源与环境系统工程", "ME11", "能源与环境系统"),
    # 创意设计学院
    ("创意设计学院", "产品设计", "CD01", "产品造型与交互设计"),
    ("创意设计学院", "新媒体艺术", "CD02", "新媒体艺术与传播"),
    ("创意设计学院", "艺术设计学", "CD03", "艺术设计理论与实践"),
    ("创意设计学院", "风景园林", "CD04", "风景园林规划设计"),
    ("创意设计学院", "城乡规划", "CD05", "城乡规划与设计"),
    ("创意设计学院", "数字媒体技术", "CD06", "数字媒体技术与应用"),
    # 商学院
    ("商学院", "财务管理", "BUS01", "财务管理与会计实务"),
    ("商学院", "电子商务", "BUS02", "电子商务运营与管理"),
    ("商学院", "工商管理", "BUS03", "企业管理与运营"),
    ("商学院", "金融工程", "BUS04", "金融工程与风险管理"),
    ("商学院", "物流工程", "BUS05", "物流系统规划与管理"),
    # 健康与教育学院
    ("健康与教育学院", "体育教育", "HE01", "体育教学与训练"),
    ("健康与教育学院", "休闲体育", "HE02", "休闲体育服务与管理"),
    ("健康与教育学院", "健康服务与管理", "HE03", "健康管理与服务"),
    ("健康与教育学院", "学前教育", "HE04", "学前教育理论与实践"),
    ("健康与教育学院", "英语", "HE05", "英语语言文学与翻译"),
    ("健康与教育学院", "数学与应用数学", "HE06", "数学理论与应用"),
]
majors = {}
for college_name, major_name, code, desc in majors_data:
    m = db.query(Major).filter(Major.college_id == colleges[college_name].id, Major.code == code).first()
    if not m:
        m = Major(college_id=colleges[college_name].id, name=major_name, code=code, description=desc)
        db.add(m)
        db.flush()
    majors[major_name] = m
db.flush()

# 班级（每个专业2024级1-2个班）
class_groups_data = [
    # 人工智能学院
    ("软件工程", 2024, "2024级软件工程1班"),
    ("软件工程", 2024, "2024级软件工程2班"),
    ("计算机科学与技术", 2024, "2024级计算机科学与技术1班"),
    ("电子信息工程", 2024, "2024级电子信息工程1班"),
    ("通信工程", 2024, "2024级通信工程1班"),
    ("物联网工程", 2024, "2024级物联网工程1班"),
    ("人工智能", 2024, "2024级人工智能1班"),
    # 智能制造与工程学院
    ("机械设计制造及其自动化", 2024, "2024级机械设计制造及其自动化1班"),
    ("电气工程及其自动化", 2024, "2024级电气工程及其自动化1班"),
    ("自动化", 2024, "2024级自动化1班"),
    ("土木工程", 2024, "2024级土木工程1班"),
    ("工程造价", 2024, "2024级工程造价1班"),
    # 创意设计学院
    ("产品设计", 2024, "2024级产品设计1班"),
    ("数字媒体技术", 2024, "2024级数字媒体技术1班"),
    ("风景园林", 2024, "2024级风景园林1班"),
    # 商学院
    ("财务管理", 2024, "2024级财务管理1班"),
    ("电子商务", 2024, "2024级电子商务1班"),
    ("工商管理", 2024, "2024级工商管理1班"),
    ("金融工程", 2024, "2024级金融工程1班"),
    # 健康与教育学院
    ("体育教育", 2024, "2024级体育教育1班"),
    ("学前教育", 2024, "2024级学前教育1班"),
    ("英语", 2024, "2024级英语1班"),
]
class_groups = {}
for major_name, grade, cg_name in class_groups_data:
    cg = db.query(ClassGroup).filter(
        ClassGroup.major_id == majors[major_name].id,
        ClassGroup.grade == grade,
        ClassGroup.name == cg_name,
    ).first()
    if not cg:
        cg = ClassGroup(major_id=majors[major_name].id, grade=grade, name=cg_name)
        db.add(cg)
        db.flush()
    class_groups[cg_name] = cg
db.flush()


# ═══════════════════════════════════════════════════════════
# 2. 用户
# ═══════════════════════════════════════════════════════════

# 学生：学号 → (姓名, 班级名, 学院名)
students_map = {
    "2024001": ("张三", "2024级软件工程1班", "人工智能学院"),
    "2024002": ("李四", "2024级软件工程1班", "人工智能学院"),
    "2024003": ("王五", "2024级计算机科学与技术1班", "人工智能学院"),
    "2024004": ("赵六", "2024级软件工程2班", "人工智能学院"),
    "2024005": ("钱七", "2024级电子信息工程1班", "人工智能学院"),
    "2024006": ("孙八", "2024级土木工程1班", "智能制造与工程学院"),
    "2024007": ("周九", "2024级财务管理1班", "商学院"),
    "2024008": ("吴十", "2024级体育教育1班", "健康与教育学院"),
    "2024009": ("郑十一", "2024级电子商务1班", "商学院"),
}

if db.query(User).count() == 0:
    users = [
        User(username="admin", password_hash=hash_password("admin123"), name="管理员", role=UserRole.ADMIN),
        User(username="t1001", password_hash=hash_password("123456"), name="王老师", role=UserRole.TEACHER, college="人工智能学院", title="导师", department="绵阳城市学院"),
        User(username="t1002", password_hash=hash_password("123456"), name="李老师", role=UserRole.TEACHER, college="人工智能学院", title="导师", department="绵阳城市学院"),
        User(username="t1003", password_hash=hash_password("123456"), name="陈慧敏", role=UserRole.TEACHER, college="人工智能学院", title="导师", department="绵阳城市学院"),
        User(username="t1004", password_hash=hash_password("123456"), name="张伟明", role=UserRole.TEACHER, college="智能制造与工程学院", title="导师", department="绵阳城市学院"),
        User(username="t1005", password_hash=hash_password("123456"), name="刘雅婷", role=UserRole.TEACHER, college="智能制造与工程学院", title="导师", department="绵阳城市学院"),
        User(username="t1006", password_hash=hash_password("123456"), name="赵志强", role=UserRole.TEACHER, college="商学院", title="导师", department="绵阳城市学院"),
        User(username="t1007", password_hash=hash_password("123456"), name="林晓娟", role=UserRole.TEACHER, college="健康与教育学院", title="导师", department="绵阳城市学院"),
    ]
    db.add_all(users)
    db.commit()
    seeded = True

# 创建学生并绑定班级
for uname, (name, cg_name, college) in students_map.items():
    u = db.query(User).filter(User.username == uname).first()
    if not u:
        u = User(username=uname, password_hash=hash_password("123456"), name=name, role=UserRole.STUDENT, college=college)
        db.add(u)
    u.class_group_id = class_groups[cg_name].id
    u.class_name = cg_name
db.commit()

# ─── 学生-导师绑定 ─────────────────────────────────────────
tutor_bindings = [
    ("2024001", "t1003"), ("2024003", "t1004"), ("2024004", "t1003"),
    ("2024005", "t1004"), ("2024006", "t1005"), ("2024007", "t1006"),
    ("2024008", "t1007"), ("2024009", "t1003"),
]
for su, tu in tutor_bindings:
    s = db.query(User).filter(User.username == su).first()
    t = db.query(User).filter(User.username == tu).first()
    if s and t and not s.tutor_id:
        s.tutor_id = t.id
db.commit()

teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
for t in teachers:
    if not t.title:
        t.title = "导师"
    if not t.department:
        t.department = "绵阳城市学院"
db.commit()


# ═══════════════════════════════════════════════════════════
# 3. 课表（按班级维度，不再逐学生复制）
# ═══════════════════════════════════════════════════════════

SEMESTER = "2024-2025-2"

if db.query(Course).count() == 0:
    all_courses = []

    # ── 2024级软件工程1班（人工智能学院）──
    cg = class_groups["2024级软件工程1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="软件工程", teacher="王老师", location="安州教学楼301", day_of_week=1, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="数据结构", teacher="赵老师", location="安州教学楼205", day_of_week=1, start_period=3, end_period=4, week_start=1, week_end=8, semester=SEMESTER, credit=4),
        Course(class_group_id=cg.id, name="操作系统", teacher="陈老师", location="安州教学楼302", day_of_week=3, start_period=1, end_period=2, week_start=9, week_end=16, semester=SEMESTER, credit=4),
        Course(class_group_id=cg.id, name="计算机网络", teacher="刘老师", location="安州实验楼401", day_of_week=5, start_period=5, end_period=6, week_start=1, week_end=12, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="Web前端开发", teacher="张老师", location="安州实验楼301", day_of_week=4, start_period=5, end_period=6, week_start=1, week_end=10, semester=SEMESTER, credit=3),
    ]

    # ── 2024级软件工程2班 ──
    cg = class_groups["2024级软件工程2班"]
    all_courses += [
        Course(class_group_id=cg.id, name="软件工程", teacher="王老师", location="安州教学楼301", day_of_week=1, start_period=5, end_period=6, week_start=1, week_end=12, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="Java程序设计", teacher="张老师", location="安州实验楼301", day_of_week=4, start_period=1, end_period=2, week_start=5, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="离散数学", teacher="王老师", location="安州教学楼302", day_of_week=4, start_period=3, end_period=4, week_start=10, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级计算机科学与技术1班 ──
    cg = class_groups["2024级计算机科学与技术1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="算法设计与分析", teacher="陈老师", location="安州教学楼301", day_of_week=2, start_period=5, end_period=6, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="C++程序设计", teacher="赵老师", location="安州实验楼401", day_of_week=3, start_period=1, end_period=2, week_start=1, week_end=8, semester=SEMESTER, credit=4),
    ]

    # ── 2024级电子信息工程1班 ──
    cg = class_groups["2024级电子信息工程1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="电路分析基础", teacher="李老师", location="安州实验楼501", day_of_week=1, start_period=1, end_period=2, week_start=1, week_end=12, semester=SEMESTER, credit=4),
        Course(class_group_id=cg.id, name="模拟电子技术", teacher="周老师", location="安州实验楼502", day_of_week=3, start_period=3, end_period=4, week_start=1, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级人工智能1班 ──
    cg = class_groups["2024级人工智能1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="深度学习", teacher="吴老师", location="安州实验楼501", day_of_week=2, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="计算机视觉", teacher="周老师", location="安州实验楼502", day_of_week=4, start_period=3, end_period=4, week_start=9, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级土木工程1班（智能制造与工程学院）──
    cg = class_groups["2024级土木工程1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="建筑材料", teacher="黄老师", location="安州建工楼101", day_of_week=1, start_period=1, end_period=2, week_start=1, week_end=10, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="建筑制图", teacher="杨老师", location="安州建工楼204", day_of_week=3, start_period=5, end_period=6, week_start=6, week_end=16, semester=SEMESTER, credit=2),
    ]

    # ── 2024级财务管理1班（商学院）──
    cg = class_groups["2024级财务管理1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="基础会计", teacher="钱老师", location="游仙经管楼301", day_of_week=1, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="财务管理", teacher="孙老师", location="游仙经管楼302", day_of_week=3, start_period=3, end_period=4, week_start=1, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级电子商务1班 ──
    cg = class_groups["2024级电子商务1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="电子商务概论", teacher="赵老师", location="游仙经管楼301", day_of_week=2, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="网络营销", teacher="孙老师", location="游仙经管楼302", day_of_week=4, start_period=3, end_period=4, week_start=9, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级工商管理1班 ──
    cg = class_groups["2024级工商管理1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="管理学原理", teacher="赵老师", location="游仙经管楼301", day_of_week=2, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="微观经济学", teacher="孙老师", location="游仙经管楼302", day_of_week=4, start_period=3, end_period=4, week_start=1, week_end=8, semester=SEMESTER, credit=3),
    ]

    # ── 2024级金融工程1班 ──
    cg = class_groups["2024级金融工程1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="金融学基础", teacher="钱老师", location="游仙经管楼303", day_of_week=1, start_period=3, end_period=4, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="概率论与数理统计", teacher="赵老师", location="游仙教学楼201", day_of_week=3, start_period=1, end_period=2, week_start=1, week_end=12, semester=SEMESTER, credit=4),
    ]

    # ── 2024级体育教育1班（健康与教育学院）──
    cg = class_groups["2024级体育教育1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="运动解剖学", teacher="林老师", location="游仙体育楼101", day_of_week=1, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="体育教学论", teacher="陈老师", location="游仙教学楼301", day_of_week=3, start_period=3, end_period=4, week_start=1, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级学前教育1班 ──
    cg = class_groups["2024级学前教育1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="学前教育学", teacher="林老师", location="游仙教育楼201", day_of_week=2, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=3),
        Course(class_group_id=cg.id, name="儿童心理学", teacher="陈老师", location="游仙教育楼202", day_of_week=4, start_period=3, end_period=4, week_start=1, week_end=16, semester=SEMESTER, credit=3),
    ]

    # ── 2024级英语1班 ──
    cg = class_groups["2024级英语1班"]
    all_courses += [
        Course(class_group_id=cg.id, name="综合英语", teacher="林老师", location="游仙外语楼101", day_of_week=1, start_period=1, end_period=2, week_start=1, week_end=16, semester=SEMESTER, credit=4),
        Course(class_group_id=cg.id, name="英语听力", teacher="陈老师", location="游仙外语楼201", day_of_week=3, start_period=3, end_period=4, week_start=1, week_end=16, semester=SEMESTER, credit=2),
    ]

    db.add_all(all_courses)
    db.commit()


# ═══════════════════════════════════════════════════════════
# 4. 校园人物 & 风景
# ═══════════════════════════════════════════════════════════

if db.query(CampusFigure).count() == 0:
    db.add_all([
        CampusFigure(name="张三", title="国家奖学金获得者", avatar="/images/avatar1.jpg", description="人工智能学院2024级学生，GPA 3.5+", category="student"),
        CampusFigure(name="赵六", title="ACM竞赛金牌得主", avatar="/images/avatar2.jpg", description="ICPC亚洲区域赛金牌，人工智能学院", category="student"),
        CampusFigure(name="周九", title="优秀学生干部", avatar="/images/avatar3.jpg", description="商学院学生会主席", category="student"),
        CampusFigure(name="王老师", title="优秀教师", avatar="/images/avatar4.jpg", description="人工智能学院副教授，主持多项省级课题", category="teacher"),
        CampusFigure(name="陈慧敏", title="优秀辅导员", avatar="/images/avatar5.jpg", description="人工智能学院辅导员，从事学生工作10年", category="teacher"),
    ])
    db.commit()
    seeded = True

if db.query(CampusScenery).count() == 0:
    db.add_all([
        CampusScenery(title="图书馆（安州）", image_url="/images/lib_anzhou.jpg", description="现代化学习空间", location="校园中心", area="anzhou"),
        CampusScenery(title="教学楼群（安州）", image_url="/images/teaching_anzhou.jpg", description="安州主教学区", location="校园东侧", area="anzhou"),
        CampusScenery(title="校园湖景（安州）", image_url="/images/lake_anzhou.jpg", description="安州休闲景区", location="校园西侧", area="anzhou"),
        CampusScenery(title="图书馆（游仙）", image_url="/images/lib_youxian.jpg", description="游仙图书馆", location="校园中心", area="youxian"),
        CampusScenery(title="教学楼群（游仙）", image_url="/images/teaching_youxian.jpg", description="游仙主教学区", location="校园东侧", area="youxian"),
        CampusScenery(title="校园林荫道（游仙）", image_url="/images/tree_youxian.jpg", description="游仙林荫大道", location="主干道", area="youxian"),
    ])
    db.commit()
    seeded = True


# ═══════════════════════════════════════════════════════════
# 5. 知识库
# ═══════════════════════════════════════════════════════════

if db.query(KnowledgeItem).count() == 0:
    db.add_all([
        KnowledgeItem(category="办事流程", question="怎么请假", answer="请假流程：学生可在对话框输入请假需求，我会自动生成请假申请。也可通过办事服务页面手动提交。"),
        KnowledgeItem(category="办事流程", question="如何申请在校证明", answer="1. 登录系统 2. 进入办事服务页面 3. 选择证明申请 4. 填写信息 5. 审批通过后可在电子版下载。"),
        KnowledgeItem(category="办事流程", question="怎么查课表", answer="对话框输入'查课表'或'今天有什么课'，我会自动调取课表信息。"),
        KnowledgeItem(category="办事流程", question="怎么查成绩", answer="对话框输入'查成绩'自动调取成绩信息，也可到成绩查询页面查看。"),
        KnowledgeItem(category="校园导航", question="图书馆在哪里", answer="安州校区位于校园中心；游仙校区位于校园中心区域。"),
        KnowledgeItem(category="校园导航", question="食堂营业时间", answer="早餐7:00-9:00，午餐11:30-13:00，晚餐17:30-19:00。"),
        KnowledgeItem(category="校园导航", question="体育馆开放时间", answer="周一至周五6:30-21:30，周末8:00-21:00。"),
        KnowledgeItem(category="规章制度", question="宿舍管理规定", answer="按时归寝(23:00前)，禁止违规电器，保持卫生，不得留宿外人。"),
        KnowledgeItem(category="规章制度", question="考试纪律", answer="提前15分钟入场，携带学生证，禁止手机，严禁作弊。"),
        KnowledgeItem(category="规章制度", question="奖学金评定标准", answer="学年GPA排名、综合素质测评、无违纪处分。"),
        KnowledgeItem(category="校园生活", question="校园卡怎么充值", answer="微信小程序、食堂充值窗口、自助充值机。"),
        KnowledgeItem(category="校园生活", question="心理咨询中心", answer="行政楼3楼305室，紧急情况可联系辅导员。"),
    ])
    db.commit()
    seeded = True



# ═══════════════════════════════════════════════════════════
# 6. 成绩
# ═══════════════════════════════════════════════════════════

if db.query(Grade).count() == 0:
    all_grades = []
    zs = sid("2024001")
    all_grades += [
        Grade(student_id=zs, course_name="高等数学(上)", score=72, credit=4, gpa=2.8, semester="2023-2024-1"),
        Grade(student_id=zs, course_name="大学英语(1)", score=68, credit=3, gpa=2.5, semester="2023-2024-1"),
        Grade(student_id=zs, course_name="思修", score=85, credit=2, gpa=3.5, semester="2023-2024-1"),
        Grade(student_id=zs, course_name="高等数学(下)", score=78, credit=4, gpa=3.0, semester="2023-2024-2"),
        Grade(student_id=zs, course_name="大学英语(2)", score=75, credit=3, gpa=2.8, semester="2023-2024-2"),
        Grade(student_id=zs, course_name="C语言", score=82, credit=3, gpa=3.3, semester="2023-2024-2"),
        Grade(student_id=zs, course_name="线性代数", score=80, credit=3, gpa=3.2, semester="2023-2024-2"),
        Grade(student_id=zs, course_name="高等数学(上)", score=85, credit=4, gpa=3.5, semester="2024-2025-1"),
        Grade(student_id=zs, course_name="大学英语", score=78, credit=3, gpa=3.0, semester="2024-2025-1"),
        Grade(student_id=zs, course_name="程序设计基础", score=92, credit=3, gpa=4.0, semester="2024-2025-1"),
        Grade(student_id=zs, course_name="概率论", score=88, credit=3, gpa=3.7, semester="2024-2025-2"),
        Grade(student_id=zs, course_name="数据结构", score=86, credit=4, gpa=3.6, semester="2024-2025-2"),
        Grade(student_id=zs, course_name="数据库原理", score=90, credit=3, gpa=3.8, semester="2024-2025-2"),
        Grade(student_id=zs, course_name="Python", score=93, credit=2, gpa=4.0, semester="2024-2025-2"),
    ]
    ls = sid("2024002")
    all_grades += [
        Grade(student_id=ls, course_name="高等数学(上)", score=61, credit=4, gpa=2.0, semester="2023-2024-1"),
        Grade(student_id=ls, course_name="大学英语(1)", score=55, credit=3, gpa=1.5, semester="2023-2024-1"),
        Grade(student_id=ls, course_name="思修", score=70, credit=2, gpa=2.5, semester="2023-2024-1"),
        Grade(student_id=ls, course_name="高等数学(下)", score=52, credit=4, gpa=1.3, semester="2023-2024-2"),
        Grade(student_id=ls, course_name="大学英语(2)", score=65, credit=3, gpa=2.2, semester="2023-2024-2"),
        Grade(student_id=ls, course_name="C语言", score=45, credit=3, gpa=0.0, semester="2023-2024-2"),
        Grade(student_id=ls, course_name="软件工程", score=72, credit=3, gpa=2.8, semester="2024-2025-1"),
        Grade(student_id=ls, course_name="数据库原理", score=68, credit=3, gpa=2.5, semester="2024-2025-1"),
        Grade(student_id=ls, course_name="Web前端开发", score=80, credit=3, gpa=3.2, semester="2024-2025-2"),
    ]
    ww = sid("2024003")
    all_grades += [
        Grade(student_id=ww, course_name="高等数学(上)", score=91, credit=4, gpa=4.0, semester="2023-2024-1"),
        Grade(student_id=ww, course_name="大学英语(1)", score=88, credit=3, gpa=3.7, semester="2023-2024-1"),
        Grade(student_id=ww, course_name="思修", score=90, credit=2, gpa=3.9, semester="2023-2024-1"),
        Grade(student_id=ww, course_name="高等数学(下)", score=93, credit=4, gpa=4.0, semester="2023-2024-2"),
        Grade(student_id=ww, course_name="大学英语(2)", score=85, credit=3, gpa=3.5, semester="2023-2024-2"),
        Grade(student_id=ww, course_name="C语言", score=92, credit=3, gpa=4.0, semester="2023-2024-2"),
        Grade(student_id=ww, course_name="线性代数", score=90, credit=3, gpa=3.9, semester="2023-2024-2"),
        Grade(student_id=ww, course_name="大数据导论", score=94, credit=3, gpa=4.0, semester="2024-2025-1"),
        Grade(student_id=ww, course_name="Python数据分析", score=96, credit=3, gpa=4.0, semester="2024-2025-1"),
        Grade(student_id=ww, course_name="机器学习基础", score=91, credit=3, gpa=4.0, semester="2024-2025-2"),
        Grade(student_id=ww, course_name="统计学", score=89, credit=3, gpa=3.8, semester="2024-2025-2"),
    ]
    zl = sid("2024004")
    all_grades += [
        Grade(student_id=zl, course_name="高等数学(上)", score=78, credit=4, gpa=3.0, semester="2023-2024-1"),
        Grade(student_id=zl, course_name="离散数学", score=85, credit=3, gpa=3.5, semester="2023-2024-1"),
        Grade(student_id=zl, course_name="C++程序设计", score=82, credit=4, gpa=3.3, semester="2023-2024-1"),
        Grade(student_id=zl, course_name="算法设计", score=88, credit=3, gpa=3.7, semester="2024-2025-1"),
        Grade(student_id=zl, course_name="数据结构", score=90, credit=4, gpa=3.9, semester="2024-2025-1"),
    ]
    qq = sid("2024005")
    all_grades += [
        Grade(student_id=qq, course_name="高等数学(上)", score=75, credit=4, gpa=2.8, semester="2023-2024-1"),
        Grade(student_id=qq, course_name="大学英语(1)", score=70, credit=3, gpa=2.5, semester="2023-2024-1"),
        Grade(student_id=qq, course_name="大数据导论", score=65, credit=3, gpa=2.2, semester="2024-2025-1"),
        Grade(student_id=qq, course_name="统计学", score=58, credit=3, gpa=1.5, semester="2024-2025-1"),
    ]
    zj = sid("2024007")
    all_grades += [
        Grade(student_id=zj, course_name="微观经济学", score=92, credit=3, gpa=4.0, semester="2023-2024-1"),
        Grade(student_id=zj, course_name="管理学原理", score=95, credit=3, gpa=4.0, semester="2023-2024-1"),
        Grade(student_id=zj, course_name="会计学基础", score=88, credit=3, gpa=3.7, semester="2023-2024-1"),
        Grade(student_id=zj, course_name="宏观经济学", score=90, credit=3, gpa=3.9, semester="2024-2025-1"),
        Grade(student_id=zj, course_name="财务管理", score=93, credit=3, gpa=4.0, semester="2024-2025-1"),
    ]
    ws = sid("2024008")
    all_grades += [
        Grade(student_id=ws, course_name="现代服务管理", score=72, credit=3, gpa=2.8, semester="2023-2024-1"),
        Grade(student_id=ws, course_name="客户关系管理", score=68, credit=3, gpa=2.5, semester="2023-2024-1"),
        Grade(student_id=ws, course_name="职场礼仪", score=80, credit=2, gpa=3.2, semester="2024-2025-1"),
    ]
    db.add_all(all_grades)
    db.commit()
    seeded = True


# ═══════════════════════════════════════════════════════════
# 7. 成长记录
# ═══════════════════════════════════════════════════════════

if db.query(GrowthRecord).count() == 0:
    now = date.today()
    records = []
    zs = sid("2024001")
    records += [
        GrowthRecord(student_id=zs, type=RecordType.COMPETITION, title="ACM校赛一等奖", date=now - timedelta(days=180), organizer="软件学院", competition_level="校级"),
        GrowthRecord(student_id=zs, type=RecordType.HONOR, title="国家励志奖学金", date=now - timedelta(days=60), honor_level="国家级"),
        GrowthRecord(student_id=zs, type=RecordType.PRACTICE, title="暑期企业实训", date=now - timedelta(days=120), practice_type="企业实习", practice_certificate="优秀实习生"),
        GrowthRecord(student_id=zs, type=RecordType.ACHIEVEMENT, title="基于AI的考勤系统", date=now - timedelta(days=30), achievement_type="软件著作权"),
    ]
    ls = sid("2024002")
    records += [
        GrowthRecord(student_id=ls, type=RecordType.PRACTICE, title="社区志愿服务", date=now - timedelta(days=200), practice_type="志愿服务"),
        GrowthRecord(student_id=ls, type=RecordType.PRACTICE, title="迎新志愿者", date=now - timedelta(days=90), practice_type="志愿服务"),
        GrowthRecord(student_id=ls, type=RecordType.COMPETITION, title="程序设计天梯赛", date=now - timedelta(days=150), organizer="计算机学院", competition_level="省级"),
    ]
    ww = sid("2024003")
    records += [
        GrowthRecord(student_id=ww, type=RecordType.PAPER, title="基于大数据的用户画像研究", date=now - timedelta(days=45), paper_type="期刊论文", paper_name="计算机应用研究", first_author="王五"),
        GrowthRecord(student_id=ww, type=RecordType.COMPETITION, title="数学建模国赛省一等奖", date=now - timedelta(days=200), organizer="中国工业与应用数学学会", competition_level="省级"),
        GrowthRecord(student_id=ww, type=RecordType.ACHIEVEMENT, title="数据可视化平台", date=now - timedelta(days=100), achievement_type="软件著作权"),
        GrowthRecord(student_id=ww, type=RecordType.HONOR, title="优秀学生标兵", date=now - timedelta(days=30), honor_level="校级"),
    ]
    zl = sid("2024004")
    records += [
        GrowthRecord(student_id=zl, type=RecordType.COMPETITION, title="ICPC亚洲区域赛银奖", date=now - timedelta(days=250), organizer="ACM/ICPC", competition_level="亚洲区"),
        GrowthRecord(student_id=zl, type=RecordType.COMPETITION, title="蓝桥杯省一等奖", date=now - timedelta(days=150), organizer="工业和信息化部", competition_level="省级"),
        GrowthRecord(student_id=zl, type=RecordType.HONOR, title="创新能力先进个人", date=now - timedelta(days=60), honor_level="校级"),
    ]
    qq = sid("2024005")
    records += [GrowthRecord(student_id=qq, type=RecordType.HONOR, title="优秀志愿者", date=now - timedelta(days=300), honor_level="院级")]
    sb = sid("2024006")
    records += [GrowthRecord(student_id=sb, type=RecordType.PRACTICE, title="新生军训优秀学员", date=now - timedelta(days=30), practice_type="军训")]
    zj = sid("2024007")
    records += [
        GrowthRecord(student_id=zj, type=RecordType.HONOR, title="国家奖学金", date=now - timedelta(days=90), honor_level="国家级"),
        GrowthRecord(student_id=zj, type=RecordType.HONOR, title="优秀学生干部", date=now - timedelta(days=180), honor_level="校级"),
        GrowthRecord(student_id=zj, type=RecordType.PAPER, title="共享经济下的大学生消费行为", date=now - timedelta(days=60), paper_type="普刊论文", paper_name="经济研究导刊", first_author="周九"),
        GrowthRecord(student_id=zj, type=RecordType.COMPETITION, title="全国大学生市场调查大赛省一等奖", date=now - timedelta(days=120), organizer="教育部统计学教指委", competition_level="省级"),
        GrowthRecord(student_id=zj, type=RecordType.PRACTICE, title="农业银行实习", date=now - timedelta(days=200), practice_type="企业实习", practice_certificate="优秀实习生"),
    ]
    db.add_all(records)
    db.commit()
    seeded = True


# ═══════════════════════════════════════════════════════════
# 8. 请假记录
# ═══════════════════════════════════════════════════════════

if db.query(LeaveRequest).count() == 0:
    now = date.today()
    leaves = []
    zs = sid("2024001")
    leaves += [
        LeaveRequest(student_id=zs, start_date=now - timedelta(days=60), end_date=now - timedelta(days=58), reason="参加ACM校赛", leave_type=LeaveType.COMPETITION, status=LeaveStatus.APPROVED),
        LeaveRequest(student_id=zs, start_date=now + timedelta(days=5), end_date=now + timedelta(days=7), reason="下周二参加ACM区域赛需要请假三天", leave_type=LeaveType.COMPETITION, status=LeaveStatus.PENDING),
    ]
    ls = sid("2024002")
    leaves += [
        LeaveRequest(student_id=ls, start_date=now - timedelta(days=30), end_date=now - timedelta(days=28), reason="回家办事", leave_type=LeaveType.PERSONAL, status=LeaveStatus.REJECTED, reject_reason="理由不充分，请补充详细信息"),
        LeaveRequest(student_id=ls, start_date=now + timedelta(days=3), end_date=now + timedelta(days=3), reason="身体不舒服想去医院检查", leave_type=LeaveType.SICK, status=LeaveStatus.PENDING),
    ]
    ws = sid("2024008")
    leaves += [
        LeaveRequest(student_id=ws, start_date=now - timedelta(days=90), end_date=now - timedelta(days=90), reason="家中有事", leave_type=LeaveType.PERSONAL, status=LeaveStatus.APPROVED),
        LeaveRequest(student_id=ws, start_date=now - timedelta(days=45), end_date=now - timedelta(days=45), reason="身体不适", leave_type=LeaveType.SICK, status=LeaveStatus.APPROVED),
        LeaveRequest(student_id=ws, start_date=now - timedelta(days=10), end_date=now - timedelta(days=9), reason="参加婚礼", leave_type=LeaveType.PERSONAL, status=LeaveStatus.PENDING),
        LeaveRequest(student_id=ws, start_date=now + timedelta(days=15), end_date=now + timedelta(days=17), reason="外出实习面试", leave_type=LeaveType.PERSONAL, status=LeaveStatus.PENDING),
    ]
    db.add_all(leaves)
    db.commit()
    seeded = True


# ═══════════════════════════════════════════════════════════
# 9. 办事工单
# ═══════════════════════════════════════════════════════════

if db.query(ServiceTicket).count() == 0:
    tickets = []
    zs = sid("2024001")
    tickets += [ServiceTicket(applicant_id=zs, applicant_name="张三", applicant_no="2024001", applicant_college="软件学院", type=TicketType.CERTIFICATE, title="在校证明", content="实习求职需要在校证明", status=TicketStatus.PENDING)]
    ls = sid("2024002")
    tickets += [
        ServiceTicket(applicant_id=ls, applicant_name="李四", applicant_no="2024002", applicant_college="软件学院", type=TicketType.PROJECT, title="科研项目立项", content="基于机器学习的校园助手优化研究", status=TicketStatus.APPROVED),
        ServiceTicket(applicant_id=ls, applicant_name="李四", applicant_no="2024002", applicant_college="软件学院", type=TicketType.CERTIFICATE, title="成绩单申请", content="考研需要", status=TicketStatus.PENDING),
    ]
    ws = sid("2024008")
    tickets += [ServiceTicket(applicant_id=ws, applicant_name="吴十", applicant_no="2024008", applicant_college="现代服务学院", type=TicketType.LEAVE, title="补假申请", content="上周五忘记请假，申请补假", status=TicketStatus.PENDING)]
    db.add_all(tickets)
    db.commit()
    seeded = True


# ═══════════════════════════════════════════════════════════
# 10. 危机预警
# ═══════════════════════════════════════════════════════════

if db.query(AIDialogSummary).count() == 0:
    alerts = []
    ls = sid("2024002")
    alerts += [
        AIDialogSummary(student_id=ls, summary="学生表示近期学习压力大，有焦虑情绪，睡眠质量不佳", level=CrisisLevel.MILD, keywords_matched="焦虑,失眠", resolved=False),
        AIDialogSummary(student_id=ls, summary="学生在对话中提到对未来的迷茫，情绪低落", level=CrisisLevel.NORMAL, keywords_matched="迷茫", resolved=True),
    ]
    qq = sid("2024005")
    alerts += [
        AIDialogSummary(student_id=qq, summary="学生多次提到失眠、焦虑，对考试感到极度恐慌，建议重点关注", level=CrisisLevel.MODERATE, keywords_matched="失眠,焦虑,考试", resolved=False),
        AIDialogSummary(student_id=qq, summary='学生表示"觉得活着没意思"，触发高危关键词，已立即通知辅导员', level=CrisisLevel.SEVERE, keywords_matched="没意思,活着", resolved=False),
    ]
    db.add_all(alerts)
    db.commit()
    seeded = True


db.close()
logger.info("Seed data created successfully")
logger.info("Colleges: 7 (AI/ME/CD/BUS/HE/MARX/LIFE), Majors: 34, ClassGroups: 22")
logger.info("Students: 2024001~2024009 (9 students)")
logger.info("Teachers: t1001~t1007 (7 teachers)")
logger.info("Tutor bindings: 陈慧敏→张三/赵六/郑十一, 张伟明→王五/钱七, etc.")
logger.info("Test accounts: all use password '123456'")
