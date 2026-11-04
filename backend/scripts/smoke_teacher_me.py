"""「我的育人成长」冒烟：验证聚合、雷达、徽章结算与 Dashboard 扩展字段。

用法：cd backend && python scripts/smoke_teacher_me.py [teacher_id]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.models.user import User  # noqa: E402
from app.main import app  # noqa: E402

TEACHER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 471

db = SessionLocal()
teacher = db.get(User, TEACHER_ID)
token = create_access_token(
    {"sub": str(teacher.id), "role": teacher.role.value, "ph": teacher.password_hash[:8]}
)
db.close()

client = TestClient(app)
H = {"Authorization": f"Bearer {token}", "X-Requested-With": "XMLHttpRequest"}

print(f"=== teacher {teacher.id} {teacher.name} ===")

r = client.get("/api/teacher/me/growth", headers=H)
print(f"[{'OK ' if r.status_code < 400 else 'ERR'}] /teacher/me/growth {r.status_code}")
if r.status_code == 200:
    d = r.json()
    lv = d["level"]
    print(f"    level={lv['level']} {lv['name']} points={lv['points']} next={lv['next_points']} prog={lv['progress']}%")
    print(f"    badges {d['badges']['earned_count']}/{d['badges']['total_count']}")
    duty = d["duty"]
    print(f"    students={duty['student_total']} coverage={duty['coverage_rate']}% cared_month={duty['cared_students_month']}")
    print(f"    tasks {duty['tasks']}")
    print(f"    teaching {d['teaching']}")
    print(f"    timeline={len(d['timeline'])} impact_total={d['impact']['total']} best={d['impact']['best_week']}")
    rd = d["radar"]
    print(f"    radar avg={rd['avg']} top={rd['top']} weak={rd['weak']} peer_cov={rd['peer_coverage']}")
    for i in rd["items"][:3]:
        print(f"      {i['icon']} {i['name']}: {i['score']} (behaviour {i['behaviour_score']}, peer {i['peer_score']})")
else:
    print(r.text[:600])

r = client.get("/api/teacher/me/capabilities", headers=H)
print(f"[{'OK ' if r.status_code < 400 else 'ERR'}] /teacher/me/capabilities {r.status_code}")

r = client.get("/api/teacher/dashboard", headers=H)
print(f"[{'OK ' if r.status_code < 400 else 'ERR'}] /teacher/dashboard {r.status_code}")
if r.status_code == 200:
    d = r.json()
    mine = {k: v for k, v in d.items() if k.startswith("my_") or k in ("today_course_count", "current_week", "semester")}
    print("    ", mine)
else:
    print(r.text[:600])

r = client.get("/api/badges/me", headers=H)
print(f"[{'OK ' if r.status_code < 400 else 'ERR'}] /badge/me {r.status_code}")
if r.status_code == 200:
    b = r.json()
    print(f"    level={b['level']['name']} earned={b['earned_count']}/{b['total_count']}")
