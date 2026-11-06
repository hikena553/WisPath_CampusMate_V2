"""排课调整（调课 / 增课）的业务层：校验、冲突检测、审批落地。

为什么值得单独成服务
--------------------
「这条申请能不能通过」的判定有三处需要一致：

1. 教师提交时——提前挡住明显冲突，别让老师白填一遍再被驳；
2. 审批人确认时——冲突提示要显示在审批卡片上；
3. 真正写回 ``courses`` 时——此时数据可能已经变了（别人刚占了这间教室）。

三处都调用 :func:`detect_conflicts`，「提示」与「拦截」用同一份口径，
不会出现「页面说没冲突、点了通过却报错」的情况。

审批落地的两条路径
------------------
- **调课**：原地修改 ``Course`` 的时间 / 地点 / 教师（不新建行，否则学生会看到两门课）；
- **增课**：新建一行 ``Course``。教师归属一律走 :func:`resolve_teacher_id`，
  保证 ``teacher_id`` 被写上——只有它能回答「这位老师教哪些课」。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.academic import ClassGroup, Course
from app.models.notification import NotificationType
from app.models.schedule_change import (
    ScheduleChangeKind,
    ScheduleChangeRequest,
    ScheduleChangeStatus,
)
from app.models.user import User, UserRole
from app.services import learning_event_service
from app.services.notification_service import send_notification
from app.services.teaching_scope import default_semester, is_my_course, resolve_teacher_id

logger = logging.getLogger(__name__)

KIND_LABEL = {ScheduleChangeKind.SWAP: "调课", ScheduleChangeKind.ADD: "增课"}
STATUS_LABEL = {
    ScheduleChangeStatus.PENDING: "待审批",
    ScheduleChangeStatus.APPROVED: "已通过",
    ScheduleChangeStatus.REJECTED: "已驳回",
    ScheduleChangeStatus.CANCELLED: "已撤回",
}

WEEKDAY_LABEL = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def weekday_label(day: int | None) -> str:
    if not day or day < 1 or day > 7:
        return "—"
    return WEEKDAY_LABEL[day]


def detect_pending_conflicts(
    db: Session,
    *,
    semester: str,
    day_of_week: int,
    start_period: int,
    end_period: int,
    week_start: int,
    week_end: int,
    class_group_id: int,
    teacher_id: int | None,
    teacher_name: str,
    location: str,
    exclude_request_id: int | None = None,
) -> list[str]:
    """检测与**其他待审批申请**的时段冲突。

    为什么必须单独查一遍
    --------------------
    待审批的申请还没写进 ``courses``，:func:`detect_conflicts` 看不到它们。
    如果只查正式课表，老师 A 和老师 B 同时申请占用同一间教室、同一时段，
    两条都会显示「无冲突」，审批人看不出问题，最后谁先被批都会挤掉别人。
    """
    q = db.query(ScheduleChangeRequest).filter(
        ScheduleChangeRequest.status == ScheduleChangeStatus.PENDING,
        ScheduleChangeRequest.semester == semester,
        ScheduleChangeRequest.day_of_week == day_of_week,
        ScheduleChangeRequest.start_period <= end_period,
        ScheduleChangeRequest.end_period >= start_period,
        ScheduleChangeRequest.week_start <= week_end,
        ScheduleChangeRequest.week_end >= week_start,
    )
    if exclude_request_id:
        q = q.filter(ScheduleChangeRequest.id != exclude_request_id)
    rows = q.all()
    if not rows:
        return []

    tips: list[str] = []
    for r in rows:
        label = f"待审批#{r.id} {r.course_name}（{r.applicant_name}）"
        # 同一条申请可能同时撞班级、撞教师、撞教室，合并成一句话
        # （否则审批卡片上同一件事被说三遍，反而看不清到底有几条冲突）
        hits: list[str] = []
        if r.class_group_id == class_group_id:
            hits.append("同班级")
        if (teacher_id and r.teacher_id == teacher_id) or (
            not r.teacher_id and teacher_name and r.teacher_name == teacher_name
        ):
            hits.append("同教师")
        if location and r.location and r.location.strip() == location.strip():
            hits.append(f"同教室 {location}")
        if hits:
            tips.append(f"{'、'.join(hits)}另有待审批申请占用该时段：{label}")
    return tips


def detect_conflicts(
    db: Session,
    *,
    semester: str,
    day_of_week: int,
    start_period: int,
    end_period: int,
    week_start: int,
    week_end: int,
    class_group_id: int,
    teacher_id: int | None,
    teacher_name: str,
    location: str,
    exclude_course_id: int | None = None,
) -> list[str]:
    """检测目标时段的三类冲突，返回人类可读的提示（空列表 = 无冲突）。

    判定口径：
    - **同班级撞课**：同一班级、同一学期、同一星期、节次区间重叠、教学周区间重叠；
    - **同教师撞课**：同上，但按教师匹配（结构化 id 优先，姓名兜底）；
    - **同教室撞课**：同上，但按地点匹配（地点为空不判定，避免「待定」互相冲突）。

    调课时 ``exclude_course_id`` 传原课程 id——它本来就在那个时段，不算冲突。
    """
    if end_period < start_period:
        return ["节次区间不合法：结束节次早于开始节次"]
    if week_end < week_start:
        return ["教学周区间不合法：结束周早于开始周"]
    if day_of_week < 1 or day_of_week > 7:
        return ["星期取值不合法（1-7）"]

    base = (
        db.query(Course)
        .filter(Course.semester == semester)
        .filter(Course.day_of_week == day_of_week)
        # 节次重叠：A.start <= B.end AND A.end >= B.start
        .filter(Course.start_period <= end_period)
        .filter(Course.end_period >= start_period)
        # 教学周重叠
        .filter(Course.week_start <= week_end)
        .filter(Course.week_end >= week_start)
    )
    if exclude_course_id:
        base = base.filter(Course.id != exclude_course_id)
    candidates = base.all()
    if not candidates:
        return []

    tips: list[str] = []
    for c in candidates:
        label = f"{c.name}（{weekday_label(c.day_of_week)} 第{c.start_period}-{c.end_period}节）"
        # 同一门课可能同时撞班级 / 教师 / 教室，合并成一条，避免同一件事说三遍
        hits: list[str] = []
        if c.class_group_id == class_group_id:
            hits.append("班级")
        is_same_teacher = (
            (teacher_id is not None and c.teacher_id == teacher_id)
            or (c.teacher_id is None and teacher_name and c.teacher == teacher_name)
        )
        if is_same_teacher:
            hits.append("授课教师")
        if location and c.location and c.location.strip() == location.strip():
            hits.append(f"教室 {location}")
        if hits:
            tips.append(f"{'、'.join(hits)}在该时段已有课：{label}")
    return tips


def build_course_from_request(db: Session, req: ScheduleChangeRequest) -> Course:
    """按申请单目标字段构造一条 ``Course``（不 commit）。"""
    teacher = db.query(User).filter(User.id == req.teacher_id).first() if req.teacher_id else None
    teacher_name = teacher.name if teacher else (req.teacher_name or req.applicant_name)
    return Course(
        class_group_id=req.class_group_id,
        name=req.course_name,
        teacher_id=req.teacher_id or resolve_teacher_id(db, teacher_name),
        teacher=teacher_name,
        location=req.location or "",
        day_of_week=req.day_of_week,
        start_period=req.start_period,
        end_period=req.end_period,
        week_start=req.week_start,
        week_end=req.week_end,
        semester=req.semester,
        credit=req.credit,
    )


def _add_skip_week(course: Course, week_no: int) -> None:
    """把某一周记进 course.skip_weeks（幂等，去重后按升序存）。"""
    weeks = {int(x) for x in (course.skip_weeks or "").split(",") if x.strip().isdigit()}
    weeks.add(int(week_no))
    course.skip_weeks = ",".join(str(w) for w in sorted(weeks)) or None


def skipped_weeks(course: Course) -> set[int]:
    """解析 course.skip_weeks，供读课表的调用方判断该周是否要跳过。"""
    return {int(x) for x in (course.skip_weeks or "").split(",") if x.strip().isdigit()}


def apply_approved(db: Session, req: ScheduleChangeRequest) -> int | None:
    """审批通过后写回正式课表，返回生效的课程 id。

    **调课是「单次调课」，不是改整门课**
    ------------------------------------
    旧实现在这里直接把原课的 day_of_week / week_start / week_end 全改了——
    等于把整门课整个学期都搬走，原时间从此消失，学生下节课就没了。
    这与「把本周的课挪到以后某一周的某一天补上」完全不是一回事。

    正确做法：
    1. 原课**不动**，只把被挪走的那一周记进 ``skip_weeks``（该周不再显示原时间）；
    2. 另建一条 ``week_start == week_end == 目标周`` 的课程，代表这一周的实际上课时间；
    3. 学生端/教师端按周读课表时，跳过 ``skip_weeks`` 命中的周，于是「本周消失、目标周出现」。
    """
    if req.kind == ScheduleChangeKind.SWAP and req.course_id:
        course = db.query(Course).filter(Course.id == req.course_id).first()
        if not course:
            # 课程在审批期间被删除：申请单仍标记通过，但不产生任何排课副作用
            logger.warning("调课申请 %s 对应的课程 %s 已不存在", req.id, req.course_id)
            return None

        # 被挪走的是哪一周：优先用申请里记录的原始周次；缺失时退回目标周
        origin_week = req.origin_week_no or req.week_start or course.week_start
        _add_skip_week(course, origin_week)

        # 原课如果本身是某次调课补出来的单次课，挪走等于这条补课作废：
        # 直接把它的生效周改到目标周即可，不要再叠一条新的，否则会越调越多。
        if course.week_start == course.week_end:
            course.week_start = req.week_start
            course.week_end = req.week_end
            course.day_of_week = req.day_of_week
            course.start_period = req.start_period
            course.end_period = req.end_period
            if req.location:
                course.location = req.location
            course.skip_weeks = None
            db.flush()
            return course.id

        makeup = Course(
            class_group_id=course.class_group_id,
            name=course.name,
            teacher_id=req.teacher_id or course.teacher_id,
            teacher=(db.get(User, req.teacher_id).name if req.teacher_id and db.get(User, req.teacher_id) else course.teacher),
            location=req.location or course.location,
            day_of_week=req.day_of_week,
            start_period=req.start_period,
            end_period=req.end_period,
            # 单次课只在目标那一周生效
            week_start=req.week_start,
            week_end=req.week_start,
            semester=course.semester,
            credit=course.credit,
            source_change_id=req.id,
        )
        db.add(makeup)
        db.flush()
        return makeup.id

    course = build_course_from_request(db, req)
    db.add(course)
    db.flush()
    return course.id


def notify_students(db: Session, req: ScheduleChangeRequest, course: Course | None) -> int:
    """把变更告知该班级学生，返回通知条数。

    学生课表本身是实时查 ``courses``，不发通知也「能看到」；
    但调课最要紧的是**别让他们白跑一趟**，所以被动数据之外还要一次主动告知。
    """
    if not req.class_group_id:
        return 0
    students = (
        db.query(User)
        .filter(User.role == UserRole.STUDENT, User.class_group_id == req.class_group_id)
        .all()
    )
    if not students:
        return 0
    when = f"第{req.week_start}周 {weekday_label(req.day_of_week)} 第{req.start_period}-{req.end_period}节"
    if req.kind == ScheduleChangeKind.SWAP:
        origin_week = req.origin_week_no or req.origin_week_start
        origin = f"第{origin_week}周 {weekday_label(req.origin_day_of_week)} 第{req.origin_start_period}-{req.origin_end_period}节"
        title = f"调课通知：{req.course_name}"
        # 说清「哪一次的课挪走了」和「什么时候补上」，学生才知道下周这个点不用来
        content = f"《{req.course_name}》原定 {origin} 的课已调整，改为 {when} 上课"
        if req.location:
            content += f"，地点 {req.location}"
    else:
        title = f"新增课程：{req.course_name}"
        content = f"新增《{req.course_name}》，上课时间 {when}"
        if req.location:
            content += f"，地点 {req.location}"
    for s in students:
        send_notification(
            db,
            s.id,
            title=title,
            content=content,
            notification_type=NotificationType.APPROVAL,
            # 学生端课表页：调课结果直接落到能看见新时间的地方
            link="/student/schedule",
            related_id=course.id if course else None,
            sender_id=req.approver_id,
        )
    return len(students)


def create_request(db: Session, teacher: User, payload) -> ScheduleChangeRequest:
    """教师发起申请：校验 + 落库（不 commit，由 API 层统一提交）。

    校验失败抛 ``ValueError``，由 API 层转 400——这里是唯一知道
    「什么算合法申请」的地方，API 层不重复判断。
    """
    kind_raw = (payload.kind or "swap").strip().lower()
    if kind_raw not in ("swap", "add"):
        raise ValueError("申请类型只能是 swap（调课）或 add（增课）")
    kind = ScheduleChangeKind(kind_raw)

    course: Course | None = None
    if kind == ScheduleChangeKind.SWAP:
        if not payload.course_id:
            raise ValueError("调课申请必须指定要调整的课程")
        course = db.query(Course).filter(Course.id == payload.course_id).first()
        if not course:
            raise ValueError("课程不存在，可能已被删除")
        if not is_my_course(course, teacher):
            raise ValueError("只能申请调整自己任教课程")

    class_group_id = payload.class_group_id or (course.class_group_id if course else None)
    if not class_group_id:
        raise ValueError("请选择班级")
    class_group = db.query(ClassGroup).filter(ClassGroup.id == class_group_id).first()
    if not class_group:
        raise ValueError("班级不存在")

    semester = (payload.semester or (course.semester if course else None) or default_semester(db) or "").strip()
    if not semester:
        raise ValueError("无法确定学期，请先在课程表中导入排课数据")

    course_name = (payload.course_name or (course.name if course else "") or "").strip()
    if not course_name:
        raise ValueError("请填写课程名称")
    if kind == ScheduleChangeKind.ADD and not payload.teacher_id:
        # 增课默认授给申请人本人：老师申请增课，通常就是自己要上
        payload.teacher_id = teacher.id

    teacher_row = db.query(User).filter(User.id == payload.teacher_id).first() if payload.teacher_id else teacher
    teacher_name = teacher_row.name if teacher_row else teacher.name
    if kind == ScheduleChangeKind.ADD and teacher_row and teacher_row.role != UserRole.TEACHER:
        raise ValueError("授课教师必须是教师账号")

    location = (payload.location if payload.location is not None else "") or (course.location if course else "")
    if kind == ScheduleChangeKind.SWAP:
        # 单次调课：目标只落在某一周，week_start / week_end 都收敛到 target_week，
        # 语义是「把第 origin_week 周这一次课挪到第 target_week 周」。
        origin_week_no = payload.origin_week_no or (course.week_start if course else 1)
        target_week = payload.target_week or payload.week_start or origin_week_no
        if course and not (course.week_start <= origin_week_no <= course.week_end):
            raise ValueError(
                f"课程只在第 {course.week_start}-{course.week_end} 周上课，第 {origin_week_no} 周没有这门课"
            )
        if target_week < 1:
            raise ValueError("目标周次不合法")
        if target_week == origin_week_no and course \
                and course.day_of_week == payload.day_of_week \
                and course.start_period == payload.start_period \
                and course.end_period == payload.end_period:
            raise ValueError("目标仍是同一周同一时段，无需调课")
        week_start = target_week
        week_end = target_week
    else:
        origin_week_no = None
        week_start = payload.week_start or (course.week_start if course else 1)
        week_end = payload.week_end or (course.week_end if course else 16)
        if week_end < week_start:
            raise ValueError("结束周不能早于开始周")

    conflicts = detect_conflicts(
        db,
        semester=semester,
        day_of_week=payload.day_of_week,
        start_period=payload.start_period,
        end_period=payload.end_period,
        week_start=week_start,
        week_end=week_end,
        class_group_id=class_group_id,
        teacher_id=payload.teacher_id,
        teacher_name=teacher_name,
        location=location,
        exclude_course_id=course.id if course else None,
    )
    if conflicts:
        # 提交阶段硬拦：这些冲突审批人也不可能放行，让老师当场改比等驳回快
        raise ValueError("所选时段存在冲突：" + "；".join(conflicts))

    # 与其它待审申请的重叠不硬拦（先到先审是教务的常规做法），但要在审批卡片上提示
    pending_tips = detect_pending_conflicts(
        db,
        semester=semester,
        day_of_week=payload.day_of_week,
        start_period=payload.start_period,
        end_period=payload.end_period,
        week_start=week_start,
        week_end=week_end,
        class_group_id=class_group_id,
        teacher_id=payload.teacher_id,
        teacher_name=teacher_name,
        location=location,
    )
    if pending_tips:
        reason = (payload.reason or "").strip()
        note = "【同批次待审重叠】" + "；".join(pending_tips)
        stored_reason = f"{reason}\n{note}" if reason else note
    else:
        stored_reason = (payload.reason or "").strip()

    req = ScheduleChangeRequest(
        kind=kind,
        status=ScheduleChangeStatus.PENDING,
        applicant_id=teacher.id,
        applicant_name=teacher.name,
        course_id=course.id if course else None,
        origin_day_of_week=course.day_of_week if course else None,
        origin_start_period=course.start_period if course else None,
        origin_end_period=course.end_period if course else None,
        origin_location=course.location if course else None,
        origin_teacher=course.teacher if course else None,
        origin_week_start=course.week_start if course else None,
        origin_week_end=course.week_end if course else None,
        origin_week_no=origin_week_no,
        class_group_id=class_group_id,
        class_name=class_group.name,
        course_name=course_name,
        teacher_id=payload.teacher_id or (course.teacher_id if course else None),
        teacher_name=teacher_name,
        location=location,
        day_of_week=payload.day_of_week,
        start_period=payload.start_period,
        end_period=payload.end_period,
        week_start=week_start,
        week_end=week_end,
        semester=semester,
        credit=payload.credit if payload.credit is not None else (course.credit if course else None),
        reason=stored_reason,
    )
    db.add(req)
    db.flush()
    learning_event_service.emit(
        db,
        actor_id=teacher.id,
        verb=f"schedule.{kind.value}.apply",
        object_type="schedule_change",
        object_id=req.id,
        context={
            "course_name": course_name,
            "class_name": class_group.name,
            "day_of_week": payload.day_of_week,
            "start_period": payload.start_period,
            "end_period": payload.end_period,
        },
    )
    return req
