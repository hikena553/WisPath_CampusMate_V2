# -*- coding: utf-8 -*-
"""为 t1001 注入心理预警手动测试数据（幂等：按 summary 前缀 [seed] 识别，重复执行只补缺）。

覆盖场景：
- 2024181 周明轩：severe 未闭环（刚发生）+ 1 条历史 moderate 已闭环（含干预记录）
- 2024182 李思涵：moderate 未闭环（13 小时前 → SLA 临期）+ 随访日期今天
- 2024183 王梓萌：mild 未闭环（3 天前 → SLA 逾期）+ 情绪台账 6 条（频次升级素材）
- 2024184 张瑞：已闭环（谈话 + 约谈家长台账）+ 1 条 mild 未闭环
- 家长联系人 / 家校沟通台账 / 教师站内通知

运行：backend 目录下 python scripts/seed_t1001_crisis.py
"""
import re
import sys
from datetime import datetime, timedelta, timezone
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
now = datetime.now(timezone.utc).replace(tzinfo=None)  # DB 存 naive UTC
MARK = "[seed]"


def cols(table: str) -> set[str]:
    cur.execute(f"SHOW COLUMNS FROM {table}")
    return {r[0] for r in cur.fetchall()}


# ═══ 0. 教师与新列检测 ═══════════════════════════════════
cur.execute("SELECT id FROM users WHERE username='t1001'")
row = cur.fetchone()
if not row:
    sys.exit("未找到教师 t1001，请先创建")
teacher_id = row[0]

alert_cols = cols("ai_dialog_summaries")
has_triage = "triage_status" in alert_cols
if not has_triage:
    print("⚠ ai_dialog_summaries 缺 triage_* 列，请先执行 alembic upgrade head；本次按旧结构插入")

emo_cols = cols("emotion_records")
has_note = "note" in emo_cols

# 幂等：清掉本脚本历史数据后重灌（保证时间相对"现在"新鲜）
for table, cond in [
    ("ai_dialog_summaries", "summary LIKE %s"),
    ("emotion_records", "note LIKE %s OR (source='ai_dialog' AND %s=%s)"),
    ("guardian_contact_logs", "content_summary LIKE %s"),
]:
    try:
        if table == "emotion_records":
            cur.execute("DELETE FROM emotion_records WHERE source='ai_dialog' AND user_id IN (SELECT id FROM users WHERE username LIKE '202418_')")
        else:
            cur.execute(f"DELETE FROM {table} WHERE {cond}", (MARK + "%",))
    except Exception as e:
        print(f"清理 {table} 跳过: {e}")
        conn.rollback()
cur.execute("DELETE FROM notifications WHERE title LIKE %s AND user_id=%s", (MARK + "%", teacher_id))
cur.execute("""DELETE g FROM guardians g JOIN users u ON u.id=g.student_id
               WHERE u.username LIKE '202418_' AND g.remark='seed'""")
conn.commit()
print("[0] 历史种子数据已清理")


def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# ═══ 1. 四名测试学生 ═════════════════════════════════════
students = [
    ("2024181", "周明轩", "2024级软件工程1班", "男"),
    ("2024182", "李思涵", "2024级软件工程1班", "女"),
    ("2024183", "王梓萌", "2024级软件工程2班", "女"),
    ("2024184", "张瑞", "2024级软件工程2班", "男"),
]
pw_hash = hash_pw("123456")
sid = {}
for uno, name, cname, gender in students:
    cur.execute("SELECT id, tutor_id FROM users WHERE username=%s", (uno,))
    r = cur.fetchone()
    if r:
        sid[uno] = r[0]
        if r[1] != teacher_id:
            cur.execute("UPDATE users SET tutor_id=%s WHERE id=%s", (teacher_id, r[0]))
            print(f"[1] {uno} {name} 已存在，重新绑定到 t1001")
        else:
            print(f"[1] {uno} {name} 已存在，跳过创建")
    else:
        cur.execute(
            """INSERT INTO users (username, password_hash, name, role, college, gender,
               tutor_id, class_name, department, password_changed)
               VALUES (%s,%s,%s,'student','人工智能学院',%s,%s,%s,'绵阳城市学院',0)""",
            (uno, pw_hash, name, gender, teacher_id, cname),
        )
        sid[uno] = cur.lastrowid
        print(f"[1] + 学生 {uno} {name} → t1001（密码 123456）")
