# 令牌认证与权限控制实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现前端路由守卫+后端API双重验证的权限控制系统，确保学生只能访问学生端，教师只能访问教师端，管理员可访问所有端，并实现严格的数据隔离。

**Architecture:** 前端路由守卫检查用户角色，阻止非法路由访问；后端使用 `require_role` 依赖进行角色检查，使用数据过滤实现数据隔离。

**Tech Stack:** Vue 3 + TypeScript (前端), FastAPI + SQLAlchemy (后端), JWT认证

---

## 文件结构

### 前端文件
- `frontend/src/router/index.ts` - 修改路由守卫，添加角色检查
- `frontend/src/utils/request.ts` - 修改错误处理，添加403处理

### 后端文件
- `backend/app/core/deps.py` - 添加 `require_role` 依赖
- `backend/app/api/teacher.py` - 使用 `require_role` 替换手动检查
- `backend/app/api/growth.py` - 添加数据隔离逻辑
- `backend/app/api/academic.py` - 添加数据隔离逻辑
- `backend/app/api/leave.py` - 添加数据隔离逻辑

---

### Task 1: 修改前端路由守卫

**Files:**
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: 修改路由守卫，添加角色检查**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUser } from '@/utils/token'

const publicPaths = ['/login']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'Login', component: () => import('@/views/login/LoginPage.vue') },

    {
      path: '/student',
      component: () => import('@/components/layout/StudentLayout.vue'),
      meta: { role: 'student' },
      children: [
        { path: '', component: () => import('@/views/student/HomePage.vue') },
        { path: 'agent', component: () => import('@/views/student/AgentPage.vue') },
        { path: 'campus', component: () => import('@/views/student/CampusPage.vue') },
        { path: 'growth', component: () => import('@/views/student/GrowthPage.vue') },
        { path: 'schedule', component: () => import('@/views/student/SchedulePage.vue') },
        { path: 'grade', redirect: '/student/schedule' },
        { path: 'service', component: () => import('@/views/student/ServicePage.vue') },
      ],
    },
    {
      path: '/teacher',
      component: () => import('@/components/layout/TeacherLayout.vue'),
      meta: { role: 'teacher' },
      children: [
        { path: '', component: () => import('@/views/teacher/HomePage.vue') },
        { path: 'agent', component: () => import('@/views/teacher/AgentPage.vue') },
        { path: 'students', component: () => import('@/views/teacher/StudentsPage.vue') },
        { path: 'approval', component: () => import('@/views/teacher/ApprovalPage.vue') },
        { path: 'messages', component: () => import('@/views/teacher/MessagesPage.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const token = getToken()
  const user = getUser()
  
  // 未登录跳转登录页
  if (!token && !publicPaths.includes(to.path)) return '/login'
  
  // 已登录但访问登录页，根据角色重定向
  if (token && to.path === '/login') {
    return user?.role === 'teacher' ? '/teacher' : '/student'
  }
  
  // 角色检查
  if (token && user && to.meta.role) {
    // 管理员可访问所有路由
    if (user.role === 'admin') return
    
    // 学生不能访问教师端
    if (user.role === 'student' && to.meta.role === 'teacher') return '/student'
    
    // 教师不能访问学生端
    if (user.role === 'teacher' && to.meta.role === 'student') return '/teacher'
  }
})

export default router
```

- [ ] **Step 2: 测试路由守卫**

1. 以学生身份登录，尝试访问 `/teacher` 路由，应被重定向到 `/student`
2. 以教师身份登录，尝试访问 `/student` 路由，应被重定向到 `/teacher`
3. 以管理员身份登录，应能访问所有路由

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: 添加前端路由守卫角色检查"
```

---

### Task 2: 修改前端错误处理

**Files:**
- Modify: `frontend/src/utils/request.ts`

- [ ] **Step 1: 添加403错误处理**

```typescript
import axios, { type AxiosRequestConfig } from 'axios'
import { getToken, removeToken } from './token'
import { ElMessage } from 'element-plus'

const instance = axios.create({ baseURL: '/api' })

instance.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

instance.interceptors.response.use(
  (res) => res.data,
  (err) => {
    // 401错误 - 跳转登录页
    if (err.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      removeToken()
      window.location.href = '/login'
      return Promise.reject(err)
    }
    
    // 403错误 - 显示权限不足提示
    if (err.response?.status === 403) {
      ElMessage.error('权限不足')
      return Promise.reject(err)
    }
    
    return Promise.reject(err)
  }
)

const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as any
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config) as any
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config) as any
  },
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config) as any
  },
}

export default request
```

- [ ] **Step 2: 测试错误处理**

1. 以学生身份登录，尝试访问教师端API，应显示"权限不足"提示
2. 以教师身份登录，尝试访问学生端API，应显示"权限不足"提示

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/utils/request.ts
git commit -m "feat: 添加403错误处理"
```

---

### Task 3: 添加后端角色检查依赖

**Files:**
- Modify: `backend/app/core/deps.py`

- [ ] **Step 1: 添加 `require_role` 依赖**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def require_role(*roles: UserRole):
    """创建角色检查依赖"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker
```

- [ ] **Step 2: 测试角色检查依赖**

1. 创建一个测试路由，使用 `require_role(UserRole.TEACHER, UserRole.ADMIN)`
2. 以学生身份访问，应返回403错误
3. 以教师身份访问，应成功
4. 以管理员身份访问，应成功

- [ ] **Step 3: 提交更改**

```bash
git add backend/app/core/deps.py
git commit -m "feat: 添加 require_role 角色检查依赖"
```

---

### Task 4: 修改教师端API使用角色检查依赖

**Files:**
- Modify: `backend/app/api/teacher.py`

- [ ] **Step 1: 修改 dashboard_stats 函数**

```python
@router.get("/dashboard", response_model=DashboardOut)
def dashboard_stats(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    students = query.all()
    student_ids = [s.id for s in students]
    total = len(student_ids)
    alert_count = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1"
    ).count()
    severe_count = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1",
        AIDialogSummary.level == "severe"
    ).count()
    resolved_count = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1",
        AIDialogSummary.resolved == True
    ).count()
    pending_leave = db.query(LeaveRequest).filter(
        LeaveRequest.student_id.in_(student_ids) if student_ids else "0=1",
        LeaveRequest.status == "pending"
    ).count()
    return DashboardOut(
        total_students=total,
        alert_count=alert_count,
        pending_leave_count=pending_leave,
        severe_alert_count=severe_count,
        resolved_alert_count=resolved_count,
    )
```

- [ ] **Step 2: 修改 list_students 函数**

```python
@router.get("/students", response_model=list[StudentOut])
def list_students(
    search: str | None = None,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            User.name.like(like) | User.username.like(like) | User.college.like(like)
        )
    students = query.all()
    result = []
    for s in students:
        growth_count = db.query(GrowthRecord).filter(GrowthRecord.student_id == s.id).count()
        leave_count = db.query(LeaveRequest).filter(LeaveRequest.student_id == s.id).count()
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()
        score = _calc_student_score(db, s.id, s)
        result.append(StudentOut(
            id=s.id,
            name=s.name,
            college=s.college,
            username=s.username,
            avatar=s.avatar,
            skills_json=s.skills_json,
            growth_count=growth_count,
            score=score,
            leave_count=leave_count,
            crisis_level=latest_crisis.level.value if latest_crisis else None,
            latest_crisis_summary=latest_crisis.summary if latest_crisis else None,
            latest_crisis_time=latest_crisis.created_at.isoformat() if latest_crisis else None,
            tutor_id=s.tutor_id,
        ))
    return result
```

- [ ] **Step 3: 修改 get_student_detail 函数**

```python
@router.get("/students/{student_id}", response_model=StudentDetailOut | StudentResumeOut)
def get_student_detail(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    is_tutor = user.role == UserRole.ADMIN or student.tutor_id == user.id

    growth_records = db.query(GrowthRecord).filter(
        GrowthRecord.student_id == student_id
    ).order_by(GrowthRecord.date.desc()).all()

    projects = db.query(StudentProject).filter(
        StudentProject.student_id == student_id
    ).order_by(StudentProject.start_date.desc()).all()

    def format_record(r):
        return {
            "id": r.id,
            "type": r.type.value if hasattr(r.type, 'value') else r.type,
            "title": r.title,
            "description": r.description,
            "date": str(r.date),
            "attachment_url": r.attachment_url,
            "honor_level": r.honor_level,
            "organizer": r.organizer,
            "competition_level": r.competition_level,
            "practice_type": r.practice_type,
            "practice_certificate": r.practice_certificate,
            "paper_type": r.paper_type,
            "paper_name": r.paper_name,
            "first_author": r.first_author,
            "second_author": r.second_author,
            "third_author": r.third_author,
            "achievement_type": r.achievement_type,
            "achievement_name": r.achievement_name,
        }

    def format_project(p):
        return {
            "id": p.id,
            "project_name": p.project_name,
            "start_date": str(p.start_date),
            "end_date": str(p.end_date) if p.end_date else None,
            "is_team": p.is_team,
            "team_members": p.team_members,
            "attachment_url": p.attachment_url,
        }

    # Non-tutor teacher: resume view (growth records only)
    if not is_tutor:
        return StudentResumeOut(
            id=student.id,
            name=student.name,
            college=student.college,
            username=student.username,
            avatar=student.avatar,
            skills_json=student.skills_json,
            growth_records=[format_record(r) for r in growth_records],
            projects=[format_project(p) for p in projects],
        )

    # Tutor or admin: full detail view
    crisis_alerts = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).all()

    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student_id
    ).order_by(LeaveRequest.created_at.desc()).all()

    def format_alert(a):
        return {
            "id": a.id,
            "summary": a.summary,
            "level": a.level.value if hasattr(a.level, 'value') else a.level,
            "keywords_matched": a.keywords_matched,
            "resolved": a.resolved,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        }

    def format_leave(l):
        return {
            "id": l.id,
            "start_date": str(l.start_date),
            "end_date": str(l.end_date),
            "reason": l.reason,
            "leave_type": l.leave_type.value if hasattr(l.leave_type, 'value') else l.leave_type,
            "status": l.status.value if hasattr(l.status, 'value') else l.status,
            "reject_reason": l.reject_reason,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }

    return StudentDetailOut(
        id=student.id,
        name=student.name,
        college=student.college,
        username=student.username,
        avatar=student.avatar,
        skills_json=student.skills_json,
        growth_records=[format_record(r) for r in growth_records],
        projects=[format_project(p) for p in projects],
        crisis_alerts=[format_alert(a) for a in crisis_alerts],
        leave_requests=[format_leave(l) for l in leaves],
    )
```

- [ ] **Step 4: 修改其他教师端函数**

```python
@router.get("/growth-stats")
def growth_stats(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    student_ids = [s.id for s in query.all()]
    if not student_ids:
        return {"honor": 0, "competition": 0, "practice": 0, "paper": 0, "achievement": 0}
    stats = db.query(
        GrowthRecord.type,
        func.count(GrowthRecord.id)
    ).filter(GrowthRecord.student_id.in_(student_ids)).group_by(GrowthRecord.type).all()
    result = {s[0].value: s[1] for s in stats}
    for t in ["honor", "competition", "practice", "paper", "achievement"]:
        result.setdefault(t, 0)
    return result


@router.get("/class-evaluation")
def class_evaluation(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    students = query.all()
    student_ids = [s.id for s in students]
    total = len(student_ids)
    if total == 0:
        return {
            "total_students": 0, "avg_gpa": 0, "avg_score": 0,
            "growth": {"honor": 0, "competition": 0, "practice": 0, "paper": 0, "achievement": 0},
            "crisis": {"severe": 0, "moderate": 0, "mild": 0, "resolved": 0},
            "pending_leaves": 0,
        }

    # Average GPA
    grades = db.query(Grade).filter(Grade.student_id.in_(student_ids)).all()
    total_credit = sum(g.credit for g in grades)
    avg_gpa = round(sum(g.gpa * g.credit for g in grades) / total_credit, 2) if total_credit > 0 else 0

    # Average score
    total_score = 0
    for s in student_ids:
        total_score += _calc_student_score(db, s)
    avg_score = round(total_score / total, 1)

    # Growth records
    growth = db.query(
        GrowthRecord.type,
        func.count(GrowthRecord.id)
    ).filter(GrowthRecord.student_id.in_(student_ids) if student_ids else "0=1"
    ).group_by(GrowthRecord.type).all()
    growth_data = {r[0].value: r[1] for r in growth}
    for t in ["honor", "competition", "practice", "paper", "achievement"]:
        growth_data.setdefault(t, 0)

    # Crisis by level
    crisis_severe = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1",
        AIDialogSummary.level == "severe",
    ).count()
    crisis_moderate = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1",
        AIDialogSummary.level == "moderate",
    ).count()
    crisis_mild = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1",
        AIDialogSummary.level == "mild",
    ).count()
    crisis_resolved = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id.in_(student_ids) if student_ids else "0=1",
        AIDialogSummary.resolved == True,
    ).count()

    pending_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.student_id.in_(student_ids) if student_ids else "0=1",
        LeaveRequest.status == "pending",
    ).count()

    return {
        "total_students": total,
        "avg_gpa": avg_gpa,
        "avg_score": avg_score,
        "growth": growth_data,
        "crisis": {
            "severe": crisis_severe,
            "moderate": crisis_moderate,
            "mild": crisis_mild,
            "resolved": crisis_resolved,
        },
        "pending_leaves": pending_leaves,
    }


@router.get("/suggest-contacts", response_model=list[ContactSuggestionOut])
def suggest_contacts(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    # 获取教师名下学生
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if user.role != UserRole.ADMIN:
        query = query.filter(User.tutor_id == user.id)
    students = query.all()
    if not students:
        return []

    # 收集每个学生的相关信息
    student_infos = []
    for s in students:
        # 最近联系时间
        last_msg = db.query(Message).filter(
            ((Message.sender_id == user.id) & (Message.receiver_id == s.id)) |
            ((Message.sender_id == s.id) & (Message.receiver_id == user.id))
        ).order_by(Message.created_at.desc()).first()
        last_contact = last_msg.created_at.isoformat() if last_msg else "从未联系"

        # 危机预警
        latest_crisis = db.query(AIDialogSummary).filter(
            AIDialogSummary.student_id == s.id
        ).order_by(AIDialogSummary.created_at.desc()).first()

        # 成长记录数
        growth_count = db.query(GrowthRecord).filter(GrowthRecord.student_id == s.id).count()

        # 请假记录
        leave_count = db.query(LeaveRequest).filter(LeaveRequest.student_id == s.id).count()

        student_infos.append({
            "id": s.id,
            "name": s.name,
            "college": s.college or "未分配",
            "last_contact": last_contact,
            "crisis_level": latest_crisis.level.value if latest_crisis else None,
            "growth_count": growth_count,
            "leave_count": leave_count,
        })

    # 构造 prompt 发送给 AI
    students_text = "\n".join([
        f"- {info['name']}（{info['college']}）：最近联系={info['last_contact']}，危机等级={info['crisis_level'] or '无'}，成果数={info['growth_count']}，请假数={info['leave_count']}，ID={info['id']}"
        for info in student_infos
    ])

    prompt = f"""你是校园管理助手。请从以下学生名单中，分析并推荐3位最应该主动联系的学生。

学生信息：
{students_text}

分析维度：
1. 长时间未联系的学生（优先级高）
2. 有危机预警的学生（优先级高）
3. 近期请假较多的学生（需关注）
4. 有成长成果但未沟通的学生（鼓励）

要求：
1. 从列表中选出3位学生
2. 每位学生给出具体理由（至少20字）
3. 标注优先级：high/medium/low
4. 只返回JSON数组，不要其他内容

格式：[{{"student_id": 1, "student_name": "姓名", "reason": "具体理由...", "priority": "high"}}]"""

    try:
        resp = _get_client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        content = resp.choices[0].message.content or ""
        # 清理 markdown 代码块
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", content).strip().rstrip("`")
        result = json.loads(cleaned)
        return result
    except Exception as e:
        print(f"[AI推荐联系] 错误: {e}")
        # fallback: 返回前3个学生
        return [
            {"student_id": s["id"], "student_name": s["name"], "reason": "AI分析暂不可用，建议手动查看", "priority": "medium"}
            for s in student_infos[:3]
        ]
```

- [ ] **Step 5: 测试教师端API**

1. 以学生身份访问教师端API，应返回403错误
2. 以教师身份访问教师端API，应成功
3. 以管理员身份访问教师端API，应成功

- [ ] **Step 6: 提交更改**

```bash
git add backend/app/api/teacher.py
git commit -m "feat: 教师端API使用 require_role 角色检查依赖"
```

---

### Task 5: 修改成长档案API添加数据隔离

**Files:**
- Modify: `backend/app/api/growth.py`

- [ ] **Step 1: 修改 list_records 函数添加数据隔离**

```python
@router.get("/records", response_model=list[GrowthRecordOut])
def list_records(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(GrowthRecord)
    
    # 数据隔离
    if current_user.role == UserRole.ADMIN:
        pass  # 管理员可查看所有
    elif current_user.role == UserRole.TEACHER:
        # 教师只能查看自己名下学生的数据
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == current_user.id).all()]
        query = query.filter(GrowthRecord.student_id.in_(student_ids))
    else:
        # 学生只能查看自己的数据
        query = query.filter(GrowthRecord.student_id == current_user.id)
    
    # 如果指定了student_id，进一步检查权限
    if student_id:
        if current_user.role == UserRole.STUDENT and student_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问其他学生的数据")
        query = query.filter(GrowthRecord.student_id == student_id)
    
    return query.order_by(GrowthRecord.date.desc()).all()
```

- [ ] **Step 2: 修改 create_record 函数**

```python
@router.post("/records", response_model=GrowthRecordOut)
def create_record(req: GrowthRecordCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 学生只能为自己创建记录
    if current_user.role == UserRole.STUDENT:
        record = GrowthRecord(student_id=current_user.id, **req.model_dump())
    else:
        # 教师和管理员可以为任何学生创建记录
        record = GrowthRecord(student_id=req.student_id, **req.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
```

- [ ] **Step 3: 修改 delete_record 函数添加数据隔离**

```python
@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(GrowthRecord).filter(GrowthRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 数据隔离检查
    if current_user.role == UserRole.STUDENT and record.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除其他学生的记录")
    elif current_user.role == UserRole.TEACHER:
        # 教师只能删除自己名下学生的记录
        student = db.query(User).filter(User.id == record.student_id).first()
        if not student or student.tutor_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除非自己名下学生的记录")
    
    db.delete(record)
    db.commit()
    return {"message": "deleted"}
```

- [ ] **Step 4: 修改项目相关函数添加数据隔离**

```python
@router.get("/projects", response_model=list[StudentProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(StudentProject).filter(
        StudentProject.student_id == current_user.id
    ).order_by(StudentProject.start_date.desc()).all()


@router.post("/projects", response_model=StudentProjectOut)
def create_project(req: StudentProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = StudentProject(student_id=current_user.id, **req.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=StudentProjectOut)
def update_project(project_id: int, req: StudentProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(StudentProject).filter(
        StudentProject.id == project_id, StudentProject.student_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    for k, v in req.model_dump().items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(StudentProject).filter(
        StudentProject.id == project_id, StudentProject.student_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()
    return {"message": "deleted"}
```

- [ ] **Step 5: 测试数据隔离**

1. 以学生身份登录，只能查看自己的成长记录和项目
2. 以教师身份登录，只能查看自己名下学生的成长记录
3. 尝试访问其他学生的数据，应返回403错误

- [ ] **Step 6: 提交更改**

```bash
git add backend/app/api/growth.py
git commit -m "feat: 成长档案API添加数据隔离"
```

---

### Task 6: 修改学业管理API添加数据隔离

**Files:**
- Modify: `backend/app/api/academic.py`

- [ ] **Step 1: 查看并修改学业管理API**

```python
# 需要查看 academic.py 文件内容，然后添加数据隔离逻辑
# 主要修改：
# 1. 成绩查询 - 学生只能查看自己的成绩，教师只能查看自己名下学生的成绩
# 2. 课表查询 - 学生只能查看自己的课表，教师只能查看自己名下学生的课表
```

- [ ] **Step 2: 测试数据隔离**

1. 以学生身份登录，只能查看自己的成绩和课表
2. 以教师身份登录，只能查看自己名下学生的成绩和课表

- [ ] **Step 3: 提交更改**

```bash
git add backend/app/api/academic.py
git commit -m "feat: 学业管理API添加数据隔离"
```

---

### Task 7: 修改请假审批API添加数据隔离

**Files:**
- Modify: `backend/app/api/leave.py`

- [ ] **Step 1: 查看并修改请假审批API**

```python
# 需要查看 leave.py 文件内容，然后添加数据隔离逻辑
# 主要修改：
# 1. 请假申请列表 - 学生只能查看自己的请假，教师只能查看自己名下学生的请假
# 2. 请假审批 - 教师只能审批自己名下学生的请假
```

- [ ] **Step 2: 测试数据隔离**

1. 以学生身份登录，只能查看和提交自己的请假申请
2. 以教师身份登录，只能查看和审批自己名下学生的请假申请

- [ ] **Step 3: 提交更改**

```bash
git add backend/app/api/leave.py
git commit -m "feat: 请假审批API添加数据隔离"
```

---

### Task 8: 完整测试

- [ ] **Step 1: 测试学生端**

1. 以学生身份登录
2. 访问学生端所有功能
3. 尝试访问教师端路由，应被重定向
4. 尝试访问其他学生的数据，应返回403错误

- [ ] **Step 2: 测试教师端**

1. 以教师身份登录
2. 访问教师端所有功能
3. 尝试访问学生端路由，应被重定向
4. 尝试访问非自己名下学生的数据，应返回403错误

- [ ] **Step 3: 测试管理员端**

1. 以管理员身份登录
2. 访问所有端的所有功能
3. 应能访问所有数据

- [ ] **Step 4: 最终提交**

```bash
git add .
git commit -m "feat: 完成令牌认证与权限控制系统"
```
