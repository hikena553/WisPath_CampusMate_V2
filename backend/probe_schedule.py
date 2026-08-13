import sys
sys.path.insert(0, r"D:\StudyNote\Mian02\backend")
from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
# 看班级1 每个学期的课程分布
for sem in ["2025-2026-2", "2025-2026-1", "2024-2025-2", "2024-2025-1"]:
    rows = db.execute(text("""
        SELECT name, teacher, day_of_week, start_period, end_period, location
        FROM courses WHERE class_group_id=1 AND semester=:s
        ORDER BY day_of_week, start_period
    """), {"s": sem}).fetchall()
    print(f"== {sem} ==")
    for r in rows:
        print(f"  周{r[2]} 第{r[3]}-{r[4]}节 {r[0]} ({r[1]}) {r[5]}")

# 检查是否同班同天同时段冲突
print("\n== 冲突检查: 同班级同学期同(周,节)重复 ==")
rows = db.execute(text("""
    SELECT class_group_id, semester, day_of_week, start_period, COUNT(*) c
    FROM courses
    GROUP BY class_group_id, semester, day_of_week, start_period
    HAVING c > 1 LIMIT 20
""")).fetchall()
print("冲突数量:", len(rows), rows[:10])

# 检查同一老师时间冲突
print("\n== 冲突检查: 同一老师同时间 ==")
rows = db.execute(text("""
    SELECT teacher, day_of_week, start_period, semester, COUNT(*) c
    FROM courses
    GROUP BY teacher, semester, day_of_week, start_period
    HAVING c > 1 LIMIT 20
""")).fetchall()
print("冲突数量:", len(rows), rows[:5])

# 检查每天节次分布
print("\n== 某班某学期 day/period 分布 ==")
rows = db.execute(text("""
    SELECT day_of_week, start_period, end_period, COUNT(*) c
    FROM courses WHERE class_group_id=1 AND semester='2025-2026-2'
    GROUP BY day_of_week, start_period, end_period
""")).fetchall()
for r in rows:
    print(f"  周{r[0]} 第{r[1]}-{r[2]}节 数量={r[3]}")
db.close()