conn.commit()


# ═══ 2. 预警记录 ═════════════════════════════════════════
def insert_alert(student_id, summary, level, kws, created, *, resolved=False,
                 intervention=None, note=None, follow_up=None, resolved_by=None,
                 source="llm", reason=None, raw=None):
    extra, params = "", []
    if has_triage:
        extra = ", triage_status, triage_source, judge_reason"
        params = ["alert", source, reason or "种子数据"]
    cur.execute(
        f"""INSERT INTO ai_dialog_summaries
            (student_id, summary, level, keywords_matched, raw_snippet, resolved,
             intervention_type, intervention_note, resolved_by, resolved_at, follow_up_date,
             created_at{extra})
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s{(',' + ','.join(['%s'] * len(params))) if params else ''})""",
        (student_id, summary, level, kws, (raw or summary)[:200], 1 if resolved else 0,
         intervention, note, resolved_by,
         now if resolved else None, follow_up, created, *params),
    )


# 2024181：severe 刚发生（未闭环、未干预）+ 历史 moderate 已闭环（1 天前干预谈话）
insert_alert(
    sid["2024181"], f"{MARK} 学生在对话中多次表达绝望情绪，称「感觉再也撑不下去了」，伴有睡眠问题", "SEVERE",
    "绝望,撑不住,失眠", now - timedelta(minutes=30),
    source="hard_gate", reason="硬词直通：自杀", raw="我真的感觉再也撑不下去了……",
)
insert_alert(
    sid["2024181"], f"{MARK} 学生倾诉考试周压力大，情绪焦虑", "MODERATE", "焦虑,压力大",
    now - timedelta(days=6), resolved=True, intervention="TALK",
    note="已面谈，情绪平稳，约定一周后复查", resolved_by=teacher_id,
    follow_up=(now + timedelta(days=1)).date(), reason="压力表达明确，建议谈话",
)

# 2024182：moderate 13 小时前（SLA 12~24h 临期）+ 随访今天
insert_alert(
    sid["2024182"], f"{MARK} 学生连续两晚未睡，自述心慌、害怕期末挂科，情绪波动明显", "MODERATE",
    "失眠,心慌,害怕", now - timedelta(hours=13),
    follow_up=now.date(), reason="睡眠困扰伴焦虑，中度预警",
)

# 2024183：mild 3 天前（SLA 逾期）+ 情绪台账 6 条
insert_alert(
    sid["2024183"], f"{MARK} 学生近两周情绪偏低，自述「没什么意思」，兴趣减退", "MILD",
    "没意思,难受", now - timedelta(days=3),
    reason="短时研判 mid：情绪偏低但无极端表达",
)
ledger_notes = [
    f"{MARK} 对话提到课程压力大，情绪一般",
    f"{MARK} 自述没睡好，上课提不起精神",
    f"{MARK} 提到和室友有些小摩擦",
    f"{MARK} 说最近食欲不太好",
    f"{MARK} 感觉日子过得没意思",
    f"{MARK} 周末也不想出门",
]
for i, note in enumerate(ledger_notes):
    created = now - timedelta(days=2, hours=i * 3)
    if has_note:
        cur.execute(
            "INSERT INTO emotion_records (user_id, emotion, confidence, source, note, created_at) VALUES (%s,%s,%s,'ai_dialog',%s,%s)",
            (sid["2024183"], "negative", 0.6, note, created),
        )
    else:
        cur.execute(
            "INSERT INTO emotion_records (user_id, emotion, confidence, source, created_at) VALUES (%s,%s,%s,'ai_dialog',%s)",
            (sid["2024183"], "negative", 0.6, created),
        )
