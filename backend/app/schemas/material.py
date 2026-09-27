"""材料档案 DTO：入参 Create/Review 与出参 Out 统一收敛于此。"""
from typing import Optional

from pydantic import BaseModel


class MaterialCreate(BaseModel):
    title: str
    category: str = "other"
    file_url: str
    file_name: str = ""
    file_type: str = ""
    remark: Optional[str] = None


class MaterialReview(BaseModel):
    action: str
    reject_reason: Optional[str] = None


class MaterialOut(BaseModel):
    id: int
    student_id: int
    title: str
    category: str
    category_label: str
    file_url: str
    file_name: str
    file_type: str
    remark: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    created_at: str