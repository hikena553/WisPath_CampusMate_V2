# -*- coding: utf-8 -*-
"""回滚误绑定 + 用全新学号为 t1001 重新注入测试学生。

Phase A: 恢复 2024101~2024106 的原导师/原班级（t2013/t2014/t2015 名下）
Phase B: 删除误插入到这些学生身上的成绩(32)/成长记录(8)/请假(5)
Phase C: 用未占用学号 2024141~2024146 创建 6 名新学生绑定 t1001，并注入配套数据
"""
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import bcrypt
import pymysql

env = Path(r"D:\StudyNote\Mian02\backend\.env").read_text(encoding="utf-8")
u, p, h, pt, db = re.search(
    r"DATABASE_URL=mysql\+pymysql://([^:]+):([^@]+)@([^:/]+):(\d+)/(\w+)", env
).groups()
conn = pymysql.connect(host=h, port=int(pt), user=u, password=p,
                       database=db, charset="utf8mb4", autocommit=False)
cur = conn.cursor()
today = date.today()


def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# ═══ Phase A: 恢复原绑定 ═══════════════════════════════════
# (学号, 原tutor_id, 原class_group_id, 原class_name)
restore = [
    ("2024101", 482, 125, "2024级健康服务与管理1班"),
    ("2024102", 482, 125, "2024级健康服务与管理1班"),
    ("2024103", 482, 21, "2024级学前教育1班"),
    ("2024104", 483, 21, "2024级学前教育1班"),
    ("2024105", 482, 22, "2024级英语1班"),
    ("2024106", 484, 22, "2024级英语1班"),
]
for uno, tutor, cg_id, cname in restore:
    cur.execute(
        "UPDATE users SET tutor_id=%s, class_group_id=%s, class_name=%s WHERE username=%s",
        (tutor, cg_id, cname, uno),
    )
    print(f"[A] 已恢复 {uno} → tutor={tutor}, class={cname}")
conn.commit()

# ═══ Phase B: 删除误插入数据 ═══════════════════════════════
sid_of = {}
cur.execute("SELECT id, username FROM users WHERE username LIKE '202410%'")
for uid, uno in cur.fetchall():
    sid_of[uno] = uid

# B1. 成绩：32 个 (学生, 课程, 学期) 组合均为本次新插入，逐组删除并校验
my_grades = {
    "2024101": [("高等数学(上)", "2023-2024-1"), ("大学英语(1)", "2023-2024-1"),
                ("C语言", "2023-2024-2"), ("数据结构", "2024-2025-1"),
                ("操作系统", "2024-2025-1"), ("Web前端开发", "2024-2025-2")],
    "2024102": [("高等数学(上)", "2023-2024-1"), ("大学英语(1)", "2023-2024-1"),
                ("C语言", "2023-2024-2"), ("线性代数", "2023-2024-2"),
                ("数据结构", "2024-2025-1"), ("数据库原理", "2024-2025-2")],
    "2024103": [("高等数学(上)", "2023-2024-1"), ("离散数学", "2023-2024-2"),
                ("Java程序设计", "2024-2025-1"), ("软件工程", "2024-2025-1"),
                ("计算机网络", "2024-2025-2")],
    "2024104": [("高等数学(上)", "2023-2024-1"), ("大学英语(1)", "2023-2024-1"),
                ("Java程序设计", "2024-2025-1"), ("软件工程", "2024-2025-1"),
                ("Web前端开发", "2024-2025-2")],
    "2024105": [("高等数学(上)", "2023-2024-1"), ("大学英语(1)", "2023-2024-1"),
                ("C语言", "2023-2024-2"), ("算法设计与分析", "2024-2025-1"),
                ("C++程序设计", "2024-2025-2")],
    "2024106": [("高等数学(上)", "2023-2024-1"), ("大学英语(1)", "2023-2024-1"),
                ("C语言", "2023-2024-2"), ("算法设计与分析", "2024-2025-1"),
                ("C++程序设计", "2024-2025-2")],
}
deleted = 0
for uno, combos in my_grades.items():
    sid = sid_of[uno]
    for course, sem in combos:
        cur.execute(
            "DELETE FROM grades WHERE student_id=%s AND course_name=%s AND semester=%s",
            (sid, course, sem),
        )
        deleted += cur.rowcount
conn.commit()
print(f"[B] 删除误插成绩: {deleted} 条（预期 32）")

