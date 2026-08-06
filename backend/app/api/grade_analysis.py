from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.academic import Grade

router = APIRouter(prefix="/api/academic", tags=["成绩分析"])


# ===== Schemas =====
class GradeStats(BaseModel):
    total_courses: int
    total_credits: float
    avg_score: float
    avg_gpa: float
    highest_gpa: float
    lowest_gpa: float
    pass_rate: float


class SemesterGPA(BaseModel):
    semester: str
    gpa: float
    credits: float
    course_count: int


class CourseTypeStats(BaseModel):
    type: str
    count: int
    avg_score: float
    avg_gpa: float


class ScoreDistribution(BaseModel):
    range: str
    count: int
    percentage: float


class GradeAnalysis(BaseModel):
    stats: GradeStats
    semester_gpa: List[SemesterGPA]
    course_type_stats: List[CourseTypeStats]
    score_distribution: List[ScoreDistribution]
    top_courses: List[dict]
    weak_courses: List[dict]


# ===== Endpoints =====
@router.get("/analysis/{student_id}", response_model=GradeAnalysis)
def get_grade_analysis(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成绩分析（学生本人、教师或管理员）"""
    if current_user.role == UserRole.STUDENT and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="无权访问他人成绩")
    
    # 获取所有成绩
    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    
    if not grades:
        return GradeAnalysis(
            stats=GradeStats(
                total_courses=0, total_credits=0, avg_score=0, avg_gpa=0,
                highest_gpa=0, lowest_gpa=0, pass_rate=0
            ),
            semester_gpa=[],
            course_type_stats=[],
            score_distribution=[],
            top_courses=[],
            weak_courses=[]
        )
    
    # 基础统计
    total_courses = len(grades)
    total_credits = sum(g.credit or 0 for g in grades)
    scores = [g.score for g in grades if g.score is not None]
    gpas = [g.gpa for g in grades if g.gpa is not None]
    
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_gpa = sum(gpas) / len(gpas) if gpas else 0
    highest_gpa = max(gpas) if gpas else 0
    lowest_gpa = min(gpas) if gpas else 0
    pass_count = sum(1 for s in scores if s >= 60)
    pass_rate = (pass_count / len(scores) * 100) if scores else 0
    
    stats = GradeStats(
        total_courses=total_courses,
        total_credits=round(total_credits, 1),
        avg_score=round(avg_score, 1),
        avg_gpa=round(avg_gpa, 2),
        highest_gpa=round(highest_gpa, 2),
        lowest_gpa=round(lowest_gpa, 2),
        pass_rate=round(pass_rate, 1)
    )
    
    # 按学期统计GPA
    semester_map = {}
    for g in grades:
        sem = g.semester or "未知学期"
        if sem not in semester_map:
            semester_map[sem] = {"gpas": [], "credits": 0, "count": 0}
        semester_map[sem]["gpas"].append(g.gpa or 0)
        semester_map[sem]["credits"] += g.credit or 0
        semester_map[sem]["count"] += 1
    
    semester_gpa = []
    for sem, data in sorted(semester_map.items(), reverse=True):
        sem_gpa = sum(data["gpas"]) / len(data["gpas"]) if data["gpas"] else 0
        semester_gpa.append(SemesterGPA(
            semester=sem,
            gpa=round(sem_gpa, 2),
            credits=round(data["credits"], 1),
            course_count=data["count"]
        ))
    
    # 按课程类型统计
    type_map = {}
    for g in grades:
        course_type = "其他"
        if g.course_name:
            if "必修" in g.course_name:
                course_type = "必修"
            elif "选修" in g.course_name:
                course_type = "选修"
            elif "实践" in g.course_name:
                course_type = "实践"
        
        if course_type not in type_map:
            type_map[course_type] = {"scores": [], "gpas": [], "count": 0}
        type_map[course_type]["scores"].append(g.score or 0)
        type_map[course_type]["gpas"].append(g.gpa or 0)
        type_map[course_type]["count"] += 1
    
    course_type_stats = []
    for type_name, data in type_map.items():
        avg_s = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        avg_g = sum(data["gpas"]) / len(data["gpas"]) if data["gpas"] else 0
        course_type_stats.append(CourseTypeStats(
            type=type_name,
            count=data["count"],
            avg_score=round(avg_s, 1),
            avg_gpa=round(avg_g, 2)
        ))
    
    # 成绩分布
    distribution_map = {
        "90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "0-59": 0
    }
    for s in scores:
        if s >= 90:
            distribution_map["90-100"] += 1
        elif s >= 80:
            distribution_map["80-89"] += 1
        elif s >= 70:
            distribution_map["70-79"] += 1
        elif s >= 60:
            distribution_map["60-69"] += 1
        else:
            distribution_map["0-59"] += 1
    
    score_distribution = []
    for range_name, count in distribution_map.items():
        percentage = (count / len(scores) * 100) if scores else 0
        score_distribution.append(ScoreDistribution(
            range=range_name,
            count=count,
            percentage=round(percentage, 1)
        ))
    
    # 优秀课程（GPA >= 3.5）
    top_courses = []
    for g in grades:
        if g.gpa and g.gpa >= 3.5:
            top_courses.append({
                "course_name": g.course_name or "未知课程",
                "score": g.score,
                "gpa": g.gpa,
                "semester": g.semester
            })
    top_courses.sort(key=lambda x: x["gpa"], reverse=True)
    
    # 薄弱课程（GPA < 2.5）
    weak_courses = []
    for g in grades:
        if g.gpa and g.gpa < 2.5:
            weak_courses.append({
                "course_name": g.course_name or "未知课程",
                "score": g.score,
                "gpa": g.gpa,
                "semester": g.semester
            })
    weak_courses.sort(key=lambda x: x["gpa"])
    
    return GradeAnalysis(
        stats=stats,
        semester_gpa=semester_gpa,
        course_type_stats=course_type_stats,
        score_distribution=score_distribution,
        top_courses=top_courses[:10],
        weak_courses=weak_courses[:10]
    )


@router.get("/analysis/class/{class_id}")
def get_class_grade_analysis(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _ = class_id  # TODO: 实现按 class_id 过滤，当前使用 tutor_id
    """获取班级成绩分析（教师或管理员）"""
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="无权访问")
    
    # 获取班级学生
    students = db.query(User).filter(
        User.tutor_id == current_user.id if current_user.role == UserRole.TEACHER else True
    ).all()
    
    student_ids = [s.id for s in students]
    
    # 获取所有成绩
    grades = db.query(Grade).filter(Grade.student_id.in_(student_ids)).all()
    
    if not grades:
        return {"students": [], "stats": {}}
    
    # 按学生统计
    student_map = {}
    for g in grades:
        if g.student_id not in student_map:
            student_map[g.student_id] = {"grades": [], "student": None}
        student_map[g.student_id]["grades"].append(g)
    
    # 获取学生信息
    for student_id in student_map:
        student = db.query(User).filter(User.id == student_id).first()
        student_map[student_id]["student"] = student
    
    # 计算每个学生的GPA
    student_stats = []
    for student_id, data in student_map.items():
        gpas = [g.gpa for g in data["grades"] if g.gpa is not None]
        avg_gpa = sum(gpas) / len(gpas) if gpas else 0
        total_credits = sum(g.credit or 0 for g in data["grades"])
        
        student_stats.append({
            "student_id": student_id,
            "student_name": data["student"].name if data["student"] else "未知",
            "avg_gpa": round(avg_gpa, 2),
            "total_credits": round(total_credits, 1),
            "course_count": len(data["grades"])
        })
    
    student_stats.sort(key=lambda x: x["avg_gpa"], reverse=True)
    
    # 班级整体统计
    all_gpas = [s["avg_gpa"] for s in student_stats if s["avg_gpa"] > 0]
    class_avg_gpa = sum(all_gpas) / len(all_gpas) if all_gpas else 0
    
    return {
        "students": student_stats,
        "stats": {
            "total_students": len(student_stats),
            "class_avg_gpa": round(class_avg_gpa, 2),
            "highest_gpa": max(all_gpas) if all_gpas else 0,
            "lowest_gpa": min(all_gpas) if all_gpas else 0
        }
    }
