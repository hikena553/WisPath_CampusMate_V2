"""学生端「我的关怀」只读接口：仅返回当前登录学生自己的数据。

- GET /summary  概览计数（激励 / 家访 / 关怀记录）
- GET /praises  我的正向激励
- GET /records  非私密关怀记录
- GET /visits   我的家访记录（含回访状态）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.care_center import (
    StudentCarePraiseOut,
    StudentCareRecordOut,
    StudentCareSummary,
    StudentCareVisitOut,
)
from app.services import care_center_service

router = APIRouter(prefix="/api/student/care", tags=["care-student"])

_student_only = require_role(UserRole.STUDENT)


@router.get("/summary", response_model=StudentCareSummary)
def my_summary(user: User = Depends(_student_only), db: Session = Depends(get_db)):
    return care_center_service.list_student_care(db, user.id)["summary"]


@router.get("/praises", response_model=list[StudentCarePraiseOut])
def my_praises(user: User = Depends(_student_only), db: Session = Depends(get_db)):
    return care_center_service.list_student_care(db, user.id)["praises"]


@router.get("/records", response_model=list[StudentCareRecordOut])
def my_records(user: User = Depends(_student_only), db: Session = Depends(get_db)):
    return care_center_service.list_student_care(db, user.id)["records"]


@router.get("/visits", response_model=list[StudentCareVisitOut])
def my_visits(user: User = Depends(_student_only), db: Session = Depends(get_db)):
    return care_center_service.list_student_care(db, user.id)["visits"]