# B2. 成长记录：按标题+插入时使用的相对日期精确匹配
my_growth = [
    ("蓝桥杯省赛三等奖", today - timedelta(days=100)),
    ("暑期软件开发实训", today - timedelta(days=45)),
    ("校一等奖学金", today - timedelta(days=70)),
    ("全国大学生数学建模竞赛省二等奖", today - timedelta(days=210)),
    ("校园二手交易平台", today - timedelta(days=20)),
    ("迎新志愿者", today - timedelta(days=80)),
    ("优秀学生干部", today - timedelta(days=55)),
    ("基于Vue的校园服务系统设计", today - timedelta(days=35)),
    ("程序设计天梯赛全国总决赛", today - timedelta(days=150)),
]
deleted = 0
for uno in sid_of:
    sid = sid_of[uno]
    for title, rdate in my_growth:
        cur.execute(
            "DELETE FROM growth_records WHERE student_id=%s AND title=%s AND date=%s",
            (sid, title, rdate),
        )
        deleted += cur.rowcount
conn.commit()
print(f"[B] 删除误插成长记录(按标题+相对日期精确匹配): {deleted} 条（预期 8）")

# B3. 请假：按 reason 精确删除（查证过恰好 5 条全为本批插入）
my_reasons = ("参加省级程序设计竞赛决赛", "感冒发烧需要就医", "家中有事需要回家处理",
              "身体不适去医院检查", "个人事务")
fmt = ",".join(["%s"] * len(my_reasons))
cur.execute(f"DELETE FROM leave_requests WHERE reason IN ({fmt})", my_reasons)
deleted = cur.rowcount
conn.commit()
print(f"[B] 删除误插请假: {deleted} 条（预期 5）")

# ═══ Phase C: 全新学号注入 ═════════════════════════════════
cur.execute("SELECT id FROM users WHERE username='t1001'")
teacher_id = cur.fetchone()[0]

cur.execute("SELECT id, name FROM class_groups WHERE name IN (%s,%s,%s)",
            ("2024级软件工程1班", "2024级软件工程2班", "2024级计算机科学与技术1班"))
cg = {name: cid for cid, name in cur.fetchall()}

students = [
    ("2024141", "林晓阳", "2024级软件工程1班", "男"),
    ("2024142", "苏雨欣", "2024级软件工程1班", "女"),
    ("2024143", "陈子豪", "2024级软件工程2班", "男"),
    ("2024144", "黄佳琪", "2024级软件工程2班", "女"),
    ("2024145", "吴浩然", "2024级计算机科学与技术1班", "男"),
    ("2024146", "郑心怡", "2024级计算机科学与技术1班", "女"),
]
pw_hash = hash_pw("123456")
student_ids = {}
for uno, name, cg_name, gender in students:
    cur.execute("SELECT id FROM users WHERE username=%s", (uno,))
    if cur.fetchone():
        sys.exit(f"学号 {uno} 已被占用，中止（避免再次误绑）")
    cur.execute(
        """INSERT INTO users (username, password_hash, name, role, college, gender,
           tutor_id, class_group_id, class_name, department, password_changed)
           VALUES (%s,%s,%s,'student','人工智能学院',%s,%s,%s,%s,'绵阳城市学院',0)""",
        (uno, pw_hash, name, gender, teacher_id, cg[cg_name], cg_name),
    )
    student_ids[uno] = cur.lastrowid
    print(f"[C] + 学生 {uno} {name} ({cg_name}) → t1001")
conn.commit()

grades_map = {
    "2024141": [(82,4,3.3,"2023-2024-1","高等数学(上)"),(79,3,3.0,"2023-2024-1","大学英语(1)"),
                (88,3,3.7,"2023-2024-2","C语言"),(85,4,3.5,"2024-2025-1","数据结构"),
                (90,4,3.8,"2024-2025-1","操作系统"),(92,3,4.0,"2024-2025-2","Web前端开发")],
    "2024142": [(94,4,4.0,"2023-2024-1","高等数学(上)"),(91,3,3.9,"2023-2024-1","大学英语(1)"),
                (96,3,4.0,"2023-2024-2","C语言"),(93,3,4.0,"2023-2024-2","线性代数"),
                (95,4,4.0,"2024-2025-1","数据结构"),(97,3,4.0,"2024-2025-2","数据库原理")],
    "2024143": [(64,4,2.0,"2023-2024-1","高等数学(上)"),(58,3,1.5,"2023-2024-2","离散数学"),
                (71,3,2.8,"2024-2025-1","Java程序设计"),(75,3,3.0,"2024-2025-1","软件工程"),
                (68,3,2.5,"2024-2025-2","计算机网络")],
    "2024144": [(85,4,3.5,"2023-2024-1","高等数学(上)"),(88,3,3.7,"2023-2024-1","大学英语(1)"),
                (83,3,3.3,"2024-2025-1","Java程序设计"),(87,3,3.7,"2024-2025-1","软件工程"),
                (89,3,3.8,"2024-2025-2","Web前端开发")],
    "2024145": [(48,4,0.0,"2023-2024-1","高等数学(上)"),(55,3,1.5,"2023-2024-1","大学英语(1)"),
                (52,3,1.3,"2023-2024-2","C语言"),(61,3,2.0,"2024-2025-1","算法设计与分析"),
                (58,4,1.5,"2024-2025-2","C++程序设计")],
    "2024146": [(76,4,2.8,"2023-2024-1","高等数学(上)"),(80,3,3.2,"2023-2024-1","大学英语(1)"),
                (78,3,3.0,"2023-2024-2","C语言"),(74,3,2.8,"2024-2025-1","算法设计与分析"),
                (81,4,3.2,"2024-2025-2","C++程序设计")],
}
n = 0
for uno, rows in grades_map.items():
    sid = student_ids[uno]
    for score, credit, gpa, sem, course in rows:
        cur.execute(
            "INSERT INTO grades (student_id, course_name, score, credit, gpa, semester) VALUES (%s,%s,%s,%s,%s,%s)",
            (sid, course, score, credit, gpa, sem),
        )
        n += 1
