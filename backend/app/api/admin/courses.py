from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.models.academic import Course, ClassGroup, Major, College, Semester
from app.schemas.academic import CourseOut, CourseCreate, CourseImportResult

router = APIRouter(tags=["admin"])

# ========== 课程管理 ==========

@router.get("/courses", response_model=list[CourseOut])
def admin_list_courses(
    class_group_id: int | None = Query(None),
    semester: str | None = Query(None),
    college_id: int | None = Query(None),
    major_id: int | None = Query(None),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员获取课程列表，支持多级筛选"""
    q = db.query(Course)
    if class_group_id:
        q = q.filter(Course.class_group_id == class_group_id)
    elif major_id:
        cg_ids = [cg.id for cg in db.query(ClassGroup).filter(ClassGroup.major_id == major_id).all()]
        q = q.filter(Course.class_group_id.in_(cg_ids))
    elif college_id:
        major_ids = [m.id for m in db.query(Major).filter(Major.college_id == college_id).all()]
        cg_ids = [cg.id for cg in db.query(ClassGroup).filter(ClassGroup.major_id.in_(major_ids)).all()]
        q = q.filter(Course.class_group_id.in_(cg_ids))
    if semester:
        q = q.filter(Course.semester == semester)
    return q.order_by(Course.day_of_week, Course.start_period).all()


@router.get("/courses/summary", summary="课程表总览统计", description="统计各学期课程表数量；以及指定学期范围内每个班级的课程编排情况（含未编排班级）")
def admin_courses_summary(
    semester: str | None = Query(None, description="学期，不传则返回全部学期的统计；班级维度的编排情况按该学期统计"),
    college_id: int | None = Query(None),
    major_id: int | None = Query(None),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """课程表总览：学期维度数量 + 班级维度编排情况（未编排班级也返回 course_count=0）"""
    # 1) 班级范围（outerjoin 专业/学院，便于前端直接展示名称）
    cg_q = (
        db.query(
            ClassGroup.id,
            ClassGroup.name,
            ClassGroup.grade,
            ClassGroup.student_count,
            Major.name.label("major_name"),
            College.name.label("college_name"),
        )
        .outerjoin(Major, ClassGroup.major_id == Major.id)
        .outerjoin(College, Major.college_id == College.id)
    )
    if college_id:
        cg_q = cg_q.filter(Major.college_id == college_id)
    elif major_id:
        cg_q = cg_q.filter(ClassGroup.major_id == major_id)

    schedules: list[dict] = []
    for row in cg_q.order_by(ClassGroup.grade.desc(), ClassGroup.name.asc()).all():
        schedules.append({
            "class_group_id": row.id,
            "class_name": row.name,
            "grade": row.grade,
            "student_count": row.student_count,
            "major_name": row.major_name or "",
            "college_name": row.college_name or "",
            "course_count": 0,
            "filled_slots": 0,
            "total_slots": 35,
        })
    scope_cg_ids = [s["class_group_id"] for s in schedules]

    # 2) 学期维度统计（受学院/专业筛选影响）
    semesters: list[dict] = []
    if scope_cg_ids:
        sem_rows = (
            db.query(
                Course.semester,
                func.count(Course.id),
                func.count(func.distinct(Course.class_group_id)),
            )
            .filter(Course.class_group_id.in_(scope_cg_ids))
            .group_by(Course.semester)
            .all()
        )
        for value, course_count, schedule_count in sem_rows:
            if not value:
                continue
            label = str(value)
            try:
                parts = label.split("-")
                if len(parts) == 3:
                    label = f"{parts[0]}-{parts[1]} 第{'一' if parts[2] == '1' else '二'}学期"
            except (IndexError, ValueError):
                pass
            semesters.append({
                "value": str(value),
                "label": label,
                "schedule_count": schedule_count,
                "course_count": course_count,
            })
        def _sem_sort_key(s: dict) -> tuple:
            try:
                parts = s["value"].split("-")
                return (-int(parts[0]), -int(parts[2]))
            except (IndexError, ValueError):
                return (0, 0)

        # 合并手工配置的学期（无课程数据也在课程表中展示，自定义名称优先）
        sem_by_value = {s["value"]: s for s in semesters}
        for sem in db.query(Semester).all():
            if sem.value in sem_by_value:
                sem_by_value[sem.value]["label"] = sem.label
            else:
                sem_by_value[sem.value] = {
                    "value": sem.value,
                    "label": sem.label,
                    "schedule_count": 0,
                    "course_count": 0,
                }
        semesters = sorted(sem_by_value.values(), key=_sem_sort_key)

    # 3) 班级维度：指定学期内的课程数与占用节次（7天 × 5个课次行 = 35 槽位）
    total_courses = 0
    if semester and scope_cg_ids:
        cg_map = {s["class_group_id"]: s for s in schedules}
        occupied: dict[int, set] = defaultdict(set)
        for c in db.query(Course).filter(
            Course.class_group_id.in_(scope_cg_ids),
            Course.semester == semester,
        ).all():
            cg = cg_map.get(c.class_group_id)
            if cg is None:
                continue
            cg["course_count"] += 1
            total_courses += 1
            for p in (1, 3, 5, 7, 9):
                if c.start_period <= p <= c.end_period:
                    occupied[c.class_group_id].add((c.day_of_week, p))
        for cg_id, rows in occupied.items():
            cg_map[cg_id]["filled_slots"] = len(rows)
    else:
        total_courses = sum(s["course_count"] for s in semesters)

    return {
        "semesters": semesters,
        "schedules": schedules,
        "total_courses": total_courses,
    }


@router.post("/courses", response_model=CourseOut)
def admin_create_course(
    data: CourseCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员新增课程"""
    cg = db.query(ClassGroup).get(data.class_group_id)
    if not cg:
        raise HTTPException(400, "班级不存在")
    # 检测时间冲突
    conflict = db.query(Course).filter(
        Course.class_group_id == data.class_group_id,
        Course.semester == data.semester,
        Course.day_of_week == data.day_of_week,
        Course.start_period <= data.end_period,
        Course.end_period >= data.start_period,
    ).first()
    if conflict:
        raise HTTPException(400, f"时间冲突：与课程「{conflict.name}」(第{conflict.start_period}-{conflict.end_period}节)重叠")
    obj = Course(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/courses/{course_id}", response_model=CourseOut)
def admin_update_course(
    course_id: int,
    data: CourseCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员修改课程"""
    obj = db.query(Course).get(course_id)
    if not obj:
        raise HTTPException(404, "课程不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/courses/batch")
def admin_batch_delete_courses(
    ids: list[int] = Body(..., embed=True),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员批量删除课程（注意：必须注册在 /courses/{course_id} 之前，避免路由被吞）"""
    count = db.query(Course).filter(Course.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted": count}


@router.delete("/courses/{course_id}")
def admin_delete_course(
    course_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """管理员删除课程"""
    obj = db.query(Course).get(course_id)
    if not obj:
        raise HTTPException(404, "课程不存在")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.get("/semesters")
def admin_list_semesters(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """获取最近12个学期列表，从当前学期往前推算"""
    from datetime import date
    today = date.today()
    year = today.year
    month = today.month

    # 当前学期: 3-8月为春季学期(2), 9-2月为秋季学期(1)
    if 3 <= month <= 8:
        current = (year - 1, year, 2)
    else:
        current = (year, year + 1, 1)

    semesters: list[dict] = []
    y_start, y_end, term = current
    for i in range(12):
        semesters.append({
            "value": f"{y_start}-{y_end}-{term}",
            "label": f"{y_start}-{y_end} 第{'一' if term == 1 else '二'}学期",
        })
        if term == 1:
            y_start -= 1
            y_end -= 1
            term = 2
        else:
            term = 1

    # 同时合并数据库中已有的学期
    db_semesters = [r[0] for r in db.query(Course.semester).distinct().order_by(Course.semester.desc()).all()]
    existing_values = {s["value"] for s in semesters}
    for s in db_semesters:
        if s and s not in existing_values:
            semesters.append({"value": s, "label": s})
            existing_values.add(s)

    # 按学期倒序排列
    def sort_key(s: dict) -> tuple:
        try:
            parts = s["value"].split("-")
            return (-int(parts[0]), -int(parts[2]))
        except (IndexError, ValueError):
            return (0, 0)

    semesters.sort(key=sort_key)

    # 补全 label
    for s in semesters:
        if "第" not in s["label"]:
            parts = s["value"].split("-")
            if len(parts) == 3:
                s["label"] = f"{parts[0]}-{parts[1]} 第{'一' if parts[2] == '1' else '二'}学期"

    return semesters


class SemesterCreate(BaseModel):
    """新增学期配置"""
    year: str = Body(..., description="学年，如 2026-2027")
    term: int = Body(..., description="学期：1 第一学期，2 第二学期")
    label: str | None = Body(None, description="自定义显示名称，不传则按学年学期自动生成")


class SemesterUpdate(BaseModel):
    """编辑学期配置（仅允许修改显示名称，value 与课程数据强关联不可改）"""
    label: str = Body(...)


@router.get("/semesters/managed", summary="学期配置列表", description="返回手工配置的学期 + 数据库中已有课程的学期，附课程数量")
def admin_list_managed_semesters(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """学期管理列表：配置表学期 ∪ 课程表学期（去重），带各自课程数量"""
    import re
    from collections import defaultdict as _dd

    # 1) 配置表学期
    rows: list[dict] = []
    for sem in db.query(Semester).order_by(Semester.id.asc()).all():
        rows.append({
            "id": sem.id,
            "value": sem.value,
            "label": sem.label,
            "managed": True,
        })

    # 2) 课程表已有学期（补全 label、去重）
    def _fmt_label(v: str) -> str:
        parts = v.split("-")
        if len(parts) == 3 and re.fullmatch(r"\d{4}-\d{4}-\d", v):
            return f"{parts[0]}-{parts[1]} 第{'一' if parts[2] == '1' else '二'}学期"
        return v

    existing_values = {r["value"] for r in rows}
    for (v,) in db.query(Course.semester).distinct().all():
        if v and v not in existing_values:
            rows.append({"id": None, "value": v, "label": _fmt_label(v), "managed": False})
            existing_values.add(v)

    # 3) 课程数量统计
    counts: dict[str, int] = _dd(int)
    for (v, c) in db.query(Course.semester, func.count(Course.id)).group_by(Course.semester).all():
        if v:
            counts[v] = c
    for r in rows:
        r["course_count"] = counts.get(r["value"], 0)

    # 4) 排序：学年倒序、学期倒序
    def _k(r: dict) -> tuple:
        m = re.fullmatch(r"(\d{4})-(\d{4})-(\d)", r["value"] or "")
        return (-int(m.group(1)), -int(m.group(3))) if m else (0, 0)

    rows.sort(key=_k)
    return rows


@router.post("/semesters", summary="新增学期配置", description="新增一个学期（无课程数据时也会在课程表总览中展示）")
def admin_create_semester(
    data: SemesterCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    import re
    if not re.fullmatch(r"\d{4}-\d{4}", data.year.strip()):
        raise HTTPException(400, detail="学年格式不正确，示例：2026-2027")
    if data.term not in (1, 2):
        raise HTTPException(400, detail="学期只能选择第一学期或第二学期")

    value = f"{data.year.strip()}-{data.term}"

    # 与配置表 / 课程表学期均不能重复
    existed = db.query(Semester).filter(Semester.value == value).first()
    if existed:
        raise HTTPException(400, detail=f"学期 {value} 已存在")
    if value in {r[0] for r in db.query(Course.semester).distinct().all() if r[0]}:
        raise HTTPException(400, detail=f"学期 {value} 已存在于课程数据中")

    label = (data.label or "").strip()
    if not label:
        label = f"{data.year.strip()} 第{'一' if data.term == 1 else '二'}学期"

    sem = Semester(value=value, label=label)
    db.add(sem)
    db.commit()
    db.refresh(sem)
    return {"id": sem.id, "value": sem.value, "label": sem.label, "course_count": 0}


@router.put("/semesters/{semester_id}", summary="编辑学期配置", description="仅允许修改显示名称（label），value 与课程数据强关联不可改")
def admin_update_semester(
    semester_id: int,
    data: SemesterUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    sem = db.get(Semester, semester_id)
    if not sem:
        raise HTTPException(404, detail="学期配置不存在")
    label = data.label.strip()
    if not label:
        raise HTTPException(400, detail="显示名称不能为空")
    sem.label = label
    db.commit()
    db.refresh(sem)
    return {"id": sem.id, "value": sem.value, "label": sem.label}


@router.delete("/semesters/{semester_id}", summary="删除学期配置", description="删除手工配置的学期；若该学期已有课程数据则拒绝删除")
def admin_delete_semester(
    semester_id: int,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    sem = db.get(Semester, semester_id)
    if not sem:
        raise HTTPException(404, detail="学期配置不存在")
    course_count = db.query(func.count(Course.id)).filter(Course.semester == sem.value).scalar() or 0
    if course_count > 0:
        raise HTTPException(400, detail=f"该学期已有 {course_count} 门课程，请先删除课程后再删除学期")
    db.delete(sem)
    db.commit()
    return {"ok": True}


@router.post("/courses/import", response_model=CourseImportResult)
async def admin_import_courses(
    file: UploadFile = File(...),
    college_id: int = Query(...),
    semester: str = Query(...),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """导入课程表 Excel，自动匹配学院下的班级"""
    import io
    import openpyxl

    college = db.query(College).get(college_id)
    if not college:
        raise HTTPException(400, "学院不存在")

    # 加载该学院下所有班级
    major_ids = [m.id for m in db.query(Major).filter(Major.college_id == college_id).all()]
    class_groups = db.query(ClassGroup).filter(ClassGroup.major_id.in_(major_ids)).all() if major_ids else []
    cg_map: dict[str, int] = {}  # 班级名 -> id
    for cg in class_groups:
        cg_map[cg.name] = cg.id
        # 也支持简称匹配，如去掉学院前缀
        short = cg.name
        for m in db.query(Major).filter(Major.id == cg.major_id).all():
            short = short.replace(m.name, "").strip()
        if short and short != cg.name:
            cg_map[short] = cg.id

    result = CourseImportResult()
    result.matched_classes = list(cg_map.keys())

    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        if not rows:
            raise HTTPException(400, "Excel 文件为空（至少需要表头行和一行数据）")

        headers = [str(h).strip() if h else "" for h in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]

        def find_col(*keys: str) -> int:
            for i, h in enumerate(headers):
                hl = h.lower().replace(" ", "").replace("_", "")
                for k in keys:
                    if k.lower().replace(" ", "").replace("_", "") == hl:
                        return i
            return -1

        idx_class = find_col("班级名称", "班级", "className", "class_name", "classname")
        idx_name = find_col("课程名称", "课程", "courseName", "course_name", "coursename", "name")
        idx_teacher = find_col("授课教师", "教师", "teacher")
        idx_location = find_col("上课地点", "教室", "地点", "location", "classroom")
        idx_day = find_col("星期", "day_of_week", "day")
        idx_start = find_col("开始节次", "start_period", "start")
        idx_end = find_col("结束节次", "end_period", "end")
        idx_ws = find_col("开始周", "week_start", "weekstart")
        idx_we = find_col("结束周", "week_end", "weekend")
        idx_credit = find_col("学分", "credit")

        if idx_class < 0 or idx_name < 0:
            raise HTTPException(400, "Excel 缺少必要列：班级名称、课程名称")

        for row_idx, row in enumerate(rows, start=2):
            try:
                class_name = str(row[idx_class]).strip() if idx_class < len(row) and row[idx_class] else ""
                course_name = str(row[idx_name]).strip() if idx_name < len(row) and row[idx_name] else ""

                if not class_name or not course_name:
                    result.errors.append({"row": row_idx, "msg": "班级名称或课程名称为空"})
                    continue

                # 匹配班级
                cg_id = cg_map.get(class_name)
                if cg_id is None:
                    # 模糊匹配
                    for name, cid in cg_map.items():
                        if class_name in name or name in class_name:
                            cg_id = cid
                            break
                if cg_id is None:
                    if class_name not in result.unmatched_classes:
                        result.unmatched_classes.append(class_name)
                    result.errors.append({"row": row_idx, "msg": f"未匹配到班级「{class_name}」"})
                    continue

                teacher = str(row[idx_teacher]).strip() if idx_teacher >= 0 and idx_teacher < len(row) and row[idx_teacher] else "未知"
                location = str(row[idx_location]).strip() if idx_location >= 0 and idx_location < len(row) and row[idx_location] else "待定"

                day_val = row[idx_day] if idx_day >= 0 and idx_day < len(row) else None
                if isinstance(day_val, str):
                    day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
                    day_val = day_map.get(day_val.strip().replace("周", "").replace("星期", ""), 1)
                day_of_week = int(day_val) if day_val is not None else 1
                if day_of_week < 1 or day_of_week > 5:
                    result.errors.append({"row": row_idx, "msg": f"无效的星期值「{day_val}」"})
                    continue

                start_period = int(row[idx_start]) if idx_start >= 0 and idx_start < len(row) and row[idx_start] is not None else 1
                end_period = int(row[idx_end]) if idx_end >= 0 and idx_end < len(row) and row[idx_end] is not None else 2
                week_start = int(row[idx_ws]) if idx_ws >= 0 and idx_ws < len(row) and row[idx_ws] is not None else 1
                week_end = int(row[idx_we]) if idx_we >= 0 and idx_we < len(row) and row[idx_we] is not None else 16
                credit = float(row[idx_credit]) if idx_credit >= 0 and idx_credit < len(row) and row[idx_credit] is not None else None

                result.total += 1

                # 检查重复
                dup = db.query(Course).filter(
                    Course.class_group_id == cg_id,
                    Course.semester == semester,
                    Course.name == course_name,
                    Course.day_of_week == day_of_week,
                    Course.start_period == start_period,
                ).first()
                if dup:
                    result.skipped += 1
                    result.errors.append({"row": row_idx, "msg": f"已存在相同课程「{course_name}」，跳过"})
                    continue

                obj = Course(
                    class_group_id=cg_id,
                    semester=semester,
                    name=course_name,
                    teacher=teacher,
                    location=location,
                    day_of_week=day_of_week,
                    start_period=start_period,
                    end_period=end_period,
                    week_start=week_start,
                    week_end=week_end,
                    credit=credit,
                )
                db.add(obj)
                result.created += 1
            except Exception as e:
                result.errors.append({"row": row_idx, "msg": str(e)})

        if result.created > 0:
            db.commit()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"解析 Excel 失败：{str(e)}")

    return result
