from pydantic import BaseModel, ConfigDict


class KnowledgeItemCreate(BaseModel):
    category: str
    question: str
    answer: str
    tags: str | None = None


class KnowledgeItemUpdate(BaseModel):
    category: str | None = None
    question: str | None = None
    answer: str | None = None
    tags: str | None = None


class KnowledgeItemOut(BaseModel):
    id: int
    category: str
    question: str
    answer: str
    tags: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    chunk_count: int
    created_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TeacherCreate(BaseModel):
    username: str
    name: str
    college: str | None = None
    title: str | None = None
    department: str | None = None
    gender: str | None = None
    phone: str | None = None


class TeacherOut(BaseModel):
    id: int
    username: str
    name: str
    college: str | None = None
    avatar: str | None = None
    title: str | None = None
    department: str | None = None
    student_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StudentBriefOut(BaseModel):
    id: int
    username: str
    name: str
    college: str | None = None
    class_name: str | None = None
    avatar: str | None = None
    score: float = 0
    crisis_level: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StudentUpdate(BaseModel):
    college: str | None = None
    class_name: str | None = None
    avatar: str | None = None
    gender: str | None = None
    age: int | None = None
    phone: str | None = None
    hometown: str | None = None
    department: str | None = None
    tutor_id: int | None = None


class ImportResult(BaseModel):
    total: int
    created: int
    skipped: int
    errors: list[str] = []
