"""教学域接口冒烟：直接打真实库，验证「课表 → 点名 → 缺勤建待办 → 出勤统计 → 成绩」。

一次性脚本，跑完即可删；不进入 pytest（依赖本地真实数据）。
用法：cd backend && python scripts/smoke_teaching.py [teacher_id]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.models.user import User  # noqa: E402
from app.main import app  # noqa: E402

TEACHER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 471

db = SessionLocal()
teacher = db.get(User, TEACHER_ID)
if not teacher:
    print("teacher not found", TEACHER_ID)
    raise SystemExit(1)
token = create_access_token(
    {"sub": str(teacher.id), "role": teacher.role.value, "ph": teacher.password_hash[:8]}
)
db.close()

client = TestClient(app)
H = {"Authorization": f"Bearer {token}", "X-Requested-With": "XMLHttpRequest"}


def show(name, r, n=300):
    ok = r.status_code < 400
    print(f"[{'OK ' if ok else 'ERR'}] {name} {r.status_code} {'' if ok else r.text[:n]}")
    return r


print(f"=== teacher {teacher.id} {teacher.name} ===")

r = show("GET /teaching/overview", client.get("/api/teaching/overview", headers=H))
course_id = None
if r.status_code == 200:
    d = r.json()
    print(
        f"    semester={d['semester']} week={d['current_week']} courses={len(d['courses'])} "
        f"today={d['today_course_count']} students={d['total_student_count']} overlap={d['overlap_student_count']}"
    )
    if d["courses"]:
        c0 = d["courses"][0]
        print(
            f"    course#{c0['id']} {c0['name']} / {c0['class_name']} / 任课 {c0['teacher']} "
            f"/ {c0['student_count']}人 / {c0['location']} / 节次{c0['start_period']}-{c0['end_period']}"
        )
        course_id = c0["id"]

if course_id:
    r = show("GET /teaching/attendance/roster", client.get(f"/api/teaching/attendance/roster?course_id={course_id}", headers=H))
    if r.status_code == 200:
        d = r.json()
        print(f"    roster={len(d['roster'])} auto_leave={sum(1 for x in d['roster'] if x['auto_leave'])} date={d['attend_date']}")
        items = [
            {"student_id": x["student_id"], "status": "absent" if i == 0 else "present"}
            for i, x in enumerate(d["roster"][:5])
        ]
        r2 = show("POST /teaching/attendance/mark", client.post(
            "/api/teaching/attendance/mark", headers=H,
            json={
                "course_id": course_id,
                "attend_date": d["attend_date"],
                "period_start": d["period_start"],
                "period_end": d["period_end"],
                "items": items,
            },
        ))
        if r2.status_code == 200:
            print("    mark:", r2.json())

    r = show("GET /teaching/attendance/stats", client.get(f"/api/teaching/attendance/stats?course_id={course_id}", headers=H))
    if r.status_code == 200:
        d = r.json()
        print(f"    sessions={d['sessions']} students={d['student_count']} avg_rate={d['avg_rate']}")

    r = show("GET /teaching/grades", client.get(f"/api/teaching/grades/{course_id}", headers=H))
    if r.status_code == 200:
        d = r.json()
        print(f"    graded={d['graded']}/{d['count']} avg={d['avg']} pass={d['pass_rate']} dist={d['distribution']}")

    r = show("POST /teaching/grades (import)", client.post(
        "/api/teaching/grades", headers=H,
        json={"course_id": course_id, "items": [{"username": "no_such_user_xyz", "score": 55}]},
    ))
    if r.status_code == 200:
        print("    import:", r.json())

show("GET /teaching/homeworks", client.get("/api/teaching/homeworks", headers=H))
r = show("GET /academic/courses?scope=taught", client.get("/api/academic/courses?scope=taught", headers=H))
if r.status_code == 200:
    print(f"    taught courses={len(r.json())}")
r = show("GET /academic/courses?scope=tutored", client.get("/api/academic/courses?scope=tutored", headers=H))
if r.status_code == 200:
    print(f"    tutored courses={len(r.json())}")
