"""微信小程序部署服务：凭据校验 → 生成小程序工程 → 上传代码（miniprogram-ci）。

链路设计（管理员在「系统设置 → 微信小程序」填写并确认后触发）：
1. 调用微信开放接口 `cgi-bin/token` 校验 AppID + AppSecret 是否有效；
2. 基于「移动端 H5 站点地址」生成一个 web-view 壳小程序工程（可直接上传）；
3. 若配置了「代码上传密钥」，调用 miniprogram-ci 上传代码，生成体验版。

重要事实（决定链路形态）：
- 微信官方不提供「仅凭 AppSecret 上传代码」的接口。上传代码必须使用小程序
  「代码上传密钥」（mp.weixin.qq.com → 开发管理 → 开发设置 下载
  `private.<appid>.key`），且该密钥需要在后台把后端出口 IP 加入白名单。
- web-view 组件要求 H5 站点域名已在小程序后台配置为「业务域名」。
因此本服务对上传步骤做降级：未配置上传密钥时仍生成工程，但把上传步骤标记为
pending 并给出明确提示，避免链路中断、也不误报成功。
"""
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value, is_encrypted
from app.models.setting import SystemSetting

logger = logging.getLogger(__name__)

WECHAT_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
# 小程序工程输出目录（容器内为后端根目录下的 wechat_mp_build）
BUILD_ROOT = Path(__file__).resolve().parent.parent.parent / "wechat_mp_build"
PROJECT_DIR = BUILD_ROOT / "project"

# 允许访问 web-view 的最小域名：必须是 https 且已完成 ICP 备案与业务域名配置
DEFAULT_VERSION = "1.0.0"

# 微信常见错误码 → 中文可读提示
_ERROR_HINTS = {
    40013: "AppID 无效，请核对小程序 AppID",
    40125: "AppSecret 无效，请在小程序后台「开发管理 → 开发设置」重置后填写",
    40164: "调用来源 IP 不在白名单，请把后端出口 IP 加入小程序后台 IP 白名单（否则代码上传也会失败）",
    41002: "缺少 AppID",
    45009: "接口调用频率超限，请稍后重试",
}


def friendly_error(errcode: int | None, errmsg: str | None) -> str:
    """把微信 errcode/errmsg 转成管理员可读的提示。"""
    if errcode in _ERROR_HINTS:
        return f"{_ERROR_HINTS[errcode]}（errcode={errcode}, {errmsg or ''}）".strip()
    if errcode:
        return f"微信接口返回错误：{errmsg or ''}（errcode={errcode}）"
    return errmsg or "未知错误"


# ===== 配置读取 =====
def _read_raw(db: Session, key: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return (row.value or "") if row else ""


def _read_secret(db: Session, key: str) -> str:
    """读取敏感配置并解密（未加密的明文原样返回）。"""
    raw = _read_raw(db, key)
    if not raw:
        return ""
    return decrypt_value(raw) if is_encrypted(raw) else raw


def load_config(db: Session) -> dict:
    """汇总微信小程序相关配置，敏感字段解密后返回。"""
    return {
        "appid": _read_raw(db, "wechat_mp_appid").strip(),
        "appsecret": _read_secret(db, "wechat_mp_appsecret").strip(),
        "h5_url": _read_raw(db, "wechat_mp_h5_url").strip(),
        "upload_key": _read_secret(db, "wechat_mp_upload_key").strip(),
    }


# ===== ① 凭据校验 =====
def verify_credentials(appid: str, appsecret: str, timeout: float = 10.0) -> dict:
    """调用微信 cgi-bin/token 校验 AppID + AppSecret。

    返回 {ok, errcode, errmsg, hint, expires_in}；成功即证明「配置 → 微信服务器」
    这一段链路已打通。
    """
    if not appid or not appsecret:
        return {
            "ok": False, "errcode": None,
            "errmsg": "AppID 或 AppSecret 未填写", "hint": "请填写小程序 AppID 与 AppSecret",
            "expires_in": 0,
        }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                WECHAT_TOKEN_URL,
                params={
                    "grant_type": "client_credential",
                    "appid": appid,
                    "secret": appsecret,
                },
            )
            data = resp.json()
    except Exception as exc:  # 网络异常 / 非 JSON 响应
        logger.warning("校验微信小程序凭据失败：%s", exc)
        return {
            "ok": False, "errcode": None,
            "errmsg": f"请求微信接口失败：{exc}", "hint": "请检查后端网络能否访问 api.weixin.qq.com",
            "expires_in": 0,
        }

    if data.get("access_token"):
        return {
            "ok": True, "errcode": 0, "errmsg": "ok",
            "hint": "AppID 与 AppSecret 有效，链路已打通",
            "expires_in": int(data.get("expires_in", 7200)),
        }
    errcode = data.get("errcode")
    errmsg = data.get("errmsg")
    return {
        "ok": False, "errcode": errcode, "errmsg": errmsg,
        "hint": friendly_error(errcode, errmsg), "expires_in": 0,
    }


# ===== ② 生成小程序工程（web-view 壳）=====
# 全屏 web-view 承载移动端 H5；src 由 index.js 的 data.url 注入
_INDEX_WXML = (
    '<!-- 由后端自动生成：全屏 web-view 承载移动端 H5 -->\n'
    '<web-view src="{{url}}" bindmessage="onMessage"></web-view>\n'
)


