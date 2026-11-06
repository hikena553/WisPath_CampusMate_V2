"""教学域 API 的请求 / 响应模型。

命名约定：``Out`` 结尾为响应，``Create`` / ``Patch`` 结尾为请求。响应模型一律
带足展示所需字段，避免前端再发第二次请求（例如点名面板需要课程名与班级名）。
"""
from datetime import date, datetime

from pydantic import BaseModel, Field


# ── 课表 ──────────────────────────────────────────────────────────


class TeachingCourseOut(BaseModel):
    """「我的教学」里的一门课。"""

    id: int
    name: str
    class_group_id: int
    class_name: str = ""
    college_name: str = ""
    teacher: str = ""
    teacher_id: int | None = None
    location: str = ""
    day_of_week: int
    start_period: int
    end_period: int
    week_start: int
    week_end: int
    semester: str
    credit: float | None = None
    student_count: int = 0
    #: 本学期已点名课次数（用于提示「这周还没点过名」）
    attendance_sessions: int = 0
    #: 被单次调课挪走的教学周（原课仍在，只是这几周不上）。
    #: 前端按周渲染时必须跳过这些周，否则会出现「挪走了又还在」。
    skip_weeks: list[int] = []
    #: 由哪张调课申请补出来的（增课为 None），用于在卡片上标「补课」
    source_change_id: int | None = None


class TeachingOverviewOut(BaseModel):
    semester: str | None = None
    semesters: list[str] = []
    current_week: int | None = None
    week_range: str = ""
    today_courses: list[TeachingCourseOut] = []
    courses: list[TeachingCourseOut] = []
    today_course_count: int = 0
    week_course_count: int = 0
    total_student_count: int = 0
    #: 同时被教与被带的学生（育人 + 教学的交集，最有价值的指标）
    overlap_student_count: int = 0


# ── 考勤 ──────────────────────────────────────────────────────────


class AttendanceRosterItem(BaseModel):
    student_id: int
    name: str
    username: str = ""
    avatar: str | None = None
    #: 当前状态，前端据此预置按钮；来自已有记录或请假自动判定
    status: str = "present"
    leave_request_id: int | None = None
    remark: str | None = None
    #: 是否已由请假单自动核销（前端置灰不可改，只能由审批撤销改变）
    auto_leave: bool = False


class AttendanceRosterOut(BaseModel):
    course: TeachingCourseOut
    attend_date: date
    period_start: int
    period_end: int
    roster: list[AttendanceRosterItem] = []
    #: 已点过名的课次日期，供前端提示「这一天已经点过」
    recorded_dates: list[date] = []


class AttendanceMarkItem(BaseModel):
    student_id: int
    status: str = "present"
    remark: str | None = Field(default=None, max_length=200)


class AttendanceMarkIn(BaseModel):
    course_id: int
    attend_date: date
    period_start: int
    period_end: int = 0
    items: list[AttendanceMarkItem]


class AttendanceMarkResult(BaseModel):
    saved: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    leave: int = 0
    excused: int = 0
    #: 本次自动由请假单核销的人数
    auto_leave: int = 0
    #: 本次缺勤自动生成的跟进任务数（已有任务不重复计）
    tasks_created: int = 0


class AttendanceStatRow(BaseModel):
    student_id: int
    name: str
    username: str = ""
    total: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    leave: int = 0
    excused: int = 0
    rate: float = 0
    #: 连续缺勤次数（从最近一次往前数），≥2 在界面上重点标红
    consecutive_absent: int = 0


class AttendanceStatsOut(BaseModel):
    course: TeachingCourseOut
    sessions: int = 0
    student_count: int = 0
    avg_rate: float = 0
    rows: list[AttendanceStatRow] = []


# ── 作业 ──────────────────────────────────────────────────────────


class HomeworkOut(BaseModel):
    id: int
    course_id: int
    course_name: str = ""
    class_group_id: int | None = None
    class_name: str = ""
    title: str
    content: str | None = None
    attachment_url: str | None = None
    due_at: datetime | None = None
    total_score: float = 100
    status: str = "published"
    submitted_count: int = 0
    graded_count: int = 0
    student_count: int = 0
    created_at: datetime | None = None
    #: 逾期未交人数（只是「未交 + 已过截止」，不是处罚，用于提醒教师跟进）
    overdue_count: int = 0


class HomeworkCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=1, max_length=200)
    content: str | None = None
    attachment_url: str | None = None
    due_at: datetime | None = None
    total_score: float = 100


class SubmissionOut(BaseModel):
    student_id: int
    name: str
    username: str = ""
    status: str = "pending"
    content: str | None = None
    attachment_url: str | None = None
    score: float | None = None
    comment: str | None = None
    submitted_at: datetime | None = None
    graded_at: datetime | None = None


class HomeworkDetailOut(BaseModel):
    homework: HomeworkOut
    submissions: list[SubmissionOut] = []


class GradeItem(BaseModel):
    student_id: int
    score: float | None = None
    comment: str | None = None


class GradeIn(BaseModel):
    items: list[GradeItem]


# ── 成绩 ──────────────────────────────────────────────────────────


class CourseGradeRow(BaseModel):
    student_id: int
    name: str
    username: str = ""
    score: float | None = None
    gpa: float | None = None
    #: 与全班均分的差值，用于「相对落后」判定
    delta: float | None = None
    level: str = "unknown"   # excellent / good / pass / fail / no_grade
    #: 是否已被辅导员关怀覆盖（避免重复跟进）
    cared: bool = False


class CourseGradeOut(BaseModel):
    course: TeachingCourseOut
    semester: str
    count: int = 0
    graded: int = 0
    avg: float | None = None
    median: float | None = None
    max_score: float | None = None
    min_score: float | None = None
    pass_rate: float | None = None
    excellent_rate: float | None = None
    distribution: dict[str, int] = {}
    rows: list[CourseGradeRow] = []


class GradeImportItem(BaseModel):
    username: str
    score: float


class GradeImportIn(BaseModel):
    course_id: int
    semester: str | None = None
    items: list[GradeImportItem]


class GradeImportResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: list[str] = []
    #: 低于警戒线、已自动生成学业预警关怀事件的学生姓名
    alerted: list[str] = []


# ── 课表：按任课教师 / 按班级查看 ─────────────────────────────────


class ScheduleTeacherOut(BaseModel):
    """课表筛选器里的一个任课教师。"""

    teacher_id: int | None = None
    name: str
    course_count: int = 0
    class_count: int = 0
    student_count: int = 0
    is_me: bool = False


class ScheduleClassOut(BaseModel):
    """课表筛选器里的一个班级。"""

    class_group_id: int
    name: str
    college_name: str | None = None
    course_count: int = 0
    student_count: int = 0
    is_mine: bool = False


class ScheduleOut(BaseModel):
    """按任意维度（我的 / 任课教师 / 班级）查出的课表，结构同构。"""

    semester: str | None = None
    semesters: list[str] = []
    #: mine / teacher / class
    scope: str = "mine"
    label: str = ""
    courses: list[TeachingCourseOut] = []
    today_courses: list[TeachingCourseOut] = []
    today_course_count: int = 0
    week_course_count: int = 0
    #: 当前教学周（前端周次选择器默认值）
    current_week: int | None = None
    total_student_count: int = 0


# ── 教学待办收件箱：把「课上的事」和「课后该做的事」接上 ──────────────


class TeachingInboxItem(BaseModel):
    """一条教学待办。

    设计口径与 ``teacher_daily_report`` 的 ``actions`` 保持一致：
    每条都带 ``link``（点进去干这件事的具体页面）与 ``can_complete``
    （低风险才能一键办结，高危与审批必须老师亲自走一遍）。
    """

    id: str
    #: attendance —— 今天有课但还没点名
    #: homework   —— 作业待批 / 待催交
    #: alert      —— 成绩低于警戒线的学业预警
    #: task       —— 教学链路派生出来的待办（含管理员派单）
    kind: str
    #: high / mid / low
    priority: str = "mid"
    title: str
    desc: str = ""
    link: str
    course_id: int | None = None
    course_name: str = ""
    class_name: str = ""
    due_text: str = ""
    count: int = 0
    action_text: str = ""
    can_complete: bool = False
    task_id: int | None = None


class TeachingInboxOut(BaseModel):
    """教学页顶部「今天要做什么」的聚合结果。"""

    items: list[TeachingInboxItem] = []
    #: 未点名课程数 / 待批作业数 / 学业预警数 / 派生待办数
    unmarked_count: int = 0
    pending_homework_count: int = 0
    grade_alert_count: int = 0
    task_count: int = 0
    #: 今天一共几节课
    today_course_count: int = 0
    generated_at: str = ""