print("[2] 2024183 情绪台账 6 条（ai_dialog）")

# 2024184：已闭环（谈话 + 约谈家长）+ 1 条 mild 未闭环
insert_alert(
    sid["2024184"], f"{MARK} 学生自述与家人争执后情绪崩溃，已平复", "MODERATE",
    "崩溃,难受", now - timedelta(days=10),
    resolved=True, intervention="PARENT_MEETING",
    note="已与学生及家长三方沟通，家庭关系缓和，持续观察", resolved_by=teacher_id,
    follow_up=(now - timedelta(days=2)).date(), reason="家庭冲突引发，建议家校沟通",
)
insert_alert(
    sid["2024184"], f"{MARK} 学生提到近期容易想哭，情绪起伏", "MILD",
    "想哭", now - timedelta(hours=5),
    reason="短时研判 mid：轻度情绪波动",
)
print("[2] 预警记录 6 条（含闭环/随访/SLA 各态）")


# ═══ 3. 家长联系人 + 家校沟通台账 ═════════════════════════
guardians = [
    ("2024184", "张国强", "父亲", "13800001841", True),
    ("2024182", "刘慧", "母亲", "13800001842", True),
]
gid = {}
for uno, name, rel, phone, primary in guardians:
    cur.execute(
        """INSERT INTO guardians (student_id, name, relation, phone, is_primary, remark, is_deleted, created_at)
           VALUES (%s,%s,%s,%s,%s,'seed',0,%s)""",
        (sid[uno], name, rel, phone, 1 if primary else 0, now),
    )
    gid[uno] = cur.lastrowid
logs = [
    ("2024184", gid["2024184"], "CRISIS", "NOTE",
     f"{MARK} 危机干预约谈家长：反馈学生情绪已平稳，建议家长周末多陪伴"),
    ("2024182", gid["2024182"], "CARE", "NOTE",
     f"{MARK} 日常关怀沟通：告知家长学生近期睡眠欠佳，请留意作息"),
]
for uno, g, scene, ch, content in logs:
    cur.execute(
        """INSERT INTO guardian_contact_logs (student_id, guardian_id, teacher_id, scene, channel, status, content_summary, is_deleted, created_at)
           VALUES (%s,%s,%s,%s,%s,'SENT',%s,0,%s)""",
        (sid[uno], g, teacher_id, scene, ch, content, now),
    )
print("[3] 家长联系人 2 位 + 沟通台账 2 条")


# ═══ 4. 教师站内通知（模拟实时推送落库） ═════════════════
notices = [
    ("urgent", f"{MARK} 心理预警（高危）", "学生周明轩对话中出现高危信号，请立即跟进"),
    ("important", f"{MARK} 心理预警（中度）", "学生李思涵出现中度预警，24 小时内请响应"),
]
for lv, title, content in notices:
    cur.execute(
        """INSERT INTO notifications (user_id, title, content, type, level, is_read, link, created_at)
           VALUES (%s,%s,%s,'crisis',%s,0,'/teacher/crisis',%s)""",
        (teacher_id, title, content, lv, now),
    )
print("[4] 教师站内通知 2 条")


# ═══ 校验输出 ═════════════════════════════════════════════
conn.commit()
cur.execute(
    """SELECT u.username, u.name, s.summary, s.level, s.resolved, s.triage_source
       FROM ai_dialog_summaries s JOIN users u ON u.id=s.student_id
       WHERE s.summary LIKE %s ORDER BY s.created_at""",
    (MARK + "%",),
)
print("\n=== 预警数据总览 ===")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]} | {r[2][:38]}… | level={r[3]} resolved={r[4]} source={r[5]}")
conn.close()
print("\n完成 ✔  学生密码均为 123456，用 t1001 登录教师端 → 心理预警 查看工作台")