def build_project(appid: str, h5_url: str, project_name: str = "smart-campus") -> dict:
    """生成一个可直接上传的 web-view 壳小程序工程，返回生成结果。"""
    if not appid:
        return {"ok": False, "message": "缺少 AppID，无法生成工程"}
    if not h5_url:
        return {"ok": False, "message": "缺少移动端 H5 站点地址，web-view 无法承载"}

    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    pages_dir = PROJECT_DIR / "pages" / "index"
    pages_dir.mkdir(parents=True, exist_ok=True)

    (PROJECT_DIR / "app.json").write_text(
        '{\n'
        '  "pages": ["pages/index/index"],\n'
        '  "window": {\n'
        '    "navigationBarTitleText": "智慧校园",\n'
        '    "navigationStyle": "custom",\n'
        '    "enablePullDownRefresh": false\n'
        '  },\n'
        '  "sitemapLocation": "sitemap.json"\n'
        '}\n',
        encoding="utf-8",
    )
    (PROJECT_DIR / "app.js").write_text("App({});\n", encoding="utf-8")
    (PROJECT_DIR / "app.wxss").write_text("page { height: 100%; }\n", encoding="utf-8")
    (PROJECT_DIR / "sitemap.json").write_text(
        '{\n  "desc": "关于本文件的更多信息，请参考文档 https://developers.weixin.qq.com/miniprogram/dev/framework/sitemap.html",\n'
        '  "rules": [{ "action": "allow", "page": "*" }]\n}\n',
        encoding="utf-8",
    )
    (PROJECT_DIR / "project.config.json").write_text(
        "{\n"
        f'  "appid": "{appid}",\n'
        f'  "projectname": "{project_name}",\n'
        '  "compileType": "miniprogram",\n'
        '  "miniprogramRoot": "./",\n'
        '  "libVersion": "3.5.0",\n'
        '  "setting": {\n'
        '    "urlCheck": false,\n'
        '    "es6": true,\n'
        '    "minified": true,\n'
        '    "postcss": true\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    (PROJECT_DIR / "project.private.config.json").write_text(
        '{\n  "projectname": "' + project_name + '",\n  "setting": { "compileHotReLoad": true }\n}\n',
        encoding="utf-8",
    )
    (pages_dir / "index.wxml").write_text(_INDEX_WXML, encoding="utf-8")
    (pages_dir / "index.js").write_text(
        "Page({\n"
        "  data: {\n"
        f"    url: {h5_url!r},\n"
        "  },\n"
        "  onLoad() {},\n"
        "  onMessage() {},\n"
        "});\n",
        encoding="utf-8",
    )
    (pages_dir / "index.json").write_text(
        '{ "usingComponents": {} }\n', encoding="utf-8"
    )
    (pages_dir / "index.wxss").write_text(
        "web-view { width: 100%; height: 100vh; }\n", encoding="utf-8"
    )

    files = sorted(
        str(p.relative_to(PROJECT_DIR)).replace("\\", "/")
        for p in PROJECT_DIR.rglob("*") if p.is_file()
    )
    return {
        "ok": True,
        "message": f"已生成小程序工程（{len(files)} 个文件）",
        "dir": str(PROJECT_DIR),
        "files": files,
    }


# ===== ③ 上传代码（miniprogram-ci）=====
def _write_upload_key(appid: str, upload_key: str) -> Path:
    """把代码上传密钥写入工程目录旁的临时文件，供 miniprogram-ci 使用。"""
    key_path = PROJECT_DIR / f"private.{appid}.key"
    key_path.write_text(upload_key, encoding="utf-8")
    return key_path


def upload_code(appid: str, upload_key: str, version: str = DEFAULT_VERSION,
                desc: str = "管理端一键部署", robot: int = 1, timeout: int = 300) -> dict:
    """调用 miniprogram-ci 上传代码。缺密钥 / 缺 Node 时降级为 pending，不抛异常。"""
    if not upload_key:
        return {
            "ok": False, "skipped": True,
            "message": "未配置「代码上传密钥」，无法自动上传；工程已生成，可手动导入微信开发者工具上传",
        }
    if not PROJECT_DIR.exists():
        return {"ok": False, "skipped": True, "message": "小程序工程尚未生成，请先执行「生成工程」"}

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        return {
            "ok": False, "skipped": True,
            "message": "后端未安装 Node.js/npm，无法运行 miniprogram-ci；工程已生成，请在本地用微信开发者工具上传",
        }

    key_path = _write_upload_key(appid, upload_key)
    cmd = [
        npx, "--yes", "miniprogram-ci", "upload",
        "--pp", str(PROJECT_DIR),
        "--pkp", str(key_path),
        "--appid", appid,
        "--uv", version,
        "--ud", desc,
        "--robot", str(robot),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "skipped": False, "message": f"上传超时（>{timeout}s），请检查网络或后端出口 IP 白名单"}
    except Exception as exc:
        return {"ok": False, "skipped": False, "message": f"执行上传命令失败：{exc}"}

    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        return {"ok": True, "message": "代码上传成功，已生成体验版（请在小程序后台设置为体验版）", "output": output[-2000:]}
    return {"ok": False, "skipped": False, "message": "代码上传失败，请查看日志", "output": output[-2000:]}


# ===== 汇总：部署链路状态（供前端展示）=====
def config_status(db: Session) -> dict:
    """返回配置完备度，供前端渲染「已配置 / 待配置」徽标与链路提示。"""
    cfg = load_config(db)
    return {
        "appid_configured": bool(cfg["appid"]),
        "appsecret_configured": bool(cfg["appsecret"]),
        "h5_url_configured": bool(cfg["h5_url"]),
        "upload_key_configured": bool(cfg["upload_key"]),
        "h5_url": cfg["h5_url"],
        "appid": cfg["appid"],
        "node_available": bool(shutil.which("npx") or shutil.which("npx.cmd")),
        "project_generated": PROJECT_DIR.exists(),
        "generated_at": (
            datetime.fromtimestamp(PROJECT_DIR.stat().st_mtime).isoformat()
            if PROJECT_DIR.exists() else None
        ),
    }