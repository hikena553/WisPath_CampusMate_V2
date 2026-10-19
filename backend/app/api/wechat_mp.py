"""微信小程序部署接口：为「系统设置 → 微信小程序」提供配置校验与一键部署链路。

部署链路分四步（前端按步骤展示）：
1) 读取配置   2) 校验 AppID/AppSecret   3) 生成小程序工程   4) 上传代码（miniprogram-ci）
仅管理员可访问；AppSecret / 代码上传密钥等敏感值加密存储、接口脱敏返回。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.crypto import is_masked_value
from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.services import wechat_mp_service as mp

router = APIRouter(prefix="/api/settings/wechat-mp", tags=["微信小程序"])


class VerifyRequest(BaseModel):
    """可传入页面当前填写值做「未保存先校验」；掩码或空值则回退数据库存储值。"""

    appid: str | None = None
    appsecret: str | None = None


class DeployRequest(BaseModel):
    version: str | None = None
    desc: str | None = None
    upload: bool = True


@router.get("/info")
def get_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """返回微信小程序配置完备度与工程生成状态（仅管理员）。"""
    return mp.config_status(db)


@router.post("/verify")
def verify(
    data: VerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """校验 AppID + AppSecret 是否有效（真实调用微信 cgi-bin/token）。"""
    cfg = mp.load_config(db)
    appid = data.appid if (data.appid and not is_masked_value(data.appid)) else cfg["appid"]
    appsecret = data.appsecret if (data.appsecret and not is_masked_value(data.appsecret)) else cfg["appsecret"]
    return mp.verify_credentials(appid or "", appsecret or "")


@router.post("/deploy")
def deploy(
    data: DeployRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """执行部署链路，逐步返回每步结果（仅管理员）。

    任一步失败不抛异常，而是以 steps[].status 标记，便于前端精确展示卡点。
    """
    cfg = mp.load_config(db)
    steps: list[dict] = []

    # ① 读取配置
    missing = [name for name, ok in (
        ("AppID", cfg["appid"]),
        ("AppSecret", cfg["appsecret"]),
        ("移动端 H5 站点地址", cfg["h5_url"]),
    ) if not ok]
    if missing:
        steps.append({
            "key": "config", "title": "读取配置", "status": "failed",
            "message": f"缺少必填配置：{'、'.join(missing)}",
        })
        return {"ok": False, "steps": steps}
    steps.append({
        "key": "config", "title": "读取配置", "status": "ok",
        "message": f"AppID={cfg['appid']}，H5={cfg['h5_url']}",
    })

    # ② 校验凭据
    verify_result = mp.verify_credentials(cfg["appid"], cfg["appsecret"])
    steps.append({
        "key": "verify", "title": "校验 AppID / AppSecret",
        "status": "ok" if verify_result["ok"] else "failed",
        "message": verify_result["hint"],
    })
    if not verify_result["ok"]:
        return {"ok": False, "steps": steps}

    # ③ 生成小程序工程
    build_result = mp.build_project(cfg["appid"], cfg["h5_url"])
    steps.append({
        "key": "build", "title": "生成小程序工程",
        "status": "ok" if build_result["ok"] else "failed",
        "message": build_result["message"],
    })
    if not build_result["ok"]:
        return {"ok": False, "steps": steps}

    # ④ 上传代码
    if not data.upload:
        steps.append({
            "key": "upload", "title": "上传代码", "status": "pending",
            "message": "已按请求跳过上传；工程已生成，可手动导入微信开发者工具",
        })
        return {"ok": True, "steps": steps}

    upload_result = mp.upload_code(
        cfg["appid"], cfg["upload_key"],
        version=(data.version or mp.DEFAULT_VERSION).strip() or mp.DEFAULT_VERSION,
        desc=(data.desc or "管理端一键部署").strip() or "管理端一键部署",
    )
    upload_status = "ok" if upload_result["ok"] else ("pending" if upload_result.get("skipped") else "failed")
    steps.append({
        "key": "upload", "title": "上传代码（miniprogram-ci）",
        "status": upload_status,
        "message": upload_result["message"],
        "output": upload_result.get("output", ""),
    })
    return {"ok": upload_result["ok"], "steps": steps}