conn.commit()
print(f"[C] 成绩插入 {n} 条")

growth = [
    ("2024141", "competition", "蓝桥杯省赛三等奖", today - timedelta(days=100), "工业和信息化部人才交流中心", "省级"),
    ("2024141", "practice", "暑期软件开发实训", today - timedelta(days=45), None, None),
    ("2024142", "honor", "校一等奖学金", today - timedelta(days=70), None, None),
    ("2024142", "competition", "全国大学生数学建模竞赛省二等奖", today - timedelta(days=210), "中国工业与应用数学学会", "省级"),
    ("2024142", "achievement", "校园二手交易平台", today - timedelta(days=20), None, None),
    ("2024143", "practice", "迎新志愿者", today - timedelta(days=80), None, None),
    ("2024144", "honor", "优秀学生干部", today - timedelta(days=55), None, None),
    ("2024146", "competition", "程序设计天梯赛全国总决赛", today - timedelta(days=150), "全国高校计算机教育研究会", "国家级"),
]
n = 0
for uno, rtype, title, rdate, organizer, level in growth:
    cur.execute(
        """INSERT INTO growth_records (student_id, type, title, date, organizer, competition_level)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (student_ids[uno], rtype, title, rdate, organizer, level),
    )
    n += 1
conn.commit()
print(f"[C] 成长记录插入 {n} 条")

leaves = [
    ("2024141", today + timedelta(days=3), today + timedelta(days=4), "参加省级程序设计竞赛决赛", "competition", "pending", None),
    ("2024142", today - timedelta(days=20), today - timedelta(days=19), "感冒发烧需要就医", "sick", "approved", None),
    ("2024143", today + timedelta(days=7), today + timedelta(days=9), "家中有事需要回家处理", "personal", "pending", None),
    ("2024144", today - timedelta(days=50), today - timedelta(days=49), "身体不适去医院检查", "sick", "approved", None),
    ("2024145", today - timedelta(days=15), today - timedelta(days=14), "个人事务", "personal", "rejected", "理由不充分，请补充详细信息后再提交"),
]
n = 0
for uno, sd, ed, reason, ltype, status, rr in leaves:
    cur.execute(
        """INSERT INTO leave_requests
           (student_id, start_date, end_date, reason, leave_type, status, tutor_id, reject_reason,
            return_confirmed, created_at, updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s)""",
        (student_ids[uno], sd, ed, reason, ltype, status, teacher_id, rr, today, today),
    )
    n += 1
conn.commit()
print(f"[C] 请假插入 {n} 条")

# ═══ 校验 ═══════════════════════════════════════════════════
cur.execute("""SELECT u.username, u.name, u.class_name FROM users u
               WHERE u.tutor_id=%s ORDER BY u.username""", (teacher_id,))
print("\n=== t1001 名下学生（最终） ===")
for r in cur.fetchall():
    print(f"  {r[0]}  {r[1]}  {r[2]}")

cur.execute("SELECT username, tutor_id, class_name FROM users WHERE username LIKE '202410%' ORDER BY username")
print("\n=== 原学生归属已恢复 ===")
for r in cur.fetchall():
    print(f"  {r[0]}  tutor_id={r[1]}  {r[2]}")

conn.close()
print("\n全部完成 ✔  新学生密码均为 123456")
