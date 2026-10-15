"""表情识别模型训练 / 微调 API。

设计要点：
- Web 运行时**不依赖 torch**：本模块只在需要发起训练时才惰性导入 `ml.train`，
  未安装训练依赖时给出明确错误，其余只读接口（列表/指标/产物）始终可用。
- 训练产物（runs/<run_id>/）由 `backend/ml/train.py` 落盘，本模块只扫描读取。
- 发起训练需管理员权限；训练在后台线程执行，返回 job_id 供轮询。
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.deps import require_role
from app.models.user import UserRole

router = APIRouter(prefix="/api/ml", tags=["ml-training"])

_admin_only = require_role(UserRole.ADMIN)

# backend/ml/runs（本文件位于 backend/app/api/）
_RUNS_DIR = Path(__file__).resolve().parents[2] / "ml" / "runs"
# 允许直接下载的产物（白名单，防目录穿越）
_ALLOWED_FILES = {
    "config.json", "metrics.json", "history.csv", "summary.md", "classification_report.txt",
    "training_curves.png", "confusion_matrix.png", "confusion_matrix_normalized.png",
    "best_model.pt",
}
# 图片型产物（供前端直接 <img> 展示）
IMAGE_FILES = {
    "training_curves.png", "confusion_matrix.png", "confusion_matrix_normalized.png",
}

# 后台训练任务注册表（进程内）
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


def _safe_run_dir(run_id: str) -> Path:
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(400, "非法 run_id")
    d = _RUNS_DIR / run_id
    if not d.is_dir():
        raise HTTPException(404, "训练运行不存在")
    return d


@router.get("/runs")
def list_runs(user=Depends(_admin_only)):
    """列出全部训练运行（按时间倒序），返回关键指标摘要。"""
    import json

    if not _RUNS_DIR.is_dir():
        return {"runs": [], "runs_dir": str(_RUNS_DIR)}

    runs = []
    for d in sorted(_RUNS_DIR.iterdir(), reverse=True):
        mf = d / "metrics.json"
        if not d.is_dir() or not mf.exists():
            continue
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        runs.append({
            "run_id": d.name,
            "created_at": meta.get("created_at"),
            "epochs_trained": meta.get("epochs_trained"),
            "best_val_acc": meta.get("best_val_acc"),
            "best_epoch": meta.get("best_epoch"),
            "test_accuracy": (meta.get("test") or {}).get("accuracy"),
            "test_macro_f1": (meta.get("test") or {}).get("macro_f1"),
            "test_top2_accuracy": (meta.get("test") or {}).get("top2_accuracy"),
            "params": meta.get("params"),
            "device": meta.get("device"),
            "elapsed_sec": meta.get("elapsed_sec"),
            "has_metrics": True,
        })
    return {"runs": runs, "count": len(runs), "runs_dir": str(_RUNS_DIR)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, user=Depends(_admin_only)):
    """读取某次运行的完整指标（metrics.json）。"""
    import json

    d = _safe_run_dir(run_id)
    mf = d / "metrics.json"
    if not mf.exists():
        raise HTTPException(404, "该运行缺少 metrics.json")
    return json.loads(mf.read_text(encoding="utf-8"))


@router.get("/runs/{run_id}/file/{name}")
def get_run_file(run_id: str, name: str, user=Depends(_admin_only)):
    """下载某次运行的产物文件（白名单限制）。"""
    if name not in _ALLOWED_FILES:
        raise HTTPException(400, f"不允许访问的产物：{name}")
    d = _safe_run_dir(run_id)
    fp = d / name
    if not fp.exists():
        raise HTTPException(404, "产物不存在")
    media = "image/png" if name.endswith(".png") else (
        "application/json" if name.endswith(".json") else
        "text/csv" if name.endswith(".csv") else "text/plain"
    )
    return FileResponse(str(fp), media_type=media, filename=name)


@router.post("/train")
def start_training(payload: dict | None = None, user=Depends(_admin_only)):
    """发起一次训练/微调（后台线程执行）。未安装 torch 时返回明确错误。"""
    payload = payload or {}
    try:
        import ml.train as ml_train  # 惰性导入：Web 运行时默认无 torch
        from ml.config import TrainingConfig
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            503,
            f"训练依赖不可用（需先 pip install -r backend/ml/requirements-train.txt）：{exc}",
        )

    overrides = payload.get("config") or {}
    cfg = TrainingConfig.from_kwargs(**overrides)
    if payload.get("smoke"):
        cfg = ml_train._apply_smoke(cfg)

    job_id = uuid.uuid4().hex[:12]
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id": job_id, "status": "running", "run_id": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "epochs": [], "error": None, "result": None,
        }

    def _worker():
        try:
            def _progress(rec):
                with _JOBS_LOCK:
                    _JOBS[job_id]["epochs"].append(rec)

            meta = ml_train.run_training(cfg, progress=_progress)
            with _JOBS_LOCK:
                _JOBS[job_id].update(status="finished", run_id=meta["run_id"], result={
                    "best_val_acc": meta["best_val_acc"],
                    "test_accuracy": meta["test"]["accuracy"],
                    "test_macro_f1": meta["test"]["macro_f1"],
                })
        except Exception as exc:  # pragma: no cover
            with _JOBS_LOCK:
                _JOBS[job_id].update(status="failed", error=str(exc))

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "running"}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user=Depends(_admin_only)):
    """查询后台训练任务进度。"""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return job