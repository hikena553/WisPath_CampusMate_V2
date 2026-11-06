"""请假撤销（撤回申请）的状态约束。

产品口径：**只有还没被审批的请假能撤销**。旧实现 `DELETE /api/leave/{id}` 没有任何
状态校验，学生可以把「已批准」的记录直接删掉 —— 辅导员台账、出勤统计、销假闭环都会
对不上，等于学生能抹掉一条已经生效的凭证。这里的用例把这个边界钉住。

统一走 `api` fixture（写请求自动带 CSRF 头）。**不要** `from tests.conftest import ...`：
那会让 conftest 以另一个模块名再执行一遍，`sys.modules["magic"]` 被换成绑定新
`_MAGIC_STATE` 的 fake 模块，后续 upload 的 MIME 用例会因读到旧状态而误判
（本文件第一版就是这样把 test_upload 的两个用例打挂的）。
"""
from datetime import date, timedelta

from app.models.leave import LeaveRequest, LeaveStatus, LeaveType


def _make_leave(db, student_id: int, status: LeaveStatus = LeaveStatus.PENDING) -> LeaveRequest:
    today = date.today()
    row = LeaveRequest(
        student_id=student_id,
        start_date=today + timedelta(days=1),
        end_date=today + timedelta(days=2),
        reason="发烧需前往医院就诊",
        leave_type=LeaveType.SICK,
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_withdraw_pending_leave(api, db, login_token):
    """待审批的申请可以撤销，撤销后记录消失。"""
    student = login_token()
    leave = _make_leave(db, student["user"].id)
    leave_id = leave.id  # 先取：记录被删后访问 ORM 属性会抛 ObjectDeletedError

    resp = api.delete(f"/api/leave/{leave_id}", headers=student["headers"])

    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "已撤销"
    db.expire_all()
    assert db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first() is None


def test_withdraw_approved_leave_rejected(api, db, login_token):
    """已批准的申请不能撤销：撤了等于抹掉已生效的请假凭证。"""
    student = login_token()
    leave = _make_leave(db, student["user"].id, LeaveStatus.APPROVED)

    resp = api.delete(f"/api/leave/{leave.id}", headers=student["headers"])

    assert resp.status_code == 400, resp.text
    assert "已通过审批" in resp.json()["detail"]
    db.expire_all()
    assert db.query(LeaveRequest).filter(LeaveRequest.id == leave.id).first() is not None


def test_withdraw_rejected_leave_rejected(api, db, login_token):
    """已退回的申请同样不删：退回原因是学生需要看到的结论，删了就查无此事。"""
    student = login_token()
    leave = _make_leave(db, student["user"].id, LeaveStatus.REJECTED)

    resp = api.delete(f"/api/leave/{leave.id}", headers=student["headers"])

    assert resp.status_code == 400, resp.text
    assert "已退回" in resp.json()["detail"]
    db.expire_all()
    assert db.query(LeaveRequest).filter(LeaveRequest.id == leave.id).first() is not None


def test_withdraw_other_students_leave_not_found(api, db, login_token):
    """越权撤销别人的请假：按「不存在」处理，不泄露该 id 的存在性。"""
    owner = login_token()
    other = login_token()
    leave = _make_leave(db, owner["user"].id)

    resp = api.delete(f"/api/leave/{leave.id}", headers=other["headers"])

    assert resp.status_code == 404, resp.text
    db.expire_all()
    assert db.query(LeaveRequest).filter(LeaveRequest.id == leave.id).first() is not None


def test_withdraw_pending_leave_after_create(api, db, login_token):
    """走真实创建接口再撤销：提交完立刻能撤（前端按钮依赖这个闭环）。"""
    student = login_token()
    today = date.today()
    created = api.post(
        "/api/leave/create",
        json={
            "start_date": str(today + timedelta(days=3)),
            "end_date": str(today + timedelta(days=3)),
            "reason": "[事假] 家里有事",
            "leave_type": "personal",
        },
        headers=student["headers"],
    )
    assert created.status_code == 200, created.text
    leave_id = created.json()["id"]

    resp = api.delete(f"/api/leave/{leave_id}", headers=student["headers"])

    assert resp.status_code == 200, resp.text
    db.expire_all()
    assert db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first() is None
