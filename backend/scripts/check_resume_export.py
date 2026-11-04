"""离线自检：拿真实档案跑一遍匹配 + 3 套模板 × DOCX/PDF，检查字体与段落是否齐全。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import resume_export  # noqa: E402

OUT = Path("D:/StudyNote/Mian02/.workbuddy/tmp/resume")


def pick_student(db):
    """挑项目最多、且有成绩的学生，数据越全越能暴露排版问题。"""
    rows = db.query(User).filter(User.role == "student").all()
    best, best_score = None, -1
    for u in rows:
        n_p = db.query(resume_export.StudentProject).filter_by(student_id=u.id).count()
        n_c = db.query(resume_export.Certificate).filter_by(student_id=u.id).count()
        n_g = db.query(resume_export.Grade).filter_by(student_id=u.id).count()
        score = n_p * 10 + n_c * 4 + n_g
        if score > best_score:
            best, best_score = u, score
    return best


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        user = pick_student(db)
        print(f"学生: id={user.id} name={user.name} college={user.college}")
        profile = resume_export.collect_profile(db, user)
        print(f"技能 {len(profile['skills'])} 项 | 项目 {len(profile['projects'])} | "
              f"证书 {len(profile['certs'])} | 成绩 {profile['grade_count']} 门 "
              f"均分 {profile['avg_score']} 绩点 {profile['gpa']}")
        print("技能:", "、".join(profile["skills"][:10]))

        for ind, job in [("internet", "backend"), ("ai", "algo"), ("other", "general")]:
            m = resume_export.evaluate(profile, ind, job)
            print(f"\n[{m['job']['label']}] 匹配度 {m['score']} ({m['level']})")
            for d in m["dims"]:
                print(f"   {d['label']}: {d['score']} (w={d['weight']}) {d['note']}")
            print("   命中:", "、".join(m["hits"][:8]) or "无")
            print("   缺口:", "、".join(m["gaps"][:5]) or "无")
            print("   建议:", " / ".join(f"{s['label']}({s['score']})" for s in m["suggest"]))

        for tpl in resume_export.TEMPLATES:
            for fmt in ("docx", "pdf"):
                r = resume_export.generate(
                    db, user, job_key="backend", industry="internet",
                    job_type="校招全职", city="成都",
                    template_key=tpl["key"], fmt=fmt,
                )
                path = OUT / r["filename"].replace(".", f"-{tpl['key']}.", 1)
                # 同名会互相覆盖，直接把模板名拼进文件名
                path = OUT / f"{tpl['key']}-{fmt}.{fmt}"
                path.write_bytes(r["data"])
                names = " / ".join(s["title"] for s in r["sections"])
                print(f"{tpl['key']:8s} {fmt:5s} {len(r['data']):>6d}B  {names}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
