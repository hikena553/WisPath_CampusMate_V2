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
