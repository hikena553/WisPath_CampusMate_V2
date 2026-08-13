"""清空 seed_test_data.py 生成的测试数据（保留 app/seed.py 原始种子数据），便于重新干净注入。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()

# 子表优先删除（避免外键约束影响）
TABLES_ORDER = [
    "conversation_messages", "conversations",
    "group_messages", "group_members", "groups",
    "messages", "notifications",
    "student_profile_snapshots",
    "teacher_announcements", "lost_found_items",
    "feedbacks", "certificates",
    "ai_dialog_summaries", "service_tickets",
    "leave_requests", "student_projects",
    "growth_records", "exams", "grades", "courses",
]

for t in TABLES_ORDER:
    try:
        db.execute(text("DELETE FROM `" + t + "`"))
        print("cleared:", t)
    except Exception as e:
        print("ERR", t, str(e)[:80])
db.commit()

# 删除测试生成的教师（t2001+）与测试学生（2023/2025/2026 级学号 + 2024 级 2024010+）
db.execute(text("DELETE FROM users WHERE username LIKE 't2%'"))
db.execute(
    text("DELETE FROM users WHERE username LIKE '2023%' ")
)
db.execute(
    text("DELETE FROM users WHERE username LIKE '2025%' ")
)
db.execute(
    text("DELETE FROM users WHERE username LIKE '2026%' ")
)
db.execute(
    text("DELETE FROM users WHERE username LIKE '2024%' AND username > '2024009' ")
)
db.commit()

# 删除注入标记，允许重新注入
db.execute(text("DELETE FROM system_settings WHERE `key` = 'test_data_seeded_v2'"))
db.commit()

for t in ["users", "class_groups", "courses", "grades", "exams", "growth_records",
          "leave_requests", "service_tickets", "ai_dialog_summaries", "certificates",
          "messages", "groups", "conversations", "system_settings"]:
    n = db.execute(text("SELECT COUNT(*) FROM `" + t + "`")).scalar()
    print("after:", t, n)
db.close()
print("done")