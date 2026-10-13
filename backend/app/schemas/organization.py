from pydantic import BaseModel
from typing import Optional


class CollegeCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class CollegeOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class MajorCreate(BaseModel):
    college_id: int
    name: str
    code: str
    description: Optional[str] = None


class MajorOut(BaseModel):
    id: int
    college_id: int
    name: str
    code: str
    description: Optional[str] = None
    college_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClassGroupCreate(BaseModel):
    major_id: int
    name: str
    grade: int


class ClassGroupOut(BaseModel):
    id: int
    major_id: int
    name: str
    grade: int
    student_count: Optional[int] = None
    major_name: Optional[str] = None
    college_name: Optional[str] = None

    class Config:
        from_attributes = True


class OrgScopeOut(BaseModel):
    """当前用户「所在组织」的范围，用于通讯录只展示自己所在组织及下级。

    scope: all（未归属任何组织，展示全部）/ college / major / class
    """

    scope: str = "all"
    college_id: Optional[int] = None
    college_name: Optional[str] = None
    major_id: Optional[int] = None
    major_name: Optional[str] = None
    class_group_id: Optional[int] = None
    class_group_name: Optional[str] = None
